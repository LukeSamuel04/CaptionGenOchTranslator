from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor


class RoundedButton(QPushButton):
    """
    极简风格微圆角按钮组件
    默认使用深邃科技蓝作为主色调，支持 primary (主操作), secondary (次级操作), danger (警示操作) 三种类型。
    """

    def __init__(self, text, btn_type="primary", parent=None):
        super().__init__(text, parent)
        self.btn_type = btn_type
        # 全局开启鼠标悬停时的手型光标
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._apply_style()

    def _apply_style(self):
        # 基础公共样式：6px 微圆角、充足的呼吸感内边距、清晰的加粗字体
        base_style = """
            QPushButton {
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
        """

        # 根据类型定义不同的颜色层级与交互反馈
        if self.btn_type == "primary":
            # 深邃科技蓝：#0078D7 (底色) -> #005A9E (悬停) -> #004578 (按下)
            color_style = """
                QPushButton {
                    background-color: #0078D7;
                    color: #FFFFFF;
                }
                QPushButton:hover {
                    background-color: #005A9E;
                }
                QPushButton:pressed {
                    background-color: #004578;
                }
                QPushButton:disabled {
                    background-color: #333333;
                    color: #777777;
                }
            """
        elif self.btn_type == "secondary":
            # 次级按钮：深灰底色，用于“取消”或“暂停”等非主要视觉焦点操作
            color_style = """
                QPushButton {
                    background-color: #3F3F3F;
                    color: #E0E0E0;
                }
                QPushButton:hover {
                    background-color: #4F4F4F;
                }
                QPushButton:pressed {
                    background-color: #2B2B2B;
                }
                QPushButton:disabled {
                    background-color: #222222;
                    color: #555555;
                }
            """
        elif self.btn_type == "danger":
            # 警示按钮：克制的深红色，用于“强制停止”或“删除”
            color_style = """
                QPushButton {
                    background-color: #D13438;
                    color: #FFFFFF;
                }
                QPushButton:hover {
                    background-color: #A80000;
                }
                QPushButton:pressed {
                    background-color: #8C0000;
                }
                QPushButton:disabled {
                    background-color: #333333;
                    color: #777777;
                }
            """
        else:
            color_style = ""

        self.setStyleSheet(base_style + color_style)