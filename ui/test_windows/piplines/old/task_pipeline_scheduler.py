import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QMessageBox, QComboBox, QLabel)
from PySide6.QtCore import Qt, QThread, Signal

from ui.components_new.containers.white_translucent_container import WhiteTranslucentContainer
from ui.components_new.log_field.blue_logfield import LogPreviewPanel
from ui.components_new.buttons.rounded_blue_button import RoundedButton

from schedulers.task_pipeline_scheduler import TaskPipelineScheduler, TaskMode, TaskConfig


# ==========================================
# 1. 定义 Mock (模拟) 打工人
# 它们长得和真实 Worker 一模一样，拥有完全一致的信号，但内部只做简单的 sleep 和发信号
# ==========================================
class MockAudioWorker(QThread):
    log_signal = Signal(str, str)
    progress_signal = Signal(str, int, int, str)
    finished_signal = Signal(bool, str)

    def __init__(self, media_path, cache_dir, parent=None):
        super().__init__(parent)
        self.media_path = media_path
        self._is_running = True

    def run(self):
        self.log_signal.emit(f"[Mock 听写] 开始模拟提取: {os.path.basename(self.media_path)}", "info")
        for i in range(1, 101, 20):
            if not self._is_running:
                self.log_signal.emit("[Mock 听写] 任务已被模拟打断！", "warning")
                self.finished_signal.emit(False, "用户手动取消")
                return
            self.progress_signal.emit("[Mock 听写] 进度", i, 100, "highlight")
            self.msleep(300)  # 模拟耗时 300 毫秒

        self.log_signal.emit("[Mock 听写] 模拟听写完成！", "success")
        # 伪造一个 JSON 缓存路径交接给下一步
        self.finished_signal.emit(True, "mock_cache/raw_segments_mock_123.json")

    def stop(self):
        self._is_running = False


class MockTranslateWorker(QThread):
    log_signal = Signal(str, str)
    progress_signal = Signal(str, int, int, str)
    finished_signal = Signal(bool, str)

    def __init__(self, source_file_path, output_dir, target_langs, file_formats, export_modes, parent=None):
        super().__init__(parent)
        self.source_file_path = source_file_path
        self._is_running = True

    def run(self):
        self.log_signal.emit(f"[Mock 翻译] 接收到上游文件: {os.path.basename(self.source_file_path)}", "info")
        self.log_signal.emit("[Mock 翻译] 假装正在唤醒大模型...", "warning")

        for i in range(1, 101, 25):
            if not self._is_running:
                self.log_signal.emit("[Mock 翻译] 任务已被模拟打断！", "warning")
                self.finished_signal.emit(False, "用户手动取消")
                return
            self.progress_signal.emit("[Mock 翻译] 进度", i, 100, "highlight")
            self.msleep(400)

        self.log_signal.emit("[Mock 翻译] 模拟排版与落盘完成！", "success")
        self.finished_signal.emit(True, "mock_output_dir/Final_Subtitles")

    def stop(self):
        self._is_running = False


# ==========================================
# 2. 核心魔法：Monkey Patching (偷梁换柱)
# 将 Scheduler 内部导入的真实 Worker 替换为我们的 Mock Worker
# ==========================================
import schedulers.task_pipeline_scheduler as tps_module

tps_module.AudioToCaptionWorker = MockAudioWorker
tps_module.TranslateTypesetCaptionWorker = MockTranslateWorker


# ==========================================
# 3. 调度器测试窗口 UI
# ==========================================
class SchedulerTestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("沙盒测试 - 工业级 Scheduler (Mock 模式)")
        self.resize(750, 600)

        self.setStyleSheet("""
            SchedulerTestWindow {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                                  stop:0 #E8F0F6, stop:1 #D2E0EB);
            }
        """)

        self.scheduler = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)

        self.glass_container = WhiteTranslucentContainer()

        # --- 顶部：指令选择区 ---
        mode_layout = QHBoxLayout()
        mode_label = QLabel("明确的任务指令 (Task Mode):")
        mode_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.combo_mode = QComboBox()
        self.combo_mode.addItem("全自动音视频翻译 (FULL_PIPELINE)", TaskMode.FULL_PIPELINE)
        self.combo_mode.addItem("仅外挂字幕翻译 (TRANSLATE_ONLY)", TaskMode.TRANSLATE_ONLY)
        self.combo_mode.addItem("仅提取原声听写 (TRANSCRIBE_ONLY)", TaskMode.TRANSCRIBE_ONLY)
        self.combo_mode.setStyleSheet("padding: 5px; font-size: 13px; border-radius: 4px;")

        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.combo_mode, stretch=1)
        self.glass_container.add_layout(mode_layout)

        # --- 中部：日志监控面板 ---
        self.log_panel = LogPreviewPanel(title="Scheduler 调度总控台日志", max_lines=500)
        self.glass_container.add_widget(self.log_panel, stretch=1)

        # --- 底部：控制按钮 ---
        btn_layout = QHBoxLayout()
        self.btn_start = RoundedButton("🚀 发送指令并执行", "primary")
        self.btn_cancel = RoundedButton("⏹ 紧急全局刹车", "danger")
        self.btn_cancel.setEnabled(False)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_cancel)

        self.glass_container.add_layout(btn_layout)
        main_layout.addWidget(self.glass_container)

        self.btn_start.clicked.connect(self._on_start_clicked)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)

        self.log_panel.append_log(">>> 调度器测试沙盒已启动。", "info")
        self.log_panel.append_log(">>> 底层耗时 Worker 已被 Mock 替换，测试过程不会消耗显存。", "success")

    def _on_start_clicked(self):
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.log_panel.clear_logs()

        # 1. 提取指令
        selected_mode = self.combo_mode.currentData()

        # 2. 伪造静态数据契约 (Payload)
        mock_config = TaskConfig(
            input_path="mock_folder/test_video.mp4" if selected_mode != TaskMode.TRANSLATE_ONLY else "mock_folder/external_sub.srt",
            output_dir="mock_folder/outputs",
            target_langs=["zh"],
            file_formats=["srt"],
            export_modes=["bilingual"],
            cache_dir="mock_folder/.cache"
        )

        # 3. 实例化调度器
        self.scheduler = TaskPipelineScheduler(
            task_mode=selected_mode,
            config=mock_config
        )

        # 4. 连接信号中转站
        self.scheduler.log_relay.connect(self.log_panel.append_log)
        self.scheduler.progress_relay.connect(self.log_panel.update_progress_line)
        self.scheduler.pipeline_finished.connect(self._on_pipeline_finished)

        # 5. 执行指令
        self.scheduler.start_pipeline()

    def _on_cancel_clicked(self):
        if self.scheduler:
            self.btn_cancel.setEnabled(False)
            self.scheduler.stop_pipeline()

    def _on_pipeline_finished(self, success: bool, message: str):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if success:
            self.log_panel.append_log(f"\n✅ 测试成功！流水线按指令完美跑通，最终产物: {message}", "success")
        else:
            self.log_panel.append_log(f"\n❌ 测试终止或失败，反馈信息: {message}", "error")