import unittest
import os
import sys
import tempfile
import json

# 动态将项目根目录加入 sys.path，确保能正确导入 core 模块
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.work_logic.subtitle_parser import SubtitleParser


class TestSubtitleParser(unittest.TestCase):
    def setUp(self):
        """测试前置准备：创建一个临时目录用于存放三种格式的测试字幕文件"""
        self.test_dir = tempfile.TemporaryDirectory()
        self.dir_path = self.test_dir.name

    def tearDown(self):
        """测试后清理：删除临时目录和文件"""
        self.test_dir.cleanup()

    def test_parse_json_format(self):
        """测试 1：解析 Whisper 输出的标准 JSON 格式"""
        json_path = os.path.join(self.dir_path, "test.json")
        mock_data = [
            {
                "start": 1.5,
                "end": 3.0,
                "text": "Hello JSON",
                "language": "en",
                "probability": 0.95
                # 故意遗漏 words 字段，测试归一化是否能补齐
            }
        ]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        # 执行解析
        result = SubtitleParser.parse(json_path)

        # 验证结果
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["start"], 1.5)
        self.assertEqual(result[0]["text"], "Hello JSON")
        self.assertEqual(result[0]["language"], "en")
        self.assertEqual(result[0]["probability"], 0.95)
        # 验证防呆占位符是否生效
        self.assertEqual(result[0]["words"], [])

    def test_parse_srt_format(self):
        """测试 2：解析纯文本 SRT 格式，并验证占位符补齐"""
        srt_path = os.path.join(self.dir_path, "test.srt")
        mock_srt_content = """1
00:00:01,500 --> 00:00:03,000
Hello SRT
This is the second line.
"""
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(mock_srt_content)

        # 执行解析
        result = SubtitleParser.parse(srt_path)

        # 验证结果
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["start"], 1.5)
        self.assertEqual(result[0]["end"], 3.0)
        self.assertEqual(result[0]["text"], "Hello SRT This is the second line.")

        # 验证缺失的元数据是否被正确填充了默认占位符
        self.assertEqual(result[0]["language"], "auto")
        self.assertEqual(result[0]["probability"], 1.0)
        self.assertEqual(result[0]["words"], [])

    def test_parse_vtt_format(self):
        """测试 3：解析纯文本 WebVTT 格式，并验证时间轴提取"""
        vtt_path = os.path.join(self.dir_path, "test.vtt")
        mock_vtt_content = """WEBVTT

00:00:02.500 --> 00:00:04.250 align:middle line:90%
Hello VTT!
"""
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write(mock_vtt_content)

        # 执行解析
        result = SubtitleParser.parse(vtt_path)

        # 验证结果
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["start"], 2.5)
        self.assertEqual(result[0]["end"], 4.25)
        self.assertEqual(result[0]["text"], "Hello VTT!")

        # 验证缺失的元数据占位符
        self.assertEqual(result[0]["language"], "auto")
        self.assertEqual(result[0]["probability"], 1.0)
        self.assertEqual(result[0]["words"], [])

    def test_invalid_file_format(self):
        """测试 4：测试异常文件格式的拦截能力"""
        txt_path = os.path.join(self.dir_path, "test.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("Some random text")

        # 验证解析不支持的格式时，是否抛出 ValueError 异常
        with self.assertRaises(ValueError):
            SubtitleParser.parse(txt_path)


if __name__ == "__main__":
    unittest.main()