from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QTimer

# 导入毛玻璃容器、日志面板组件、按钮组件和文件浏览组件
from ui.components.containers.white_translucent_container import WhiteTranslucentContainer
from ui.components.log_field.blue_logfield import LogPreviewPanel
from ui.components.buttons.rounded_blue_button import RoundedButton
from ui.components.file_browsers.blue_file_browser import FileBrowseWidget


class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UI 组件沙盒测试 - 日志与文件浏览")
        # 稍微加宽一点窗口，以容纳新增的测试按钮
        self.resize(750, 520)

        # 维持浅灰蓝色的渐变背景，以衬托半透明玻璃容器
        self.setStyleSheet("""
            TestWindow {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                                  stop:0 #E8F0F6, stop:1 #D2E0EB);
            }
        """)

        # 主窗口外层布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)

        # 实例化毛玻璃容器
        self.glass_container = WhiteTranslucentContainer()

        # ==========================================
        # 1. 顶部：文件控制器测试区
        # ==========================================
        self.video_browser = FileBrowseWidget(
            label_text="输入视频文件",
            mode="open_file",
            file_filter="视频文件 (*.mp4 *.mkv *.avi);;所有文件 (*.*)"
        )
        self.glass_container.add_widget(self.video_browser)

        self.output_dir_browser = FileBrowseWidget(
            label_text="批量输出目录",
            mode="directory"
        )
        self.glass_container.add_widget(self.output_dir_browser)

        # ==========================================
        # 2. 中间：日志面板测试区
        # ==========================================
        self.log_panel = LogPreviewPanel(title="任务执行日志", max_lines=500)
        # 使用 stretch=1 让日志面板把所有多余的垂直空间撑满
        self.glass_container.add_widget(self.log_panel, stretch=1)

        # ==========================================
        # 3. 底部：控制按钮区
        # ==========================================
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_info = RoundedButton("普通信息", "primary")
        self.btn_success = RoundedButton("成功状态", "primary")
        self.btn_warn = RoundedButton("警告状态", "secondary")
        self.btn_error = RoundedButton("报错信息", "danger")
        self.btn_progress = RoundedButton("模拟进度条", "primary")  # 新增：进度条触发按钮
        self.btn_clear = RoundedButton("清空", "secondary")

        btn_layout.addWidget(self.btn_info)
        btn_layout.addWidget(self.btn_success)
        btn_layout.addWidget(self.btn_warn)
        btn_layout.addWidget(self.btn_error)
        btn_layout.addWidget(self.btn_progress)
        btn_layout.addWidget(self.btn_clear)

        self.glass_container.add_layout(btn_layout)

        # 将组装好的容器加入主窗口
        main_layout.addWidget(self.glass_container)

        # ==========================================
        # 初始化定时器 (用于模拟后台进度的飞速刷新)
        # ==========================================
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self._on_progress_tick)
        self.current_progress = 0

        # 连接测试按钮信号
        self._connect_signals()

        # 写入几条初始启动日志
        self.log_panel.append_log(">>> UI 组件沙盒测试环境初始化...", "info")
        self.log_panel.append_log(">>> 极客风格进度条功能已就绪，请点击下方【模拟进度条】测试。", "success")

    def _connect_signals(self):
        # 普通日志写入测试
        self.btn_info.clicked.connect(
            lambda: self.log_panel.append_log("正在解析视频文件参数: input_video.mp4", "info")
        )
        self.btn_success.clicked.connect(
            lambda: self.log_panel.append_log("音频提取成功，用时 1.34s", "success")
        )
        self.btn_warn.clicked.connect(
            lambda: self.log_panel.append_log("发现部分静音片段，时间轴已自动跳过", "warning")
        )
        self.btn_error.clicked.connect(
            lambda: self.log_panel.append_log("API 连接超时！请检查网络设置或代理", "error")
        )
        self.btn_clear.clicked.connect(self.log_panel.clear_logs)

        # 绑定进度条测试按钮
        self.btn_progress.clicked.connect(self._start_progress_simulation)

    def _start_progress_simulation(self):
        """启动进度条模拟"""
        if not self.progress_timer.isActive():
            self.current_progress = 0
            self.log_panel.append_log("开始请求本地大语言模型进行翻译...", "warning")
            # 设定每 40 毫秒跳动一次，模拟高频刷新
            self.progress_timer.start(40)

    def _on_progress_tick(self):
        """定时器回调：高频更新单行进度条"""
        self.current_progress += 1
        if self.current_progress <= 100:
            # 核心测试：调用新的进度条方法
            self.log_panel.update_progress_line("[ALMA] 正在翻译时间轴", self.current_progress, 100)
        else:
            self.progress_timer.stop()
            self.log_panel.append_log("[系统] 当前翻译任务全部完成！", "success")