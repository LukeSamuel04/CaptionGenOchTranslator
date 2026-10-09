from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt


class WhiteTranslucentContainer(QFrame):
    """
    白蓝色极简半透明容器 (毛玻璃风格模拟)
    提供高度可复用的边距、圆角和阴影包裹，专门用于盛放其他子组件。
    (已接入全局 QSS 主题框架)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置对象名以便 QSS 准确命中，不污染子组件
        self.setObjectName("glassContainer")
        # 核心修复：开启自定义组件的 QSS 背景与边框渲染权限
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._apply_glass_style()
        self._setup_container_layout()

    def _apply_glass_style(self):
        # [核心改动] 移除了此处的 self.setStyleSheet(...)，彻底打破样式隔离墙

        # 2. 弥散阴影：为玻璃卡片增加悬浮感 (由于 QSS 不支持复杂阴影，故保留在 Python 代码中)[cite: 17]
        # 注意：使用极淡的蓝灰色阴影，而不是死板的纯黑阴影[cite: 17]
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)  # 阴影扩散范围[cite: 17]
        shadow.setColor(QColor(0, 50, 100, 15))  # 带有微蓝调的极淡阴影[cite: 17]
        shadow.setOffset(0, 6)  # 垂直方向微弱下坠[cite: 17]
        self.setGraphicsEffect(shadow)

    def _setup_container_layout(self):
        # 容器内部自带布局，管理塞进来的子组件[cite: 17]
        self.content_layout = QVBoxLayout(self)
        # 预留舒适的内部呼吸感 (留白)[cite: 17]
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        # 子组件之间的默认间距[cite: 17]
        self.content_layout.setSpacing(15)

    # --- 对外暴露的嵌套接口 ---

    def add_widget(self, widget: QWidget, stretch=0, alignment=Qt.AlignmentFlag.AlignTop):
        """向玻璃容器中嵌套单个组件"""
        self.content_layout.addWidget(widget, stretch, alignment)

    def add_layout(self, layout, stretch=0):
        """向玻璃容器中嵌套整个布局 (比如一行包含多个按钮的 QHBoxLayout)"""
        self.content_layout.addLayout(layout, stretch)

    def add_stretch(self, stretch=1):
        """添加弹性空间，用于将组件推向一侧"""
        self.content_layout.addStretch(stretch)

    def clear_content(self):
        """清空容器内的所有内容（用于动态刷新页面场景）"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()