from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCursor


class MultiStatusFetchConfigButton(QPushButton):
    """
    带有内置状态机和防抖机制的专属下载配置按钮。
    自带四种形态：默认、查询中、成功驻留(蓝绿色)、失败驻留(橙色)。
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 1. 锁死最小尺寸与内边距，彻底解决切换样式时按钮“缩水干瘪”的问题
        self.setMinimumSize(120, 36)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # 2. 内置定时器，把延时恢复的逻辑封装在组件内部，不污染外部页面
        self.reset_timer = QTimer(self)
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(self.set_default_state)

        # 初始化为默认状态
        self.set_default_state()

    def set_default_state(self):
        """恢复为初始的深灰可点击状态"""
        self.setText("检查云端更新")
        self.setEnabled(True)
        self.setToolTip("")  # 清空可能残留的报错悬浮提示
        self.setStyleSheet("""
            QPushButton {
                background-color: #4A4A4A;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5A5A5A;
            }
            QPushButton:pressed {
                background-color: #3A3A3A;
            }
        """)

    def set_fetching_state(self):
        """切换为灰显禁用的查询状态"""
        self.setText("查询中...")
        self.setEnabled(False)
        self.setStyleSheet("""
            QPushButton {
                background-color: #888888;
                color: #E0E0E0;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
            }
        """)

    def set_success_state(self):
        """切换为高亮的蓝绿色成功状态，并启动自动恢复倒计时"""
        self.setText("获取成功")
        self.setEnabled(False)  # 保持禁用，防止在展示成功动画时被连击
        self.setStyleSheet("""
            QPushButton {
                background-color: #009688;  /* 呼应整体UI风格的科技蓝绿色 (Teal) */
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        # 启动 1.5 秒倒计时，时间到后自动触发 self.set_default_state
        self.reset_timer.start(1500)

    def set_error_state(self, error_msg: str = ""):
        """切换为橙色失败状态，记录详情到ToolTip，并启动自动恢复倒计时"""
        self.setText("查询失败")
        self.setEnabled(False)

        # 将详细的系统报错写入悬浮提示，供需要时查看
        if error_msg:
            self.setToolTip(error_msg)

        self.setStyleSheet("""
            QPushButton {
                background-color: #F29C38;  /* 柔和克制的警示橙色 */
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        # 错误状态同样驻留 1.5 秒后打回原形
        self.reset_timer.start(1500)