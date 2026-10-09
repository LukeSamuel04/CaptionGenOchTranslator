import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox
from PySide6.QtCore import QTimer

# 导入我们刚刚编写的带取消按钮的进度条组件
from ui.components.progress_bars.download_pb_with_cancel import DownloadProgressBarWithCancel


class PBTestingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("下载进度条 (带取消按钮) - 沙箱测试台")
        self.resize(500, 200)
        self.setStyleSheet("background-color: #F3F3F3;")  # 模拟界面的浅色背景

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 30)

        # ==========================================
        # 1. 挂载被测试的核心组件
        # ==========================================
        self.pb = DownloadProgressBarWithCancel(title="Whisper Large-V3 下载中...")
        self.pb.set_range(0, 100)
        self.pb.set_status_text("准备下载...")

        # [核心测试] 监听并绑定内部发出的取消信号
        self.pb.cancel_requested.connect(self.on_cancel_requested)

        self.layout.addWidget(self.pb)
        self.layout.addStretch()

        # ==========================================
        # 2. 模拟场景控制区 (遥控器)
        # ==========================================
        self.control_layout = QHBoxLayout()

        self.btn_start = QPushButton("▶ 模拟下载")
        self.btn_pause = QPushButton("⏸ 模拟暂停")
        self.btn_error = QPushButton("⚠ 模拟出错")
        self.btn_reset = QPushButton("⟳ 重置进度")

        # 简单的按钮样式，方便区分
        for btn in [self.btn_start, self.btn_pause, self.btn_error, self.btn_reset]:
            btn.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #E0E0E0;")

        self.control_layout.addWidget(self.btn_start)
        self.control_layout.addWidget(self.btn_pause)
        self.control_layout.addWidget(self.btn_error)
        self.control_layout.addWidget(self.btn_reset)

        self.layout.addLayout(self.control_layout)

        # ==========================================
        # 3. 模拟后台 Worker 线程的定时器
        # ==========================================
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.current_val = 0

        # 绑定遥控器按钮事件
        self.btn_start.clicked.connect(self.start_download)
        self.btn_pause.clicked.connect(self.pause_download)
        self.btn_error.clicked.connect(self.error_download)
        self.btn_reset.clicked.connect(self.reset_download)

    # --- 模拟场景槽函数 ---

    def start_download(self):
        self.pb.set_theme("#0078D7")  # 恢复为下载中的蓝色
        self.timer.start(50)  # 50ms 刷新一次进度，模拟高速下载

    def pause_download(self):
        self.timer.stop()
        self.pb.set_theme("#888888")  # 暂停时变为灰色
        self.pb.set_status_text(f"已暂停 | {self.current_val} MB / 100 MB")

    def error_download(self):
        self.timer.stop()
        self.pb.set_theme("#D13438")  # 出错时变为警示红
        self.pb.set_status_text("校验失败，文件损坏")

    def reset_download(self):
        self.timer.stop()
        self.current_val = 0
        self.pb.set_value(0)
        self.pb.set_theme("#8BC34A")  # 恢复原初始色
        self.pb.set_status_text("准备下载...")

    def update_progress(self):
        self.current_val += 1
        if self.current_val >= 100:
            self.current_val = 100
            self.timer.stop()
            self.pb.set_value(100)
            self.pb.set_status_text("下载完成")
        else:
            self.pb.set_value(self.current_val)
            self.pb.set_status_text(f"12.5 MB/s | {self.current_val} MB / 100 MB")

    # --- 测试信号捕获 ---
    def on_cancel_requested(self):
        """当点击进度条右侧的小红叉时触发"""
        self.timer.stop()
        # 弹窗证明信号完美透传出来了
        QMessageBox.warning(
            self,
            "信号捕获成功",
            "成功捕获到 cancel_requested 信号！\n\n未来在主页面中，这里将执行：\n1. 杀掉正在运行的 Worker 线程\n2. 删除已下载的 .part 碎片文件"
        )
        self.reset_download()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PBTestingWindow()
    window.show()
    sys.exit(app.exec())