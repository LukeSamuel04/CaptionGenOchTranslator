import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
from PySide6.QtCore import QTimer, Qt

# 引入你刚刚写好的目标组件
from ui.components.buttons.muti_status_fetch_config_button import MultiStatusFetchConfigButton


class FetchConfigButtonTestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多状态刷新按钮 - 独立测试台")
        # 略微加宽窗口，以容纳底部一排 4 个测试按钮
        self.resize(550, 350)
        # 模拟主程序的浅色背景，方便观察按钮边缘和阴影
        self.setStyleSheet("background-color: #F4F5F7;")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ==========================================
        # 1. 目标测试组件区 (上方)
        # ==========================================
        self.title_label = QLabel("标准业务流测试 (点击下方按钮)")
        self.title_label.setStyleSheet("color: #666666; font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.title_label)

        # 实例化目标按钮
        self.target_btn = MultiStatusFetchConfigButton()
        # 绑定点击事件，模拟完整的网络请求流
        self.target_btn.clicked.connect(self._simulate_network_request)

        # 居中放置，防止被布局器暴力拉伸，严格测试其自身的 Size 约束
        self.main_layout.addWidget(self.target_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # ==========================================
        # 分割线
        # ==========================================
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #DDDDDD; margin-top: 40px; margin-bottom: 20px;")
        self.main_layout.addWidget(line)

        # ==========================================
        # 2. 强制状态干预区 (下方)
        # ==========================================
        self.panel_label = QLabel("手动状态定格测试 (强行覆写当前状态)")
        self.panel_label.setStyleSheet("color: #888888; font-size: 12px; margin-bottom: 10px;")
        self.panel_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.panel_label)

        self.control_layout = QHBoxLayout()
        self.control_layout.setSpacing(10)

        self.btn_force_default = QPushButton("强制: 默认态")
        self.btn_force_default.clicked.connect(self.target_btn.set_default_state)

        self.btn_force_fetching = QPushButton("强制: 查询中")
        self.btn_force_fetching.clicked.connect(self.target_btn.set_fetching_state)

        self.btn_force_success = QPushButton("强制: 获取成功")
        self.btn_force_success.clicked.connect(self.target_btn.set_success_state)

        # 新增：强制失败状态，并传入模拟的报错文本以测试 ToolTip
        self.btn_force_error = QPushButton("强制: 查询失败")
        self.btn_force_error.clicked.connect(lambda: self.target_btn.set_error_state("模拟的网络连接超时报错 (Error: 404)"))

        # 统一给底部控制面板的按钮加上简单的样式（加入了新增的 error 按钮）
        for btn in [self.btn_force_default, self.btn_force_fetching, self.btn_force_success, self.btn_force_error]:
            btn.setStyleSheet("""
                QPushButton { background-color: #FFFFFF; border: 1px solid #CCCCCC; border-radius: 4px; padding: 6px; }
                QPushButton:hover { background-color: #EEEEEE; }
            """)
            self.control_layout.addWidget(btn)

        self.main_layout.addLayout(self.control_layout)

    def _simulate_network_request(self):
        """
        模拟实际业务中的异步网络请求流程。
        """
        # 1. 立即切换为查询态 (禁用点击，防抖)
        self.target_btn.set_fetching_state()

        # 2. 模拟网络耗时 (1.2秒)，随后自动触发成功态
        # 注意：成功态内部自带 1.5 秒驻留后恢复默认的逻辑，这里无需再写恢复代码
        QTimer.singleShot(1200, self.target_btn.set_success_state)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FetchConfigButtonTestWindow()
    window.show()
    sys.exit(app.exec())