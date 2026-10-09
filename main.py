import multiprocessing
import sys
import os
from pathlib import Path
# ==========================================
# 建立全局坐标系与路径锁 (必须在所有业务导入之前)
# ==========================================
# 因为该入口文件位于项目根目录，直接获取其所在文件夹即可
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 注册全局定位信号：将绝对根目录写入系统环境变量，供深层模块直接读取
os.environ["APP_PROJECT_ROOT"] = PROJECT_ROOT
# ==========================================

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindowNew

def main():
    # 强制适配高分屏（如 4K 显示器），防止 UI 元素模糊缩放
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    # ==========================================
    # 加载全局样式表 (QSS) - 双层架构合并
    # ==========================================
    project_root = os.environ.get("APP_PROJECT_ROOT")
    if project_root:
        styles_dir = Path(project_root) / "ui" / "styles"
        common_qss_path = styles_dir / "common.qss"
        theme_qss_path = styles_dir / "dark_theme.qss"

        if common_qss_path.exists() and theme_qss_path.exists():
            with open(common_qss_path, "r", encoding="utf-8") as fc, \
                    open(theme_qss_path, "r", encoding="utf-8") as ft:
                # 拼接两个样式表：基础骨架 + 颜色皮肤
                combined_qss = fc.read() + "\n" + ft.read()
                app.setStyleSheet(combined_qss)
        else:
            print(f"Warning: 找不到样式表文件，请检查 {styles_dir} 目录")
    # 实例化并展示主窗口
    window = MainWindowNew()
    window.show()

    # 进入 Qt 的事件循环，保持窗口运行不退出
    sys.exit(app.exec())

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()