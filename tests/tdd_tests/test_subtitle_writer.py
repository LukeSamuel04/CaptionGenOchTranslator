import os
import unittest
import shutil
from core.work_logic.subtitle_writer import SubtitleWriter


class TestSubtitleWriter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        测试前的准备工作：构造模拟数据和测试专用的输出目录。
        """
        cls.test_out_dir = os.path.join(os.path.dirname(__file__), "test_outputs")
        cls.mock_segments = [
            {"start": 0.0, "end": 2.5, "text": "Oh, look at that!", "translated": "哦，瞧那！"},
            {"start": 2.5, "end": 4.0, "text": "It is a huge apple.", "translated": "它是一个巨大的苹果。"},
            # 制造一个极短的片段，测试时间戳精确度
            {"start": 61.999, "end": 62.001, "text": "Wow.", "translated": "哇。"}
        ]

    def test_timestamp_formatting(self):
        """
        测试核心底层逻辑：浮点数秒数到 SRT/VTT 时间戳的转换是否精准。
        """
        print("\n[*] 正在测试时间戳转换引擎...")

        # 测试普通转换 (SRT 逗号)
        self.assertEqual(SubtitleWriter.format_timestamp(2.5, "srt"), "00:00:02,500")

        # 测试满 60 秒进位
        self.assertEqual(SubtitleWriter.format_timestamp(61.999, "srt"), "00:01:01,999")

        # 测试 VTT 格式的点号
        self.assertEqual(SubtitleWriter.format_timestamp(3661.123, "vtt"), "01:01:01.123")

    def test_srt_export_all_modes(self):
        """
        测试 SRT 文件的多模式生成（纯原文、纯译文、双语合并）。
        """
        print("\n[*] 正在测试 SRT 多轨道批量导出...")
        output_prefix = os.path.join(self.test_out_dir, "test_video")

        generated_files = SubtitleWriter.export_subtitles(
            segments=self.mock_segments,
            output_prefix=output_prefix,
            modes=["original", "translated", "bilingual"],
            file_format="srt",
            lang_code="zh"
        )

        # 1. 检查是否成功生成了 3 个文件
        self.assertEqual(len(generated_files), 3)
        self.assertTrue(os.path.exists(generated_files["original"]))
        self.assertTrue(os.path.exists(generated_files["translated"]))
        self.assertTrue(os.path.exists(generated_files["bilingual"]))

        # 2. 抽查“双语字幕”的内容格式是否正确（上译下原）
        with open(generated_files["bilingual"], "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("哦，瞧那！\nOh, look at that!", content, "双语拼接逻辑错误")
            self.assertIn("00:00:00,000 --> 00:00:02,500", content, "时间轴格式错误")

    def test_vtt_export(self):
        """
        测试 WebVTT 格式的独有特征 (文件头必须包含 WEBVTT)。
        """
        print("\n[*] 正在测试 VTT 格式导出...")
        output_prefix = os.path.join(self.test_out_dir, "test_web")

        generated_files = SubtitleWriter.export_subtitles(
            segments=self.mock_segments,
            output_prefix=output_prefix,
            modes=["bilingual"],
            file_format="vtt",
            lang_code="zh"
        )

        with open(generated_files["bilingual"], "r", encoding="utf-8") as f:
            content = f.read()
            self.assertTrue(content.startswith("WEBVTT"), "VTT 文件缺失 WEBVTT 头部声明")
            self.assertIn("00:00:00.000 --> 00:00:02.500", content, "VTT 时间轴未正确使用点号")

    @classmethod
    def tearDownClass(cls):
        """
        测试结束后，自动清理生成的临时测试文件，保持项目干净。
        """
        if os.path.exists(cls.test_out_dir):
            shutil.rmtree(cls.test_out_dir)
            print(f"\n[*] 测试清理完毕，已删除临时目录: {cls.test_out_dir}")


if __name__ == '__main__':
    unittest.main()