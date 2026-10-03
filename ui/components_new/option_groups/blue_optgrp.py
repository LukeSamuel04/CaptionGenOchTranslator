from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QCheckBox, QRadioButton, QButtonGroup)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor


class OptionGroup(QWidget):
    """
    白蓝极简风复合选项组 (Option Group)
    极致纯净版：支持横向、纵向以及网格(Grid)排版，完美修复 Qt 圆形边框变形与残影 Bug。
    """
    # 选项改变时发射信号，传递当前选中的索引列表
    selection_changed = Signal(list)

    def __init__(self, title="", options=None, default_checked=None,
                 is_single_choice=False, orientation="vertical", grid_columns=0, parent=None):
        super().__init__(parent)
        self.title_text = title
        self.options = options if options else []
        self.default_checked = default_checked if default_checked else []
        self.is_single_choice = is_single_choice
        self.orientation = orientation
        self.grid_columns = grid_columns  # 新增：网格列数 (0表示不使用网格)

        self.buttons = []
        # 用于单选模式的互斥管理
        self.button_group = QButtonGroup(self) if self.is_single_choice else None

        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)

        # 1. 渲染标题 (如果有)
        if self.title_text:
            self.title_label = QLabel(self.title_text)
            self.title_label.setStyleSheet("color: #555555; font-size: 13px; font-weight: bold;")
            self.main_layout.addWidget(self.title_label)

        # 2. 准备选项容器布局 (横向、纵向或网格)
        if self.grid_columns > 0:
            self.options_layout = QGridLayout()
            self.options_layout.setHorizontalSpacing(20)
            self.options_layout.setVerticalSpacing(12)
        elif self.orientation == "horizontal":
            self.options_layout = QHBoxLayout()
            self.options_layout.setSpacing(12)
        else:
            self.options_layout = QVBoxLayout()
            self.options_layout.setSpacing(12)

        # 3. 动态生成选项按钮
        for i, text in enumerate(self.options):
            if self.is_single_choice:
                btn = QRadioButton(text)
                self.button_group.addButton(btn, i)
            else:
                btn = QCheckBox(text)

            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

            # 初始选中状态
            if i in self.default_checked:
                btn.setChecked(True)

            # 绑定信号
            btn.toggled.connect(self._on_button_toggled)

            self.buttons.append(btn)

            # 4. 根据布局模式挂载组件
            if self.grid_columns > 0:
                # 计算网格的行和列
                row, col = divmod(i, self.grid_columns)
                self.options_layout.addWidget(btn, row, col)
            else:
                self.options_layout.addWidget(btn)

        # 如果是横排且未启用网格，末尾加一个弹簧把选项往左挤
        if self.grid_columns == 0 and self.orientation == "horizontal":
            self.options_layout.addStretch()

        self.main_layout.addLayout(self.options_layout)

        # 5. 注入白蓝极简样式
        self._apply_styles()

    def _apply_styles(self):
        base_style = """
            QCheckBox, QRadioButton {
                color: #333333;
                font-size: 14px;
                spacing: 8px; /* 框与文字的间距 */
            }
        """

        # 多选框样式 (无勾号，纯净蓝方块)
        checkbox_style = """
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 1px solid rgba(0, 120, 215, 60);
                background-color: rgba(255, 255, 255, 200);
                margin: 0px; 
            }
            QCheckBox::indicator:hover {
                border: 1px solid #0078D7;
            }
            QCheckBox::indicator:checked {
                background-color: #0078D7;
                border: 1px solid #0078D7;
            }
        """

        # 单选框样式 (动态补偿宽高，确保外圈永远是完美的 16x16 圆形，彻底消灭残影)
        radio_style = """
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
                border-radius: 8px; /* 14 + 1 + 1 = 16，16的一半是8 */
                border: 1px solid rgba(0, 120, 215, 60);
                background-color: rgba(255, 255, 255, 200);
                margin: 0px;
            }
            QRadioButton::indicator:hover {
                border: 1px solid #0078D7;
            }
            QRadioButton::indicator:checked {
                width: 8px;   /* 缩小内部宽高以补偿粗边框 */
                height: 8px;
                border-radius: 8px; /* 8 + 4 + 4 = 16，16的一半依然是8，完美重合！ */
                border: 4px solid #0078D7; 
                background-color: #FFFFFF;
            }
            QRadioButton::indicator:checked:hover {
                /* 修复悬停时的边框抖动 */
                border: 4px solid #005A9E; 
            }
        """

        self.setStyleSheet(base_style + checkbox_style + radio_style)

    def _on_button_toggled(self, checked):
        # 任何选项发生改变，都把最新的选中列表抛出
        self.selection_changed.emit(self.get_selected_indices())

    # --- 外部业务接口 ---

    def get_selected_indices(self):
        """获取选中的索引列表"""
        selected = []
        for i, btn in enumerate(self.buttons):
            if btn.isChecked():
                selected.append(i)
        return selected

    def get_selected_texts(self):
        """获取选中的纯文本列表"""
        selected = []
        for btn in self.buttons:
            if btn.isChecked():
                selected.append(btn.text())
        return selected