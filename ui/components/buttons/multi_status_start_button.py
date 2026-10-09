from PySide6.QtWidgets import QPushButton, QMessageBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor


class MultiStatusStartButton(QPushButton):
    """
    多状态任务控制按钮组件 (Stateful Task Control Button)

    职责：
    维护自身的 Idle(待机) / Running(运行) / Stopping(停止中) 三种视觉与交互状态。
    向上层页面暴露极其干净的两个信号，接管“防误触弹窗”等脏活累活。
    """

    # --- 对外暴露的极简通信信号 ---
    start_requested = Signal()  # 当处于“待机”状态且被点击时发射
    stop_requested = Signal()  # 当处于“运行”状态被点击，且用户在警告弹窗中点击“确认”后发射

    def __init__(self,
                 idle_text="🚀 开始生成",
                 running_text="⏹ 停止当前任务",
                 stopping_text="⏳ 正在安全终止...",
                 parent=None):
        super().__init__(parent)

        # 保存各状态下的文本配置
        self.idle_text = idle_text
        self.running_text = running_text
        self.stopping_text = stopping_text

        # 初始状态
        self._current_state = "idle"

        # 绑定自身的点击事件，在内部进行拦截和分发
        self.clicked.connect(self._on_clicked)

        # 默认进入待机状态
        self.set_idle()

    # ==========================================
    # 内部点击拦截器与逻辑路由
    # ==========================================
    def _on_clicked(self):
        if self._current_state == "idle":
            # 待机状态下，直接向外发射启动信号
            self.start_requested.emit()

        elif self._current_state == "running":
            # 运行状态下，拦截点击，弹出强警告二次确认框
            reply = QMessageBox.question(
                self.window(),  # 依附于主窗口，使其能在屏幕中央弹出
                "确认终止任务",
                "当前 AI 引擎正在高速运行中。\n\n强制终止可能会导致当前进度丢失。\n您确定要停止吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No  # 默认焦点在“否”上，防止误敲回车
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 只有用户明确同意，才向外发射停止信号
                self.stop_requested.emit()

        elif self._current_state == "stopping":
            # 停止中状态（按钮处于 disabled），理论上进不到这里，但写上作为防弹设计
            pass

    # ==========================================
    # 供页面调用的外部控制接口 (State Setters)
    # ==========================================
    def set_idle(self):
        """将按钮重置为蓝色待机状态"""
        self._current_state = "idle"
        self.setText(self.idle_text)
        self.setEnabled(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet(self._get_base_style() + self._get_idle_color())

    def set_running(self):
        """将按钮切换为橙色运行状态 (悬停变红)"""
        self._current_state = "running"
        self.setText(self.running_text)
        self.setEnabled(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet(self._get_base_style() + self._get_running_color())

    def set_stopping(self):
        """将按钮切换为灰色结算状态 (禁用点击)"""
        self._current_state = "stopping"
        self.setText(self.stopping_text)
        self.setEnabled(False)
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.setStyleSheet(self._get_base_style() + self._get_stopping_color())

    # ==========================================
    # QSS 样式表装配工厂 (复用白蓝极简规范)
    # ==========================================
    def _get_base_style(self):
        # 基础公共样式：6px 微圆角、充足的呼吸感内边距、清晰的加粗字体
        return """
            QPushButton {
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 15px;
                font-weight: bold;
                border: none;
            }
        """

    def _get_idle_color(self):
        # 深邃科技蓝 -> 悬停亮蓝 -> 按下深蓝
        return """
            QPushButton {
                background-color: #0078D7;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
        """

    def _get_running_color(self):
        # 运行中：警示橙色 -> 悬停转深红 (高危操作警告) -> 按下更深的红
        return """
            QPushButton {
                background-color: #F2994A;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #D13438;
            }
            QPushButton:pressed {
                background-color: #8C0000;
            }
        """

    def _get_stopping_color(self):
        # 结算中：深灰色禁用状态
        return """
            QPushButton:disabled {
                background-color: #333333;
                color: #777777;
            }
        """