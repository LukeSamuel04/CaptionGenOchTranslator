from PySide6.QtCore import QThread, Signal
from core.download_logic.model_config_getter import ModelConfigGetter


class FetchConfigWorker(QThread):
    """
    独立的网络请求线程（侦察兵）。
    专门负责去云端拉取最新的模型配置 JSON，绝对不阻塞主 UI 线程。
    """
    # ==========================================
    # 定义跨线程通信的 Qt 信号
    # ==========================================
    # 成功信号：携带解析好的 JSON 字典发回给 UI
    success_signal = Signal(dict)

    # 失败信号：携带具体的报错文本发回给 UI
    error_signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 初始化机制层，由于之前改造过，这里会自动从环境变量提取正确的项目根目录
        self.getter = ModelConfigGetter()

    def run(self):
        """
        线程启动后的核心执行区。
        这里的任何耗时操作都不会影响界面的拖拽和渲染。
        """
        try:
            # 发起硬核的同步网络请求
            new_data = self.getter.fetch_remote_json()

            # 请求成功，立刻把数据打包成信号发射出去
            self.success_signal.emit(new_data)

        except Exception as e:
            # 捕获 DNS 解析失败、超时或 JSON 格式错误，发射错误信号
            self.error_signal.emit(f"无法连接至云端服务器。\n详细信息: {str(e)}")