from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, Property, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QCursor, QPainterPath


class _SwitchCore(QCheckBox):
    """
    内部纯绘制的拨动开关核心部件。
    不直接对外使用，仅作为 ToggleSwitch 的内部组件。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 22)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._offset = 2.0  # 滑块的初始 X 坐标偏移量

        # 配置平滑滑动动画 (150ms 极速响应)
        self.anim = QPropertyAnimation(self, b"offset")
        self.anim.setDuration(150)

        self.toggled.connect(self._on_toggled)

    def _get_offset(self):
        return self._offset

    def _set_offset(self, value):
        self._offset = value
        self.update()  # 触发重绘

    # 注册可以被 QPropertyAnimation 动画驱动的自定义属性
    offset = Property(float, fget=_get_offset, fset=_set_offset)

    def _on_toggled(self, checked):
        # 动态计算滑块的起始和终点位置
        self.anim.setStartValue(self._offset)
        # 滑块直径为 18 (22 - 4)，右侧终点为 40 - 18 - 2 = 20
        self.anim.setEndValue(20.0 if checked else 2.0)
        self.anim.start()

    def paintEvent(self, event):
        """完全接管绘制逻辑，不再使用任何系统自带样式"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # 开启抗锯齿

        # 1. 绘制背景胶囊底槽
        bg_color = QColor("#0078D7") if self.isChecked() else QColor("#D0D0D0")
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), self.height() / 2, self.height() / 2)
        painter.fillPath(path, QBrush(bg_color))

        # 2. 绘制白色圆形滑块
        handle_radius = self.height() - 4
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#FFFFFF")))

        # 绘制阴影以增加高级感
        painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
        painter.drawEllipse(QRectF(self._offset, 3, handle_radius, handle_radius))

        # 绘制实体滑块
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(QRectF(self._offset, 2, handle_radius, handle_radius))


class ToggleSwitch(QWidget):
    """
    白蓝极简风 iOS 样式拨动开关组件
    包含主标题、补充说明(Description)以及动画开关。
    """
    toggled = Signal(bool)

    def __init__(self, title, description="", default_state=False, parent=None):
        super().__init__(parent)
        self.title_text = title
        self.description_text = description

        self._setup_ui()
        # 初始化默认状态 (不触发动画)
        self.switch_core.blockSignals(True)
        self.switch_core.setChecked(default_state)
        self.switch_core._set_offset(20.0 if default_state else 2.0)
        self.switch_core.blockSignals(False)

        # 允许点击整个外层卡片区域来触发开关
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 5, 0, 5)

        # 左侧文本区布局
        self.text_layout = QVBoxLayout()
        self.text_layout.setSpacing(2)

        # 主标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        self.text_layout.addWidget(self.title_label)

        # 补充说明 (灰字，更小的字号)
        if self.description_text:
            self.desc_label = QLabel(self.description_text)
            self.desc_label.setStyleSheet("color: #888888; font-size: 12px;")
            self.text_layout.addWidget(self.desc_label)

        self.main_layout.addLayout(self.text_layout)

        # 弹性空间，将开关推向最右侧
        self.main_layout.addStretch()

        # 右侧动画开关核心
        self.switch_core = _SwitchCore()
        self.main_layout.addWidget(self.switch_core, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 信号转发
        self.switch_core.toggled.connect(self.toggled.emit)

    def mouseReleaseEvent(self, event):
        """重写鼠标释放事件：点击整个组件区域任意位置，都能触发开关，极大提升体验"""
        super().mouseReleaseEvent(event)
        self.switch_core.setChecked(not self.switch_core.isChecked())

    # --- 外部业务接口 ---

    def get_value(self):
        """获取当前开关布尔值"""
        return self.switch_core.isChecked()

    def set_value(self, state: bool):
        """通过代码改变开关状态"""
        self.switch_core.setChecked(state)