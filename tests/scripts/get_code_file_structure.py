import os
import sys
from pathlib import Path

# ==========================================
# 配置区
# ==========================================
# 将这里替换为你项目的绝对路径。例如：r"C:\Users\Work\Documents\Code\CaptionGenOchTranslator"
# 如果留空 (None)，它将默认扫描本脚本所在的当前目录
TARGET_ROOT = r"C:\Users\Work\Documents\Code\CaptionGenOchTranslator"

# 需要过滤掉的无用文件夹或文件后缀，保持输出清爽
IGNORE_DIRS = {'.git', '.venv', 'venv', '__pycache__', '.idea', '.vscode', '.caption_cache', 'assets'}
IGNORE_EXTS = {'.pyc', '.pyo', '.pyd', '.DS_Store'}


def generate_tree(directory: Path, prefix: str = ""):
    """递归生成并打印目录树"""
    # 获取目录下的所有内容，并按照文件夹在前、文件在后的规则排序
    try:
        paths = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        print(prefix + "├── [Permission Denied]")
        return

    # 过滤掉不需要显示的路径
    valid_paths = []
    for p in paths:
        if p.name in IGNORE_DIRS:
            continue
        if p.is_file() and p.suffix in IGNORE_EXTS:
            continue
        valid_paths.append(p)

    # 遍历并绘制树形结构
    count = len(valid_paths)
    for index, path in enumerate(valid_paths):
        is_last = (index == count - 1)
        connector = "└── " if is_last else "├── "

        print(prefix + connector + path.name)

        if path.is_dir():
            # 如果是目录，向下递归，并按需增加前缀（缩进层级）
            extension = "    " if is_last else "│   "
            generate_tree(path, prefix + extension)


def main():
    # 1. 确定要扫描的绝对路径
    if TARGET_ROOT and os.path.exists(TARGET_ROOT):
        root_path = Path(TARGET_ROOT).resolve()
    else:
        # 如果没有硬编码路径，则以本脚本所在的绝对路径作为起点
        root_path = Path(__file__).resolve().parent

    print(f"📦 Project Root: {root_path}\n")

    # 2. 生成目录树
    generate_tree(root_path)


if __name__ == "__main__":
    main()