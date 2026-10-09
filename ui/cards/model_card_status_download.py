import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal

from ui.components.buttons.muti_status_download_button import MultiStatusDownloadButton, DownloadUIState
from ui.components.progress_bars.download_pb_with_cancel import DownloadProgressBarWithCancel
from ui.components.containers.white_translucent_container import WhiteTranslucentContainer


class ModelCardStatusDownload(QWidget):
    # 原有的主动作信号（下载、暂停、继续）
    action_requested = Signal(str, DownloadUIState)
    # [新增] 专门用于向上传递取消下载指令的信号
    cancel_download_requested = Signal(str)

    def __init__(self, model_info: dict, parent=None):
        super().__init__(parent)
        self.model_info = model_info
        self.model_id = model_info.get("model_id", "unknown_model")

        # 状态记忆体，用于在仅切换状态（如暂停）时维持进度条不归零
        self._current_downloaded = 0
        self._current_total = 1

        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.container = WhiteTranslucentContainer(self)
        self.card_layout = QHBoxLayout()
        self.card_layout.setSpacing(12)

        # ====================
        # 左侧区：模型基础信息 + 进度条 (垂直排布)
        # ====================
        self.info_layout = QVBoxLayout()
        self.info_layout.setSpacing(4)

        name = self.model_info.get("display_name", "未命名模型")
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        self.name_label.setWordWrap(True)
        self.name_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

        desc = self.model_info.get("description", "暂无描述")
        self.desc_label = QLabel(desc)
        self.desc_label.setStyleSheet("color: #666666; font-size: 12px;")
        self.desc_label.setWordWrap(True)
        self.desc_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

        total_size_bytes = sum(f.get("size_bytes", 0) for f in self.model_info.get("files", []))
        self.size_label = QLabel(f"磁盘占用: {self._format_size(total_size_bytes)}")
        self.size_label.setStyleSheet("color: #999999; font-size: 11px;")

        self.info_layout.addWidget(self.name_label)
        self.info_layout.addWidget(self.desc_label)
        self.info_layout.addWidget(self.size_label)

        # [核心替换] 使用带有取消按钮的定制化进度条
        self.progress_bar = DownloadProgressBarWithCancel(title="下载进度", show_floating_text=True)
        self.progress_bar.setVisible(False)
        # 捕获进度条内部发出的取消信号，转发给卡片的统一处理函数
        self.progress_bar.cancel_requested.connect(self._on_cancel_requested)

        self.info_layout.addSpacing(8)
        self.info_layout.addWidget(self.progress_bar)

        self.info_layout.addStretch()

        # ====================
        # 右侧区：多状态操作按钮
        # ====================
        self.action_layout = QVBoxLayout()
        self.action_btn = MultiStatusDownloadButton()
        self.action_btn.clicked.connect(self._on_btn_clicked)

        self.action_layout.addStretch()
        self.action_layout.addWidget(self.action_btn)
        self.action_layout.addStretch()

        self.card_layout.addLayout(self.info_layout, stretch=1)
        self.card_layout.addLayout(self.action_layout)

        self.container.add_layout(self.card_layout)
        self.main_layout.addWidget(self.container)

    def update_card_state(self, state: DownloadUIState, downloaded_bytes: int = None, total_bytes: int = None):
        self.action_btn.update_status(state)

        # 如果外部传了真实数据（如初始化校验状态时），则更新记忆体
        if downloaded_bytes is not None:
            self._current_downloaded = downloaded_bytes
        if total_bytes is not None:
            self._current_total = total_bytes

        if state in [DownloadUIState.DOWNLOADING, DownloadUIState.RESUME]:
            self.progress_bar.setVisible(True)
            self.progress_bar.set_range(0, 100)

            # 全程使用记忆体里的数据计算，确保暂停时进度绝不丢失
            percent = 0 if self._current_total == 0 else int((self._current_downloaded / self._current_total) * 100)
            self.progress_bar.set_value(percent)

            status_text = f"{self._format_size(self._current_downloaded)} / {self._format_size(self._current_total)}"
            if state == DownloadUIState.RESUME:
                status_text = f"已暂停 | {status_text}"
            self.progress_bar.set_status_text(status_text)

            theme_color = "#0078D7" if state == DownloadUIState.DOWNLOADING else "#888888"
            self.progress_bar.set_theme(theme_color)

        elif state == DownloadUIState.INSTALLED:
            self.progress_bar.setVisible(False)

        elif state == DownloadUIState.CORRUPTED:
            self.progress_bar.setVisible(True)
            self.progress_bar.set_value(100)
            self.progress_bar.set_status_text("校验失败，文件损坏")
            self.progress_bar.set_theme("#D13438")

        else:
            self.progress_bar.setVisible(False)

    def update_realtime_progress(self, downloaded_bytes: int, total_bytes: int, speed_kbps: float):
        # 每次收到高频的实时下载进度时，巩固记忆体
        self._current_downloaded = downloaded_bytes
        self._current_total = total_bytes

        percent = 0 if total_bytes == 0 else int((downloaded_bytes / total_bytes) * 100)
        self.progress_bar.set_value(percent)

        speed_text = f"{speed_kbps / 1024:.1f} MB/s" if speed_kbps > 1024 else f"{speed_kbps:.1f} KB/s"
        status_text = f"{speed_text} | {self._format_size(downloaded_bytes)} / {self._format_size(total_bytes)}"
        self.progress_bar.set_status_text(status_text)

    def _on_btn_clicked(self):
        current_state = self.action_btn.get_current_state()
        self.action_requested.emit(self.model_id, current_state)

    def _on_cancel_requested(self):
        # [新增] 将底层进度条的取消请求贴上模型 ID，向外（主页面）传递
        self.cancel_download_requested.emit(self.model_id)

    @staticmethod
    def _format_size(size_in_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024.0:
                if unit in ['B', 'KB']:
                    return f"{int(size_in_bytes)} {unit}"
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} PB"