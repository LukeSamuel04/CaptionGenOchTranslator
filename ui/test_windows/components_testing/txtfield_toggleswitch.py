from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt

# 导入毛玻璃容器、文本输入框和按钮组件
from ui.components_new.containers.white_translucent_container import WhiteTranslucentContainer
from ui.components_new.text_fields.blue_textfield import LabeledTextField
from ui.components_new.buttons.rounded_blue_button import RoundedButton
from ui.components_new.toggle_switches.ios_styled_ts import ToggleSwitch

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UI 组件沙盒测试 - 文本输入框")
        self.resize(500, 350)

        # 维持浅灰蓝色的渐变背景，以衬托半透明玻璃容器
        self.setStyleSheet("""
            TestWindow {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                                  stop:0 #E8F0F6, stop:1 #D2E0EB);
            }
        """)

        # 主窗口外层布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)

        # 实例化毛玻璃容器
        self.glass_container = WhiteTranslucentContainer()

        # 1. 挂载密码模式的输入框测试 (API Key)
        self.api_input = LabeledTextField(
            label_text="OpenAI API 密钥",
            placeholder_text="请输入 sk- 开头的密钥...",
            is_password=True
        )
        self.glass_container.add_widget(self.api_input)

        # 2. 挂载带默认值的常规输入框测试 (输出文件名)
        self.filename_input = LabeledTextField(
            label_text="输出字幕文件名",
            default_text="output_subtitle_v1.srt"
        )
        self.glass_container.add_widget(self.filename_input)

        self.glass_container.add_stretch(1)

        # 3. 挂载测试按钮，用于模拟任务开始/结束，动态触发只读状态
        self.toggle_lock_btn = RoundedButton("模拟启动 AI 任务 (锁定输入)", "primary")
        self.toggle_lock_btn.clicked.connect(self._on_toggle_lock_clicked)
        self.glass_container.add_widget(self.toggle_lock_btn)

        # 将容器加入主窗口
        main_layout.addWidget(self.glass_container)

        # 记录当前是否处于锁定状态
        self.is_locked = False
        # toggle switch测试
        self.gpu_switch = ToggleSwitch(
            title="启用 GPU 硬件加速",
            description="大幅提升视频处理速度，需要 NVIDIA 显卡支持",
            default_state=True
        )
        self.glass_container.add_widget(self.gpu_switch)
    def _on_toggle_lock_clicked(self):
        # 切换锁定状态
        self.is_locked = not self.is_locked

        # 同步改变两个输入框的只读状态
        self.api_input.set_readonly(self.is_locked)
        self.filename_input.set_readonly(self.is_locked)

        # 动态更新按钮的文本提示
        if self.is_locked:
            self.toggle_lock_btn.setText("任务运行中... (点击解锁)")
        else:
            self.toggle_lock_btn.setText("模拟启动 AI 任务 (锁定输入)")