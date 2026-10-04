from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from ui.components_new.option_groups.blue_optgrp import OptionGroup

# 导入毛玻璃容器和刚写好的下拉框组件
from ui.components_new.containers.white_translucent_container import WhiteTranslucentContainer
from ui.components_new.comboboxes.blue_up_subtitle_cb import LabeledComboBox


class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UI 组件沙盒测试 - 动态置灰与样式核对")
        self.resize(550, 700)

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

        # ==========================================
        # 1. 挂载控制器下拉框
        # ==========================================
        # 控制器 1: 用于测试单选组的置灰
        self.control_combo_1 = LabeledComboBox(
            label_text="测试控制器 1 (控制 AI 推理引擎单选组):",
            items=["默认：全部启用", "测试：禁用 'CUDA 加速' (查看是否自动取消选中)", "测试：禁用 'MPS 加速'"],
            default_index=0
        )
        self.glass_container.add_widget(self.control_combo_1)

        # 控制器 2: 用于测试多选组的置灰
        self.control_combo_2 = LabeledComboBox(
            label_text="测试控制器 2 (控制目标语言多选组):",
            items=["默认：全部启用", "测试：禁用 '简体中文' (查看自动取消选中)", "测试：禁用 '日语' 和 '韩语'"],
            default_index=0
        )
        self.glass_container.add_widget(self.control_combo_2)

        # ==========================================
        # 2. 挂载被控的选项组
        # ==========================================
        # 测试 1: 多选模式 (方形，横向排列) - 这个保持静态，作为对照组
        self.export_group = OptionGroup(
            title="导出字幕格式 (对照组，不受控制)",
            options=["SRT", "TXT", "VTT"],
            default_checked=[0, 1],
            is_single_choice=False,
            orientation="horizontal"
        )
        self.glass_container.add_widget(self.export_group)

        # 测试 2: 单选模式 (圆形，纵向排列) - 受 Controller 1 控制
        # 默认选中 Index 1 (CUDA)，这样可以测试禁用已选项的逻辑
        self.engine_group = OptionGroup(
            title="AI 推理引擎 (单选测试区)",
            options=["CPU 模式 (慢速, 兼容性好)", "CUDA 加速 (极速, 需 N 卡)", "MPS 加速 (Mac 专用)"],
            default_checked=[1],
            is_single_choice=True,
            orientation="vertical"
        )
        self.glass_container.add_widget(self.engine_group)

        # 测试3，多个选项，测试网格 - 受 Controller 2 控制
        # 默认选中 Index 0 (简中)，用于测试禁用已选项逻辑
        self.lang_test = OptionGroup(
            title="目标语言 (多选与网格测试区)",
            options=["简体中文", "繁体中文", "英语", "日语", "韩语", "德语", "法语", "西班牙语", "俄语", "阿拉伯语",
                     "乌克兰语"],
            default_checked=[0, 2],
            is_single_choice=False,
            grid_columns=3  # 开启网格模式
        )
        self.glass_container.add_widget(self.lang_test)

        # 添加弹性空间
        self.glass_container.add_stretch(1)
        main_layout.addWidget(self.glass_container)

        # ==========================================
        # 3. 绑定测试信号
        # ==========================================
        self.control_combo_1.selection_changed.connect(self._on_combo1_changed)
        self.control_combo_2.selection_changed.connect(self._on_combo2_changed)

    # ==========================================
    # 4. 测试逻辑槽函数
    # ==========================================
    def _on_combo1_changed(self, text: str, index: int):
        """测试单选框置灰逻辑"""
        if index == 0:
            # 恢复全部启用
            self.engine_group.set_item_enabled(1, True)
            self.engine_group.set_item_enabled(2, True)
        elif index == 1:
            # 禁用 Index 1，如果它当前被选中，会触发内部的强制取消机制
            self.engine_group.set_item_enabled(1, False)
            self.engine_group.set_item_enabled(2, True)
        elif index == 2:
            self.engine_group.set_item_enabled(1, True)
            self.engine_group.set_item_enabled(2, False)

    def _on_combo2_changed(self, text: str, index: int):
        """测试多选框与网格的置灰逻辑"""
        if index == 0:
            # 恢复全部启用
            self.lang_test.set_item_enabled(0, True)
            self.lang_test.set_item_enabled(3, True)
            self.lang_test.set_item_enabled(4, True)
        elif index == 1:
            # 禁用简中 (Index 0)
            self.lang_test.set_item_enabled(0, False)
            self.lang_test.set_item_enabled(3, True)
            self.lang_test.set_item_enabled(4, True)
        elif index == 2:
            # 禁用日语 (Index 3) 和韩语 (Index 4)
            self.lang_test.set_item_enabled(0, True)
            self.lang_test.set_item_enabled(3, False)
            self.lang_test.set_item_enabled(4, False)