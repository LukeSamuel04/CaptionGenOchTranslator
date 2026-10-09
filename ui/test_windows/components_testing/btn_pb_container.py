import sys
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSlider, QLabel
from PySide6.QtCore import Qt

# 导入组件
from ui.components.buttons.rounded_blue_button import RoundedButton
from ui.components.progress_bars.colourful_progress_horved_pb import UniversalProgressBar
from ui.components.containers.white_translucent_container import WhiteTranslucentContainer


class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UI 组件沙盒测试 - 白蓝玻璃极简风")
        self.resize(550, 400)

        # 换用浅灰蓝色的渐变背景，以衬托半透明白色容器的通透感和弥散阴影
        self.setStyleSheet("""
            TestWindow {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                                  stop:0 #E8F0F6, stop:1 #D2E0EB);
            }
        """)

        # 主窗口的基础外层布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)

        # 1. 实例化白蓝色毛玻璃容器
        self.glass_container = WhiteTranslucentContainer()

        # --- 2. 将组件像拼图一样塞进容器肚子里 ---

        # 放入三个测试按钮
        self.glass_container.add_widget(RoundedButton("开始下载 (Primary)", "primary"))
        self.glass_container.add_widget(RoundedButton("暂停任务 (Secondary)", "secondary"))
        self.glass_container.add_widget(RoundedButton("强制终止 (Danger)", "danger"))

        # 用弹性空间把按钮和下方的进度条隔开一点距离
        self.glass_container.add_stretch(1)

        # 放入彩色悬浮进度条
        self.progress_bar = UniversalProgressBar(title="Llama 3.1 8B 模型下载测试")
        self.progress_bar.set_status_text("正在连接服务器...")
        self.glass_container.add_widget(self.progress_bar)

        # 放入测试滑块和提示文字
        tip_label = QLabel("拖动下方滑块，测试数值悬浮跟随效果：")
        tip_label.setStyleSheet("color: #666666; font-size: 12px; margin-top: 15px;")
        self.glass_container.add_widget(tip_label)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        # 滑块颜色适配科技蓝
        self.slider.setStyleSheet(
            "QSlider::handle:horizontal { background: #0078D7; width: 15px; margin: -5px 0; border-radius: 7px; }"
        )
        self.glass_container.add_widget(self.slider)
        self.slider.valueChanged.connect(self._on_slider_changed)

        # 3. 把组装好的整个大卡片放进窗口主布局
        main_layout.addWidget(self.glass_container)

    def _on_slider_changed(self, val):
        self.progress_bar.set_value(val)
        if val == 0:
            self.progress_bar.set_status_text("等待下载...")
        elif val < 100:
            speed = 2.0 + (val % 5) * 0.5
            self.progress_bar.set_status_text(f"下载中 - {speed:.1f} MB/s")
        else:
            self.progress_bar.set_status_text("下载完成！")