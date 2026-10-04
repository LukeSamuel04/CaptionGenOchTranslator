from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QProgressBar)
from PySide6.QtCore import Qt, Signal


class UniversalProgressBar(QWidget):
    """
    通用复合进度条组件
    支持：左侧标题、右侧状态提示、以及跟随进度条末端悬浮的数值显示。
    """
    progress_completed = Signal()  # 当进度达到最大值时向外发射

    def __init__(self, title="进度", show_floating_text=True, parent=None):
        super().__init__(parent)
        self.show_floating_text = show_floating_text
        self._setup_ui(title)

    def _setup_ui(self, title):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)

        # --- 1. 顶部信息栏：标题(左) 与 状态(右) ---
        self.header_layout = QHBoxLayout()

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; color: #E0E0E0; font-size: 13px;")

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #AAAAAA; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.status_label)

        self.main_layout.addLayout(self.header_layout)

        # --- 2. 进度条与悬浮文字容器 ---
        # 预留 30px 高度：进度条本身占 12px，下方留出空间给悬浮文字
        self.bar_container = QWidget()
        self.bar_container.setFixedHeight(30)

        # 纯净的进度条本体 (隐藏原生文字)
        self.progress_bar = QProgressBar(self.bar_container)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #333333;
                border-radius: 6px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #8BC34A; /* 匹配参考图的清爽绿色 */
                border-radius: 6px;
            }
        """)

        # 跟随进度的悬浮文字
        self.floating_label = QLabel("0", self.bar_container)
        self.floating_label.setStyleSheet("color: #8BC34A; font-weight: bold; font-size: 12px;")
        self.floating_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.floating_label.setVisible(self.show_floating_text)

        self.main_layout.addWidget(self.bar_container)

    def resizeEvent(self, event):
        """核心逻辑1：窗口大小变化时，进度条宽度自适应，并重新计算悬浮文字位置"""
        super().resizeEvent(event)
        # 固定进度条的 Y 坐标和高度，宽度撑满容器
        self.progress_bar.setGeometry(0, 2, self.bar_container.width(), 12)
        self._update_floating_label_pos()

    def _update_floating_label_pos(self):
        """核心逻辑2：动态计算悬浮文字的 X 坐标，使其吸附在色块末端"""
        if not self.show_floating_text or self.progress_bar.maximum() == 0:
            return

        # 计算当前进度的像素宽度
        ratio = self.progress_bar.value() / self.progress_bar.maximum()
        bar_width = self.progress_bar.width()

        # 动态获取文字的实际渲染宽度，留出边缘 Buffer
        text_width = self.floating_label.fontMetrics().horizontalAdvance(self.floating_label.text()) + 10
        self.floating_label.setFixedWidth(text_width)

        # 将文字中心点对准进度条色块的最右侧边缘
        x_pos = int(ratio * bar_width) - (text_width // 2)

        # 边缘防越界处理 (防止进度在 0% 或 100% 时文字超出窗口被裁切)
        if x_pos < 0:
            x_pos = 0
        elif x_pos + text_width > bar_width:
            x_pos = bar_width - text_width

        # 将文字定位在进度条正下方
        self.floating_label.move(x_pos, 16)

    # --- 外部调用接口 ---

    def set_value(self, value):
        """更新进度数值并触发重绘"""
        self.progress_bar.setValue(value)
        self.floating_label.setText(f"{value}")
        self._update_floating_label_pos()

        if value >= self.progress_bar.maximum():
            self.progress_completed.emit()

    def set_status_text(self, text):
        """更新右上角的网速或文件状态等提示"""
        self.status_label.setText(text)

    def set_theme(self, color_hex):
        """支持动态切换主题色（例如下载错误时变红，完成时变绿）"""
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #333333;
                border-radius: 6px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {color_hex};
                border-radius: 6px;
            }}
        """)
        self.floating_label.setStyleSheet(f"color: {color_hex}; font-weight: bold; font-size: 12px;")

    def set_range(self, min_val, max_val):
        self.progress_bar.setRange(min_val, max_val)
        self._update_floating_label_pos()