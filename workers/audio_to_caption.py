import os
import json
import time
import gc
from pathlib import Path
from PySide6.QtCore import QThread, Signal

# 引入核心底层引擎
from core.whisper_engine import WhisperEngine
from core.audio_processor import extract_audio


class AudioToCaptionWorker(QThread):
    """
    第一阶段打工人：纯听写 Worker。
    职责：剥离音频 -> Whisper 听写 -> 导出 JSON -> 强力清空显存。
    绝对不干涉 UI 展示，不负责最终字幕排版。
    """

    # --- 双通道通信对讲机 ---
    # 普通日志信号：(文本内容, 颜色级别)
    log_signal = Signal(str, str)
    # 极客进度条信号：(前缀文本, 当前进度, 总进度, 颜色级别)
    progress_signal = Signal(str, int, int, str)
    # 任务完结/交接信号：(是否成功, 生成的 JSON 路径或错误信息)
    finished_signal = Signal(bool, str)

    def __init__(self, media_path: str, cache_dir: str, parent=None):
        super().__init__(parent)
        self.media_path = media_path
        self.cache_dir = cache_dir
        self.is_running = True

    def run(self):
        # 预先定义引擎变量，方便在 finally 中清理
        whisper_engine = None
        temp_audio_path = None

        try:
            # ==========================================
            # 步骤 1：准备工作与音频剥离
            # ==========================================
            os.makedirs(self.cache_dir, exist_ok=True)
            temp_audio_path = os.path.join(self.cache_dir, "temp_extract_audio.wav")

            media_name = Path(self.media_path).name
            self.log_signal.emit(f"[系统] 开始处理媒体文件: {media_name}", "info")
            self.log_signal.emit("[系统] 正在抽离音频流...", "warning")

            success, result_msg = extract_audio(self.media_path, temp_audio_path)
            if not success:
                raise RuntimeError(f"音频提取失败: {result_msg}")

            self.log_signal.emit("[系统] 音频抽离成功，准备载入听写引擎。", "success")

            # ==========================================
            # 步骤 2：加载 Whisper 引擎并执行听写
            # ==========================================
            self.log_signal.emit("[系统] 正在载入 Whisper AI 模型到显存...", "warning")
            whisper_engine = WhisperEngine()

            segments = []
            transcription_generator = whisper_engine.transcribe_audio(temp_audio_path)

            for segment_data in transcription_generator:
                # 核心防抖与退出机制：检测到取消信号，直接抛出异常打断
                if not self.is_running:
                    raise InterruptedError("用户手动中止了听写任务")

                segments.append(segment_data)

                # 将底层返回的 0-100 进度百分比，通过专属通道发送给 UI 画图
                progress = int(segment_data.get("progress", 0))
                self.progress_signal.emit("[Whisper] 正在听写音频时间轴", progress, 100, "highlight")

            if not segments:
                raise RuntimeError("未提取到任何有效语音，请检查视频是否静音。")

            # 确保进度条走到 100%
            self.progress_signal.emit("[Whisper] 正在听写音频时间轴", 100, 100, "success")
            self.log_signal.emit(f"[Whisper] 听写完成！共解析 {len(segments)} 句话。", "success")

            # ==========================================
            # 步骤 3：数据无损序列化落盘 (JSON 接力棒)
            # ==========================================
            video_stem = Path(self.media_path).stem
            json_filename = f"raw_segments_{video_stem}_{int(time.time())}.json"
            json_cache_path = os.path.join(self.cache_dir, json_filename)

            with open(json_cache_path, "w", encoding="utf-8") as f:
                json.dump(segments, f, ensure_ascii=False, indent=2)

            self.log_signal.emit("[系统] 听写数据已缓存，准备打扫战场...", "info")

            # ==========================================
            # 步骤 4：任务圆满交接
            # ==========================================
            self.finished_signal.emit(True, json_cache_path)

        except InterruptedError as e:
            self.log_signal.emit(f"[系统] {str(e)}", "error")
            self.finished_signal.emit(False, str(e))
        except Exception as e:
            self.log_signal.emit(f"[严重错误] 听写阶段发生异常: {str(e)}", "error")
            self.finished_signal.emit(False, str(e))
        finally:
            # ==========================================
            # 步骤 5：极其严苛的硬件资源强制回收
            # ==========================================
            self.log_signal.emit("[系统] 正在执行硬件级显存清理...", "warning")

            # 1. 删掉占硬盘的临时音频
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except Exception:
                    pass

            # 2. 彻底销毁模型实例
            if whisper_engine:
                del whisper_engine

            # 3. 强制 Python 和 PyTorch 回收显存
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

            # 稍作停顿，确保显存释放的系统指令生效
            time.sleep(0.5)
            self.log_signal.emit("[系统] 底层清理完毕，当前 Worker 生命周期终结。", "info")

    def stop(self):
        """外部调用接口：通知线程安全退出"""
        self.is_running = False