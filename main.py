import multiprocessing
import sys
import os
from pathlib import Path

# ==========================================
# 建立全局坐标系与双层路径锁 (兼容 PyInstaller 打包)
# ==========================================
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # 生产环境：运行在打包后的 exe 中
    # sys._MEIPASS 是 PyInstaller 解压静态资源（如 qss）的临时目录
    RESOURCE_ROOT = sys._MEIPASS
    # sys.executable 是 exe 文件真实物理路径，取其所在目录用于保存持久化数据
    DATA_ROOT = os.path.dirname(sys.executable)
else:
    # 开发环境：运行在本地 Python 源码中
    # 读写都在当前项目源码的根目录下
    RESOURCE_ROOT = DATA_ROOT = os.path.dirname(os.path.abspath(__file__))

# 注册全局定位信号：拆分读写路径，供深层模块按需读取
os.environ["APP_RESOURCE_DIR"] = RESOURCE_ROOT  # 专用于读取随软件打包的静态资源
os.environ["APP_DATA_DIR"] = DATA_ROOT  # 专用于写入用户产生的持久化数据 (缓存、输出等)
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
    # 【核心修改】：样式表属于静态资源，必须从 APP_RESOURCE_DIR 读取
    resource_root = os.environ.get("APP_RESOURCE_DIR")
    if resource_root:
        styles_dir = Path(resource_root) / "ui" / "styles"
        common_qss_path = styles_dir / "common.qss"
        theme_qss_path = styles_dir / "light_theme.qss"

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