from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from ui.components_new.option_groups.blue_optgrp import OptionGroup

# 导入毛玻璃容器和刚写好的下拉框组件
from ui.components_new.containers.white_translucent_container import WhiteTranslucentContainer
from ui.components_new.comboboxes.blue_up_subtitle_cb import LabeledComboBox


class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UI 组件沙盒测试 - 下拉框 (ComboBox)")
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

        # 1. 挂载第一个下拉框测试 (源语言)
        self.source_combo = LabeledComboBox(
            label_text="视频源语言 (Source Language)",
            items=["自动检测 (Auto Detect)", "英语 (English)", "日语 (Japanese)", "韩语 (Korean)"],
            default_index=0
        )
        self.glass_container.add_widget(self.source_combo)

        # 2. 挂载第二个下拉框测试 (目标语言)
        self.target_combo = LabeledComboBox(
            label_text="目标翻译语言 (Target Language)",
            items=["简体中文 (Simplified Chinese)", "英语 (English)", "西班牙语 (Spanish)"],
            default_index=0
        )
        self.glass_container.add_widget(self.target_combo)

        # 在 self.glass_container.add_stretch(1) 之前加入：

        # 测试 1: 多选模式 (方形，横向排列)
        self.export_group = OptionGroup(
            title="导出字幕格式 (允许多选)",
            options=["SRT", "TXT", "VTT"],
            default_checked=[0, 1],
            is_single_choice=False,
            orientation="horizontal"
        )
        self.glass_container.add_widget(self.export_group)

        # 测试 2: 单选模式 (圆形，纵向排列)
        self.engine_group = OptionGroup(
            title="AI 推理引擎 (单选)",
            options=["CPU 模式 (慢速, 兼容性好)", "CUDA 加速 (极速, 需 N 卡)", "MPS 加速 (Mac 专用)"],
            default_checked=[1],
            is_single_choice=True,
            orientation="vertical"
        )
        self.glass_container.add_widget(self.engine_group)
        # 添加弹性空间把下拉框顶在上面
        self.glass_container.add_stretch(1)

        #测试3，多个选项，测试网格
        self.lang_test = OptionGroup(
            title="目标语言测试 (3列网格)",
            options=["简体中文", "繁体中文", "英语", "日语", "韩语", "德语", "法语", "西班牙语", "俄语", "阿拉伯语",
                     "乌克兰语"],
            default_checked=[0, 2],
            is_single_choice=False,
            grid_columns=3  # 开启网格模式
        )
        self.glass_container.add_widget(self.lang_test)
        # 将容器加入主窗口
        main_layout.addWidget(self.glass_container)