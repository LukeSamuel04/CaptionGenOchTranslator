import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFileDialog
from PySide6.QtCore import Qt, Signal
from ui.components_new.buttons.rounded_blue_button import RoundedButton


class FileBrowseWidget(QWidget):
    """
    白蓝极简风文件/目录选择器
    强制只读输入框配合原生 QFileDialog，彻底杜绝非法路径导致的崩溃。
    """
    # 路径发生改变时向外发射信号
    path_changed = Signal(str)

    def __init__(self, label_text, mode="open_file", file_filter="All Files (*)",
                 placeholder="请点击右侧按钮选择路径...", default_path="", parent=None):
        super().__init__(parent)
        self.label_text = label_text
        self.mode = mode  # 可选: "open_file", "save_file", "directory"
        self.file_filter = file_filter
        self.placeholder = placeholder
        self.current_path = default_path

        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(6)

        # 1. 标题标签
        if self.label_text:
            self.title_label = QLabel(self.label_text)
            self.title_label.setStyleSheet("color: #555555; font-size: 13px; font-weight: bold;")
            self.main_layout.addWidget(self.title_label)

        # 2. 横向组合布局 (输入框 + 按钮)
        self.input_layout = QHBoxLayout()
        self.input_layout.setSpacing(8)

        # 只读的路径显示框
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        self.path_input.setPlaceholderText(self.placeholder)
        if self.current_path:
            self.path_input.setText(self.current_path)

        # 注入只读专属的极简 QSS 样式 (与 TextField 的只读状态统一)
        self.path_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(240, 244, 248, 200); 
                border: 1px solid rgba(0, 120, 215, 30);
                border-radius: 6px;
                padding: 8px 12px;
                color: #555555;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(0, 120, 215, 60); 
            }
        """)

        # 浏览按钮 (复用次级按钮 Secondary，保持视觉克制)
        self.browse_btn = RoundedButton("浏览...", btn_type="secondary")
        self.browse_btn.clicked.connect(self._on_browse_clicked)

        # 将组件按比例组装 (输入框拿全部弹性空间，按钮保持固定大小)
        self.input_layout.addWidget(self.path_input, stretch=1)
        self.input_layout.addWidget(self.browse_btn, stretch=0)

        self.main_layout.addLayout(self.input_layout)

    def _on_browse_clicked(self):
        """唤起系统原生的文件资源管理器"""
        selected_path = ""

        # 使用传入的 current_path 作为弹窗的默认打开位置，如果为空则默认桌面
        start_dir = self.current_path if self.current_path else os.path.expanduser("~")

        if self.mode == "open_file":
            selected_path, _ = QFileDialog.getOpenFileName(self, "选择文件", start_dir, self.file_filter)
        elif self.mode == "save_file":
            selected_path, _ = QFileDialog.getSaveFileName(self, "保存文件", start_dir, self.file_filter)
        elif self.mode == "directory":
            selected_path = QFileDialog.getExistingDirectory(self, "选择文件夹", start_dir)

        # 如果用户没有点取消，则更新路径并发射信号
        if selected_path:
            # 统一将路径分隔符转换为正斜杠，防止 Windows 反斜杠引发转义 Bug
            selected_path = selected_path.replace("\\", "/")
            self.set_path(selected_path)

    # --- 外部业务接口 ---

    def get_path(self):
        """获取当前选中的绝对路径"""
        return self.current_path

    def set_path(self, path):
        """使用代码强行设置路径，并触发 UI 更新和信号"""
        self.current_path = path
        self.path_input.setText(self.current_path)
        self.path_changed.emit(self.current_path)