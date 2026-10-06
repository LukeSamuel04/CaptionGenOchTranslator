import unittest
import copy
from core.work_logic.translator import TranslatorEngine


class TestTranslatorEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        在所有测试开始前只初始化一次大模型，避免重复加载浪费时间和显存。
        """
        print("\n[测试准备] 正在加载 Llama 3.1 8B 翻译引擎...")
        cls.engine = TranslatorEngine(context_size=2)

    def test_multilingual_translation(self):
        """
        测试多语言翻译，验证滑动窗口和 JSON 约束是否在各种语言下都能稳定工作。
        """
        # 模拟 Whisper 引擎吐出的标准数据结构
        mock_segments = [
            {"start": 0.0, "end": 2.0, "text": "Oh, look at that!"},
            {"start": 2.0, "end": 4.0, "text": "It is a huge apple."},
            {"start": 4.0, "end": 6.0, "text": "I want to eat it."},
            {"start": 6.0, "end": 8.0, "text": "But it might be poisonous."},
            {"start": 8.0, "end": 10.0, "text": "Let's leave it here."}
        ]

        target_languages = ["简体中文", "阿拉伯语", "乌克兰语", "德语", "西班牙语"]

        for lang in target_languages:
            print(f"\n{'=' * 40}")
            print(f"[*] 开始测试翻译语言: {lang}")
            print(f"{'=' * 40}")

            # 使用深拷贝，因为 translate_segments 会直接在传入的字典里原地添加 'translated' 键
            # 如果不拷贝，第一轮循环后字典就被污染了
            test_data = copy.deepcopy(mock_segments)

            # 将 generator 转换为 list 强制执行所有 yield
            results = list(self.engine.translate_segments(test_data, target_lang=lang))

            # 断言验证
            self.assertEqual(len(results), len(mock_segments), "翻译后的条目数量与原字幕不符")

            for item in results:
                # 检查必备字段是否都成功注入
                self.assertIn("translated", item, "缺失译文关键字段")
                self.assertIn("translation_progress", item, "缺失进度字段")
                self.assertNotEqual(item["translated"], "", "译文为空")

                print(f"[{item['start']}s - {item['end']}s]")
                print(f"原文: {item['text']}")
                print(f"译文: {item['translated']}\n")


if __name__ == '__main__':
    unittest.main()