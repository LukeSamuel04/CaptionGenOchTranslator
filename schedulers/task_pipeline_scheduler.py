import os
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from PySide6.QtCore import QObject, Signal

# 导入我们的两个底层打工人
from workers.audio_to_caption import AudioToCaptionWorker
from workers.translate_typeset_caption import TranslateTypesetCaptionWorker


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
# 步骤 2：重构后的工业级调度器
# ==========================================
class TaskPipelineScheduler(QObject):
    """
    全局任务流水线调度器（总包工头）。
    职责：
    1. 显式路由：严格按照外部传入的 TaskMode 指令执行，绝不猜测用户意图。
    2. 信号中转：将底层 Worker 的日志和进度信号无缝透传给主 UI。
    3. 接力控制：在步骤 1 成功后，根据指令决定是否将 JSON 缓存路径喂给步骤 2。
    4. 全局刹车：精准打断当前正在运行的任何子任务。
    """

    # --- 统一对外（UI 界面）发射的信号中转站 ---
    log_relay = Signal(str, str)
    progress_relay = Signal(str, int, int, str)
    pipeline_finished = Signal(bool, str)

    def __init__(self, task_mode: TaskMode, config: TaskConfig, parent=None):
        super().__init__(parent)

        # 接收明确的指令和参数包裹
        self.task_mode = task_mode
        self.config = config

        # 维护 Worker 实例的状态指针
        self.worker1 = None
        self.worker2 = None

        # 流程控制锁
        self._is_cancelled = False

    def start_pipeline(self):
        """核心入口：瞎子执行官，只看指令不看文件"""
        self._is_cancelled = False

        self.log_relay.emit(f"[调度器] 收到系统明确指令: {self.task_mode.name}，正在装载对应流水线...", "info")

        # 严格按照显式指令路由
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
    # 步骤 1：语音提取与听写
    # ==========================================
    def _start_step1(self):
        if self._is_cancelled:
            return

        self.log_relay.emit("\n" + "=" * 40 + "\n[阶段 1/2] 语音识别与时间轴生成\n" + "=" * 40, "info")

        self.worker1 = AudioToCaptionWorker(
            media_path=self.config.input_path,
            cache_dir=self.config.cache_dir
        )

        # 信号对接
        self.worker1.log_signal.connect(self.log_relay.emit)
        self.worker1.progress_signal.connect(self.progress_relay.emit)
        self.worker1.finished_signal.connect(self._on_step1_finished)

        self.worker1.start()

    def _on_step1_finished(self, success: bool, message: str):
        # 彻底清理指针，防止内存泄漏
        self.worker1.deleteLater()
        self.worker1 = None

        if not success:
            # 步骤 1 失败（报错或被取消），整条流水线崩溃终止
            self.pipeline_finished.emit(False, f"语音识别阶段终止: {message}")
            return

        if self._is_cancelled:
            self.pipeline_finished.emit(False, "流水线已被强制中断。")
            return

        # 步骤 1 成功，message 此时就是极其精确的 JSON 缓存绝对路径
        json_cache_path = message

        # 指令分流：如果用户只需要听写，任务到此结束
        if self.task_mode == TaskMode.TRANSCRIBE_ONLY:
            self.log_relay.emit(f"[调度器] 仅听写任务已圆满完成！JSON缓存已生成: {Path(json_cache_path).name}",
                                "success")
            self.pipeline_finished.emit(True, json_cache_path)

        # 否则，继续执行翻译排版
        else:
            self.log_relay.emit(f"[调度器] 第一阶段顺利竣工！准备物理交接文件: {Path(json_cache_path).name}", "success")
            self._start_step2(json_cache_path)

    # ==========================================
    # 步骤 2：翻译与排版落盘
    # ==========================================
    def _start_step2(self, source_text_path: str):
        if self._is_cancelled:
            return

        self.log_relay.emit("\n" + "=" * 40 + "\n[阶段 2/2] AI 翻译与排版落盘\n" + "=" * 40, "info")

        self.worker2 = TranslateTypesetCaptionWorker(
            source_file_path=source_text_path,
            output_dir=self.config.output_dir,
            target_langs=self.config.target_langs,
            file_formats=self.config.file_formats,
            export_modes=self.config.export_modes
        )

        # 信号对接
        self.worker2.log_signal.connect(self.log_relay.emit)
        self.worker2.progress_signal.connect(self.progress_relay.emit)
        self.worker2.finished_signal.connect(self._on_step2_finished)

        self.worker2.start()

    def _on_step2_finished(self, success: bool, message: str):
        self.worker2.deleteLater()
        self.worker2 = None

        if not success:
            self.pipeline_finished.emit(False, f"翻译排版阶段终止: {message}")
        else:
            self.log_relay.emit("\n🎉 [调度器] 全部流水线任务圆满完成！", "success")
            self.pipeline_finished.emit(True, message)

    # ==========================================
    # 全局控制接口
    # ==========================================
    def stop_pipeline(self):
        """精准打断当前正在执行的任务环节"""
        self._is_cancelled = True
        self.log_relay.emit("[调度器] 收到紧急终止指令，正在拦截流水线并清理底层资源...", "warning")

        # 谁在干活，就让谁停下
        if self.worker1 and self.worker1.isRunning():
            self.worker1.stop()
        elif self.worker2 and self.worker2.isRunning():
            self.worker2.stop()