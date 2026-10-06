import os
import sys
import unittest

# 动态将项目根目录加入到系统路径中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.work_logic.whisper_engine import WhisperEngine


class TestWhisperEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        在所有测试用例开始前执行一次。
        在这里初始化引擎，确保大模型只被加载一次。
        """
        print("\n[测试准备] ...")
        cls.engine = WhisperEngine()
        print("[测试准备] 引擎初始化完成。")

    def test_engine_initialization(self):
        """测试引擎是否正确检测到硬件并完成了初始化"""
        self.assertIsNotNone(self.engine.model)
        self.assertTrue(self.engine.device in ["cuda", "cpu"])
        print(f"[测试通过] 引擎硬件模式: {self.engine.device}")

    # =====================================================================
    # 【真实的物理音频集成测试】
    # 默认跳过。你要测试真实的音频，请把下方 @unittest.skip 这一行注释掉！
    # =====================================================================
    @unittest.skip("跳过真实的音频识别测试。要测试的话，请注释掉此行代码。")
    def test_real_audio_transcription(self):
        """测试用例：真实环境测试，读取你准备好的 .wav 音频并识别"""

        # 1. 在这里填入你刚才用 audio_processor 测试时生成的那个 .wav 文件的绝对路径！
        real_audio_path = r"C:\Users\Luke\OneDrive\Desktop\study files\test_audio_output.wav"

        if not os.path.exists(real_audio_path):
            self.fail(f"找不到测试音频文件: {real_audio_path}，请先准备好音频！")

        print(f"\n[真实测试] 开始听写音频: {real_audio_path}")

        segment_count = 0
        last_progress = 0.0

        # 2. 核心：遍历引擎返回的生成器
        for data_drop in self.engine.transcribe_audio(real_audio_path):
            segment_count += 1

            # 取出数据
            start_time = data_drop["start"]
            end_time = data_drop["end"]
            text = data_drop["text"]
            progress = data_drop["progress"]

            # 断言基本逻辑
            self.assertGreaterEqual(end_time, start_time)
            self.assertGreaterEqual(progress, last_progress)  # 进度应该是一直往前走，不倒退
            self.assertLessEqual(progress, 100.0)  # 进度最高只能是 100%

            last_progress = progress

            # 打印出来让你直观看到效果
            print(f"进度: [{progress:5.1f}%] | {start_time:5.2f}s -> {end_time:5.2f}s | {text}")

        # 断言是否真的输出了内容
        self.assertGreater(segment_count, 0, "模型没有识别出任何字幕！")
        print(f"[真实测试] 成功！共识别出 {segment_count} 句话。")


if __name__ == '__main__':
    unittest.main()