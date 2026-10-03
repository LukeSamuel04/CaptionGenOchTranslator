import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

# 引入白蓝极简风组件
from ui.components_new.containers.white_translucent_container import WhiteTranslucentContainer
from ui.components_new.file_browsers.blue_file_browser import FileBrowseWidget
from ui.components_new.option_groups.blue_optgrp import OptionGroup
from ui.components_new.log_field.blue_logfield import LogPreviewPanel
from ui.components_new.buttons.rounded_blue_button import RoundedButton

# 引入后台工作线程
from ui.workers.ai_task_worker import AITaskWorker


class WorkspacePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 核心语言字典映射
        self.SUPPORTED_LANGS = {
            self.tr("简体中文 (Chinese Simplified)"): "zh",
            self.tr("繁体中文 (Chinese Traditional)"): "zh-tw",
            self.tr("英语 (English)"): "en",
            self.tr("日语 (日本語)"): "ja",
            self.tr("韩语 (한국어)"): "ko",
            self.tr("德语 (Deutsch)"): "de",
            self.tr("法语 (Français)"): "fr",
            self.tr("西班牙语 (Español)"): "es",
            self.tr("俄语 (Русский)"): "ru",
            self.tr("阿拉伯语 (العربية)"): "ar",
            self.tr("乌克兰语 (Українська)"): "uk"
        }
        self.lang_keys = list(self.SUPPORTED_LANGS.keys())
        self.lang_values = list(self.SUPPORTED_LANGS.values())

        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)

        # ==========================================
        # 1. 顶部配置区 (毛玻璃容器)
        # ==========================================
        self.config_container = WhiteTranslucentContainer()

        # 1.1 文件路径选择器
        self.input_browser = FileBrowseWidget(
            label_text=self.tr("媒体输入文件 (Video/Audio)"),
            mode="open_file",
            file_filter=self.tr("音视频文件 (*.mp4 *.mkv *.avi *.mov *.mp3 *.wav *.aac);;所有文件 (*.*)")
        )
        self.config_container.add_widget(self.input_browser)

        default_out_dir = os.path.abspath(os.path.join(os.getcwd(), "output_captions"))
        self.output_browser = FileBrowseWidget(
            label_text=self.tr("字幕输出目录 (Output Directory)"),
            mode="directory",
            default_path=default_out_dir
        )
        self.config_container.add_widget(self.output_browser)

        # 1.2 目标语言 (网格布局 OptionGroup)
        self.lang_group = OptionGroup(
            title=self.tr("目标语言 (Target Languages - 可多选)"),
            options=self.lang_keys,
            default_checked=[0, 2],  # 默认勾选简中和英语
            is_single_choice=False,
            grid_columns=3
        )
        self.config_container.add_widget(self.lang_group)

        # 1.3 导出格式与模式 (横向组装)
        format_mode_layout = QHBoxLayout()

        self.format_group = OptionGroup(
            title=self.tr("文件格式"),
            options=["SRT", "WebVTT"],
            default_checked=[0],  # 默认选 SRT
            orientation="horizontal"
        )

        self.mode_group = OptionGroup(
            title=self.tr("排版模式"),
            options=[self.tr("纯原声"), self.tr("纯译文"), self.tr("双语对译")],
            default_checked=[1, 2],  # 默认选纯译文和双语
            orientation="horizontal"
        )

        format_mode_layout.addWidget(self.format_group)
        format_mode_layout.addWidget(self.mode_group)
        format_mode_layout.addStretch()

        self.config_container.add_layout(format_mode_layout)
        main_layout.addWidget(self.config_container)

        # ==========================================
        # 2. 底部日志与控制区
        # ==========================================
        self.log_panel = LogPreviewPanel(title=self.tr("实时运行日志 (Console Log)"))
        main_layout.addWidget(self.log_panel, stretch=1)

        self.start_btn = RoundedButton(self.tr("开始生成 (Start Generation)"), btn_type="primary")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.clicked.connect(self._on_start_clicked)
        main_layout.addWidget(self.start_btn)

    # ==========================================
    # 数据校验与组装逻辑
    # ==========================================
    def validate_inputs(self) -> bool:
        """全方位的参数合法性校验"""
        if not self.input_browser.get_path():
            QMessageBox.warning(self, self.tr("警告"), self.tr("请先选择需要处理的音视频文件！"))
            return False

        if not self.output_browser.get_path():
            QMessageBox.warning(self, self.tr("警告"), self.tr("输出目录不能为空！"))
            return False

        selected_modes = self.mode_group.get_selected_indices()
        if not selected_modes:
            QMessageBox.warning(self, self.tr("警告"), self.tr("请至少选择一种排版模式！"))
            return False

        if not self.format_group.get_selected_indices():
            QMessageBox.warning(self, self.tr("警告"), self.tr("请至少选择一种字幕格式！"))
            return False

        # 校验：选择翻译或双语模式时，必须勾选至少一种目标语言
        needs_translation = (1 in selected_modes) or (2 in selected_modes)
        if needs_translation and not self.lang_group.get_selected_indices():
            QMessageBox.warning(self, self.tr("警告"), self.tr("导出模式包含了翻译需求，请至少勾选一种目标语言！"))
            return False

        return True

    def get_configuration(self) -> dict:
        """打包用户的配置，生成向底层引擎传递的数据结构"""
        selected_langs = [self.lang_values[i] for i in self.lang_group.get_selected_indices()]

        format_mapping = {0: "srt", 1: "vtt"}
        selected_formats = [format_mapping[i] for i in self.format_group.get_selected_indices()]

        mode_mapping = {0: "original", 1: "translated", 2: "bilingual"}
        selected_modes = [mode_mapping[i] for i in self.mode_group.get_selected_indices()]

        return {
            "media_path": self.input_browser.get_path(),
            "output_dir": self.output_browser.get_path(),
            "target_langs": selected_langs,
            "file_formats": selected_formats,
            "export_modes": selected_modes
        }

    # ==========================================
    # 核心任务调度与 UI 锁定逻辑
    # ==========================================
    def _on_start_clicked(self):
        if not self.validate_inputs():
            return

        config_data = self.get_configuration()

        # 锁定当前界面的可交互区域
        self.start_btn.setEnabled(False)
        self.start_btn.setText(self.tr("AI 引擎高速运行中..."))
        self.config_container.setEnabled(False)
        self.log_panel.clear_logs()

        # 唤起真实的后台任务线程
        self.worker = AITaskWorker(config_data)

        # 绑定信号：让底层引擎直接向日志面板输出变色文本
        self.worker.log_signal.connect(self.log_panel.append_log)
        self.worker.finished_signal.connect(self._on_task_finished)

        self.worker.start()

    def _on_task_finished(self, success: bool, message: str):
        # 任务结束，全域解锁 UI
        self.start_btn.setEnabled(True)
        self.start_btn.setText(self.tr("开始生成 (Start Generation)"))
        self.config_container.setEnabled(True)

        if success:
            self.log_panel.append_log(self.tr("[系统] 恭喜！所有字幕已成功生成并落盘。"), "success")
            reply = QMessageBox.question(
                self,
                self.tr("处理完成"),
                self.tr("字幕生成完毕！是否立即打开输出文件夹？\n\n路径: ") + message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(message))
        else:
            self.log_panel.append_log(self.tr(f"[系统] 任务意外终止。原因: {message}"), "error")
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"处理过程中发生错误:\n{message}"))