import sys
import os

# 动态获取项目根目录并加入系统路径，确保绝对导入(ui.components...)能成功
current_dir = os.path.dirname(os.path.abspath(__file__))
# 向上回退三级：components_testing -> test_windows -> ui -> 项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt
from ui.components.buttons.muti_status_download_button import MultiStatusDownloadButton, DownloadUIState


class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多状态下载按钮 - UI测试窗")
        self.resize(600, 250)
        self.setStyleSheet("background-color: #F3F3F3;")  # 设置一个浅色背景以便看清按钮边缘

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # --- 1. 目标测试组件 ---
        self.test_button = MultiStatusDownloadButton()
        # 稍微加宽一点，让视觉效果更好
        self.test_button.setMinimumWidth(150)

        # 将按钮居中放置
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.test_button)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # 状态反馈标签
        self.feedback_label = QLabel("当前状态: 未点击")
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback_label.setStyleSheet("color: #666666; font-size: 14px; font-weight: bold;")
        main_layout.addWidget(self.feedback_label)

        # 绑定点击事件，测试交互是否正常
        self.test_button.clicked.connect(self._on_target_button_clicked)

        # --- 2. 状态切换控制台 ---
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)

        # 定义一系列基础按钮来强行改变目标按钮的状态
        btn_normal = QPushButton("设为: NORMAL (未安装)")
        btn_normal.clicked.connect(lambda: self._switch_state(DownloadUIState.NORMAL))

        btn_resume = QPushButton("设为: RESUME (部分)")
        btn_resume.clicked.connect(lambda: self._switch_state(DownloadUIState.RESUME))

        btn_downloading = QPushButton("设为: DOWNLOADING (下载中)")
        btn_downloading.clicked.connect(lambda: self._switch_state(DownloadUIState.DOWNLOADING))

        btn_installed = QPushButton("设为: INSTALLED (已安装)")
        btn_installed.clicked.connect(lambda: self._switch_state(DownloadUIState.INSTALLED))

        btn_corrupted = QPushButton("设为: CORRUPTED (损坏)")
        btn_corrupted.clicked.connect(lambda: self._switch_state(DownloadUIState.CORRUPTED))

        control_layout.addWidget(btn_normal)
        control_layout.addWidget(btn_resume)
        control_layout.addWidget(btn_downloading)
        control_layout.addWidget(btn_installed)
        control_layout.addWidget(btn_corrupted)

        main_layout.addStretch()
        main_layout.addLayout(control_layout)

    def _switch_state(self, new_state):
        """调用目标按钮的 update_status 方法进行状态切换"""
        self.test_button.update_status(new_state)
        self.feedback_label.setText(f"UI 已刷新，当前等待点击操作...")

    def _on_target_button_clicked(self):
        """当目标按钮被点击时，读取它内部的当前状态"""
        current_state = self.test_button.get_current_state()
        self.feedback_label.setText(f"按钮被点击！当前内部属性值为: {current_state.name}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())