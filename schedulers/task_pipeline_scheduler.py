import os
import multiprocessing
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from PySide6.QtCore import QObject, Signal

# 导入跨进程对讲机 (前台监听员)
from core.ipc_listener import IPCListener

# 导入我们刚刚重构好的纯 Python 独立函数 (非类)
from workers.audio_to_caption import run_audio_to_caption_process
from workers.translate_typeset_caption import run_translate_typeset_process


# ==========================================
# 步骤 1：定义任务枚举与数据契约
# ==========================================
class TaskMode(Enum):
    """明确的任务执行指令枚举"""
    FULL_PIPELINE = "full_pipeline"  # 全自动：语音提取 -> 听写 -> 翻译 -> 排版
    TRANSLATE_ONLY = "translate_only"  # 仅翻译排版：外挂字幕 -> 翻译 -> 排版
    TRANSCRIBE_ONLY = "transcribe_only"  # 仅提取听写：语音提取 -> 听写 (不触发排版)


@dataclass
class TaskConfig:
    """全局任务配置包裹 (Payload)"""
    input_path: str
    output_dir: str
    target_langs: list
    file_formats: list
    export_modes: list
    cache_dir: str


# ==========================================
# 步骤 2：多进程工业级调度器
# ==========================================
class TaskPipelineScheduler(QObject):
    """
    全新多进程全局调度器（总包工头）。
    职责：
    1. 进程孵化：通过 multiprocessing.Process 启动隔离的 AI 任务。
    2. 通讯桥接：配置 Queue 并挂载 IPCListener 监听底层汇报。
    3. 物理强杀：通过 process.terminate() 实现瞬间系统级内存回收。
    """

    # --- 统一对外（UI 界面）发射的信号中转站 ---
    log_relay = Signal(str, str)
    progress_relay = Signal(str, int, int, str)
    pipeline_finished = Signal(bool, str)

    def __init__(self, task_mode: TaskMode, config: TaskConfig, parent=None):
        super().__init__(parent)
        self.task_mode = task_mode
        self.config = config

        # 多进程核心控制器
        self.active_process = None
        self.ipc_queue = None
        self.active_listener = None

        self._is_cancelled = False

    def start_pipeline(self):
        """核心入口：瞎子执行官，只看指令不看文件"""
        self._is_cancelled = False
        self.log_relay.emit(f"[调度器] 收到系统明确指令: {self.task_mode.name}，正在装载多进程流水线...", "info")

        if self.task_mode == TaskMode.FULL_PIPELINE:
            self._start_step1()
        elif self.task_mode == TaskMode.TRANSLATE_ONLY:
            self._start_step2(self.config.input_path)
        elif self.task_mode == TaskMode.TRANSCRIBE_ONLY:
            self._start_step1()
        else:
            self.log_relay.emit(f"[严重错误] 调度器收到未知指令: {self.task_mode}", "error")
            self.pipeline_finished.emit(False, "未知的任务路由指令")

    # ==========================================
    # 核心进程启动与环境清理工具
    # ==========================================
    def _cleanup_current_process(self):
        """物理打扫战场，准备迎接下一个子进程"""
        if self.active_listener:
            self.active_listener.stop()
            self.active_listener.deleteLater()
            self.active_listener = None

        if self.active_process:
            if self.active_process.is_alive():
                self.active_process.terminate()
                self.active_process.join(timeout=1)
            self.active_process = None

        if self.ipc_queue:
            self.ipc_queue.close()
            self.ipc_queue = None

    # ==========================================
    # 步骤 1：语音提取与听写 (启动独立子进程)
    # ==========================================
    def _start_step1(self):
        if self._is_cancelled:
            return

        self.log_relay.emit("\n" + "=" * 40 + "\n[阶段 1/2] 语音识别与时间轴生成 (隔离运行)\n" + "=" * 40, "info")

        self._cleanup_current_process()
        self.ipc_queue = multiprocessing.Queue()

        # 挂载前线监听员
        self.active_listener = IPCListener(self.ipc_queue)
        self.active_listener.log_relay.connect(self.log_relay.emit)
        # 闭包转发进度，适配旧版 4 参数的 progress_relay 契约
        self.active_listener.progress_relay.connect(
            lambda v: self.progress_relay.emit("[Whisper] 听写进度", v, 100, "highlight")
        )
        self.active_listener.step_finished.connect(self._on_step1_finished)

        # 派发参数，启动物理隔离的纯 Python 函数
        args = (self.config.input_path, self.config.cache_dir, self.ipc_queue)
        self.active_process = multiprocessing.Process(target=run_audio_to_caption_process, args=args)

        self.active_listener.start()
        self.active_process.start()

    def _on_step1_finished(self, success: bool, message: str):
        if not success:
            self.pipeline_finished.emit(False, f"语音识别阶段终止: {message}")
            return

        if self._is_cancelled:
            self.pipeline_finished.emit(False, "流水线已被强制中断。")
            return

        json_cache_path = message

        if self.task_mode == TaskMode.TRANSCRIBE_ONLY:
            self.log_relay.emit(f"[调度器] 仅听写任务已圆满完成！JSON缓存: {Path(json_cache_path).name}", "success")
            self.pipeline_finished.emit(True, json_cache_path)
        else:
            self.log_relay.emit(f"[调度器] 听写阶段竣工！进程已物理销毁，显卡 0 占用。秒接翻译阶段...", "warning")
            # 告别定时器，因为进程级资源回收是瞬间完成的！
            self._start_step2(json_cache_path)

    # ==========================================
    # 步骤 2：翻译与排版落盘 (启动独立子进程)
    # ==========================================
    def _start_step2(self, source_text_path: str):
        if self._is_cancelled:
            return

        self.log_relay.emit("\n" + "=" * 40 + "\n[阶段 2/2] AI 翻译与排版落盘 (隔离运行)\n" + "=" * 40, "info")

        self._cleanup_current_process()
        self.ipc_queue = multiprocessing.Queue()

        self.active_listener = IPCListener(self.ipc_queue)
        self.active_listener.log_relay.connect(self.log_relay.emit)
        self.active_listener.progress_relay.connect(
            lambda v: self.progress_relay.emit("[ALMA] 翻译排版进度", v, 100, "highlight")
        )
        self.active_listener.step_finished.connect(self._on_step2_finished)

        args = (
            source_text_path,
            self.config.output_dir,
            self.config.target_langs,
            self.config.file_formats,
            self.config.export_modes,
            self.ipc_queue
        )
        self.active_process = multiprocessing.Process(target=run_translate_typeset_process, args=args)

        self.active_listener.start()
        self.active_process.start()

    def _on_step2_finished(self, success: bool, message: str):
        self._cleanup_current_process()

        if not success:
            self.pipeline_finished.emit(False, f"翻译排版阶段终止: {message}")
        else:
            self.log_relay.emit("\n🎉 [调度器] 全部流水线任务圆满完成！", "success")
            self.pipeline_finished.emit(True, message)

    # ==========================================
    # 全局控制接口
    # ==========================================
    def stop_pipeline(self):
        """物理强杀：不谈判，不等待，直接通知操作系统切断电源"""
        self._is_cancelled = True
        self.log_relay.emit("[调度器] 收到紧急终止指令！正在执行操作系统级进程强杀...", "error")

        self._cleanup_current_process()
        self.pipeline_finished.emit(False, "任务已被用户强行终止。系统资源已彻底释放。")