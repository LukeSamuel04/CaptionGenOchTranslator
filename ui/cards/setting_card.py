from PySide6.QtWidgets import QLabel, QFrame
from PySide6.QtCore import Qt

# 引入我们之前封装好的白蓝半透明容器作为底座
from ui.components.containers.white_translucent_container import WhiteTranslucentContainer


class SettingCard(WhiteTranslucentContainer):
    """
    通用设置分类卡片 (Dumb Container)。
    继承自 WhiteTranslucentContainer，自带玻璃阴影和内边距排版。
    仅负责展示顶部的分类标题和分割线，没有任何业务逻辑。
    具体的设置交互控件(开关、下拉框等)由外部页面通过 add_widget() 动态注入。
    """

    def __init__(self, title_text: str, parent=None):
        super().__init__(parent)
        self.title_text = title_text
        self._setup_card_header()

    def _setup_card_header(self):
        # ==========================================
        # 1. 顶部标题标签
        # ==========================================
        self.title_label = QLabel(self.title_text)

        # 【关键架构】：绝不在 Python 里写 setStyleSheet，只赋予独立的 ID
        # 样式的控制权彻底交给外部的全局主题文件 (light.qss / dark.qss)
        self.title_label.setObjectName("settingCardTitle")

        # ==========================================
        # 2. 水平分割线
        # ==========================================
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.Shape.HLine)
        self.separator.setFrameShadow(QFrame.Shadow.Plain)

        # 同样只分配 ID，用于 QSS 控制线条颜色和粗细
        self.separator.setObjectName("settingCardSeparator")

        # ==========================================
        # 3. 将标题和分割线挂载到卡片内部
        # ==========================================
        # 复用父类 WhiteTranslucentContainer 提供的嵌套接口
        self.add_widget(self.title_label)
        self.add_widget(self.separator)

        # 注：因为 QVBoxLayout 是顺序排列的，外部页面在实例化此卡片后，
        # 继续调用 card.add_widget(xxx控件) 时，新控件自然会乖乖排在分割线的正下方。