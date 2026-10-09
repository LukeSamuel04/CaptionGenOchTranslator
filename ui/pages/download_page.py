import os
import shutil
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QFrame, QMessageBox
from PySide6.QtCore import Qt

# 引入核心业务逻辑 (Core)
from core.download_logic.model_config_getter import ModelConfigGetter
from core.download_logic.model_download_checker import ModelDownloadChecker, DownloadStatus

# 引入独立网络请求线程与 Worker
from workers.fetch_config import FetchConfigWorker
from workers.download_model import ModelDownloadWorker

# [核心修改] 引入全新的“两卡流”分离组件，取代原本臃肿的 ModelDownloadCard
from ui.cards.model_card_status_download import ModelCardStatusDownload
from ui.cards.model_card_status_installed import ModelCardStatusInstalled

from ui.components.buttons.muti_status_download_button import DownloadUIState
from ui.components.toggle_switches.ios_styled_ts import ToggleSwitch
from ui.components.buttons.muti_status_fetch_config_button import MultiStatusFetchConfigButton


class DownloadPage(QWidget):
    """
    模型下载主页面。
    聚合顶栏控制、模型卡片双列列表，并充当 UI 层与 Worker/Core 层的中枢调度器。
    具备卡片生命周期管理能力，实现下载卡与安装卡的无缝交接。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DownloadPage")

        self.config_getter = ModelConfigGetter()
        self.status_checker = ModelDownloadChecker()

        # 调度中心的“三大花名册”
        self.card_widgets = {}  # 存放当前正在显示的卡片实例
        self.card_layouts = {}  # 记录每个模型应该被插在左列还是右列
        self.models_info_cache = {}  # 缓存各个模型的原始配置字典，方便切卡时传递

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
        # [核心改动] 发放身份证号，移除 setStyleSheet
        self.scroll_area.setObjectName("downloadScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.content_widget = QWidget()
        # [核心改动] 发放身份证号，移除 background: transparent
        self.content_widget.setObjectName("downloadScrollContent")
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
    # 数据加载与“发牌官”逻辑
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
            model_id = model_info.get("model_id", "")
            category = model_info.get("category", "translation")

            self.models_info_cache[model_id] = model_info
            target_layout = self.right_col_layout if category == "translation" else self.left_col_layout
            self.card_layouts[model_id] = target_layout

            status_report = self.status_checker.check_status(model_info)
            card = self._create_card_by_status(model_info, status_report)

            target_layout.insertWidget(target_layout.count() - 1, card)
            self.card_widgets[model_id] = card

    def _create_card_by_status(self, model_info: dict, status_report: dict) -> QWidget:
        ui_state = self._map_status_to_ui_state(status_report["status"])

        if ui_state == DownloadUIState.INSTALLED:
            card = ModelCardStatusInstalled(model_info)
            card.delete_requested.connect(self._on_delete_requested)
            return card
        else:
            card = ModelCardStatusDownload(model_info)
            card.update_card_state(
                state=ui_state,
                downloaded_bytes=status_report["downloaded_bytes"],
                total_bytes=status_report["total_bytes"]
            )
            card.action_requested.connect(self._dispatch_card_action)
            card.cancel_download_requested.connect(self._on_cancel_requested)
            return card

    def _swap_card(self, model_id: str, new_status: DownloadStatus):
        old_card = self.card_widgets.get(model_id)
        if not old_card:
            return

        model_info = self.models_info_cache[model_id]
        layout = self.card_layouts[model_id]

        mock_report = {"status": new_status.value, "downloaded_bytes": 0, "total_bytes": 1}
        new_card = self._create_card_by_status(model_info, mock_report)

        idx = layout.indexOf(old_card)
        layout.insertWidget(idx, new_card)

        old_card.setParent(None)
        old_card.deleteLater()

        self.card_widgets[model_id] = new_card

    def _clear_cards(self):
        for card in self.card_widgets.values():
            card.setParent(None)
            card.deleteLater()
        self.card_widgets.clear()
        self.card_layouts.clear()
        self.models_info_cache.clear()

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
    # 异步网络请求
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
    # 交互调度中心 (Dispatcher & Terminator)
    # ==========================================
    def _dispatch_card_action(self, model_id: str, current_state: DownloadUIState):
        use_mirror = self.mirror_switch.get_value()
        card = self.card_widgets.get(model_id)
        if not card or not isinstance(card, ModelCardStatusDownload):
            return

        if current_state in (DownloadUIState.NORMAL, DownloadUIState.RESUME, DownloadUIState.CORRUPTED):
            if current_state == DownloadUIState.CORRUPTED:
                self._delete_model_files(model_id, only_partials=False)

            card.update_card_state(DownloadUIState.DOWNLOADING)

            if model_id in self.download_workers:
                return

            worker = ModelDownloadWorker(model_info=card.model_info, use_mirror=use_mirror)
            worker.progress_updated.connect(self._on_download_progress)
            worker.download_finished.connect(self._on_download_finished)
            worker.download_paused.connect(self._on_download_paused)
            worker.error_occurred.connect(self._on_download_error)

            self.download_workers[model_id] = worker
            worker.start()

        elif current_state == DownloadUIState.DOWNLOADING:
            card.update_card_state(DownloadUIState.RESUME)
            worker = self.download_workers.get(model_id)
            if worker:
                worker.pause()

    def _on_cancel_requested(self, model_id: str):
        reply = QMessageBox.question(
            self,
            "终止下载",
            f"确定要取消 [{model_id}] 的下载吗？\n已下载的碎片进度将被清除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            worker = self.download_workers.get(model_id)
            if worker:
                worker.pause()
                self._cleanup_download_worker(model_id)

            self._delete_model_files(model_id, only_partials=True)

            card = self.card_widgets.get(model_id)
            if isinstance(card, ModelCardStatusDownload):
                card.update_card_state(DownloadUIState.NORMAL)

    def _on_delete_requested(self, model_id: str):
        reply = QMessageBox.question(
            self,
            "删除模型",
            f"确定要彻底卸载模型 [{model_id}] 吗？\n此操作将释放本地磁盘空间且无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._delete_model_files(model_id, only_partials=False)
            self._swap_card(model_id, DownloadStatus.NOT_INSTALLED)

    def _delete_model_files(self, model_id: str, only_partials: bool = False):
        model_info = self.models_info_cache.get(model_id)
        if not model_info:
            return

        project_root = os.environ.get("APP_PROJECT_ROOT", "")
        install_dir_rel = model_info.get("install_dir", "")
        if not project_root or not install_dir_rel:
            return

        install_dir_abs = os.path.join(project_root, install_dir_rel.replace("/", os.sep))

        if only_partials:
            for f_node in model_info.get("files", []):
                part_file = os.path.join(install_dir_abs, f_node["file_name"] + ".part")
                if os.path.exists(part_file):
                    try:
                        os.remove(part_file)
                    except:
                        pass
        else:
            if os.path.exists(install_dir_abs):
                try:
                    shutil.rmtree(install_dir_abs)
                except:
                    pass

    # ==========================================
    # 下载 Worker 信号反馈槽函数
    # ==========================================
    def _on_download_progress(self, model_id: str, downloaded_bytes: int, total_bytes: int, speed_kbps: float):
        card = self.card_widgets.get(model_id)
        if isinstance(card, ModelCardStatusDownload):
            card.update_realtime_progress(downloaded_bytes, total_bytes, speed_kbps)

    def _on_download_finished(self, model_id: str):
        self._cleanup_download_worker(model_id)
        self._swap_card(model_id, DownloadStatus.INSTALLED)

    def _on_download_paused(self, model_id: str):
        card = self.card_widgets.get(model_id)
        if isinstance(card, ModelCardStatusDownload):
            card.update_card_state(DownloadUIState.RESUME)
        self._cleanup_download_worker(model_id)

    def _on_download_error(self, model_id: str, error_msg: str):
        card = self.card_widgets.get(model_id)
        if isinstance(card, ModelCardStatusDownload):
            card.update_card_state(DownloadUIState.RESUME)
        QMessageBox.warning(self, "下载失败", f"模型 {model_id} 下载异常，请重试。\n详细信息: {error_msg}")
        self._cleanup_download_worker(model_id)

    def _cleanup_download_worker(self, model_id: str):
        if model_id in self.download_workers:
            worker = self.download_workers.pop(model_id)
            worker.deleteLater()