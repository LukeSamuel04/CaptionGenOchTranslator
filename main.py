import multiprocessing
import sys
from PySide6.QtWidgets import QApplication

from ui.main_window_new import MainWindowNew
from ui.test_windows.components_testing.combox_optgrp import TestWindow

def main():
    # 强制适配高分屏（如 4K 显示器），防止 UI 元素模糊缩放
    import os
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)

    # 实例化并展示主窗口
    window=MainWindowNew()
    window.show()

    # 进入 Qt 的事件循环，保持窗口运行不退出
    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()