import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QFrame, QMessageBox
from PySide6.QtCore import Qt

# 引入核心业务逻辑 (Core)
from core.download_logic.model_config_getter import ModelConfigGetter
from core.download_logic.model_download_checker import ModelDownloadChecker, DownloadStatus

# 引入独立网络请求线程
from workers.fetch_config import FetchConfigWorker
# 引入下载模型的核心 Worker
from workers.download_model import ModelDownloadWorker

# 引入精美的 UI 组件 (UI)
from ui.cards.model_download_card import ModelDownloadCard
from ui.components_new.buttons.muti_status_download_button import DownloadUIState
from ui.components_new.toggle_switches.ios_styled_ts import ToggleSwitch
from ui.components_new.buttons.muti_status_fetch_config_button import MultiStatusFetchConfigButton


class DownloadPage(QWidget):
    """
    模型下载主页面。
    聚合顶栏控制、模型卡片双列列表，并充当 UI 层与 Worker/Core 层的中枢调度器。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DownloadPage")

        self.config_getter = ModelConfigGetter()
        self.status_checker = ModelDownloadChecker()
        self.card_widgets = {}
        self.fetch_worker = None

        self.download_workers = {}

        self._setup_ui()
        self._load_local_data()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        # ==========================================
        # 1. 顶部操作栏 (Header)
        # ==========================================
        self.header_layout = QHBoxLayout()

        self.title_label = QLabel("AI 模型引擎管理")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333333;")
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()

        self.mirror_switch = ToggleSwitch(title="启用国内镜像加速", description="使用 HF-Mirror 节点")
        self.header_layout.addWidget(self.mirror_switch)
        self.header_layout.addSpacing(20)

        self.refresh_btn = MultiStatusFetchConfigButton()
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        self.header_layout.addWidget(self.refresh_btn)

        self.main_layout.addLayout(self.header_layout)

        # ==========================================
        # 2. 核心滚动列表区 (Scroll Area)
        # ==========================================
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # [核心修改 3] 将 ScrollBarAlwaysOff 改为 ScrollBarAsNeeded，赋予极端情况下的容错能力
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { border: none; background: transparent; width: 8px; margin: 0px; }
            QScrollBar::handle:vertical { background-color: rgba(0, 0, 0, 30); min-height: 30px; border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background-color: rgba(0, 120, 215, 150); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
            /* 补充简单的横向滚动条样式，以防它出现时显得突兀 */
            QScrollBar:horizontal { border: none; background: transparent; height: 8px; margin: 0px; }
            QScrollBar::handle:horizontal { background-color: rgba(0, 0, 0, 30); min-width: 30px; border-radius: 4px; }
            QScrollBar::handle:horizontal:hover { background-color: rgba(0, 120, 215, 150); }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { border: none; background: none; width: 0px; }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
        """)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 10, 0)

        self.empty_label = QLabel("暂无本地模型配置，请点击右上角获取云端更新。")
        self.empty_label.setStyleSheet("color: #888888; font-size: 14px;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.empty_label)

        # --- 左右双列排版容器 ---
        self.columns_widget = QWidget()
        self.columns_layout = QHBoxLayout(self.columns_widget)
        self.columns_layout.setContentsMargins(0, 0, 0, 0)
        self.columns_layout.setSpacing(10)

        # 左列：听写模型
        self.left_col_layout = QVBoxLayout()
        left_title = QLabel("阶段一：语音识别引擎 (必备)")
        left_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #555555; margin-bottom: 10px;")
        self.left_col_layout.addWidget(left_title)
        self.left_col_layout.addStretch()

        self.vline = QFrame()
        self.vline.setFrameShape(QFrame.Shape.VLine)
        self.vline.setFrameShadow(QFrame.Shadow.Plain)
        self.vline.setStyleSheet("color: #E0E0E0;")

        # 右列：翻译模型
        self.right_col_layout = QVBoxLayout()
        right_title = QLabel("阶段二：智能翻译引擎 (必备)")
        right_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #555555; margin-bottom: 10px;")
        self.right_col_layout.addWidget(right_title)
        self.right_col_layout.addStretch()

        self.columns_layout.addLayout(self.left_col_layout, stretch=1)
        self.columns_layout.addWidget(self.vline)
        self.columns_layout.addLayout(self.right_col_layout, stretch=1)

        self.content_layout.addWidget(self.columns_widget)
        self.columns_widget.setVisible(False)

        self.content_layout.addStretch()
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)

    # ==========================================
    # 数据加载与渲染逻辑
    # ==========================================
    def _load_local_data(self):
        cached_data = self.config_getter.read_local_cache()
        if cached_data and "models" in cached_data:
            self._render_cards(cached_data["models"])
        else:
            self._clear_cards()
            self.empty_label.setVisible(True)
            self.columns_widget.setVisible(False)

    def _render_cards(self, models_list: list):
        self._clear_cards()

        if not models_list:
            self.empty_label.setVisible(True)
            self.columns_widget.setVisible(False)
            return

        self.empty_label.setVisible(False)
        self.columns_widget.setVisible(True)

        for model_info in models_list:
            card = ModelDownloadCard(model_info)
            model_id = model_info.get("model_id", "")

            status_report = self.status_checker.check_status(model_info)
            ui_state = self._map_status_to_ui_state(status_report["status"])

            card.update_card_state(
                state=ui_state,
                downloaded_bytes=status_report["downloaded_bytes"],
                total_bytes=status_report["total_bytes"]
            )
            card.action_requested.connect(self._dispatch_card_action)

            if "whisper" in model_id.lower():
                self.left_col_layout.insertWidget(self.left_col_layout.count() - 1, card)
            else:
                self.right_col_layout.insertWidget(self.right_col_layout.count() - 1, card)

            self.card_widgets[model_id] = card

    def _clear_cards(self):
        for card in self.card_widgets.values():
            card.setParent(None)
            card.deleteLater()
        self.card_widgets.clear()

    @staticmethod
    def _map_status_to_ui_state(core_status_str: str) -> DownloadUIState:
        mapping = {
            DownloadStatus.NOT_INSTALLED.value: DownloadUIState.NORMAL,
            DownloadStatus.PARTIAL.value: DownloadUIState.RESUME,
            DownloadStatus.INSTALLED.value: DownloadUIState.INSTALLED,
            DownloadStatus.CORRUPTED.value: DownloadUIState.CORRUPTED
        }
        return mapping.get(core_status_str, DownloadUIState.NORMAL)

    # ==========================================
    # 异步网络请求与状态调度
    # ==========================================
    def _on_refresh_clicked(self):
        self.refresh_btn.set_fetching_state()

        self.fetch_worker = FetchConfigWorker()
        self.fetch_worker.success_signal.connect(self._on_fetch_success)
        self.fetch_worker.error_signal.connect(self._on_fetch_error)
        self.fetch_worker.finished.connect(self.fetch_worker.deleteLater)
        self.fetch_worker.start()

    def _on_fetch_success(self, new_data: dict):
        self.config_getter.save_to_cache(new_data)
        self._render_cards(new_data.get("models", []))
        self.refresh_btn.set_success_state()

    def _on_fetch_error(self, error_msg: str):
        self.refresh_btn.set_error_state(error_msg)

    # ==========================================
    # 交互调度中心 (Dispatcher)
    # ==========================================
    def _dispatch_card_action(self, model_id: str, current_state: DownloadUIState):
        use_mirror = self.mirror_switch.get_value()
        card = self.card_widgets.get(model_id)
        if not card:
            return

        print(f"\n--- [事件分发] 模型: {model_id} | 当前状态: {current_state.name} | 使用镜像: {use_mirror} ---")

        if current_state in (DownloadUIState.NORMAL, DownloadUIState.RESUME, DownloadUIState.CORRUPTED):
            # 1. 拦截并清理损坏文件
            if current_state == DownloadUIState.CORRUPTED:
                print("指令：清理本地损坏文件...")
                project_root = os.environ.get("APP_PROJECT_ROOT", "")
                install_dir_rel = card.model_info.get("install_dir", "")
                if project_root and install_dir_rel:
                    install_dir_abs = os.path.join(project_root, install_dir_rel.replace("/", os.sep))
                    for f_node in card.model_info.get("files", []):
                        corrupted_file = os.path.join(install_dir_abs, f_node["file_name"])
                        if os.path.exists(corrupted_file):
                            try:
                                os.remove(corrupted_file)
                            except OSError:
                                pass

            # 2. 视觉上立即切换为“正在下载”状态
            card.update_card_state(DownloadUIState.DOWNLOADING)

            # 3. 避免重复启动 Worker
            if model_id in self.download_workers:
                return

            print("指令：启动 Worker 线程开始/继续下载！")
            worker = ModelDownloadWorker(model_info=card.model_info, use_mirror=use_mirror)

            # 绑定所有的核心信号
            worker.progress_updated.connect(self._on_download_progress)
            worker.download_finished.connect(self._on_download_finished)
            worker.download_paused.connect(self._on_download_paused)
            worker.error_occurred.connect(self._on_download_error)

            self.download_workers[model_id] = worker
            worker.start()

        elif current_state == DownloadUIState.DOWNLOADING:
            print("指令：通知对应的 Worker 线程暂停下载！")
            card.update_card_state(DownloadUIState.RESUME)

            # 找到 Worker 并发起暂停指令
            worker = self.download_workers.get(model_id)
            if worker:
                worker.pause()

    # ==========================================
    # 下载 Worker 信号反馈槽函数
    # ==========================================
    def _on_download_progress(self, model_id: str, downloaded_bytes: int, total_bytes: int, speed_kbps: float):
        card = self.card_widgets.get(model_id)
        if card:
            card.update_realtime_progress(downloaded_bytes, total_bytes, speed_kbps)

    def _on_download_finished(self, model_id: str):
        card = self.card_widgets.get(model_id)
        if card:
            card.update_card_state(DownloadUIState.INSTALLED)
        self._cleanup_download_worker(model_id)

    def _on_download_paused(self, model_id: str):
        card = self.card_widgets.get(model_id)
        if card:
            card.update_card_state(DownloadUIState.RESUME)
        self._cleanup_download_worker(model_id)

    def _on_download_error(self, model_id: str, error_msg: str):
        card = self.card_widgets.get(model_id)
        if card:
            # 出错时退回可供重试的状态
            card.update_card_state(DownloadUIState.RESUME)
        QMessageBox.warning(self, "下载失败", f"模型 {model_id} 下载异常，请重试。\n详细信息: {error_msg}")
        self._cleanup_download_worker(model_id)

    def _cleanup_download_worker(self, model_id: str):
        """安全释放线程资源并从字典中移除"""
        if model_id in self.download_workers:
            worker = self.download_workers.pop(model_id)
            worker.deleteLater()