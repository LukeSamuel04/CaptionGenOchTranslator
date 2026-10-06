import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QMessageBox
from PySide6.QtCore import Qt

# 引入核心业务逻辑 (Core)
from core.download_logic.model_config_getter import ModelConfigGetter
from core.download_logic.model_download_checker import ModelDownloadChecker, DownloadStatus

# 引入精美的 UI 组件 (UI)
from ui.cards.model_download_card import ModelDownloadCard
from ui.components_new.buttons.muti_status_download_button import DownloadUIState
from ui.components_new.buttons.rounded_blue_button import RoundedButton
from ui.components_new.toggle_switches.ios_styled_ts import ToggleSwitch


class DownloadPage(QWidget):
    """
    模型下载主页面。
    负责聚合顶栏控制、模型卡片列表，并充当 UI 层与 Worker/Core 层的中枢调度器。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DownloadPage")

        # 实例化 Core 层的机制类
        self.config_getter = ModelConfigGetter()
        self.status_checker = ModelDownloadChecker()

        # 存放所有卡片实例的字典，方便后续根据 model_id 精准更新单张卡片
        self.card_widgets = {}

        self._setup_ui()

        # 页面初始化完成，极速读取本地缓存进行首次渲染
        self._load_local_data()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        # ==========================================
        # 1. 顶部操作栏 (Header)
        # ==========================================
        self.header_layout = QHBoxLayout()

        # 标题
        self.title_label = QLabel("AI 模型引擎管理")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333333;")
        self.header_layout.addWidget(self.title_label)

        self.header_layout.addStretch()  # 将后续组件推向右侧

        # 全局加速开关
        self.mirror_switch = ToggleSwitch(title="启用国内镜像加速", description="使用 HF-Mirror 节点")
        self.header_layout.addWidget(self.mirror_switch)

        # 留出一点呼吸间距
        self.header_layout.addSpacing(20)

        # 刷新/检查更新按钮
        self.refresh_btn = RoundedButton("检查云端更新", btn_type="secondary")
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        self.header_layout.addWidget(self.refresh_btn)

        self.main_layout.addLayout(self.header_layout)

        # ==========================================
        # 2. 核心滚动列表区 (Scroll Area)
        # ==========================================
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # 注入我们之前调优的 Mac 风极简滚动条 QSS
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { border: none; background: transparent; width: 8px; margin: 0px; }
            QScrollBar::handle:vertical { background-color: rgba(0, 0, 0, 30); min-height: 30px; border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background-color: rgba(0, 120, 215, 150); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        # 盛放卡片的内层容器
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.content_widget)
        self.cards_layout.setContentsMargins(0, 0, 10, 0)  # 右侧留 10px 避让滚动条
        self.cards_layout.setSpacing(20)

        # 无数据时的占位提示
        self.empty_label = QLabel("暂无本地模型配置，请点击右上角获取云端更新。")
        self.empty_label.setStyleSheet("color: #888888; font-size: 14px;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cards_layout.addWidget(self.empty_label)

        self.cards_layout.addStretch()  # 弹簧，把卡片往上顶

        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)

    # ==========================================
    # 数据加载与渲染逻辑
    # ==========================================
    def _load_local_data(self):
        """读取本地缓存的 JSON，并渲染卡片"""
        cached_data = self.config_getter.read_local_cache()
        if cached_data and "models" in cached_data:
            self._render_cards(cached_data["models"])
        else:
            # 没有缓存，显示空状态
            self._clear_cards()
            self.empty_label.setVisible(True)

    def _render_cards(self, models_list: list):
        """遍历模型配置，生成并挂载卡片组件"""
        self._clear_cards()
        self.empty_label.setVisible(False)

        for model_info in models_list:
            # 1. 实例化卡片
            card = ModelDownloadCard(model_info)
            model_id = model_info.get("model_id")

            # 2. 调用 Core 的 Checker 检查本地硬盘状态
            status_report = self.status_checker.check_status(model_info)

            # 3. 将 Core 层的状态映射为 UI 层的展示形态
            ui_state = self._map_status_to_ui_state(status_report["status"])

            # 4. 初始化卡片视图
            card.update_card_state(
                state=ui_state,
                downloaded_bytes=status_report["downloaded_bytes"],
                total_bytes=status_report["total_bytes"]
            )

            # 5. 挂载信号与布局
            card.action_requested.connect(self._dispatch_card_action)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)  # 插入在弹簧之前

            # 存入字典，未来 Worker 下载时可以通过 self.card_widgets[model_id] 直接刷新它
            self.card_widgets[model_id] = card

    def _clear_cards(self):
        """清空现有卡片（在强刷更新时使用）"""
        for card in self.card_widgets.values():
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self.card_widgets.clear()

    @staticmethod
    def _map_status_to_ui_state(core_status_str: str) -> DownloadUIState:
        """核心机制枚举转 UI 展示枚举"""
        mapping = {
            DownloadStatus.NOT_INSTALLED.value: DownloadUIState.NORMAL,
            DownloadStatus.PARTIAL.value: DownloadUIState.RESUME,
            DownloadStatus.INSTALLED.value: DownloadUIState.INSTALLED,
            DownloadStatus.CORRUPTED.value: DownloadUIState.CORRUPTED
        }
        return mapping.get(core_status_str, DownloadUIState.NORMAL)

    # ==========================================
    # 交互调度中心 (Dispatcher)
    # ==========================================
    def _on_refresh_clicked(self):
        """
        处理右上角刷新的点击。
        目前为了 MVP 先做个同步拦截提示，后续可以丢进 Worker 以免断网卡死。
        """
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("获取中...")

        try:
            # 直接调用 getter 的极简方法请求云端
            new_data = self.config_getter.fetch_remote_json()
            # 保存到本地缓存
            self.config_getter.save_to_cache(new_data)
            # 重新根据新数据渲染列表
            self._render_cards(new_data.get("models", []))

        except Exception as e:
            QMessageBox.warning(self, "更新失败", f"无法获取云端模型配置，请检查网络。\n详细信息: {str(e)}")
        finally:
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("检查云端更新")

    def _dispatch_card_action(self, model_id: str, current_state: DownloadUIState):
        """
        中枢分发器：接收所有卡片的点击信号，并决定如何调用 DownloadWorker。
        """
        use_mirror = self.mirror_switch.get_value()
        card = self.card_widgets.get(model_id)
        if not card:
            return

        print(f"\n--- [事件分发] 模型: {model_id} | 当前状态: {current_state.name} | 使用镜像: {use_mirror} ---")

        if current_state == DownloadUIState.NORMAL or current_state == DownloadUIState.RESUME:
            print("指令：启动 Worker 线程开始/继续下载！")
            # TODO: 实例化 DownloadWorker -> 连接 worker.progress 信号到 card.update_realtime_progress -> start()
            # 视觉上立即切换为“暂停/下载中”状态
            card.update_card_state(DownloadUIState.DOWNLOADING)

        elif current_state == DownloadUIState.DOWNLOADING:
            print("指令：通知对应的 Worker 线程暂停下载！")
            # TODO: 找到对应的 worker 并调用 worker.pause()
            card.update_card_state(DownloadUIState.RESUME)

        elif current_state == DownloadUIState.CORRUPTED:
            print("指令：清理本地损坏文件，并重新开始下载！")
            # TODO: 清理文件 -> 切换状态 -> 启动 Worker
            card.update_card_state(DownloadUIState.DOWNLOADING)