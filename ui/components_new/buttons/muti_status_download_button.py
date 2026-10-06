from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from enum import Enum


class DownloadUIState(Enum):
    """定义按钮在 UI 层的视觉状态"""
    NORMAL = "NORMAL"  # 未安装 (蓝色: 下载)
    RESUME = "RESUME"  # 存在部分文件 (黄色/橙色: 继续下载)
    DOWNLOADING = "DOWNLOADING"  # 正在下载 (深灰色: 暂停)
    INSTALLED = "INSTALLED"  # 已安装 (浅灰色/禁用状态: 已安装)
    CORRUPTED = "CORRUPTED"  # 文件损坏 (红色: 重新下载)


class MultiStatusDownloadButton(QPushButton):
    """
    针对模型下载场景深度定制的多状态按钮。
    内置了不同下载阶段的文案与颜色映射，外部只需调用 update_status() 即可完成一键切换。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_state = None

        # 基础样式常量
        self.BASE_STYLE = """
            QPushButton {
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: bold;
                border: none;
            }
        """

        # 初始状态设为未安装
        self.update_status(DownloadUIState.NORMAL)

    def update_status(self, state: DownloadUIState):
        """
        核心方法：根据传入的状态枚举，动态切换按钮的文案、颜色和交互反馈
        """
        if self.current_state == state:
            return

        self.current_state = state
        self.setEnabled(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        if state == DownloadUIState.NORMAL:
            self.setText("下载")
            color_style = """
                QPushButton { background-color: #0078D7; color: #FFFFFF; }
                QPushButton:hover { background-color: #005A9E; }
                QPushButton:pressed { background-color: #004578; }
            """

        elif state == DownloadUIState.RESUME:
            self.setText("继续下载")
            # 科技橙色，提示用户有未完成的任务
            color_style = """
                QPushButton { background-color: #D83B01; color: #FFFFFF; }
                QPushButton:hover { background-color: #EA460D; }
                QPushButton:pressed { background-color: #A32A00; }
            """

        elif state == DownloadUIState.DOWNLOADING:
            self.setText("暂停")
            # 次级操作色 (深灰)，降低下载过程中的视觉干扰
            color_style = """
                QPushButton { background-color: #3F3F3F; color: #E0E0E0; }
                QPushButton:hover { background-color: #4F4F4F; }
                QPushButton:pressed { background-color: #2B2B2B; }
            """

        elif state == DownloadUIState.INSTALLED:
            self.setText("已安装")
            self.setEnabled(False)  # 已安装状态下按钮不可点击
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            color_style = """
                QPushButton:disabled { 
                    background-color: #E2E2E2; 
                    color: #A0A0A0; 
                }
            """

        elif state == DownloadUIState.CORRUPTED:
            self.setText("重新下载")
            # 警示红，提示文件异常
            color_style = """
                QPushButton { background-color: #D13438; color: #FFFFFF; }
                QPushButton:hover { background-color: #A80000; }
                QPushButton:pressed { background-color: #8C0000; }
            """
        else:
            color_style = ""

        self.setStyleSheet(self.BASE_STYLE + color_style)

    def get_current_state(self) -> DownloadUIState:
        """供外部获取当前按钮状态，以决定点击时执行什么业务逻辑"""
        return self.current_state