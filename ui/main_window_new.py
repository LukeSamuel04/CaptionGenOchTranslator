from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QListWidget, QStackedWidget, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


# --- 占位区域：未来等页面开发完毕后，解开这里的注释进行真实导入 ---
from ui.pages.workspace_page import WorkspacePage
# from ui.pages.download_page import DownloadPage
# from ui.pages.settings_page import SettingsPage

class PlaceholderPage(QWidget):
    """通用的临时占位页面，用于在灰度更新期间替代尚未组装好的 UI"""

    def __init__(self, title_text):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel(f"{title_text}\n\n(新版白蓝极简风组件正在接入中...)")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(20)
        label.setFont(font)
        label.setStyleSheet("color: #777777;")
        layout.addWidget(label)


class MainWindowNew(QMainWindow):
    """
    全新极简架构主窗口
    职责严格限定为：绘制全局侧边栏导航 + 管理右侧多页面路由堆栈。
    """

    def __init__(self):
        super().__init__()
        # 继承原有的基础窗口设置[cite: 14]
        self.setWindowTitle(self.tr("CaptionGen Translator - 专业离线AI字幕引擎 (全新极简版)"))
        self.resize(1000, 700)
        self.setMinimumSize(950, 700)
        # 2. 调用居中！
        self.center_window()
        # 建立中央画布和主水平布局 (左右分栏)[cite: 14]
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 构建页面模块
        self._setup_sidebar()
        self._setup_stacked_widget()

        # 绑定导航路由信号[cite: 14]
        self.sidebar.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

    def _setup_sidebar(self):
        """搭建左侧导航栏 (无损迁移原有的优秀深色主题样式)"""
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(130)
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # 原汁原味保留的 QSS 样式[cite: 14]
        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                color: #dcdcdc;
                border: none;
                padding-top: 20px;
                font-size: 15px;
            }
            QListWidget::item {
                height: 50px;
                padding-left: 20px;
            }
            QListWidget::item:selected {
                background-color: #0078D7;
                color: white;
                font-weight: bold;
                border-left: 4px solid #00A2FF;
            }
            QListWidget::item:hover:!selected {
                background-color: #3f3f3f;
            }
        """)

        # 添加导航项目[cite: 14]
        self.sidebar.addItem(self.tr("工作台"))
        self.sidebar.addItem(self.tr("组件下载"))
        self.sidebar.addItem(self.tr("系统设置"))

        self.main_layout.addWidget(self.sidebar)

    def _setup_stacked_widget(self):
        """搭建右侧多页面栈"""
        self.stacked_widget = QStackedWidget()
        # 右侧内容区加一点边距，防止页面内容贴边[cite: 14]
        self.stacked_widget.setContentsMargins(20, 20, 20, 20)

        # TODO: 未来在这里将 PlaceholderPage 替换为真实的 WorkspacePage 等实例
        self.workspace_page = WorkspacePage()
        self.download_page = PlaceholderPage("组件下载")
        self.settings_page = PlaceholderPage("系统设置")

        self.stacked_widget.addWidget(self.workspace_page)
        self.stacked_widget.addWidget(self.download_page)
        self.stacked_widget.addWidget(self.settings_page)

        self.main_layout.addWidget(self.stacked_widget, stretch=1)

    def center_window(self):
        """将窗口移动到屏幕正中央"""
        # 获取当前屏幕的可用几何区域（自动扣除底部的 Windows 任务栏）
        screen_geometry = self.screen().availableGeometry()

        # 获取我们自己窗口的几何数据
        window_geometry = self.frameGeometry()

        # 把窗口的中心点，对齐到屏幕的中心点
        window_geometry.moveCenter(screen_geometry.center())

        # 真正移动窗口到计算好的左上角位置
        self.move(window_geometry.topLeft())