from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QProgressBar, QTextEdit
)
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import Qt


class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.reset()  # 初始化时写入默认状态语

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 最外层容器
        group_box = QGroupBox(self.tr("实时监控与日志 (Monitor & Logs)"))
        group_layout = QVBoxLayout(group_box)
        group_layout.setSpacing(12)

        # ==========================================
        # 1. 进度条区域 (双轨制)
        # ==========================================
        # 1.1 听写引擎进度 (Whisper)
        dictation_layout = QHBoxLayout()
        self.dictation_label = QLabel(self.tr("听写进度: 0%"))
        self.dictation_label.setMinimumWidth(120)  # 固定宽度防止进度跳动时界面抖动
        self.dictation_progress = QProgressBar()
        self.dictation_progress.setValue(0)

        dictation_layout.addWidget(self.dictation_label)
        dictation_layout.addWidget(self.dictation_progress)

        # 1.2 翻译引擎进度 (ALMA)
        translation_layout = QHBoxLayout()
        self.translation_label = QLabel(self.tr("翻译进度: 0%"))
        self.translation_label.setMinimumWidth(120)
        self.translation_progress = QProgressBar()
        self.translation_progress.setValue(0)

        translation_layout.addWidget(self.translation_label)
        translation_layout.addWidget(self.translation_progress)

        # ==========================================
        # 2. 实时终端黑框 (Console Log)
        # ==========================================
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)  # 设为只读，防止用户乱敲字

        # 注入 CSS 样式，打造专业的深色代码终端风格
        self.log_console.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #CCCCCC;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                border-radius: 4px;
                padding: 8px;
            }
        """)

        # 组装
        group_layout.addLayout(dictation_layout)
        group_layout.addLayout(translation_layout)
        group_layout.addWidget(self.log_console)

        main_layout.addWidget(group_box)

    # ==========================================
    # 供外部 (Worker子线程) 调用的控制接口
    # ==========================================

    def add_log(self, message: str, level: str = "info"):
        """
        向终端黑框追加日志，并自动滚动到最底部。
        :param message: 日志内容
        :param level: 日志级别 (info/success/warning/error)，决定文字颜色
        """
        color_map = {
            "info": "#CCCCCC",  # 默认浅灰
            "success": "#4CAF50",  # 成功绿
            "warning": "#FFC107",  # 警告黄
            "error": "#F44336",  # 错误红
            "highlight": "#00BCD4"  # 强调青
        }
        hex_color = color_map.get(level, "#CCCCCC")

        # 使用简单的 HTML span 标签给文本上色
        html_msg = f'<span style="color: {hex_color};">{message}</span>'
        self.log_console.append(html_msg)

        # 自动将滚动条拉到最下方
        cursor = self.log_console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_console.setTextCursor(cursor)

    def update_dictation_progress(self, percent: int, text: str = None):
        """更新听写进度条"""
        self.dictation_progress.setValue(percent)
        if text:
            self.dictation_label.setText(text)
        else:
            self.dictation_label.setText(self.tr(f"听写进度: {percent}%"))

    def update_translation_progress(self, percent: int, text: str = None):
        """更新翻译进度条"""
        self.translation_progress.setValue(percent)
        if text:
            self.translation_label.setText(text)
        else:
            self.translation_label.setText(self.tr(f"翻译进度: {percent}%"))

    def reset(self):
        """每次点击'开始生成'时，清空之前的数据"""
        self.dictation_progress.setValue(0)
        self.translation_progress.setValue(0)
        self.dictation_label.setText(self.tr("听写进度: 0%"))
        self.translation_label.setText(self.tr("翻译进度: 0%"))
        self.log_console.clear()
        self.add_log(self.tr("[系统] 引擎就绪，等待任务指令..."), "highlight")