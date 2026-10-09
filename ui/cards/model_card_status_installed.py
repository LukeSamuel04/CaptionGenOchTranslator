import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal

# 引入我们刚才重构好的通用红叉按钮
from ui.components.buttons.close_or_cancel_X_button import CloseOrCancelXButton
from ui.components.containers.white_translucent_container import WhiteTranslucentContainer


class ModelCardStatusInstalled(QWidget):
    """
    模型管理卡片 (已安装状态专用)。
    极其轻量化，只负责展示模型基础信息，并提供右上角的卸载/删除功能。
    """
    # 专属的删除信号，直接向上层抛出 model_id
    delete_requested = Signal(str)

    def __init__(self, model_info: dict, parent=None):
        super().__init__(parent)
        self.model_info = model_info
        self.model_id = model_info.get("model_id", "unknown_model")

        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.container = WhiteTranslucentContainer(self)
        self.card_layout = QHBoxLayout()
        self.card_layout.setSpacing(12)

        # ====================
        # 左侧区：模型基础信息 (垂直排布)
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

        # 底部加一个弹簧，让左侧文字紧凑靠上
        self.info_layout.addStretch()

        # ====================
        # 右侧区：右上角删除按钮 + 右下角状态标签
        # ====================
        self.action_layout = QVBoxLayout()
        self.action_layout.setSpacing(0)

        # 1. 顶部：利用横向布局+弹簧，将删除按钮推到最右侧
        self.top_right_layout = QHBoxLayout()
        self.top_right_layout.addStretch()  # 左侧弹簧

        # 实例化通用红叉按钮
        self.delete_btn = CloseOrCancelXButton(tooltip_text="删除本地模型", icon_size=20)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        self.top_right_layout.addWidget(self.delete_btn)

        # 2. 底部：已安装的静态提示 (取代了原来的动态主按钮)
        self.installed_label = QLabel("已安装")
        self.installed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.installed_label.setFixedSize(80, 32)
        # 设计一个低调且不可点击的灰色样式
        self.installed_label.setStyleSheet("""
            QLabel {
                background-color: #EAEAEA;
                color: #A0A0A0;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
        """)

        # 组合右侧垂直布局
        self.action_layout.addLayout(self.top_right_layout)
        self.action_layout.addStretch()  # 中间加弹簧，把按钮顶在右上，标签压在右下
        self.action_layout.addWidget(self.installed_label, alignment=Qt.AlignmentFlag.AlignRight)

        # ====================
        # 总体组装
        # ====================
        self.card_layout.addLayout(self.info_layout, stretch=1)
        self.card_layout.addLayout(self.action_layout)

        self.container.add_layout(self.card_layout)
        self.main_layout.addWidget(self.container)

    def _on_delete_clicked(self):
        # 触发时，直接将带有自己名字的信号抛出
        self.delete_requested.emit(self.model_id)

    @staticmethod
    def _format_size(size_in_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024.0:
                if unit in ['B', 'KB']:
                    return f"{int(size_in_bytes)} {unit}"
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} PB"