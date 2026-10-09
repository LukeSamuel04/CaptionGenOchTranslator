import os
import json
import urllib.request
from typing import Optional, Dict, Any


class ModelConfigGetter:
    """
    纯粹的数据获取工具类 (机制层)。
    只提供原子化的网络请求与本地文件读写操作，不包含任何业务策略（如超时回退或缓存决策）。
    """

    def __init__(self):
        # 【核心修改】：改为读取专门用于写入持久化数据的 APP_DATA_DIR
        data_root = os.environ.get("APP_DATA_DIR")
        if not data_root:
            raise RuntimeError("未检测到全局数据目录变量 APP_DATA_DIR，请确保程序由 main.py 启动。")

        # 拼接出项目数据目录下的精确缓存路径 (打包后将落在 exe 同级物理目录)
        self.cache_dir = os.path.join(data_root, ".caption_cache", "model_config_cache")
        self.cache_file = os.path.join(self.cache_dir, "models_cache.json")

        self.remote_url = "https://raw.githubusercontent.com/LukeSamuel04/CaptionGenOchTranslator/dev-download-page/configs/downloads/models.json"
        self.timeout = 5

    def fetch_remote_json(self) -> Dict[str, Any]:
        """
        死脑筋地去请求云端 JSON。
        成功则返回解析后的字典，失败则直接向上抛出异常，交由 Worker/UI 去捕获和决策。
        """
        req = urllib.request.Request(
            self.remote_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            content = response.read().decode('utf-8')
            data = json.loads(content)

            if "models" not in data:
                raise ValueError("JSON 格式异常：未检测到 'models' 根节点")

            return data

    def read_local_cache(self) -> Optional[Dict[str, Any]]:
        """
        死脑筋地读取本地缓存。
        如果文件不存在或解析失败，安静地返回 None。
        """
        if not os.path.exists(self.cache_file):
            return None

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save_to_cache(self, data: Dict[str, Any]) -> None:
        """
        将传入的数据强行写入本地缓存。
        如果所需的层级目录不存在，os.makedirs 会自动补全。
        """
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


# =========================================
# 独立测试入口
# =========================================
if __name__ == "__main__":
    getter = ModelConfigGetter()

    print("1. 测试拉取云端数据...")
    try:
        remote_data = getter.fetch_remote_json()
        print(f"成功获取云端模型数量: {len(remote_data.get('models', []))}")

        print("\n2. 测试写入本地缓存...")
        getter.save_to_cache(remote_data)
        print(f"写入成功，精确路径: {getter.cache_file}")
    except Exception as e:
        print(f"云端获取失败: {e}")

    print("\n3. 测试读取本地缓存...")
    local_data = getter.read_local_cache()
    if local_data:
        print(f"成功读取本地缓存模型数量: {len(local_data.get('models', []))}")
    else:
        print("本地无可用缓存。")