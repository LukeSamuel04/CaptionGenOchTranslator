from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QListView
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor


class LabeledComboBox(QWidget):
    """
    白蓝极简风带标题的下拉框组件 (方案 A: 上下布局)
    包含标题标签和高度定制化的下拉选择框。
    """
    # 当用户选择新选项时向外发射信号，携带 (当前文本, 当前索引)
    selection_changed = Signal(str, int)

    def __init__(self, label_text, items=None, default_index=0, parent=None):
        super().__init__(parent)
        self.items = items if items else []
        self.default_index = default_index

        self._setup_ui(label_text)
        self._connect_signals()

    def _setup_ui(self, label_text):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(6)  # 标题和下拉框的呼吸间距

        # 1. 标题标签
        self.title_label = QLabel(label_text)
        self.title_label.setStyleSheet("color: #555555; font-size: 13px; font-weight: bold;")
        self.main_layout.addWidget(self.title_label)

        # 2. 下拉框本体
        self.combo = QComboBox()
        self.combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.combo.addItems(self.items)
        if 0 <= self.default_index < len(self.items):
            self.combo.setCurrentIndex(self.default_index)

        # 核心技巧：用 QListView 替换原生的下拉视图，这样才能对其应用圆角和 Padding
        list_view = QListView()
        list_view.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.combo.setView(list_view)

        # 3. 注入白蓝极简 QSS 样式
        self.combo.setStyleSheet("""
            /* 1. 下拉框主控区常态 */
            QComboBox {
                background-color: rgba(255, 255, 255, 200);
                border: 1px solid rgba(0, 120, 215, 60); /* 极淡的微蓝边框 */
                border-radius: 6px;
                padding: 8px 12px;
                color: #333333;
                font-size: 14px;
            }

            /* 鼠标悬停与展开时的焦点状态 */
            QComboBox:hover, QComboBox:on {
                border: 1px solid #0078D7; /* 科技蓝高亮 */
                background-color: #FFFFFF;
            }

            /* 右侧下拉箭头区域 */
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: none; /* 去除原生分割线 */
            }

            /* ==========================================
               核心修复：使用本地相对路径引入真实的箭头图片 
               ========================================== */
            QComboBox::down-arrow {
                width: 14px;
                height: 14px;
                image: url("assets/icons/black_arrow_for_combobox.png");
            }

            /* 2. 弹出的下拉菜单层 (QListView) */
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 120, 215, 60);
                border-radius: 6px;
                padding: 4px;
                outline: 0px; /* 去除点击时的虚线框 */
            }

            /* 菜单中的每一项 */
            QComboBox QAbstractItemView::item {
                min-height: 32px;
                border-radius: 4px;
                padding-left: 8px;
                color: #333333;
            }

            /* 菜单项鼠标悬停 */
            QComboBox QAbstractItemView::item:hover {
                background-color: #F0F4F8; /* 极浅的蓝灰底色 */
                color: #0078D7;
            }

            /* 菜单项被选中 */
            QComboBox QAbstractItemView::item:selected {
                background-color: #E5F1FB; /* 浅科技蓝 */
                color: #0078D7;
                font-weight: bold;
            }
        """)

        self.main_layout.addWidget(self.combo)

    def _connect_signals(self):
        # 将原生的变化信号转发为我们自定义的更易用的信号
        self.combo.currentIndexChanged.connect(self._on_index_changed)

    def _on_index_changed(self, index):
        text = self.combo.currentText()
        self.selection_changed.emit(text, index)

    # --- 暴露给外部页面的业务接口 ---

    def get_value(self):
        """获取当前选中的文本"""
        return self.combo.currentText()

    def get_index(self):
        """获取当前选中的序号"""
        return self.combo.currentIndex()

    def set_items(self, new_items):
        """动态刷新下拉框选项"""
        self.combo.blockSignals(True)  # 刷新时不触发信号，避免死循环
        self.combo.clear()
        self.combo.addItems(new_items)
        self.combo.blockSignals(False)