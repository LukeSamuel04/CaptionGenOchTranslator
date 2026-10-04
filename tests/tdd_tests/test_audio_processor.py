import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 动态将项目根目录加入到系统路径中，确保能顺利导入 core 文件夹下的模块
# 假设当前文件层级是：项目根目录/tests/tdd_tests/test_audio_processor.py
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.audio_processor import extract_audio


class TestAudioProcessor(unittest.TestCase):

    def test_file_not_exists(self):
        """测试用例 1：当传入的视频文件不存在时，是否正确被拦截并返回 False"""
        success, msg = extract_audio("fake_not_exist_video.mp4", "output.wav")
        self.assertFalse(success)
        self.assertIn("找不到视频文件", msg)

    @patch('core.audio_processor.subprocess.run')
    @patch('core.audio_processor.os.path.exists')
    def test_extract_audio_success_mock(self, mock_exists, mock_run):
        """测试用例 2 (Mock)：模拟 FFmpeg 成功提取音频的理想情况"""
        # 设定 os.path.exists 的返回值：第一次(查视频)存在，第二次(查输出音频)也存在
        mock_exists.side_effect = [True, True]

        # 模拟 subprocess.run 成功执行返回 (returncode == 0)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        success, msg = extract_audio("dummy_video.mp4", "dummy_audio.wav")

        self.assertTrue(success)
        self.assertEqual(msg, "dummy_audio.wav")

    @patch('core.audio_processor.subprocess.run')
    @patch('core.audio_processor.os.path.exists')
    def test_extract_audio_ffmpeg_error_mock(self, mock_exists, mock_run):
        """测试用例 3 (Mock)：模拟 FFmpeg 执行报错的情况"""
        mock_exists.return_value = True  # 假设视频是存在的

        # 模拟 subprocess.run 返回错误码 (returncode != 0) 并且携带了报错信息
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "FFmpeg Error: Invalid data found when processing input"
        mock_run.return_value = mock_result

        success, msg = extract_audio("dummy_video.mp4", "dummy_audio.wav")

        self.assertFalse(success)
        self.assertIn("FFmpeg 提取失败", msg)

    # =====================================================================
    # 【真实的物理文件集成测试】
    # 默认是跳过的。你要测试真实的视频，请把下方 @unittest.skip 这一行注释掉！
    # =====================================================================
    @unittest.skip("跳过真实的视频测试。要测试的话，请注释掉此行代码。")
    def test_real_video_extraction(self):
        """测试用例 4：真实环境测试，读取你的视频并生成真实音频"""

        # 1. 在这里填入你本地准备好的测试视频的绝对路径
        real_video_path = r"C:\Users\Luke\OneDrive\Desktop\study files\Assignment_build_something.mp4"

        # 2. 设定提取出来的音频要保存在哪里（比如存在同一个目录下）
        real_audio_output = r"C:\Users\Luke\OneDrive\Desktop\study files\test_audio_output.wav"

        print(f"\n[真实测试] 开始从 {real_video_path} 提取音频...")

        success, msg = extract_audio(real_video_path, real_audio_output)

        if success:
            print(f"[真实测试] 成功！音频已生成: {msg}")
            # 断言生成的文件确实存在，而且不是 0KB 的空文件
            self.assertTrue(os.path.exists(real_audio_output))
            self.assertGreater(os.path.getsize(real_audio_output), 0)

            # 测试完毕后自动清理生成的音频文件（如果你想保留下来听听看，可以注释掉下面这行）
            #os.remove(real_audio_output)
        else:
            print(f"[真实测试] 失败: {msg}")
            self.fail("真实视频提取音频失败")


if __name__ == '__main__':
    unittest.main()