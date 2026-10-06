import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal

# 导入我们精心封装的底层 UI 组件
from ui.components_new.buttons.muti_status_download_button import MultiStatusDownloadButton, DownloadUIState
# 注意：以下两个导入路径请根据你实际的工程目录结构进行微调
from ui.components_new.progress_bars.colourful_progress_horved_pb import UniversalProgressBar
from ui.components_new.containers.white_translucent_container import WhiteTranslucentContainer


class ModelDownloadCard(QWidget):
    """
    模型下载卡片组件。
    负责渲染单个模型的信息、进度条，并管理多状态下载按钮。
    向外暴露 action_requested 信号，交由主页面调度 Worker 线程。
    """
    # 当按钮被点击时，向外发射信号：携带 (模型ID, 当前按钮所处的状态)
    action_requested = Signal(str, DownloadUIState)

    def __init__(self, model_info: dict, parent=None):
        super().__init__(parent)
        self.model_info = model_info
        self.model_id = model_info.get("model_id", "unknown_model")

        self._setup_ui()

    def _setup_ui(self):
        # 整体的主布局，消除边缘留白
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 1. 使用半透明毛玻璃容器作为卡片的底座
        self.container = WhiteTranslucentContainer(self)

        # 卡片内部使用横向布局：左(信息) - 中(进度) - 右(操作)
        self.card_layout = QHBoxLayout()
        self.card_layout.setSpacing(20)

        # ====================
        # 左侧区：模型基础信息
        # ====================
        self.info_layout = QVBoxLayout()
        self.info_layout.setSpacing(6)

        # 模型名称
        name = self.model_info.get("display_name", "未命名模型")
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("color: #333333; font-size: 16px; font-weight: bold;")

        # 模型描述 (支持自动换行)
        desc = self.model_info.get("description", "暂无描述")
        self.desc_label = QLabel(desc)
        self.desc_label.setStyleSheet("color: #666666; font-size: 13px;")
        self.desc_label.setWordWrap(True)
        self.desc_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # 预估总大小
        total_size_bytes = sum(f.get("size_bytes", 0) for f in self.model_info.get("files", []))
        self.size_label = QLabel(f"磁盘占用: {self._format_size(total_size_bytes)}")
        self.size_label.setStyleSheet("color: #888888; font-size: 12px;")

        self.info_layout.addWidget(self.name_label)
        self.info_layout.addWidget(self.desc_label)
        self.info_layout.addWidget(self.size_label)
        self.info_layout.addStretch()  # 把文字往上顶

        # ====================
        # 中间区：进度条 (按需显隐)
        # ====================
        self.progress_layout = QVBoxLayout()
        self.progress_bar = UniversalProgressBar(title="下载进度", show_floating_text=True)
        # 初始状态下隐藏进度条
        self.progress_bar.setVisible(False)

        self.progress_layout.addStretch()
        self.progress_layout.addWidget(self.progress_bar)
        self.progress_layout.addStretch()

        # ====================
        # 右侧区：多状态操作按钮
        # ====================
        self.action_layout = QVBoxLayout()
        self.action_btn = MultiStatusDownloadButton()
        # 绑定点击事件，向外层透传信号
        self.action_btn.clicked.connect(self._on_btn_clicked)

        self.action_layout.addStretch()
        self.action_layout.addWidget(self.action_btn)
        self.action_layout.addStretch()

        # 将三大区块按比例组装 (左侧占3份，中间占4份，右侧占1份固定宽度)
        self.card_layout.addLayout(self.info_layout, stretch=3)
        self.card_layout.addLayout(self.progress_layout, stretch=4)
        self.card_layout.addLayout(self.action_layout, stretch=1)

        # 把组装好的横向布局塞进毛玻璃容器里
        self.container.add_layout(self.card_layout)
        self.main_layout.addWidget(self.container)

    # ====================
    # 外部调用的业务接口
    # ====================
    def update_card_state(self, state: DownloadUIState, downloaded_bytes: int = 0, total_bytes: int = 1):
        """
        供上层页面调用：同步更新按钮颜色和进度条显隐。
        """
        # 更新按钮外观
        self.action_btn.update_status(state)

        # 进度条显隐与设值逻辑
        if state in [DownloadUIState.DOWNLOADING, DownloadUIState.RESUME]:
            self.progress_bar.setVisible(True)
            self.progress_bar.set_range(0, 100)

            # 计算百分比
            percent = 0 if total_bytes == 0 else int((downloaded_bytes / total_bytes) * 100)
            self.progress_bar.set_value(percent)

            # 状态文本
            status_text = f"{self._format_size(downloaded_bytes)} / {self._format_size(total_bytes)}"
            if state == DownloadUIState.RESUME:
                status_text = f"已暂停 | {status_text}"
            self.progress_bar.set_status_text(status_text)

            # 下载时显示蓝色，暂停时显示灰色
            theme_color = "#0078D7" if state == DownloadUIState.DOWNLOADING else "#888888"
            self.progress_bar.set_theme(theme_color)

        elif state == DownloadUIState.INSTALLED:
            self.progress_bar.setVisible(False)

        elif state == DownloadUIState.CORRUPTED:
            self.progress_bar.setVisible(True)
            self.progress_bar.set_value(100)
            self.progress_bar.set_status_text("校验失败，文件损坏")
            self.progress_bar.set_theme("#D13438")  # 红色

        else:  # NORMAL
            self.progress_bar.setVisible(False)

    def update_realtime_progress(self, downloaded_bytes: int, total_bytes: int, speed_kbps: float):
        """供 Worker 下载时高频调用的接口，刷新进度条和网速"""
        percent = 0 if total_bytes == 0 else int((downloaded_bytes / total_bytes) * 100)
        self.progress_bar.set_value(percent)

        speed_text = f"{speed_kbps / 1024:.1f} MB/s" if speed_kbps > 1024 else f"{speed_kbps:.1f} KB/s"
        status_text = f"{speed_text} | {self._format_size(downloaded_bytes)} / {self._format_size(total_bytes)}"
        self.progress_bar.set_status_text(status_text)

    # ====================
    # 内部辅助与槽函数
    # ====================
    def _on_btn_clicked(self):
        """捕获按钮点击，并将自身携带的 model_id 和当前状态抛给主页面去决策"""
        current_state = self.action_btn.get_current_state()
        self.action_requested.emit(self.model_id, current_state)

    @staticmethod
    def _format_size(size_in_bytes: int) -> str:
        """字节数格式化为人类可读的字符串"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024.0:
                if unit in ['B', 'KB']:
                    return f"{int(size_in_bytes)} {unit}"
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} PB"