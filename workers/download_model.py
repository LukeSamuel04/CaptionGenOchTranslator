import os
import time
import requests
from PySide6.QtCore import QThread, Signal
from typing import Dict, Any


class ModelDownloadWorker(QThread):
    """
    负责执行模型实际下载的核心异步线程。
    支持断点续传、实时网速计算、随时暂停，并与 ModelDownloadChecker 共享同样的目录与 .part 逻辑。
    """
    # ==========================================
    # 定义跨线程通信的 Qt 信号
    # ==========================================
    # 进度更新信号: (模型ID, 已下载字节数, 总字节数, 实时网速_KBps)
    progress_updated = Signal(str, int, int, float)

    # 下载完成信号: (模型ID)
    download_finished = Signal(str)

    # 暂停成功信号: (模型ID)
    download_paused = Signal(str)

    # 错误信号: (模型ID, 错误详情)
    error_occurred = Signal(str, str)

    def __init__(self, model_info: Dict[str, Any], use_mirror: bool = False, parent=None):
        super().__init__(parent)
        self.model_info = model_info
        self.model_id = model_info.get("model_id", "unknown")
        self.use_mirror = use_mirror

        # 线程控制标志位
        self._is_paused = False

        # 【核心修改】：统一获取持久化数据目录，确保大模型下载后不被临时目录清理
        self.data_root = os.environ.get("APP_DATA_DIR")
        if not self.data_root:
            raise RuntimeError("未检测到全局数据目录变量 APP_DATA_DIR")

    def pause(self):
        """外部调用：请求暂停下载"""
        self._is_paused = True

    def run(self):
        """线程核心执行区"""
        try:
            # 1. 准备目录
            install_dir_rel = self.model_info.get("install_dir", "")
            # 基于 data_root 拼接出绝对路径
            install_dir_abs = os.path.join(self.data_root, install_dir_rel.replace("/", os.sep))
            os.makedirs(install_dir_abs, exist_ok=True)

            files_info = self.model_info.get("files", [])
            total_expected_bytes = sum(f.get("size_bytes", 0) for f in files_info)

            # 2. 预计算当前已下载的总量 (为了刚启动时进度条不为0)
            total_downloaded_bytes = self._calculate_initial_downloaded(install_dir_abs, files_info)

            # 3. 遍历每个文件开始下载
            for file_node in files_info:
                if self._is_paused:
                    break

                file_name = file_node["file_name"]
                expected_size = file_node.get("size_bytes", 0)
                download_url = file_node.get("url", "")

                if not download_url:
                    continue

                # 镜像替换逻辑 (拦截 huggingface.co 替换为 hf-mirror.com)
                if self.use_mirror and "huggingface.co" in download_url:
                    download_url = download_url.replace("huggingface.co", "hf-mirror.com")

                target_file_path = os.path.join(install_dir_abs, file_name)
                part_file_path = target_file_path + ".part"

                # 场景 A: 该文件已经完整存在，直接跳过
                if os.path.exists(target_file_path) and os.path.getsize(target_file_path) == expected_size:
                    continue

                # 场景 B: 需要下载或断点续传
                headers = {}
                write_mode = 'wb'
                downloaded_for_this_file = 0

                if os.path.exists(part_file_path):
                    downloaded_for_this_file = os.path.getsize(part_file_path)
                    if downloaded_for_this_file < expected_size:
                        # 核心：设置 HTTP Range 头实现断点续传
                        headers['Range'] = f'bytes={downloaded_for_this_file}-'
                        write_mode = 'ab'  # 追加写入模式
                    elif downloaded_for_this_file == expected_size:
                        # 极端情况：.part 文件其实已经下完了，只是没改名
                        os.rename(part_file_path, target_file_path)
                        continue
                    else:
                        # .part 文件比预期的还大（可能损坏），删掉重下
                        os.remove(part_file_path)
                        downloaded_for_this_file = 0
                        total_downloaded_bytes -= downloaded_for_this_file

                # 发起真实的网络请求
                self._download_single_file(
                    download_url, headers, part_file_path, write_mode,
                    total_downloaded_bytes, total_expected_bytes
                )

                if self._is_paused:
                    break

                # 单个文件下载完成后，将其从 .part 重命名为正式文件
                if os.path.exists(part_file_path) and os.path.getsize(part_file_path) == expected_size:
                    os.rename(part_file_path, target_file_path)

                # 累加下一个文件的基础已下载量
                total_downloaded_bytes += expected_size - downloaded_for_this_file

            # 4. 循环结束后的状态判定
            if self._is_paused:
                self.download_paused.emit(self.model_id)
            else:
                self.download_finished.emit(self.model_id)

        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(self.model_id, f"网络请求异常: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(self.model_id, f"下载发生错误: {str(e)}")

    def _download_single_file(self, url: str, headers: dict, part_path: str, write_mode: str,
                              base_downloaded_bytes: int, total_expected_bytes: int):
        """抽取出的单文件流式下载逻辑"""
        # 设置 stream=True 进行流式读取，避免把几十G的模型直接塞进内存
        with requests.get(url, headers=headers, stream=True, timeout=15) as response:
            response.raise_for_status()

            with open(part_path, write_mode) as f:
                start_time = time.time()
                bytes_since_last_calc = 0
                current_total_downloaded = base_downloaded_bytes

                # 每次拉取 8KB 数据块
                for chunk in response.iter_content(chunk_size=8192):
                    if self._is_paused:
                        # 优雅暂停：一旦收到暂停标志，立刻跳出循环，退出上下文管理器释放连接
                        break

                    if chunk:
                        f.write(chunk)
                        chunk_size = len(chunk)
                        current_total_downloaded += chunk_size
                        bytes_since_last_calc += chunk_size

                        now = time.time()
                        # 每隔 0.5 秒发射一次信号，避免高频发信卡死 UI 线程
                        if now - start_time >= 0.5:
                            speed = bytes_since_last_calc / (now - start_time)
                            speed_kbps = speed / 1024.0

                            self.progress_updated.emit(
                                self.model_id,
                                current_total_downloaded,
                                total_expected_bytes,
                                speed_kbps
                            )

                            # 重置计时器和字节池
                            start_time = now
                            bytes_since_last_calc = 0

    def _calculate_initial_downloaded(self, install_dir_abs: str, files_info: list) -> int:
        """复刻 Checker 的逻辑，精准计算启动瞬间的已下载量"""
        total = 0
        for file_node in files_info:
            target_path = os.path.join(install_dir_abs, file_node["file_name"])
            part_path = target_path + ".part"

            if os.path.exists(target_path):
                total += os.path.getsize(target_path)
            elif os.path.exists(part_path):
                total += os.path.getsize(part_path)
        return total