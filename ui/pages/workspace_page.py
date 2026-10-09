import os
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QMessageBox, QLabel)
from PySide6.QtCore import Qt, QUrl

# 引入白蓝极简风组件
from ui.components.containers.white_translucent_container import WhiteTranslucentContainer
from ui.components.file_browsers.blue_file_browser import FileBrowseWidget
from ui.components.option_groups.blue_optgrp import OptionGroup
from ui.components.log_field.blue_logfield import LogPreviewPanel

# 引入带标题下拉框
from ui.components.comboboxes.blue_up_subtitle_cb import LabeledComboBox

# 引入多状态核心开关
from ui.components.buttons.multi_status_start_button import MultiStatusStartButton

# 引入后端调度器与数据契约
from schedulers.task_pipeline_scheduler import TaskPipelineScheduler, TaskMode, TaskConfig


class WorkspacePage(QWidget):
    """
    全新工作台页面 (Controller) - 终极形态
    职责：
    1. 负责收集用户配置，组装数据包裹 (TaskConfig)。
    2. 监听顶层任务模式下拉框，实现表单的动态折叠、联动与特定选项的智能置灰。
    3. 统筹 UI 的锁定与解锁，彻底释放底层多进程物理资源。
    4. 采用无弹窗的超链接沉浸式日志反馈。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # [核心新增]：颁发全局身份证，确保未来主题系统可精准控制该页面
        self.setObjectName("workspacePage")

        # 核心语言字典映射
        self.SUPPORTED_LANGS = {
            self.tr("简体中文 (Chinese Simplified)"): "zh",
            self.tr("繁体中文 (Chinese Traditional)"): "zh-tw",
            self.tr("英语 (English)"): "en",
            self.tr("日语 (日本語)"): "ja",
            self.tr("韩语 (한국어)"): "ko",
            self.tr("德语 (Deutsch)"): "de",
            self.tr("西班牙语 (Español)"): "es",
            self.tr("阿拉伯语 (العربية)"): "ar",
            self.tr("乌克兰语 (Українська)"): "uk"
        }
        self.lang_keys = list(self.SUPPORTED_LANGS.keys())
        self.lang_values = list(self.SUPPORTED_LANGS.values())

        # 后端调度器实例指针
        self.scheduler = None

        self._setup_ui()

        # 初始化时触发一次下拉框联动，设定初始的 UI 隐藏状态与置灰状态
        self._on_mode_changed(self.task_mode_cb.get_value(), self.task_mode_cb.get_index())

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)

        # ==========================================
        # 1. 顶部配置区 (毛玻璃容器)
        # ==========================================
        self.config_container = WhiteTranslucentContainer()

        # 1.0 全局指令下达器 (动态路由核心)
        task_modes = [
            "🎬 全自动翻译 (音视频 -> 听写 -> 翻译)",
            "🎙️ 仅提取原声 (音视频 -> 提取原声字幕)",
            "📝 仅翻译外挂字幕 (本地字幕 -> 翻译)"
        ]
        self.task_mode_cb = LabeledComboBox(self.tr("核心任务指令 (Task Mode)"), items=task_modes, default_index=0)
        self.task_mode_cb.selection_changed.connect(self._on_mode_changed)
        self.config_container.add_widget(self.task_mode_cb)

        # 1.1 文件路径选择器
        self.input_browser = FileBrowseWidget(
            label_text=self.tr("媒体或字幕输入文件 (Input File)"),
            mode="open_file",
            file_filter=self.tr("支持的文件 (*.mp4 *.mkv *.avi *.mov *.mp3 *.wav *.aac);;所有文件 (*.*)")
        )
        self.config_container.add_widget(self.input_browser)

        default_out_dir = os.path.abspath(os.path.join(os.getcwd(), "output_captions"))
        self.output_browser = FileBrowseWidget(
            label_text=self.tr("最终输出目录 (Output Directory)"),
            mode="directory",
            default_path=default_out_dir
        )
        self.config_container.add_widget(self.output_browser)

        # 1.2 目标语言 (网格布局) - 支持动态隐藏
        self.lang_group = OptionGroup(
            title=self.tr("目标语言 (Target Languages - 可多选)"),
            options=self.lang_keys,
            default_checked=[0, 2],
            is_single_choice=False,
            grid_columns=3
        )
        self.config_container.add_widget(self.lang_group)

        # 1.3 导出格式与模式 (横向组装) - 支持动态隐藏
        self.format_mode_widget = QWidget()
        format_mode_layout = QHBoxLayout(self.format_mode_widget)
        format_mode_layout.setContentsMargins(0, 0, 0, 0)

        self.format_group = OptionGroup(
            title=self.tr("文件格式"),
            options=["SRT", "WebVTT"],
            default_checked=[0],
            orientation="horizontal"
        )

        self.mode_group = OptionGroup(
            title=self.tr("排版模式"),
            options=[self.tr("纯原声"), self.tr("纯译文"), self.tr("双语对译")],
            default_checked=[1, 2],
            orientation="horizontal"
        )

        format_mode_layout.addWidget(self.format_group)
        format_mode_layout.addWidget(self.mode_group)
        format_mode_layout.addStretch()

        self.config_container.add_widget(self.format_mode_widget)
        main_layout.addWidget(self.config_container)

        # ==========================================
        # 2. 底部日志与控制区
        # ==========================================
        self.log_panel = LogPreviewPanel(title=self.tr("实时运行日志 (Console Log)"))
        # 允许 QTextBrowser (需在 blue_logfield.py 中修改) 直接点击链接打开本地文件夹
        if hasattr(self.log_panel.log_area, "setOpenExternalLinks"):
            self.log_panel.log_area.setOpenExternalLinks(True)

        main_layout.addWidget(self.log_panel, stretch=1)

        # 接入全新的多状态控制按钮
        self.task_btn = MultiStatusStartButton()
        self.task_btn.setMinimumHeight(45)
        main_layout.addWidget(self.task_btn)

        # === 核心信号缝合 ===
        self.task_btn.start_requested.connect(self._on_start_requested)
        self.task_btn.stop_requested.connect(self._on_stop_requested)

    # ==========================================
    # 核心交互：动态表单联动
    # ==========================================
    def _on_mode_changed(self, text: str, index: int):
        """当下发指令改变时，瞬间变形联动下方的操作面板"""
        if index == 0:  # 全自动翻译
            self.input_browser.file_filter = "音视频文件 (*.mp4 *.mkv *.avi *.mov *.mp3 *.wav *.aac);;所有文件 (*.*)"
            self.lang_group.setVisible(True)
            self.mode_group.setVisible(True)
            # 恢复“纯原声”选项的可点击状态
            self.mode_group.set_item_enabled(0, True)

        elif index == 1:  # 仅提取原声
            self.input_browser.file_filter = "音视频文件 (*.mp4 *.mkv *.avi *.mov *.mp3 *.wav *.aac);;所有文件 (*.*)"
            # 极简折叠：翻译配置项瞬间消失
            self.lang_group.setVisible(False)
            self.mode_group.setVisible(False)
            # 内部保持一致性，确保切回其他模式时状态正常
            self.mode_group.set_item_enabled(0, True)

        elif index == 2:  # 仅翻译外挂字幕
            self.input_browser.file_filter = "字幕与缓存文件 (*.json *.srt *.vtt);;所有文件 (*.*)"
            self.lang_group.setVisible(True)
            self.mode_group.setVisible(True)
            # 核心防御：在此模式下，原声已经存在，直接置灰禁用“纯原声”选项
            self.mode_group.set_item_enabled(0, False)

    # ==========================================
    # 数据校验与组装打包
    # ==========================================
    def validate_inputs(self, current_mode_index: int) -> bool:
        """全方位的参数合法性校验"""
        if not self.input_browser.get_path():
            QMessageBox.warning(self, self.tr("缺少输入"), self.tr("请先选择需要处理的文件！"))
            return False
        if not self.output_browser.get_path():
            QMessageBox.warning(self, self.tr("缺少输出"), self.tr("输出目录不能为空！"))
            return False
        if not self.format_group.get_selected_indices():
            QMessageBox.warning(self, self.tr("参数缺失"), self.tr("请至少选择一种字幕格式！"))
            return False

        # 针对翻译模式的联合校验
        if current_mode_index in [0, 2]:
            selected_modes = self.mode_group.get_selected_indices()
            if not selected_modes:
                QMessageBox.warning(self, self.tr("参数缺失"), self.tr("请至少选择一种排版模式！"))
                return False

            needs_translation = (1 in selected_modes) or (2 in selected_modes)
            if needs_translation and not self.lang_group.get_selected_indices():
                QMessageBox.warning(self, self.tr("参数缺失"), self.tr("当前需要 AI 翻译介入，请至少勾选一种目标语言！"))
                return False

            # 这条规则作为底层兜底，虽然 UI 上已经置灰了选项，但保留校验更安全
            if current_mode_index == 2 and 0 in selected_modes and len(selected_modes) == 1:
                QMessageBox.warning(self, self.tr("逻辑冲突"),
                                    self.tr("您当前处于'仅翻译'模式，排版不能只选择导出'纯原声'，请选择翻译模式！"))
                return False

        return True

    def _build_task_config(self, mode_idx: int) -> TaskConfig:
        """根据当前 UI 状态打包数据包裹"""
        format_mapping = {0: "srt", 1: "vtt"}
        selected_formats = [format_mapping[i] for i in self.format_group.get_selected_indices()]

        # 动态组装包裹内容
        if mode_idx == 1:
            # 仅提取原声时，后台强制以 original 模式落盘
            selected_langs = []
            selected_modes = ["original"]
        else:
            selected_langs = [self.lang_values[i] for i in self.lang_group.get_selected_indices()]
            mode_mapping = {0: "original", 1: "translated", 2: "bilingual"}
            selected_modes = [mode_mapping[i] for i in self.mode_group.get_selected_indices()]

        cache_dir = os.path.abspath(os.path.join(os.getcwd(), ".caption_cache"))
        os.makedirs(cache_dir, exist_ok=True)

        return TaskConfig(
            input_path=self.input_browser.get_path(),
            output_dir=self.output_browser.get_path(),
            target_langs=selected_langs,
            file_formats=selected_formats,
            export_modes=selected_modes,
            cache_dir=cache_dir
        )

    def _set_ui_enabled(self, enabled: bool):
        """统一锁定/解锁界面的输入控件"""
        self.config_container.setEnabled(enabled)

    # ==========================================
    # 状态机响应流转 (Controller 核心)
    # ==========================================
    def _on_start_requested(self):
        """响应按钮的开始请求"""
        mode_idx = self.task_mode_cb.get_index()

        if not self.validate_inputs(mode_idx):
            return

        self._set_ui_enabled(False)
        self.task_btn.set_running()
        self.log_panel.clear_logs()

        # 映射后端指令
        mode_mapping = {
            0: TaskMode.FULL_PIPELINE,
            1: TaskMode.TRANSCRIBE_ONLY,
            2: TaskMode.TRANSLATE_ONLY
        }
        mode_instruction = mode_mapping[mode_idx]
        config = self._build_task_config(mode_idx)

        # 唤醒多进程调度器
        self.scheduler = TaskPipelineScheduler(task_mode=mode_instruction, config=config)

        # 缝合跨进程通信桥梁
        self.scheduler.log_relay.connect(self.log_panel.append_log)
        self.scheduler.progress_relay.connect(self.log_panel.update_progress_line)
        self.scheduler.pipeline_finished.connect(self._on_task_finished)

        # 发射！
        self.scheduler.start_pipeline()

    def _on_stop_requested(self):
        """响应按钮的强行停止请求"""
        self.task_btn.set_stopping()
        if self.scheduler:
            self.scheduler.stop_pipeline()

    def _on_task_finished(self, success: bool, message: str):
        """响应后端的彻底完工/终止信号"""
        self._set_ui_enabled(True)
        self.task_btn.set_idle()

        # 核心防爆破：彻底清理多进程物理资源与底层通讯队列
        if self.scheduler:
            if hasattr(self.scheduler, "_cleanup_current_process"):
                self.scheduler._cleanup_current_process()
            self.scheduler.deleteLater()
            self.scheduler = None

        if success:
            # 去除烦人的弹窗，采用沉浸式超链接反馈
            if os.path.exists(message):
                folder_url = QUrl.fromLocalFile(message).toString()
                self.log_panel.append_log(
                    f'[系统] 🎉 任务圆满完成！字幕已落盘。<a href="{folder_url}" style="color: #107C10; text-decoration: underline;">点击此处立即打开输出文件夹</a>',
                    "success"
                )
            else:
                self.log_panel.append_log("[系统] 🎉 任务圆满完成！", "success")
        else:
            self.log_panel.append_log(f"[系统] ❌ 任务已终止。原因: {message}", "error")