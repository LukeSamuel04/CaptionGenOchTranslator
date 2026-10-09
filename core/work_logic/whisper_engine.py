import os
import torch
from faster_whisper import WhisperModel

class WhisperEngine:
    def __init__(self, model_size_or_path=None):
        """
                初始化 Whisper 引擎，加载模型常驻内存。
                """
        if model_size_or_path is None:
            # 【核心修改】：接入持久化数据目录，读取实际存放在硬盘上的大模型文件
            data_root = os.environ.get("APP_DATA_DIR")
            if not data_root:
                raise RuntimeError("未检测到全局数据目录变量 APP_DATA_DIR，请确保程序由 main.py 启动。")
            # 拼接出绝对路径：项目真正的物理根目录/assets/models/whisper-large-v3
            model_size_or_path = os.path.join(data_root, 'assets', 'models', 'whisper-large-v3')

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
        """
        if not audio_path:
            raise ValueError("未提供音频路径")

        # [核心优化区：抗幻觉与防碎化]
        # 1. vad_filter=True: 砍掉无声纯音乐片段
        # 2. min_silence_duration_ms=1000: 低于1秒的停顿不切断，解决字幕碎片化
        # 3. condition_on_previous_text=False: 彻底禁止模型参考上一句的乱码，切断复读机死循环
        segments, info = self.model.transcribe(
            audio_path,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=1000, speech_pad_ms=400),
            condition_on_previous_text=False
        )

        total_duration = info.duration
        print(f"[*] 识别开始 - 检测到主要语言: {info.language} | 音频总长: {total_duration:.2f}秒")

        for segment in segments:
            progress_percent = min(100.0, (segment.end / total_duration) * 100)

            yield {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "progress": progress_percent,
                "language": info.language
            }