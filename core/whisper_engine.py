import os
import torch
from faster_whisper import WhisperModel

class WhisperEngine:
    def __init__(self, model_size_or_path=None):
        """
        初始化 Whisper 引擎，加载模型常驻内存。

        :param model_size_or_path: 模型路径或名称。如果留空，默认使用软件自带的本地离线大模型。
        """
        # 1. 动态定位本地离线模型路径
        if model_size_or_path is None:
            # 获取当前文件 (whisper_engine.py) 所在的 core 文件夹，再往上一级得到项目根目录
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # 拼接出绝对路径：项目根目录/assets/models/whisper-large-v3
            model_size_or_path = os.path.join(base_dir, 'assets', 'models', 'whisper-large-v3')

        print(f"[*] 正在初始化 Whisper 引擎 (准备加载模型: {model_size_or_path})...")

        # 2. 硬件嗅探：自动决定算力和精度
        if torch.cuda.is_available():
            self.device = "cuda"
            self.compute_type = "float16"  # 显卡模式，半精度跑得快且省显存
            print(f"[*] 硬件检测: Nvidia GPU (CUDA) 就绪，开启全速模式。")
        else:
            self.device = "cpu"
            self.compute_type = "int8"  # CPU 模式，必须用 int8，否则内存容易炸
            print(f"[*] 硬件检测: 未发现兼容 GPU，降级为 CPU 内存省流模式。")

        # 3. 加载模型进入内存/显存
        try:
            self.model = WhisperModel(
                model_size_or_path=model_size_or_path,
                device=self.device,
                compute_type=self.compute_type
            )
            print("[*] Whisper 引擎启动完毕，随时待命！")
        except Exception as e:
            raise RuntimeError(f"模型加载失败，请检查路径或依赖环境: {str(e)}")

    def transcribe_audio(self, audio_path: str):
        """
        执行语音识别 (生成器模式 yield)

        :param audio_path: 已经提取好的干净 .wav 音频路径
        :yield: 字典，包含起始时间、结束时间、文本、当前总进度百分比
        """
        if not audio_path:
            raise ValueError("未提供音频路径")

        # beam_size=5 是精度与速度的最佳平衡点
        # vad_filter=True 极为关键：自动砍掉无声、纯音乐片段，防止模型产生“幻觉重复”
        segments, info = self.model.transcribe(audio_path, beam_size=5, vad_filter=True)

        # info 对象里有 Faster-Whisper 分析出的音频总时长和语言种类
        total_duration = info.duration
        print(f"[*] 识别开始 - 检测到主要语言: {info.language} | 音频总长: {total_duration:.2f}秒")

        # 3. 循环遍历结果 (Generator 核心逻辑)
        # 注意：这里的 segments 是一个迭代器，模型是在背后边跑边往外吐数据的
        for segment in segments:
            # 计算当前进度百分比 (最高不超过100%)
            # segment.end 是当前这句话结束在第几秒
            progress_percent = min(100.0, (segment.end / total_duration) * 100)

            # 使用 yield 而不是 return。
            # 这相当于往外“挤”出一滴水，保留当前函数状态，外部拿走这滴水后，这里会继续往下执行
            yield {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "progress": progress_percent,
                "language": info.language
            }