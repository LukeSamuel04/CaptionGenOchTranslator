from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QHBoxLayout,
                               QComboBox, QLineEdit, QTextEdit)
from PySide6.QtCore import QTimer

# 导入我们刚刚编写的多状态按钮
from ui.components_new.buttons.multi_status_start_button import MultiStatusStartButton


class MultiStatusButtonTestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("沙盒测试 - 多状态调度按钮")
        self.resize(500, 400)
        self.setStyleSheet("background-color: #E8F0F6; font-family: 'Segoe UI', sans-serif;")

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # 1. 模拟的页面配置区 (用于测试运行时的锁定/解锁)
        self.mock_ui_group = QGroupBox("页面配置选项 (运行期间应被锁定)")
        self.mock_ui_group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #ccc; margin-top: 10px; }")
        mock_layout = QHBoxLayout(self.mock_ui_group)

        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["简体中文", "English", "日本語"])
        self.input_file = QLineEdit()
        self.input_file.setPlaceholderText("这里模拟文件路径输入框...")

        mock_layout.addWidget(self.combo_lang)
        mock_layout.addWidget(self.input_file)
        main_layout.addWidget(self.mock_ui_group)

        # 2. 模拟的日志输出区
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(
            "background-color: #2b2b2b; color: #00FF00; font-family: Consolas; border-radius: 4px; padding: 5px;")
        self.log_area.append(">>> 页面初始化完毕，按钮处于待机状态 (Idle)")
        main_layout.addWidget(self.log_area, stretch=1)

        # 3. 核心主角：多状态按钮
        self.task_btn = MultiStatusStartButton()
        main_layout.addWidget(self.task_btn)

        # 4. 信号缝合 (页面接管按钮的对外通信)
        self.task_btn.start_requested.connect(self._on_start_requested)
        self.task_btn.stop_requested.connect(self._on_stop_requested)

    # ==========================================
    # 模拟页面的 Controller 逻辑
    # ==========================================
    def _on_start_requested(self):
        self.log_area.append("\n[页面接收信号] start_requested! 准备启动任务...")

        # 1. 锁定页面其他 UI
        self.mock_ui_group.setEnabled(False)
        self.log_area.append("[页面动作] 已锁定配置选项区，防止用户误触。")

        # 2. 命令按钮进入运行状态
        self.task_btn.set_running()
        self.log_area.append("[页面动作] 已命令按钮切换至 Running 状态 (橙色)。试着悬停看看！")

    def _on_stop_requested(self):
        self.log_area.append("\n[页面接收信号] stop_requested! 用户已在弹窗中确认停止。")

        # 1. 命令按钮进入停止/结算状态
        self.task_btn.set_stopping()
        self.log_area.append("[页面动作] 已命令按钮切换至 Stopping 状态 (灰色禁用)。")
        self.log_area.append(">>> 正在模拟后台清理显存 (耗时 2 秒)...")

        # 2. 模拟后台 Scheduler 清理资源的耗时
        QTimer.singleShot(2000, self._on_mock_backend_cleaned_up)

    def _on_mock_backend_cleaned_up(self):
        self.log_area.append("\n[后台通知] 清理完毕，任务彻底终止！")

        # 1. 解锁页面 UI
        self.mock_ui_group.setEnabled(True)
        self.log_area.append("[页面动作] 已重新解锁配置选项区。")

        # 2. 命令按钮恢复待机状态
        self.task_btn.set_idle()
        self.log_area.append("[页面动作] 已命令按钮恢复 Idle 状态 (蓝色)。")