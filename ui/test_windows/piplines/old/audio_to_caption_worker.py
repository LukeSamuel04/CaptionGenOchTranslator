import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt

# 导入白蓝极简风组件
from ui.components_new.containers.white_translucent_container import WhiteTranslucentContainer
from ui.components_new.file_browsers.blue_file_browser import FileBrowseWidget
from ui.components_new.log_field.blue_logfield import LogPreviewPanel
from ui.components_new.buttons.rounded_blue_button import RoundedButton

# 导入我们刚刚写好的独立听写 Worker
from workers.audio_to_caption import AudioToCaptionWorker


class AudioToCaptionTestWindow(QWidget):
    """
    第一阶段 Worker (音频到文本) 的专属沙盒测试窗口。
    用于独立测试 Whisper 听写、极客进度条更新以及中途取消功能。
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("沙盒测试 - 纯听写 Worker (Audio to Caption)")
        self.resize(750, 550)

        # 维持浅灰蓝色的渐变背景，以衬托半透明玻璃容器
        self.setStyleSheet("""
            AudioToCaptionTestWindow {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                                  stop:0 #E8F0F6, stop:1 #D2E0EB);
            }
        """)

        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)

        # 实例化毛玻璃容器[cite: 14]
        self.glass_container = WhiteTranslucentContainer()

        # ==========================================
        # 1. 顶部：输入文件选择[cite: 15]
        # ==========================================
        self.file_browser = FileBrowseWidget(
            label_text="选择测试视频/音频文件",
            mode="open_file",
            file_filter="音视频文件 (*.mp4 *.mkv *.avi *.mov *.mp3 *.wav);;所有文件 (*.*)"
        )
        self.glass_container.add_widget(self.file_browser)

        # ==========================================
        # 2. 中间：高科技日志与进度面板[cite: 16]
        # ==========================================
        self.log_panel = LogPreviewPanel(title="Worker 实时运行日志", max_lines=500)
        self.glass_container.add_widget(self.log_panel, stretch=1)

        # ==========================================
        # 3. 底部：控制按钮区[cite: 13]
        # ==========================================
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.btn_start = RoundedButton("🚀 开始听写测试", "primary")
        self.btn_cancel = RoundedButton("⏹ 强制取消", "danger")
        self.btn_cancel.setEnabled(False)  # 初始状态下取消按钮不可用

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_cancel)

        self.glass_container.add_layout(btn_layout)
        main_layout.addWidget(self.glass_container)

        # 绑定按钮事件
        self.btn_start.clicked.connect(self._on_start_clicked)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)

        # 初始日志提示
        self.log_panel.append_log(">>> 第一阶段 Worker 测试环境已就绪。", "info")
        self.log_panel.append_log(">>> 请选择媒体文件，点击开始以验证 Whisper 听写与进度条响应。", "success")

    # ==========================================
    # 核心测试逻辑：启动 Worker 并连接信号
    # ==========================================
    def _on_start_clicked(self):
        media_path = self.file_browser.get_path()
        if not media_path:
            QMessageBox.warning(self, "警告", "请先选择需要测试的音视频文件！")
            return

        # 准备一个缓存目录存放生成的 JSON 文件
        # 我们把它放在当前运行目录下的 .caption_cache 文件夹中
        cache_dir = os.path.abspath(os.path.join(os.getcwd(), ".caption_cache"))

        # 1. 锁定 UI，防止用户重复点击
        self.btn_start.setEnabled(False)
        self.file_browser.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.log_panel.clear_logs()

        # 2. 实例化 Worker
        self.worker = AudioToCaptionWorker(media_path=media_path, cache_dir=cache_dir)

        # 3. 完美缝合“双通道对讲机”
        # 将 Worker 发出的普通日志信号，直连到面板的 append_log 方法
        self.worker.log_signal.connect(self.log_panel.append_log)
        # 将 Worker 发出的进度信号，直连到面板的 update_progress_line 方法
        self.worker.progress_signal.connect(self.log_panel.update_progress_line)
        # 将 Worker 的任务结束信号，连到我们自定义的收尾方法
        self.worker.finished_signal.connect(self._on_worker_finished)

        # 4. 点火发射
        self.worker.start()

    def _on_cancel_clicked(self):
        """测试 Worker 的中途打断机制"""
        if self.worker and self.worker.isRunning():
            self.btn_cancel.setEnabled(False)
            self.log_panel.append_log("[系统] 正在发送终止指令，等待 Worker 安全退出并清理显存...", "warning")
            self.worker.stop()  # 触发 Worker 内部的 InterruptedError

    def _on_worker_finished(self, success: bool, message: str):
        """Worker 彻底结束（无论成功、失败还是取消）后的回调"""
        # 解锁 UI
        self.btn_start.setEnabled(True)
        self.file_browser.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if success:
            self.log_panel.append_log(f"\n[测试成功] 🎈 JSON 缓存文件已完美生成！\n路径: {message}", "success")
            # 可以在这里自动打开生成的 JSON 文件夹供你检查
            cache_dir = os.path.dirname(message)
            import webbrowser
            webbrowser.open(f"file:///{cache_dir}")
        else:
            self.log_panel.append_log(f"\n[测试结束] 任务未能完成。\n反馈信息: {message}", "error")