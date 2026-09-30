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
    """

    log_signal = Signal(str, str)
    dict_prog_signal = Signal(int)
    trans_prog_signal = Signal(int)
    finished_signal = Signal(bool, str)

    def __init__(self, config_data: dict, parent=None):
        super().__init__(parent)
        self.config = config_data

        self.media_path = self.config.get("media_path", "")
        self.output_dir = self.config.get("output_dir", "")
        self.target_langs = self.config.get("target_langs", [])
        self.file_formats = self.config.get("file_formats", ["srt"])
        self.export_modes = self.config.get("export_modes", ["original", "translated", "bilingual"])

        self.is_running = True

    def run(self):
        try:
            # ==========================================
            # 阶段 0：提取音频
            # ==========================================
            self.log_signal.emit(f"[系统] 正在从媒体文件中提取音频: {os.path.basename(self.media_path)}", "info")
            audio_output_path = os.path.join(self.output_dir, "temp_audio.wav")

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
            transcription_generator = whisper_engine.transcribe_audio(audio_output_path)

            for segment_data in transcription_generator:
                if not self.is_running:
                    self.log_signal.emit("[系统] 任务已手动中止！", "error")
                    return

                segments.append(segment_data)

                progress = int(segment_data.get("progress", 0))
                self.dict_prog_signal.emit(progress)

            if not segments:
                raise RuntimeError("Whisper 引擎未能从媒体文件中提取出任何有效文本，请检查视频是否有声音。")

            self.dict_prog_signal.emit(100)
            self.log_signal.emit(f"[Whisper] 听写完成！共提取 {len(segments)} 个字幕段落。", "success")

            try:
                os.remove(audio_output_path)
            except Exception as e:
                self.log_signal.emit(f"[警告] 无法删除临时音频文件: {e}", "warning")

            # ==========================================
            # 【新增中间拦截检查点】：强制保存原始听写文件用于独立 Debug
            # ==========================================
            self.log_signal.emit("[系统] 正在导出第一阶段原始听写字幕 (诊断专用)...", "info")
            debug_out_prefix = os.path.join(self.output_dir, f"【诊断专用】原始听写_{Path(self.media_path).stem}")
            try:
                SubtitleWriter.export_subtitles(
                    segments=segments,
                    output_prefix=debug_out_prefix,
                    modes=["original"],
                    file_format="srt",
                    lang_code="orig"
                )
                self.log_signal.emit(f"[系统] 原始字幕已落盘，随时可双击核对！", "success")
            except Exception as e:
                self.log_signal.emit(f"[警告] 诊断字幕导出失败，但不影响主流程: {e}", "warning")

            # ==========================================
            # 暴力释放 Whisper 显存，为大模型腾出空间
            # ==========================================
            self.log_signal.emit("[系统] 正在卸载 Whisper 模型并清空显存...", "warning")
            del whisper_engine
            import gc
            gc.collect()
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            time.sleep(1)
            self.log_signal.emit("[系统] 显存已腾空，准备无缝接力...", "success")

            # ==========================================
            # 第二阶段：目标语言循环翻译
            # ==========================================
            needs_translation = "translated" in self.export_modes or "bilingual" in self.export_modes

            if needs_translation and self.target_langs:
                self.log_signal.emit("[系统] 正在唤醒本地大语言模型...", "warning")
                translator = TranslatorEngine()

                total_langs = len(self.target_langs)

                # 【新增逻辑】：从 Whisper 生成的 segments 中提取全局源语言代号
                detected_source_lang = segments[0].get("language", "auto") if segments else "auto"

                # 【核心修复】：直接将遍历出来的字符串当做 lang_code 使用
                for lang_idx, lang_code in enumerate(self.target_langs):

                    self.log_signal.emit(f"[ALMA] 开始翻译目标语言 ({lang_idx + 1}/{total_langs}): {lang_code.upper()}", "highlight")

                    translated_segments = []
                    # 直接将纯净的代号传递给 translator，并加入 source_lang 参数
                    generator = translator.translate_segments(
                        segments,
                        target_lang=lang_code,
                        source_lang=detected_source_lang
                    )

                    for seg_idx, new_seg in enumerate(generator):
                        if not self.is_running:
                            self.log_signal.emit("[系统] 任务已手动中止！", "error")
                            return

                        translated_segments.append(new_seg)

                        base_progress = (lang_idx / total_langs) * 100
                        seg_progress = new_seg.get("translation_progress", 0)
                        current_lang_progress = (seg_progress / 100.0) * (100 / total_langs)

                        self.trans_prog_signal.emit(int(base_progress + current_lang_progress))
                        self.log_signal.emit(f"[ALMA] 正在翻译第 {seg_idx + 1} 句...", "info")

                    self._export_files(translated_segments, lang_code)

            else:
                self.trans_prog_signal.emit(100)
                self._export_files(segments, lang_code="orig")

            # ==========================================
            # 任务圆满结束
            # ==========================================
            self.log_signal.emit("[系统] 所有处理流程执行完毕！", "success")
            self.finished_signal.emit(True, self.output_dir)

        except Exception as e:
            self.log_signal.emit(f"[严重错误] 执行中发生异常: {str(e)}", "error")
            self.finished_signal.emit(False, str(e))

    def _export_files(self, segments_data: list, lang_code: str):
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
        self.is_running = False