import sys
import os

# 动态获取项目根目录并加入系统路径，确保绝对导入能成功
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QScrollArea, QLabel
from PySide6.QtCore import Qt
from ui.cards.model_download_card import ModelDownloadCard
from ui.components_new.buttons.muti_status_download_button import DownloadUIState


class CardTestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("模型下载卡片 - UI 样式画廊")
        self.resize(800, 600)
        # 设置整个窗口的底色为极浅的蓝灰色，完美衬托白色半透明毛玻璃卡片
        self.setStyleSheet("background-color: #F0F4F8;")

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        title = QLabel("模型下载页卡片 UI 测试画廊")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #333333;")
        main_layout.addWidget(title)

        # ==========================================
        # 核心滚动区 (注入 Mac 极简风格滚动条)
        # ==========================================
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # 完美复用 logfield 的定制化 QSS
        scroll_area.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background: transparent; 
            }
            /* 隐形轨道 */
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 8px;
                margin: 0px;
            }
            /* 悬浮胶囊滑块 */
            QScrollBar::handle:vertical {
                background-color: rgba(0, 0, 0, 30);
                min-height: 30px;
                border-radius: 4px;
            }
            /* 悬停高亮 */
            QScrollBar::handle:vertical:hover {
                background-color: rgba(0, 120, 215, 150);
            }
            /* 隐藏丑陋的上下箭头 */
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        # 盛放卡片的内层容器
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(content_widget)
        # 右侧预留出 10px 边距，防止极简滚动条滑动时遮挡卡片的右侧按钮
        self.cards_layout.setContentsMargins(0, 0, 10, 0)
        self.cards_layout.setSpacing(20)

        # 挂载模拟卡片
        self._mount_mock_cards()

        # 底部加个弹簧，把卡片往上顶
        self.cards_layout.addStretch()

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # 底部用来显示点击信号的调试日志
        self.log_label = QLabel("等待交互...")
        self.log_label.setStyleSheet("color: #0078D7; font-weight: bold;")
        main_layout.addWidget(self.log_label)

    def _mount_mock_cards(self):
        """生成模拟数据并挂载卡片"""

        # --- 卡片 1：模拟正常未安装状态 ---
        mock_model_1 = {
            "model_id": "whisper-large-v3",
            "name": "Whisper Large-V3 (推荐)",
            "description": "OpenAI 发布的超大规模语音识别模型，极高准确率，完美应对复杂口音与多语种混说场景。",
            "files": [{"size_bytes": 3150000000}]  # 约 3GB
        }
        card1 = ModelDownloadCard(mock_model_1)
        card1.update_card_state(DownloadUIState.NORMAL)
        card1.action_requested.connect(self._on_card_action)
        self.cards_layout.addWidget(card1)

        # --- 卡片 2：模拟高速下载中的状态 ---
        mock_model_2 = {
            "model_id": "llama-3-8b",
            "name": "LLaMA 3.1 (8B 参数大语言模型)",
            "description": "Meta 最新开源的高效大语言模型，配合本地 GPU 可实现近乎实时的神经机器翻译与文本润色。",
            "files": [{"size_bytes": 4920000000}]  # 约 4.58GB
        }
        card2 = ModelDownloadCard(mock_model_2)
        # 先设为下载中状态
        card2.update_card_state(DownloadUIState.DOWNLOADING, downloaded_bytes=1500000000, total_bytes=4920000000)
        # 覆盖调用一次实时进度刷新，以显示动态的网速和具体文本
        card2.update_realtime_progress(downloaded_bytes=1500000000, total_bytes=4920000000, speed_kbps=12540.5)
        card2.action_requested.connect(self._on_card_action)
        self.cards_layout.addWidget(card2)

        # --- 卡片 3：模拟已经安装完成的状态 ---
        mock_model_3 = {
            "model_id": "qwen-2-7b",
            "name": "Qwen 2 (7B 通义千问)",
            "description": "阿里云通义千问第二代，中文理解能力极为优异，是中英双向互译的绝佳选择。",
            "files": [{"size_bytes": 4120000000}]
        }
        card3 = ModelDownloadCard(mock_model_3)
        card3.update_card_state(DownloadUIState.INSTALLED)
        card3.action_requested.connect(self._on_card_action)
        self.cards_layout.addWidget(card3)

    def _on_card_action(self, model_id, state):
        """捕获卡片发出的内部信号"""
        self.log_label.setText(f"[信号捕获] 点击了模型卡片 '{model_id}'，当前状态为: {state.name}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CardTestWindow()
    window.show()
    sys.exit(app.exec())