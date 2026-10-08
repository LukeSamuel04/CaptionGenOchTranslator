import multiprocessing
import sys
import os

from ui import main_window

# ==========================================
# 建立全局坐标系与路径锁 (必须在所有业务导入之前)
# ==========================================
# 因为该入口文件位于项目根目录，直接获取其所在文件夹即可
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 强制将根目录推入 sys.path 的最高优先级，解决所有 Import 歧义
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 注册全局定位信号：将绝对根目录写入系统环境变量，供深层模块直接读取
os.environ["APP_PROJECT_ROOT"] = PROJECT_ROOT
# ==========================================

from PySide6.QtWidgets import QApplication
from ui.main_window_new import MainWindowNew
from ui.test_windows.components_testing.muti_status_fetch_config_button import FetchConfigButtonTestWindow

def main():
    # 强制适配高分屏（如 4K 显示器），防止 UI 元素模糊缩放
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)

    # 实例化并展示主窗口
    window = MainWindowNew()
    window.show()

    # 进入 Qt 的事件循环，保持窗口运行不退出
    sys.exit(app.exec())

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()