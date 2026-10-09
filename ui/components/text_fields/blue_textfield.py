from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit
from PySide6.QtCore import Qt, Signal


class LabeledTextField(QWidget):
    """
    白蓝极简风带标题文本输入框
    支持密码模式和只读模式(ReadOnly)，在保证任务运行时无法修改的同时允许用户选中并复制内容。
    """
    # 当文本发生改变时向外发射信号
    text_changed = Signal(str)

    def __init__(self, label_text, placeholder_text="", default_text="",
                 is_password=False, is_readonly=False, parent=None):
        super().__init__(parent)
        self.label_text = label_text
        self.placeholder_text = placeholder_text
        self.default_text = default_text
        self.is_password = is_password
        self.initial_readonly = is_readonly

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(6)

        # 1. 标题标签
        self.title_label = QLabel(self.label_text)
        self.title_label.setStyleSheet("color: #555555; font-size: 13px; font-weight: bold;")
        self.main_layout.addWidget(self.title_label)

        # 2. 输入框本体
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(self.placeholder_text)
        self.input_field.setText(self.default_text)

        # 如果开启密码模式，则将字符显示为小圆点
        if self.is_password:
            self.input_field.setEchoMode(QLineEdit.EchoMode.Password)

        self.main_layout.addWidget(self.input_field)

        # 3. 注入白蓝极简样式
        self._apply_styles()

        # 4. 初始化只读状态
        self.set_readonly(self.initial_readonly)

    def _apply_styles(self):
        # 注意 QLineEdit[readOnly="true"] 属性选择器的使用，用来动态切换只读状态下的样式
        style = """
            QLineEdit {
                background-color: rgba(255, 255, 255, 200);
                border: 1px solid rgba(0, 120, 215, 60);
                border-radius: 6px;
                padding: 8px 12px;
                color: #333333;
                font-size: 14px;
            }
            /* 正常可输入状态下的聚焦高亮 */
            QLineEdit:focus {
                border: 1px solid #0078D7;
                background-color: #FFFFFF;
            }
            /* 只读状态：背景变暗退化为灰蓝色，文字变浅，边框弱化 */
            QLineEdit[readOnly="true"] {
                background-color: rgba(240, 244, 248, 200); 
                color: #777777;
                border: 1px solid rgba(0, 120, 215, 30);
            }
            /* 只读状态下点击，不再显示强烈的科技蓝边框，暗示无法输入 */
            QLineEdit[readOnly="true"]:focus {
                border: 1px solid rgba(0, 120, 215, 40); 
            }
        """
        self.input_field.setStyleSheet(style)

    def _connect_signals(self):
        self.input_field.textChanged.connect(self.text_changed.emit)

    # --- 外部业务接口 ---

    def get_text(self):
        """获取当前输入框的纯文本"""
        return self.input_field.text()

    def set_text(self, text):
        """用代码主动填充输入框"""
        self.input_field.setText(text)

    def set_readonly(self, is_readonly):
        """
        动态锁定/解锁输入框。
        当 AI 引擎开始任务时调用 set_readonly(True)，任务结束调用 set_readonly(False)。
        """
        self.input_field.setReadOnly(is_readonly)

        # [高级技巧] Qt 样式引擎刷新机制
        # 因为我们使用了 [readOnly="true"] 的 QSS 属性选择器，
        # 在代码里改变状态后，必须调用 unpolish 和 polish 强制刷新，否则颜色不会马上变。
        self.input_field.style().unpolish(self.input_field)
        self.input_field.style().polish(self.input_field)