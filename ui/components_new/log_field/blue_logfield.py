from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor


class LogPreviewPanel(QWidget):
    """
    白蓝极简风日志/预览面板
    支持色彩分级 (Info/Success/Error/Warning/Highlight)。
    新增特性：自带自动滚动和极简定制滚动条，支持极客风格单行覆盖刷新机制，完美解决进度刷屏问题。
    """

    def __init__(self, title="运行日志", max_lines=1000, parent=None):
        super().__init__(parent)
        self.title_text = title
        self.max_lines = max_lines

        # 预设的语义化颜色字典[cite: 13]
        self.colors = {
            "info": "#555555",  # 深灰 (常规信息)[cite: 13]
            "success": "#107C10",  # 微软绿 (成功提示)[cite: 13]
            "error": "#D13438",  # 警示红 (错误/崩溃)[cite: 13]
            "warning": "#D83B01",  # 亮橙色 (警告/跳过)[cite: 13]
            "highlight": "#0078D7"  # 科技蓝 (新增：用于强调进度条)
        }

        # 状态锁：记录最后一次输出是否为进度条，用于判断是否需要单行覆写
        self._is_last_log_progress = False

        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(6)

        # 1. 标题[cite: 13]
        if self.title_text:
            self.title_label = QLabel(self.title_text)
            self.title_label.setStyleSheet("color: #555555; font-size: 13px; font-weight: bold;")
            self.main_layout.addWidget(self.title_label)

        # 2. 日志文本区域[cite: 13]
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        # 性能保护：限制最大保存行数，防止几十万行日志卡死 UI[cite: 13]
        self.log_area.document().setMaximumBlockCount(self.max_lines)
        self.main_layout.addWidget(self.log_area)

        # 3. 注入极简样式与定制滚动条[cite: 13]
        self._apply_styles()

    def _apply_styles(self):
        # 整体面板样式：极浅的蓝灰底色，形成微微下陷的展示区视觉感[cite: 13]
        panel_style = """
            QTextEdit {
                background-color: rgba(245, 248, 250, 200);
                border: 1px solid rgba(0, 120, 215, 40);
                border-radius: 6px;
                padding: 8px;
                font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
                font-size: 13px;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border: 1px solid rgba(0, 120, 215, 100);
            }
        """

        # 极致美化的 Mac 风格细条滚动条[cite: 13]
        scrollbar_style = """
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 8px;
                margin: 2px 0 2px 0;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(0, 0, 0, 30);
                min-height: 30px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(0, 120, 215, 150); /* 悬停变蓝 */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px; /* 隐藏原生上下箭头 */
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """

        self.log_area.setStyleSheet(panel_style + scrollbar_style)

    # --- 外部业务接口 ---

    def append_log(self, text: str, level: str = "info"):
        """
        追加一行带颜色的普通日志。
        """
        # 一旦输出普通日志，立刻释放状态锁，确保后续的进度条能另起一行
        self._is_last_log_progress = False

        color = self.colors.get(level, self.colors["info"])
        html_text = text.replace('\n', '<br>')
        formatted_text = f'<span style="color: {color};">{html_text}</span>'

        self.log_area.append(formatted_text)
        self._scroll_to_bottom()

    def update_progress_line(self, prefix_text: str, current: int, total: int, level: str = "highlight"):
        """
        专门用于更新进度条的方法。
        利用 QTextCursor 精准选中当前行文本并覆写，保留换行符防止吞噬历史日志。
        """
        color = self.colors.get(level, self.colors["highlight"])

        # 安全计算百分比
        pct = 100 if total <= 0 else int((current / total) * 100)
        pct = max(0, min(100, pct))

        # 绘制无缝字符进度条 (设定总长度为 20 个字符)
        bar_length = 20
        filled_length = int((pct / 100) * bar_length)
        empty_length = bar_length - filled_length

        # 使用 Unicode 实体块和阴影块
        bar_str = '█' * filled_length + '░' * empty_length

        # 强制使用 Consolas 等宽字体包裹色块区域，确保严丝合缝
        formatted_text = (
            f'<span style="color: {color};">'
            f'{prefix_text} '
            f'<span style="font-family: Consolas, \'Courier New\', monospace;">[{bar_str}]</span>'
            f' {pct}%'
            f'</span>'
        )

        cursor = self.log_area.textCursor()

        if self._is_last_log_progress:
            # 核心修正：光标移至文档末尾，向左选中直到本行开头（KeepAnchor 相当于按住 Shift 键选取）
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)

            # 此时只删除了本行的纯文本，保留了上方的隐藏换行符
            cursor.removeSelectedText()
            cursor.insertHtml(formatted_text)
        else:
            # 如果上一行是普通日志，就正常追加，并锁上状态
            self.log_area.append(formatted_text)
            self._is_last_log_progress = True

        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """内部辅助方法：强制滚动条到底部"""
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_logs(self):
        """清空所有日志，并重置进度条状态"""
        self.log_area.clear()
        self._is_last_log_progress = False

    def get_all_logs(self):
        """获取纯文本日志（不含 HTML 颜色标签），供导出保存使用"""
        return self.log_area.toPlainText()