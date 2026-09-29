import os
import time
from pathlib import Path
from PySide6.QtCore import QThread, Signal

# 导入你写好的核心底层引擎
from core.whisper_engine import WhisperEngine
from core.translator import TranslatorEngine
from core.subtitle_writer import SubtitleWriter
from core.audio_processor import extract_audio


class AITaskWorker(QThread):
    """
    真实的 AI 后台任务线程。
    负责调度 Whisper 和 Llama/ALMA，并将执行进度通过 Signal 安全传递给主线程 UI。
    """

    # 定义通讯信号
    log_signal = Signal(str, str)  # 发送日志 (内容, 级别: info/success/warning/error)
    dict_prog_signal = Signal(int)  # 听写进度 (0-100)
    trans_prog_signal = Signal(int)  # 翻译进度 (0-100)
    finished_signal = Signal(bool, str)  # 任务结束信号 (是否成功, 提示信息/路径)

    def __init__(self, config_data: dict, parent=None):
        super().__init__(parent)
        self.config = config_data

        # 解析前端传来的参数
        self.media_path = self.config.get("media_path", "")
        self.output_dir = self.config.get("output_dir", "")
        self.target_langs = self.config.get("target_langs", [])
        self.file_formats = self.config.get("file_formats", ["srt"])
        self.export_modes = self.config.get("export_modes", ["original", "translated", "bilingual"])

        self.is_running = True

    def run(self):
        """线程启动时自动执行的入口函数"""
        try:
            # ==========================================
            # 阶段 0：提取音频
            # ==========================================
            self.log_signal.emit(f"[系统] 正在从媒体文件中提取音频: {os.path.basename(self.media_path)}", "info")
            audio_output_path = os.path.join(self.output_dir, "temp_audio.wav")

            # 确保输出目录存在
            os.makedirs(self.output_dir, exist_ok=True)

            success, result_msg = extract_audio(self.media_path, audio_output_path)

            if not success:
                raise RuntimeError(result_msg)

            self.log_signal.emit("[系统] 音频提取成功，准备听写...", "success")

            # ==========================================
            # 第一阶段：Whisper 语音转写
            # ==========================================
            self.log_signal.emit("[系统] 初始化 Whisper 听写引擎...", "warning")
            whisper_engine = WhisperEngine()

            self.log_signal.emit("[Whisper] 正在处理提取的音频文件", "highlight")

            segments = []

            # 使用正确的生成器方法名称并处理 yield
            transcription_generator = whisper_engine.transcribe_audio(audio_output_path)

            for segment_data in transcription_generator:
                if not self.is_running:
                    self.log_signal.emit("[系统] 任务已手动中止！", "error")
                    return

                segments.append(segment_data)

                # 发送进度更新
                progress = int(segment_data.get("progress", 0))
                self.dict_prog_signal.emit(progress)
                # 可选：如果你想看到每一句听写的日志，取消注释下一行
                # self.log_signal.emit(f"[Whisper] 识别: {segment_data.get('text', '')}", "info")

            if not segments:
                raise RuntimeError("Whisper 引擎未能从媒体文件中提取出任何有效文本，请检查视频是否有声音。")

            self.dict_prog_signal.emit(100)
            self.log_signal.emit(f"[Whisper] 听写完成！共提取 {len(segments)} 个字幕段落。", "success")

            # 可选：清理临时音频文件
            try:
                os.remove(audio_output_path)
            except Exception as e:
                self.log_signal.emit(f"[警告] 无法删除临时音频文件: {e}", "warning")
            # ==========================================
            # 【新增核心修复】：暴力释放 Whisper 显存，为大模型腾出空间
            # ==========================================
            self.log_signal.emit("[系统] 正在卸载 Whisper 模型并清空显存...", "warning")
            del whisper_engine  # 斩断对象的引用
            import gc
            gc.collect()  # 强制 Python 立即回收内存
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()  # 强制 PyTorch 清空显卡缓存碎片
            time.sleep(1)  # 稍微停顿，给显卡一点时间完成物理释放
            self.log_signal.emit("[系统] 显存已腾空，准备无缝接力...", "success")
            # ==========================================
            # 第二阶段：目标语言循环翻译
            # ==========================================
            needs_translation = "translated" in self.export_modes or "bilingual" in self.export_modes

            if needs_translation and self.target_langs:
                self.log_signal.emit("[系统] 正在唤醒本地大语言模型...", "warning")
                translator = TranslatorEngine()

                total_langs = len(self.target_langs)

                # 按照用户勾选的多语种，循环进行翻译
                for lang_idx, lang_info in enumerate(self.target_langs):
                    lang_code = lang_info['code']
                    lang_name = lang_info['name']

                    self.log_signal.emit(f"[ALMA] 开始翻译目标语言 ({lang_idx + 1}/{total_langs}): {lang_name}",
                                         "highlight")

                    translated_segments = []

                    # 使用生成器方法逐句翻译
                    generator = translator.translate_segments(segments, target_lang=lang_name)

                    for seg_idx, new_seg in enumerate(generator):
                        if not self.is_running:
                            self.log_signal.emit("[系统] 任务已手动中止！", "error")
                            return

                        # 收集翻译完成的单句字典
                        translated_segments.append(new_seg)

                        # 计算综合进度条
                        base_progress = (lang_idx / total_langs) * 100
                        seg_progress = new_seg.get("translation_progress", 0)
                        current_lang_progress = (seg_progress / 100.0) * (100 / total_langs)

                        self.trans_prog_signal.emit(int(base_progress + current_lang_progress))
                        self.log_signal.emit(f"[ALMA] 正在翻译第 {seg_idx + 1} 句...", "info")

                    # 当前语种翻译完毕，导出字幕文件
                    self._export_files(translated_segments, lang_code)

            else:
                # 仅导出原文的情况
                self.trans_prog_signal.emit(100)
                self._export_files(segments, lang_code="orig")

            # ==========================================
            # 任务圆满结束
            # ==========================================
            self.log_signal.emit("[系统] 所有处理流程执行完毕！", "success")
            self.finished_signal.emit(True, self.output_dir)

        except Exception as e:
            # 捕获异常，防止软件闪退
            self.log_signal.emit(f"[严重错误] 执行中发生异常: {str(e)}", "error")
            self.finished_signal.emit(False, str(e))

    def _export_files(self, segments_data: list, lang_code: str):
        """
        根据用途和格式创建嵌套文件夹，并调用 SubtitleWriter 落盘。
        """
        video_name = Path(self.media_path).stem
        if not video_name:
            video_name = "Untitled_Media"

        base_out_dir = Path(self.output_dir) / video_name

        folder_mapping = {
            "original": "Original_原声音轨",
            "translated": "Translated_纯译文轨",
            "bilingual": "Bilingual_双语字幕轨"
        }

        for fmt in self.file_formats:
            for mode in self.export_modes:
                # 逻辑过滤
                if mode == "original" and lang_code != "orig":
                    continue
                if mode in ["translated", "bilingual"] and lang_code == "orig":
                    continue

                folder_name = folder_mapping.get(mode, mode)
                format_folder_name = f"{folder_name}_{fmt.upper()}"

                target_dir = base_out_dir / format_folder_name
                target_dir.mkdir(parents=True, exist_ok=True)

                file_prefix = str(target_dir / video_name)

                SubtitleWriter.export_subtitles(
                    segments=segments_data,
                    output_prefix=file_prefix,
                    modes=[mode],
                    file_format=fmt,
                    lang_code=lang_code if lang_code != "orig" else "en"
                )

                self.log_signal.emit(f"[写入器] 已生成: {format_folder_name} -> [{lang_code}]", "info")

    def stop(self):
        """提供给界面的强制停止接口"""
        self.is_running = False