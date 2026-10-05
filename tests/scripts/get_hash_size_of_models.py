import hashlib
import os

# 1. 自动定位到项目根目录
# __file__ 是当前脚本的绝对路径，退两级 (..) 就回到了 CaptionGenOchTranslator 根目录
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))


def get_file_info(file_path):
    if not os.path.exists(file_path):
        return "不存在", "不存在"

    size_bytes = os.path.getsize(file_path)

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096 * 1024), b""):
            sha256_hash.update(byte_block)

    return size_bytes, sha256_hash.hexdigest()


# 2. 将相对路径与根目录拼接成绝对路径
relative_paths = [
    "assets/models/llama-3.1-8b/llama-3.1-8b.gguf",
    "assets/models/whisper-large-v3/model.bin",
    "assets/models/whisper-large-v3/config.json",
    "assets/models/whisper-large-v3/preprocessor_config.json",
    "assets/models/whisper-large-v3/tokenizer.json",
    "assets/models/whisper-large-v3/vocabulary.json"
]

files_to_check = [os.path.join(project_root, p.replace("/", os.sep)) for p in relative_paths]

print("-" * 50)
for file in files_to_check:
    filename = os.path.basename(file)
    print(f"文件: {filename}")
    size, file_hash = get_file_info(file)
    print(f"精确字节 (size_bytes): {size}")
    print(f"哈希值 (sha256): {file_hash}")
    print("-" * 50)