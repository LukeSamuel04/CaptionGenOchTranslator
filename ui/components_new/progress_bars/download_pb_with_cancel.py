from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtCore import Qt, Signal

# 导入你原有的通用进度条作为父类 (注意导入路径请根据你的实际情况微调)
from .colourful_progress_horved_pb import UniversalProgressBar
# 导入我们刚刚重构的独立红叉按钮组件 (注意导入路径请根据你的实际情况微调)
from ui.components_new.buttons.close_or_cancel_X_button import CloseOrCancelXButton


class DownloadProgressBarWithCancel(UniversalProgressBar):
    """
    带有取消按钮的定制版进度条。
    完美继承自 UniversalProgressBar，不污染底层通用组件。
    内部利用布局重组（将原生进度条与新按钮水平打包）实现扩展。
    """
    # 新增独立信号：当用户点击红叉时发射
    cancel_requested = Signal()

    def __init__(self, title="下载进度", show_floating_text=True, parent=None):
        # 1. 先让父类把原本的标题、状态、进度条全部画好
        super().__init__(title, show_floating_text, parent)

        # 2. 注入我们的“红叉”修改
        self._setup_cancel_ui()

    def _setup_cancel_ui(self):
        # --- A. 实例化通用的取消小按钮 ---
        # 尺寸默认已改为 20，这里直接传入 tooltip 和信号绑定即可
        self.cancel_btn = CloseOrCancelXButton(tooltip_text="取消下载", icon_size=20)
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)

        # --- B. 核心布局魔术：狸猫换太子 ---
        # 1. 从父类的垂直主布局 (main_layout) 中，把包含进度条的底层容器 (bar_container) 摘出来
        self.main_layout.removeWidget(self.bar_container)

        # 2. 新建一个横向布局，用来并排容纳：进度条容器 + 取消按钮
        self.pb_with_btn_layout = QHBoxLayout()
        self.pb_with_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.pb_with_btn_layout.setSpacing(10)  # 进度条和叉叉之间的呼吸间距

        # 3. 重新组装：左边是进度条容器（设为拉伸 stretch=1），右边是取消按钮
        self.pb_with_btn_layout.addWidget(self.bar_container, stretch=1)
        # 对齐到顶部，因为 bar_container 内部高度是 30px，这样叉叉能刚好和进度条色块对齐
        self.pb_with_btn_layout.addWidget(self.cancel_btn, alignment=Qt.AlignmentFlag.AlignTop)

        # 4. 把重组好的横向布局，塞回父类主布局的最下面
        self.main_layout.addLayout(self.pb_with_btn_layout)