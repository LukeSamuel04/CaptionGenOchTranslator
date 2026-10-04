import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QMessageBox, QComboBox, QLabel)

# 导入白蓝极简风组件
from ui.components_new.containers.white_translucent_container import WhiteTranslucentContainer
from ui.components_new.log_field.blue_logfield import LogPreviewPanel
from ui.components_new.buttons.rounded_blue_button import RoundedButton

# 导入全新的多进程调度器
from schedulers.task_pipeline_scheduler import TaskPipelineScheduler, TaskMode, TaskConfig

# 为了方便测试，我们借用一下之前的组件
from ui.components_new.file_browsers.blue_file_browser import FileBrowseWidget


# ==========================================
# 工业级多进程调度器 测试沙盒
# ==========================================
class SchedulerTestWindow(QWidget):
    """
    现在，这个窗口不仅是一个沙盒，更是一个直接挂载真实多进程大模型的发射台。
    彻底删除了所有的 Mock 伪造类。
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("沙盒测试 - 真实多进程引擎 (Scheduler)")
        self.resize(800, 650)

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

        # ==========================================
        # 1. 顶部：输入配置区
        # ==========================================
        # 1.1 指令选择
        mode_layout = QHBoxLayout()
        mode_label = QLabel("任务指令 (Task Mode):")
        mode_label.setStyleSheet("font-weight: bold; font-size: 13px;")

        self.combo_mode = QComboBox()
        self.combo_mode.addItem("全自动音视频翻译 (FULL_PIPELINE)", TaskMode.FULL_PIPELINE)
        self.combo_mode.addItem("仅翻译纯文本字幕 (TRANSLATE_ONLY)", TaskMode.TRANSLATE_ONLY)
        self.combo_mode.addItem("仅提取原声听写 (TRANSCRIBE_ONLY)", TaskMode.TRANSCRIBE_ONLY)
        self.combo_mode.setStyleSheet("padding: 5px; font-size: 13px; border-radius: 4px;")

        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.combo_mode, stretch=1)
        self.glass_container.add_layout(mode_layout)

        # 1.2 真实文件路径选择
        self.file_browser = FileBrowseWidget(
            label_text="输入文件 (音视频 或 .json/.srt)",
            mode="open_file",
            file_filter="所有支持的文件 (*.mp4 *.mkv *.wav *.json *.srt *.vtt);;所有文件 (*.*)"
        )
        self.glass_container.add_widget(self.file_browser)

        # 1.3 输出目录选择
        default_out_dir = os.path.abspath(os.path.join(os.getcwd(), "output_captions_test"))
        self.dir_browser = FileBrowseWidget(
            label_text="最终输出目录",
            mode="directory",
            default_path=default_out_dir
        )
        self.glass_container.add_widget(self.dir_browser)

        # ==========================================
        # 2. 中间：日志监控面板
        # ==========================================
        self.log_panel = LogPreviewPanel(title="Scheduler 多进程调度台", max_lines=500)
        self.glass_container.add_widget(self.log_panel, stretch=1)

        # ==========================================
        # 3. 底部：控制按钮
        # ==========================================
        btn_layout = QHBoxLayout()
        self.btn_start = RoundedButton("🚀 唤醒独立进程执行", "primary")
        self.btn_cancel = RoundedButton("⚡ 物理级强杀进程", "danger")
        self.btn_cancel.setEnabled(False)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_cancel)

        self.glass_container.add_layout(btn_layout)
        main_layout.addWidget(self.glass_container)

        self.btn_start.clicked.connect(self._on_start_clicked)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)

        self.log_panel.append_log(">>> 真实多进程沙盒已启动。", "info")
        self.log_panel.append_log(">>> 这里不再是模拟！将真实唤醒显卡并加载大模型。", "warning")

    def _on_start_clicked(self):
        input_path = self.file_browser.get_path()
        output_dir = self.dir_browser.get_path()

        if not input_path:
            QMessageBox.warning(self, "警告", "请先选择需要测试的输入文件！")
            return

        self.btn_start.setEnabled(False)
        self.file_browser.setEnabled(False)
        self.combo_mode.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.log_panel.clear_logs()

        selected_mode = self.combo_mode.currentData()

        # 建立缓存目录
        cache_dir = os.path.abspath(os.path.join(os.getcwd(), ".caption_cache"))

        # 准备硬编码测试的契约数据
        real_config = TaskConfig(
            input_path=input_path,
            output_dir=output_dir,
            target_langs=["zh", "en"],  # 测试双语翻译
            file_formats=["srt", "vtt"],
            export_modes=["bilingual", "original"],
            cache_dir=cache_dir
        )

        # 实例化全新的多进程调度器
        self.scheduler = TaskPipelineScheduler(
            task_mode=selected_mode,
            config=real_config
        )

        # 挂载信号监听桥梁 (接收跨进程数据)
        self.scheduler.log_relay.connect(self.log_panel.append_log)
        self.scheduler.progress_relay.connect(self.log_panel.update_progress_line)
        self.scheduler.pipeline_finished.connect(self._on_pipeline_finished)

        # 发射！
        self.scheduler.start_pipeline()

    def _on_cancel_clicked(self):
        if self.scheduler:
            self.btn_cancel.setEnabled(False)
            self.log_panel.append_log("[指令下达] 正在向操作系统发送进程终止信号...", "warning")
            # 调用物理强杀
            self.scheduler.stop_pipeline()

    def _on_pipeline_finished(self, success: bool, message: str):
        self.btn_start.setEnabled(True)
        self.file_browser.setEnabled(True)
        self.combo_mode.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if success:
            self.log_panel.append_log(f"\n✅ 进程生命周期结束。最终产物: {message}", "success")
        else:
            self.log_panel.append_log(f"\n❌ 任务未完成。信息: {message}", "error")