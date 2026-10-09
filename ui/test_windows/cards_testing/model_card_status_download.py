import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox
from PySide6.QtCore import QTimer

# 引入被测试的下载卡片组件与状态枚举
from ui.cards.model_card_status_download import ModelCardStatusDownload
from ui.components.buttons.muti_status_download_button import DownloadUIState


class CardTestingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("下载状态卡片 (Store Card) - 沙箱测试台")
        self.resize(600, 300)
        self.setStyleSheet("background-color: #F3F3F3;")  # 模拟界面的浅色背景

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(20)

        # ==========================================
        # 1. 准备虚拟的模型配置数据
        # ==========================================
        self.mock_model_info = {
            "model_id": "llama-3.1-8b-test",
            "display_name": "测试专用-LLaMA-3.1-8B",
            "description": "这是一个用于沙箱测试的虚拟模型配置。占用磁盘空间约 4.58 GB，支持断点续传与取消逻辑测试。",
            "files": [
                {"file_name": "dummy1.bin", "size_bytes": 2000000000},
                {"file_name": "dummy2.bin", "size_bytes": 2920738944}
            ]
        }

        # 记录模拟下载的进度 (总计约 4920738944 Bytes)
        self.total_bytes = sum(f["size_bytes"] for f in self.mock_model_info["files"])
        self.downloaded_bytes = 0

        # ==========================================
        # 2. 挂载被测试的核心卡片组件
        # ==========================================
        self.card = ModelCardStatusDownload(self.mock_model_info)

        # 初始状态设为未下载
        self.card.update_card_state(DownloadUIState.NORMAL)

        # [核心测试] 监听卡片发出的主按钮动作信号
        self.card.action_requested.connect(self._on_card_action_requested)
        # [核心测试] 监听卡片透传出来的进度条取消信号
        self.card.cancel_download_requested.connect(self._on_cancel_requested)

        self.layout.addWidget(self.card)
        self.layout.addStretch()

        # ==========================================
        # 3. 模拟后台下载 Worker 的定时器
        # ==========================================
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._simulate_download_progress)

        # ==========================================
        # 4. 外部遥控器 (用于暴力重置状态)
        # ==========================================
        self.control_layout = QHBoxLayout()
        self.btn_reset = QPushButton("⟳ 暴力重置为【未下载】状态")
        self.btn_reset.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #E0E0E0;")
        self.btn_reset.clicked.connect(self._reset_all)
        self.control_layout.addStretch()
        self.control_layout.addWidget(self.btn_reset)

        self.layout.addLayout(self.control_layout)

    # ==========================================
    # 模拟主页面 (DownloadPage) 的调度逻辑
    # ==========================================
    def _on_card_action_requested(self, model_id: str, state: DownloadUIState):
        """模拟主页面接收到卡片主按钮的点击事件"""
        if state in (DownloadUIState.NORMAL, DownloadUIState.RESUME, DownloadUIState.CORRUPTED):
            # 用户点击了“下载”或“继续”
            self.card.update_card_state(DownloadUIState.DOWNLOADING, self.downloaded_bytes, self.total_bytes)
            self.timer.start(50)  # 启动定时器，模拟开始下载

        elif state == DownloadUIState.DOWNLOADING:
            # 用户点击了“暂停”
            self.timer.stop()
            self.card.update_card_state(DownloadUIState.RESUME)

    def _on_cancel_requested(self, model_id: str):
        """模拟主页面接收到红叉的取消事件，并弹出防抖确认框"""
        # 1. 必须先暂停后台的下载线程 (定时器)
        was_downloading = self.timer.isActive()
        self.timer.stop()

        # 2. 弹窗二次确认
        reply = QMessageBox.question(
            self,
            "终止下载",
            f"确定要取消模型 [{model_id}] 的下载吗？\n已下载的进度将被全部清除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 3. 用户确认取消：清理进度，重置卡片状态
            self.downloaded_bytes = 0
            self.card.update_card_state(DownloadUIState.NORMAL)
            QMessageBox.information(self, "已清理", "残留的碎片文件已在后台清理完毕。")
        else:
            # 4. 用户反悔：如果刚才正在下载，就恢复下载
            if was_downloading:
                self.timer.start(50)

    # ==========================================
    # 定时器模拟下载过程
    # ==========================================
    def _simulate_download_progress(self):
        # 每次模拟下载大约 25MB，制造高速下载的视觉效果
        chunk_size = 25 * 1024 * 1024
        self.downloaded_bytes += chunk_size

        # 模拟瞬时网速 (KB/s)
        speed_kbps = 520 * 1024  # 模拟 520 MB/s 的极致内网速度

        if self.downloaded_bytes >= self.total_bytes:
            self.downloaded_bytes = self.total_bytes
            self.timer.stop()
            # 模拟下载完成，通知卡片状态变迁（现实中主页面会在这里把卡片替换成 InstalledCard）
            self.card.update_card_state(DownloadUIState.INSTALLED)
            QMessageBox.success(self, "下载完成",
                                "模型下载完毕！在真实业务中，这张卡片将被销毁，替换为 Installed 管理卡片。")
        else:
            # 高频调用卡片的实时更新接口
            self.card.update_realtime_progress(self.downloaded_bytes, self.total_bytes, speed_kbps)

    def _reset_all(self):
        """方便重复测试的重置按钮"""
        self.timer.stop()
        self.downloaded_bytes = 0
        self.card.update_card_state(DownloadUIState.NORMAL)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CardTestingWindow()
    window.show()
    sys.exit(app.exec())