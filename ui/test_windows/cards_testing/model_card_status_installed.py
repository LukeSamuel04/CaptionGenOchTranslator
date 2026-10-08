import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QMessageBox

# 引入被测试的已安装状态卡片组件
from ui.cards.model_card_status_installed import ModelCardStatusInstalled


class InstalledCardTestingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("已安装卡片 (Installed Card) - 沙箱测试台")
        self.resize(600, 200)
        self.setStyleSheet("background-color: #F3F3F3;")  # 模拟界面的浅色背景

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 30)

        # ==========================================
        # 1. 准备虚拟的已安装模型配置数据
        # ==========================================
        self.mock_model_info = {
            "model_id": "whisper-large-v3-test",
            "display_name": "测试专用-Whisper-Large-V3",
            "description": "这是一个完全下载并驻留在本地硬盘的虚拟模型。你可以尝试缩放窗口，观察右上角红叉的自适应排版是否稳定。",
            "files": [
                {"file_name": "model.safetensors", "size_bytes": 3110000000}
            ]
        }

        # ==========================================
        # 2. 挂载被测试的核心卡片组件
        # ==========================================
        self.card = ModelCardStatusInstalled(self.mock_model_info)

        # [核心测试] 监听卡片透传出来的删除信号
        self.card.delete_requested.connect(self._on_delete_requested)

        self.layout.addWidget(self.card)

        # 底部加一个弹簧，把卡片顶在窗口上方，方便测试窗口拉伸
        self.layout.addStretch()

    # ==========================================
    # 模拟主页面 (DownloadPage) 的调度逻辑
    # ==========================================
    def _on_delete_requested(self, model_id: str):
        """模拟主页面接收到右上角红叉的删除事件，并弹出防抖确认框"""

        # 弹窗二次确认防抖
        reply = QMessageBox.question(
            self,
            "删除本地模型",
            f"确定要彻底删除模型 [{model_id}] 吗？\n此操作将释放约 2.9 GB 的本地磁盘空间，且无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 用户确认删除：模拟清理操作
            QMessageBox.information(
                self,
                "已删除",
                "本地模型文件已被物理抹除！\n\n在真实的业务逻辑中，主页面此时会执行：\n1. shutil.rmtree() 删掉本地文件夹\n2. 销毁当前这张 Installed 卡片\n3. 在原位置重新实例化一张 Download (Store) 卡片"
            )

            # 为了在测试台中表现出“被删了”，我们直接把测试卡片隐藏掉
            self.card.setVisible(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InstalledCardTestingWindow()
    window.show()
    sys.exit(app.exec())