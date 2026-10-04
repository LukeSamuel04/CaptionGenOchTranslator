import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt

# 导入白蓝极简风组件
from ui.components_new.containers.white_translucent_container import WhiteTranslucentContainer
from ui.components_new.file_browsers.blue_file_browser import FileBrowseWidget
from ui.components_new.log_field.blue_logfield import LogPreviewPanel
from ui.components_new.buttons.rounded_blue_button import RoundedButton

# 导入我们刚刚重构好的翻译 Worker
from workers.translate_typeset_caption import TranslateTypesetCaptionWorker


class TranslateCaptionTestWindow(QWidget):
    """
    第二阶段 Worker (大语言模型翻译) 的专属沙盒测试窗口。
    用于独立验证外挂字幕解析、大模型翻译流转、复合进度条以及最终文件落盘功能。
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("沙盒测试 - 纯翻译 Worker (Translate Caption)")
        self.resize(750, 600)

        # 维持浅灰蓝色的渐变背景，以衬托半透明玻璃容器
        self.setStyleSheet("""
            TranslateCaptionTestWindow {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                                  stop:0 #E8F0F6, stop:1 #D2E0EB);
            }
        """)

        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)

        # 实例化毛玻璃容器
        self.glass_container = WhiteTranslucentContainer()

        # ==========================================
        # 1. 顶部：输入文件与输出目录选择
        # ==========================================
        # 源字幕文件浏览器 (支持 JSON 和标准字幕)
        self.file_browser = FileBrowseWidget(
            label_text="选择源字幕文件 (支持 .json, .srt, .vtt)",
            mode="open_file",
            file_filter="字幕/缓存文件 (*.json *.srt *.vtt);;所有文件 (*.*)"
        )
        self.glass_container.add_widget(self.file_browser)

        # 输出目录浏览器
        default_out_dir = os.path.abspath(os.path.join(os.getcwd(), "output_captions"))
        self.dir_browser = FileBrowseWidget(
            label_text="选择最终成品输出目录",
            mode="directory",
            default_path=default_out_dir
        )
        self.glass_container.add_widget(self.dir_browser)

        # ==========================================
        # 2. 中间：高科技日志与进度面板
        # ==========================================
        self.log_panel = LogPreviewPanel(title="翻译 Worker 实时运行日志", max_lines=500)
        self.glass_container.add_widget(self.log_panel, stretch=1)

        # ==========================================
        # 3. 底部：控制按钮区
        # ==========================================
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.btn_start = RoundedButton("🚀 开始翻译测试", "primary")
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
        self.log_panel.append_log(">>> 第二阶段 Worker 测试环境已就绪。", "info")
        self.log_panel.append_log(
            ">>> 提示：你可以直接选择第一阶段生成的 .json 缓存，或者网上下载的英文字幕 .srt 进行测试。", "success")

    # ==========================================
    # 核心测试逻辑：启动 Worker 并连接信号
    # ==========================================
    def _on_start_clicked(self):
        source_path = self.file_browser.get_path()
        output_dir = self.dir_browser.get_path()

        if not source_path or not output_dir:
            QMessageBox.warning(self, "警告", "请先选择源字幕文件和输出目录！")
            return

        # 1. 锁定 UI，防止用户重复点击
        self.btn_start.setEnabled(False)
        self.file_browser.setEnabled(False)
        self.dir_browser.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.log_panel.clear_logs()

        # --- 测试用的硬编码参数 (你可以随时在这里修改测试用例) ---
        test_target_langs = ["zh"]  # 目标语言：简体中文
        test_file_formats = ["srt"]  # 导出格式：SRT
        test_export_modes = ["bilingual", "translated", "original"]  # 导出模式：双语、纯译文、原声

        self.log_panel.append_log(
            f"[测试参数] 目标语言: {test_target_langs} | 格式: {test_file_formats} | 模式: {test_export_modes}", "info")

        # 2. 实例化 Worker
        self.worker = TranslateTypesetCaptionWorker(
            source_file_path=source_path,
            output_dir=output_dir,
            target_langs=test_target_langs,
            file_formats=test_file_formats,
            export_modes=test_export_modes
        )

        # 3. 完美缝合“双通道对讲机”
        self.worker.log_signal.connect(self.log_panel.append_log)
        self.worker.progress_signal.connect(self.log_panel.update_progress_line)
        self.worker.finished_signal.connect(self._on_worker_finished)

        # 4. 点火发射
        self.worker.start()

    def _on_cancel_clicked(self):
        """测试 Worker 的中途打断机制"""
        if self.worker and self.worker.isRunning():
            self.btn_cancel.setEnabled(False)
            self.log_panel.append_log("[系统] 正在发送终止指令，等待翻译模型安全退出并清理显存...", "warning")
            self.worker.stop()  # 触发 Worker 内部的 InterruptedError

    def _on_worker_finished(self, success: bool, message: str):
        """Worker 彻底结束（无论成功、失败还是取消）后的回调"""
        # 解锁 UI
        self.btn_start.setEnabled(True)
        self.file_browser.setEnabled(True)
        self.dir_browser.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if success:
            self.log_panel.append_log(f"\n[测试成功] 🎈 翻译成品文件已生成并分类落盘！\n路径: {message}", "success")
            # 自动打开生成的文件夹供你检查
            try:
                import webbrowser
                webbrowser.open(f"file:///{message}")
            except Exception:
                pass
        else:
            self.log_panel.append_log(f"\n[测试结束] 任务未能完成。\n反馈信息: {message}", "error")