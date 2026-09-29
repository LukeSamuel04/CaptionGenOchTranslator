import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QCheckBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt


class ConfigPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 初始化支持的语言字典 (键: 供界面显示的带本地语言标识的文本, 值: 内部语种代号)
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
        self.lang_checkboxes = {}  # 用于存储生成的语言复选框对象

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)

        # ==========================================
        # 1. 路径配置区 (输入与输出)
        # ==========================================
        path_group = QGroupBox(self.tr("文件与路径 (Files & Paths)"))
        path_layout = QVBoxLayout(path_group)

        # 1.1 媒体输入
        input_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText(self.tr("请选择需要处理的视频或音频文件..."))
        self.file_path_edit.setReadOnly(True)
        self.browse_input_btn = QPushButton(self.tr("选择文件 (Input)"))
        self.browse_input_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_input_btn.clicked.connect(self._browse_input_file)
        input_layout.addWidget(self.file_path_edit)
        input_layout.addWidget(self.browse_input_btn)

        # 1.2 目录输出
        output_layout = QHBoxLayout()
        self.out_dir_edit = QLineEdit()
        # 默认放在程序运行目录下的 output_captions 文件夹中
        default_out_dir = os.path.abspath(os.path.join(os.getcwd(), "output_captions"))
        self.out_dir_edit.setText(default_out_dir)
        self.browse_output_btn = QPushButton(self.tr("更改目录 (Output)"))
        self.browse_output_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_output_btn.clicked.connect(self._browse_output_dir)
        output_layout.addWidget(self.out_dir_edit)
        output_layout.addWidget(self.browse_output_btn)

        path_layout.addLayout(input_layout)
        path_layout.addLayout(output_layout)

        # ==========================================
        # 2. 目标语言多选区 (网格布局)
        # ==========================================
        lang_group = QGroupBox(self.tr("目标语言 (Target Languages - 可多选)"))
        lang_layout = QGridLayout(lang_group)
        lang_layout.setHorizontalSpacing(20)
        lang_layout.setVerticalSpacing(10)

        # 将语言动态生成复选框，以 3 列的形式平铺展示
        row, col, max_cols = 0, 0, 3
        for display_name, lang_code in self.SUPPORTED_LANGS.items():
            chk = QCheckBox(display_name)
            # 默认勾选简体中文和英语作为演示
            if lang_code in ["zh", "en"]:
                chk.setChecked(True)
            self.lang_checkboxes[lang_code] = chk
            lang_layout.addWidget(chk, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # ==========================================
        # 3. 格式与模式配置区 (多选)
        # ==========================================
        export_group = QGroupBox(self.tr("导出设置 (Export Settings - 可多选)"))
        export_layout = QVBoxLayout(export_group)

        # 3.1 字幕格式多选
        fmt_layout = QHBoxLayout()
        fmt_label = QLabel(self.tr("文件格式:"))
        self.chk_srt = QCheckBox("SRT")
        self.chk_vtt = QCheckBox("WebVTT")
        self.chk_srt.setChecked(True)  # 默认勾选 SRT

        fmt_layout.addWidget(fmt_label)
        fmt_layout.addWidget(self.chk_srt)
        fmt_layout.addWidget(self.chk_vtt)
        fmt_layout.addStretch()

        # 3.2 轨道模式多选
        mode_layout = QHBoxLayout()
        mode_label = QLabel(self.tr("排版模式:"))
        self.chk_original = QCheckBox(self.tr("纯原声 (Original)"))
        self.chk_translated = QCheckBox(self.tr("纯译文 (Translated)"))
        self.chk_bilingual = QCheckBox(self.tr("双语对译 (Bilingual)"))

        self.chk_translated.setChecked(True)
        self.chk_bilingual.setChecked(True)

        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.chk_original)
        mode_layout.addWidget(self.chk_translated)
        mode_layout.addWidget(self.chk_bilingual)
        mode_layout.addStretch()

        export_layout.addLayout(fmt_layout)
        export_layout.addLayout(mode_layout)

        # ==========================================
        # 组装到主面板
        # ==========================================
        main_layout.addWidget(path_group)
        main_layout.addWidget(lang_group)
        main_layout.addWidget(export_group)

    def _browse_input_file(self):
        file_filter = self.tr("音视频文件 (*.mp4 *.mkv *.avi *.mov *.mp3 *.wav *.aac);;所有文件 (*.*)")
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("选择媒体文件"), "", file_filter)
        if file_path:
            self.file_path_edit.setText(file_path)

    def _browse_output_dir(self):
        current_dir = self.out_dir_edit.text()
        dir_path = QFileDialog.getExistingDirectory(self, self.tr("选择输出目录"), current_dir)
        if dir_path:
            # 保证路径使用的分隔符兼容当前系统 (Windows/Mac)
            self.out_dir_edit.setText(os.path.normpath(dir_path))

    def get_configuration(self) -> dict:
        """打包用户的多选配置，生成包含列表的数据结构"""
        selected_langs = []
        for display_name, lang_code in self.SUPPORTED_LANGS.items():
            if self.lang_checkboxes[lang_code].isChecked():
                # 我们同时把“显示名”和“内部代号”传给后台
                # 这样后台既能用显示名作为 prompt 喂给 ALMA，又能用代号命名文件
                selected_langs.append({"code": lang_code, "name": display_name})

        selected_formats = []
        if self.chk_srt.isChecked(): selected_formats.append("srt")
        if self.chk_vtt.isChecked(): selected_formats.append("vtt")

        selected_modes = []
        if self.chk_original.isChecked(): selected_modes.append("original")
        if self.chk_translated.isChecked(): selected_modes.append("translated")
        if self.chk_bilingual.isChecked(): selected_modes.append("bilingual")

        return {
            "media_path": self.file_path_edit.text().strip(),
            "output_dir": self.out_dir_edit.text().strip(),
            "target_langs": selected_langs,
            "file_formats": selected_formats,
            "export_modes": selected_modes
        }

    def validate_inputs(self) -> bool:
        """全方位的多选参数合法性校验"""
        # 1. 查媒体
        if not self.file_path_edit.text().strip():
            QMessageBox.warning(self, self.tr("警告"), self.tr("请先选择需要处理的音视频文件！"))
            return False

        # 2. 查输出路径
        if not self.out_dir_edit.text().strip():
            QMessageBox.warning(self, self.tr("警告"), self.tr("输出目录不能为空！"))
            return False

        # 3. 查模式与格式
        if not (self.chk_original.isChecked() or self.chk_translated.isChecked() or self.chk_bilingual.isChecked()):
            QMessageBox.warning(self, self.tr("警告"), self.tr("请至少选择一种排版模式！"))
            return False
        if not (self.chk_srt.isChecked() or self.chk_vtt.isChecked()):
            QMessageBox.warning(self, self.tr("警告"), self.tr("请至少选择一种字幕格式！"))
            return False

        # 4. 智能查语言：如果选择了需要翻译的模式，就必须勾选至少一种语言
        needs_translation = self.chk_translated.isChecked() or self.chk_bilingual.isChecked()
        if needs_translation:
            any_lang_selected = any(chk.isChecked() for chk in self.lang_checkboxes.values())
            if not any_lang_selected:
                QMessageBox.warning(self, self.tr("警告"), self.tr("导出模式包含了翻译需求，请至少勾选一种目标语言！"))
                return False

        return True