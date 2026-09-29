import os
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QMessageBox
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

# 导入前端组件
from ui.components.config_panel import ConfigPanel
from ui.components.log_panel import LogPanel

# 导入真实的 AI 后台线程
from ui.workers.ai_task_worker import AITaskWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 配置窗口基础属性
        self.setWindowTitle(self.tr("CaptionGen Translator - 专业离线AI字幕引擎"))
        self.resize(900, 800)
        self.setMinimumSize(850, 700)

        # 建立中央画布和主垂直布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # ---------------------------------------------------------
        # 1. 挂载组件
        # ---------------------------------------------------------
        self.config_panel = ConfigPanel(self)
        self.main_layout.addWidget(self.config_panel)

        self.log_panel = LogPanel(self)
        self.main_layout.addWidget(self.log_panel)

        self.main_layout.addStretch()

        # ---------------------------------------------------------
        # 2. 全局控制区
        # ---------------------------------------------------------
        self.start_btn = QPushButton(self.tr("开始生成 (Start Generation)"))
        self.start_btn.setMinimumHeight(45)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #AAAAAA;
            }
        """)
        self.main_layout.addWidget(self.start_btn)

        # 绑定点击事件
        self.start_btn.clicked.connect(self._on_start_clicked)

        # 预留 worker 实例变量
        self.worker = None

    def _on_start_clicked(self):
        """点击开始按钮的统筹逻辑"""
        # 1. 校验前端参数
        if not self.config_panel.validate_inputs():
            return

        config_data = self.config_panel.get_configuration()

        # 2. 锁定界面，防止任务运行中途用户误触
        self.start_btn.setEnabled(False)
        self.start_btn.setText(self.tr("AI 引擎高速运行中..."))
        self.config_panel.setEnabled(False)
        self.log_panel.reset()

        # 3. 启动真实的后台多线程引擎
        self.worker = AITaskWorker(config_data)

        # 精准连接信号与插槽
        self.worker.log_signal.connect(self.log_panel.add_log)
        self.worker.dict_prog_signal.connect(self.log_panel.update_dictation_progress)
        self.worker.trans_prog_signal.connect(self.log_panel.update_translation_progress)
        self.worker.finished_signal.connect(self._on_task_finished)

        # 引擎发车！
        self.worker.start()

    def _on_task_finished(self, success: bool, message: str):
        """
        任务完成后的收尾工作
        :param success: 任务是否成功完成
        :param message: 成功时返回输出路径，失败时返回错误原因
        """
        # 1. 解锁界面
        self.start_btn.setEnabled(True)
        self.start_btn.setText(self.tr("开始生成 (Start Generation)"))
        self.config_panel.setEnabled(True)

        # 2. 根据结果处理
        if success:
            self.log_panel.add_log(self.tr("[系统] 恭喜！所有字幕已成功生成并落盘。"), "success")

            # 弹窗询问是否打开文件夹
            reply = QMessageBox.question(
                self,
                self.tr("处理完成"),
                self.tr("字幕生成完毕！是否立即打开输出文件夹？\n\n路径: ") + message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 跨平台打开本地文件夹的 Qt 标准写法
                QDesktopServices.openUrl(QUrl.fromLocalFile(message))
        else:
            self.log_panel.add_log(self.tr(f"[系统] 任务意外终止，请检查日志。原因: {message}"), "error")
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"处理过程中发生错误:\n{message}"))

    def closeEvent(self, event):
        """窗口关闭时的拦截逻辑，防止强制关闭导致后台线程变成僵尸进程"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.warning(
                self,
                self.tr("警告"),
                self.tr("AI 引擎正在后台运行，强制关闭可能导致数据损坏。\n确定要退出吗？"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.worker.stop()
                self.worker.wait()  # 等待线程安全退出
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()