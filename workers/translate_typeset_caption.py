import os
import time
import gc
from pathlib import Path
from PySide6.QtCore import QThread, Signal

# 引入核心底层引擎
from core.translator import TranslatorEngine
from core.subtitle_writer import SubtitleWriter
from core.subtitle_parser import SubtitleParser  # 新增：专门负责归一化的解析器


class TranslateTypesetCaptionWorker(QThread):
    """
    第二阶段打工人：大语言模型翻译 Worker。
    职责：委托解析源文件 -> 唤醒 LLM -> 循环翻译 -> 格式化落盘 -> 强力清空显存。
    """

    # --- 双通道通信对讲机 ---
    log_signal = Signal(str, str)
    progress_signal = Signal(str, int, int, str)
    finished_signal = Signal(bool, str)

    def __init__(self, source_file_path: str, output_dir: str, target_langs: list,
                 file_formats: list, export_modes: list, parent=None):
        super().__init__(parent)
        self.source_file_path = source_file_path
        self.output_dir = output_dir
        self.target_langs = target_langs
        self.file_formats = file_formats
        self.export_modes = export_modes

        self.is_running = True

    def run(self):
        translator = None

        try:
            # ==========================================
            # 步骤 1：智能数据解析 (委托给专门的 SubtitleParser)
            # ==========================================
            self.log_signal.emit("[系统] 正在解析并归一化源字幕文件...", "info")

            # 核心改变：调用外部解析器，无论输入什么，都会安全返回标准字典列表
            segments = SubtitleParser.parse(self.source_file_path)

            if not segments:
                raise RuntimeError("源文件解析失败或内容为空。")

            # 提取源语言代号，Parser 已经保证了 language 字段必然存在
            detected_source_lang = segments[0].get("language", "auto")

            # ==========================================
            # 步骤 1.5：原声字幕的顺手生成
            # ==========================================
            if "original" in self.export_modes:
                self.log_signal.emit("[系统] 检测到纯原声需求，正在导出原声音轨...", "info")
                self._export_to_disk(segments, "orig", ["original"])
                self.log_signal.emit("[系统] 原声字幕导出完毕。", "success")

            # ==========================================
            # 步骤 2：判断是否需要启动翻译引擎
            # ==========================================
            needs_translation = "translated" in self.export_modes or "bilingual" in self.export_modes
            if not needs_translation or not self.target_langs:
                self.log_signal.emit("[系统] 无需大模型翻译任务，流程结束。", "success")
                self.finished_signal.emit(True, self.output_dir)
                return

            self.log_signal.emit("[系统] 正在唤醒大语言模型到显存...", "warning")
            translator = TranslatorEngine()

            # ==========================================
            # 步骤 3：多目标语言循环翻译与防抖
            # ==========================================
            total_langs = len(self.target_langs)

            for lang_idx, lang_code in enumerate(self.target_langs):
                self.log_signal.emit(f"[ALMA] 开始翻译目标语言 ({lang_idx + 1}/{total_langs}): {lang_code.upper()}",
                                     "highlight")

                translated_segments = []
                # 调用核心引擎的生成器
                generator = translator.translate_segments(
                    segments=segments,
                    target_lang=lang_code,
                    source_lang=detected_source_lang
                )

                for seg_idx, new_seg in enumerate(generator):
                    # 核心防抖与退出机制
                    if not self.is_running:
                        raise InterruptedError("用户手动中止了翻译任务")

                    translated_segments.append(new_seg)

                    # 复合进度条计算：(当前语言的基础百分比) + (当前句子的微观进度)
                    base_progress = (lang_idx / total_langs) * 100
                    seg_progress = new_seg.get("translation_progress", 0)
                    current_lang_progress = (seg_progress / 100.0) * (100 / total_langs)
                    total_progress = int(base_progress + current_lang_progress)

                    self.progress_signal.emit(f"[ALMA] {lang_code.upper()} 翻译进度", total_progress, 100, "highlight")

                # ==========================================
                # 步骤 4：当前语言成品格式化与落盘
                # ==========================================
                self._export_to_disk(translated_segments, lang_code, self.export_modes)

            self.progress_signal.emit("[ALMA] 所有翻译任务处理完成", 100, 100, "success")
            self.log_signal.emit("[系统] 翻译全流程执行完毕！", "success")
            self.finished_signal.emit(True, self.output_dir)

        except InterruptedError as e:
            self.log_signal.emit(f"[系统] {str(e)}", "error")
            self.finished_signal.emit(False, str(e))
        except Exception as e:
            self.log_signal.emit(f"[严重错误] 翻译阶段发生异常: {str(e)}", "error")
            self.finished_signal.emit(False, str(e))
        finally:
            # ==========================================
            # 步骤 5：打扫战场与显存物理释放
            # ==========================================
            self.log_signal.emit("[系统] 正在执行翻译引擎显存清理...", "warning")

            if translator:
                del translator

            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

            time.sleep(0.5)
            self.log_signal.emit("[系统] 翻译 Worker 生命周期终结。", "info")

    def _export_to_disk(self, segments_data: list, lang_code: str, active_modes: list):
        """内部辅助方法：对接 SubtitleWriter 执行按文件夹分类落盘"""
        media_name = Path(self.source_file_path).stem
        if media_name.startswith("raw_segments_"):
            media_name = media_name.replace("raw_segments_", "").rsplit("_", 1)[0]

        base_out_dir = Path(self.output_dir) / media_name

        folder_mapping = {
            "original": "Original_原声音轨",
            "translated": "Translated_纯译文轨",
            "bilingual": "Bilingual_双语字幕轨"
        }

        for fmt in self.file_formats:
            for mode in active_modes:
                # 逻辑过滤：当处理原声时，跳过纯译文/双语的生成；当处理翻译时，跳过纯原声的生成
                if mode == "original" and lang_code != "orig":
                    continue
                if mode in ["translated", "bilingual"] and lang_code == "orig":
                    continue

                folder_name = folder_mapping.get(mode, mode)
                format_folder_name = f"{folder_name}_{fmt.upper()}"

                target_dir = base_out_dir / format_folder_name
                target_dir.mkdir(parents=True, exist_ok=True)

                file_prefix = str(target_dir / media_name)

                SubtitleWriter.export_subtitles(
                    segments=segments_data,
                    output_prefix=file_prefix,
                    modes=[mode],
                    file_format=fmt,
                    lang_code=lang_code if lang_code != "orig" else "en"
                )
                self.log_signal.emit(f"[写入器] 已生成文件: {format_folder_name} -> [{lang_code}]", "info")

    def stop(self):
        self.is_running = False