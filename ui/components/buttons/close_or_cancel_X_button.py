from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QCursor, QFont


class CloseOrCancelXButton(QPushButton):
    """
    通用的红叉按钮组件 (纯净主题驱动版)。
    所有的颜色、悬浮状态、圆角均由外部全局 QSS 接管。
    Python 代码仅负责核心结构与逻辑行为。
    """

    def __init__(self, tooltip_text="关闭", icon_size=20, font_size=14, parent=None):
        super().__init__("✖", parent)

        # 核心改动 1：颁发“身份证”，供全局 QSS 精准狙击
        self.setObjectName("CloseXButton")

        # 核心改动 2：结构性属性依然在 Python 层设定
        self.setFixedSize(QSize(icon_size, icon_size))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(tooltip_text)

        # 核心改动 3：使用 Qt 原生 API 设置字体，彻底拔除局部的 setStyleSheet
        font = QFont()
        font.setPixelSize(font_size)
        font.setBold(True)
        self.setFont(font)