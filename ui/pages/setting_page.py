from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel
from PySide6.QtCore import Qt

# 引入卡片底座
from ui.cards.setting_card import SettingCard

# 引入我们封装好的各类 UI 积木
from ui.components.comboboxes.blue_up_subtitle_cb import LabeledComboBox
from ui.components.toggle_switches.ios_styled_ts import ToggleSwitch
from ui.components.file_browsers.blue_file_browser import FileBrowseWidget
from ui.components.buttons.rounded_blue_button import RoundedButton


class SettingPage(QWidget):
    """
    全局设置页面。
    采用“卡片式”流式布局。页面本身只负责 UI 积木的实例化与拼装，
    具体的配置保存与读取将由后续的 SettingsManager 接管。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingPage")
        self._setup_ui()

    def _setup_ui(self):
        # 1. 页面主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        # 2. 页面大标题
        self.page_title = QLabel("全局设置")
        # 赋予一个特定的 ObjectName，方便后续在 QSS 中统一管理 (如 font-size: 24px; font-weight: bold;)
        self.page_title.setObjectName("pageMainTitle")
        # 临时写一个内联样式防丢失，后续可移入 common.qss
        self.page_title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.main_layout.addWidget(self.page_title)

        # 3. 核心滚动区域 (防止卡片过多时小屏幕显示不全)
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("settingScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # 承载所有卡片的内部容器
        self.content_widget = QWidget()
        self.content_widget.setObjectName("settingScrollContent")
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 20, 0)  # 右侧留出滚动条空间
        self.content_layout.setSpacing(20)  # 卡片之间的间距

        # ==========================================
        # 开始拼装卡片
        # ==========================================
        self._build_appearance_card()
        self._build_performance_card()
        self._build_network_storage_card()

        # 底部增加弹性空间，把所有卡片往上顶
        self.content_layout.addStretch()

        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)

    def _build_appearance_card(self):
        """构建：外观与个性化卡片"""
        card = SettingCard(title_text="外观与个性化")

        # 零件 1：系统语言
        self.lang_combo = LabeledComboBox(
            label_text="系统显示语言 (Language)",
            items=["简体中文", "English"]
        )

        # 零件 2：深色模式开关
        self.theme_switch = ToggleSwitch(
            title="启用深色模式 (Dark Mode)",
            description="开启后界面将切换为深色调，适合夜间使用。"
        )

        card.add_widget(self.lang_combo)
        card.add_widget(self.theme_switch)

        self.content_layout.addWidget(card)

    def _build_performance_card(self):
        """构建：硬件与核心性能卡片"""
        card = SettingCard(title_text="硬件与核心性能")

        # 零件 1：推理设备
        self.device_combo = LabeledComboBox(
            label_text="AI 推理设备 (Device)",
            items=["自动检测 (Auto)", "显卡加速 (CUDA GPU)", "处理器计算 (CPU)"]
        )

        # 零件 2：计算精度
        self.precision_combo = LabeledComboBox(
            label_text="模型计算精度 (Compute Type)",
            items=[
                "Float16 (推荐，平衡速度与显存)",
                "Int8 (省显存模式，适合低配电脑)",
                "Float32 (高精度，极度消耗资源)"
            ]
        )

        card.add_widget(self.device_combo)
        card.add_widget(self.precision_combo)

        self.content_layout.addWidget(card)

    def _build_network_storage_card(self):
        """构建：下载与网络卡片"""
        card = SettingCard(title_text="文件存储与网络")

        # 零件 1：全局镜像加速
        self.mirror_switch = ToggleSwitch(
            title="启用国内镜像加速",
            description="从云端拉取模型或更新时，优先使用 HF-Mirror 节点。"
        )

        # 零件 2：默认输出路径
        self.output_path_browser = FileBrowseWidget(
            label_text="默认字幕/翻译导出位置",
            mode="directory",
            placeholder="请选择默认保存文件夹..."
        )

        # 零件 3：清理缓存按钮 (使用危险警告色)
        self.clear_cache_btn = RoundedButton(
            text="一键清理所有模型与临时文件",
            btn_type="danger"
        )
        # 可以用一个水平布局把按钮推到右边，显得更精致
        # 或者直接放进去，看你希望按钮是占满宽度还是只占一半

        card.add_widget(self.mirror_switch)
        card.add_widget(self.output_path_browser)

        # 给清理按钮上面加一点点间距，将其与普通设置项隔开
        card.add_stretch(1)
        card.add_widget(self.clear_cache_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.content_layout.addWidget(card)

    # ==========================================
    # 占位：事件绑定区 (准备对接 SettingsManager)
    # ==========================================
    # 未来我们会在这里写类似下面的代码：
    # def _connect_signals(self):
    #     self.theme_switch.toggled.connect(SettingsManager.set_dark_mode)
    #     self.lang_combo.selection_changed.connect(SettingsManager.set_language)