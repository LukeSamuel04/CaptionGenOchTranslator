from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QCursor


class CloseOrCancelXButton(QPushButton):
    """
    通用的红叉按钮组件。
    平时呈现为低调的灰色，鼠标悬浮时变为警示红色。
    完全与业务解耦，可复用于取消下载、删除卡片、关闭窗口等任何需要“毁灭性/关闭操作”的场景。
    """

    def __init__(self, tooltip_text="关闭", icon_size=20, font_size=14, parent=None):
        super().__init__("✖", parent)

        # 设定固定大小，并使其呈正方形以保证圆角渲染为完美的圆形
        self.setFixedSize(QSize(icon_size, icon_size))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(tooltip_text)

        self._setup_style(font_size, icon_size // 2)

    def _setup_style(self, font_size: int, border_radius: int):
        # 扁平化红色系样式设计：默认透明灰，悬浮浅红，按下深红
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #888888;
                font-size: {font_size}px;
                font-weight: bold;
                border: none;
                border-radius: {border_radius}px;
            }}
            QPushButton:hover {{
                color: #D13438;
                background-color: rgba(209, 52, 56, 30);
            }}
            QPushButton:pressed {{
                color: #A80000;
                background-color: rgba(209, 52, 56, 50);
            }}
        """)