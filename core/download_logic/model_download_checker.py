import os
from enum import Enum
from typing import Dict, Any


class DownloadStatus(Enum):
    """定义模型下载状态的纯净枚举"""
    NOT_INSTALLED = "NOT_INSTALLED"  # 毫无下载痕迹
    PARTIAL = "PARTIAL"  # 存在 .part 文件或只下载了部分文件
    INSTALLED = "INSTALLED"  # 全部文件存在且大小分毫不差
    CORRUPTED = "CORRUPTED"  # 存在已完成的文件但大小与配置不符


class ModelDownloadChecker:
    """
    状态判定器：不涉及网络和界面，只专注于比准本地磁盘文件与 JSON 配置的契合度。
    """

    def __init__(self):
        # 【核心修改】：统一接入持久化数据目录，抛弃原本的 APP_PROJECT_ROOT
        self.data_root = os.environ.get("APP_DATA_DIR")
        if not self.data_root:
            raise RuntimeError("未检测到全局数据目录变量 APP_DATA_DIR，请确保程序由 main.py 启动。")

    def check_status(self, model_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        传入单个模型的 JSON 配置字典，返回本地该模型的下载状态。
        """
        install_dir_rel = model_info.get("install_dir", "")
        # 替换斜杠以兼容不同操作系统，基于 data_root 拼接出绝对路径
        install_dir_abs = os.path.join(self.data_root, install_dir_rel.replace("/", os.sep))
        files_info = model_info.get("files", [])

        total_expected_bytes = 0
        total_downloaded_bytes = 0
        is_corrupted = False
        is_missing_or_partial = False

        for file_node in files_info:
            file_name = file_node["file_name"]
            expected_size = file_node.get("size_bytes", 0)
            total_expected_bytes += expected_size

            target_file_path = os.path.join(install_dir_abs, file_name)
            part_file_path = target_file_path + ".part"

            # 场景 A: 存在已“完成”的文件
            if os.path.exists(target_file_path):
                actual_size = os.path.getsize(target_file_path)
                total_downloaded_bytes += actual_size
                # 严密比对字节数
                if actual_size != expected_size:
                    is_corrupted = True
                    is_missing_or_partial = True

            # 场景 B: 存在正在下载的临时文件
            elif os.path.exists(part_file_path):
                is_missing_or_partial = True
                part_size = os.path.getsize(part_file_path)
                total_downloaded_bytes += part_size

            # 场景 C: 什么都没有
            else:
                is_missing_or_partial = True

        # 防止因为损坏的文件异常庞大，导致进度条超过 100%
        total_downloaded_bytes = min(total_downloaded_bytes, total_expected_bytes)

        # 决策最终状态
        if is_corrupted:
            final_status = DownloadStatus.CORRUPTED
        elif not is_missing_or_partial and total_expected_bytes > 0:
            final_status = DownloadStatus.INSTALLED
        elif total_downloaded_bytes > 0:
            final_status = DownloadStatus.PARTIAL
        else:
            final_status = DownloadStatus.NOT_INSTALLED

        return {
            "status": final_status.value,
            "downloaded_bytes": total_downloaded_bytes,
            "total_bytes": total_expected_bytes
        }


# =========================================
# 极简测试用例
# =========================================
if __name__ == "__main__":
    # 模拟从 JSON 中取出的 LLaMA 节点
    mock_model_info = {
        "model_id": "llama-3.1-8b",
        "install_dir": "assets/models/llama-3.1-8b",
        "files": [
            {
                "file_name": "llama-3.1-8b.gguf",
                "size_bytes": 4920738944
            }
        ]
    }

    checker = ModelDownloadChecker()
    result = checker.check_status(mock_model_info)
    print(f"检查模型: {mock_model_info['model_id']}")
    print(f"返回状态: {result}")