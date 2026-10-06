import queue
from PySide6.QtCore import QThread, Signal


class IPCListener(QThread):
    """
    跨进程通信监听器 (IPC Bridge)

    职责：
    作为一个轻量级的后台 Qt 线程，死死盯住来自独立子进程的 multiprocessing.Queue。
    一旦拿到字典格式的纯文本消息，立刻“转译”为 Qt 信号发射给主界面。
    这样既保证了主 UI 不卡顿，又实现了跨进程的安全通信。
    """

    # --- 统一定义向 UI 界面发射的合法 Qt 信号 ---
    log_relay = Signal(str, str)  # 发送日志 (日志内容, 级别标签)
    progress_relay = Signal(int)  # 发送进度 (0-100的整数)
    step_finished = Signal(bool, str)  # 发送完成/异常终止信号 (是否成功, 结果路径或报错信息)

    def __init__(self, ipc_queue, parent=None):
        super().__init__(parent)
        self.ipc_queue = ipc_queue
        self._is_stopped = False

    def run(self):
        """
        线程启动后的死循环监听
        """
        while not self._is_stopped:
            try:
                # 核心机制：设置 0.1 秒的超时时间。
                # 这样做是为了防止线程永远阻塞在 .get() 上，导致主程序想退出时杀不掉这个监听线程。
                msg = self.ipc_queue.get(timeout=0.1)

                # 拿到消息后，立刻路由处理
                if isinstance(msg, dict):
                    self._process_msg(msg)

            except queue.Empty:
                # 队列里暂时没消息，直接进入下一次循环继续盯梢
                continue
            except Exception as e:
                # 兜底防御：防止底层队列句柄被强制销毁时导致程序崩溃
                self.log_relay.emit(f"[IPC通信] 监听通道异常: {str(e)}", "error")
                break

    def _process_msg(self, msg: dict):
        """
        解析子进程传来的数据字典，并分发到对应的 Qt 信号

        子进程发来的字典必须遵循以下契约：
        {'type': 'log', 'message': '...', 'level': 'info'}
        {'type': 'progress', 'value': 45}
        {'type': 'finished', 'success': True, 'message': '缓存路径'}
        {'type': 'error', 'message': '堆栈溢出报错信息'}
        """
        msg_type = msg.get("type")

        if msg_type == "log":
            # 提取内容和级别（默认 info）
            message = msg.get("message", "")
            level = msg.get("level", "info")
            self.log_relay.emit(message, level)

        elif msg_type == "progress":
            value = msg.get("value", 0)
            self.progress_relay.emit(value)

        elif msg_type == "finished":
            success = msg.get("success", True)
            message = msg.get("message", "")
            self.step_finished.emit(success, message)

        elif msg_type == "error":
            # 捕获子进程发来的严重错误
            message = msg.get("message", "子进程发生未知错误")
            self.step_finished.emit(False, message)

    def stop(self):
        """
        优雅终止监听器
        供 Scheduler 在任务彻底结束，或者用户强制取消时调用。
        """
        self._is_stopped = True
        self.wait()  # 阻塞等待 run() 循环安全退出