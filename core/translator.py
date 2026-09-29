import os
import json
import torch
from llama_cpp import Llama


class TranslatorEngine:
    def __init__(self, model_path=None, context_size=2):
        """
        初始化大语言模型翻译引擎。
        :param model_path: GGUF 模型路径。如果留空，默认去 assets/models 寻找。
        :param context_size: 默认的上下文窗口大小（前后各保留几句）。
        """
        if model_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(base_dir, 'assets', 'models', 'llama-3.1-8b', 'llama-3.1-8b.gguf')

        print(f"[*] 正在唤醒本地大语言模型 (路径: {model_path})...")

        try:
            # 初始化 Llama 模型
            self.llm = Llama(
                model_path=model_path,
                n_gpu_layers=-1,  # 核心参数！-1 表示将所有计算层卸载到 4070 Ti 显存中，实现极速推理
                n_ctx=2048,  # 将上下文窗口拉高到 2048，防止长句溢出崩溃
                verbose=False  # 关闭底层的 C++ 刷屏日志，保持控制台清爽
            )
            self.context_size = context_size
            print("[*] 翻译大脑启动完毕，显存接力成功！")
        except Exception as e:
            raise RuntimeError(f"翻译模型加载失败，请检查 GGUF 文件路径是否正确: {str(e)}")

    def _build_messages(self, prev_context, target_text, next_context, target_lang):
        """
        构建包含 Few-Shot 示范的 ChatML 格式 Prompt。
        使用动态示例映射，防止模型被固定的中文示例带偏。
        """
        # 动态生成对应语言的示例译文
        example_map = {
            "简体中文": "一个苹果！",
            "繁体中文": "一個蘋果！",
            "德语": "Ein Apfel!",
            "西班牙语": "¡Una manzana!",
            "阿拉伯语": "تفاحة!",
            "乌克兰语": "Яблуко!",
            "法语": "Une pomme !",
            "日语": "りんご！",
            "韩语": "사과!",
            "俄语": "Яблоко!"
        }
        # 如果遇到字典里没有的语言，就使用占位符暗示 AI
        example_translation = example_map.get(target_lang, f"<Translate 'An apple!' to {target_lang}>")

        system_prompt = f"""You are a professional subtitle translator. Translate the [TARGET SENTENCE] into {target_lang} using the provided context.
Strictly adhere to the following rules:
1. Do NOT translate the [PREVIOUS CONTEXT] or [NEXT CONTEXT].
2. The target sentence might be a fragment. Preserve its fragmented state. Do NOT artificially add subjects or complete the sentence.
3. Do NOT output any explanations, conversational filler, or extra text.
4. You MUST output ONLY valid JSON format.

[EXAMPLE]
[PREVIOUS CONTEXT]:
N-1: Look at this!
[TARGET SENTENCE]:
N: An apple!
[NEXT CONTEXT]:
N+1: So big.
[OUTPUT]:
{{"translation": "{example_translation}"}}
"""

        user_prompt = "[PREVIOUS CONTEXT]:\n"
        user_prompt += "\n".join(prev_context) if prev_context else "None"
        user_prompt += "\n\n[TARGET SENTENCE]:\n" + target_text
        user_prompt += "\n\n[NEXT CONTEXT]:\n"
        user_prompt += "\n".join(next_context) if next_context else "None"
        user_prompt += "\n\n[OUTPUT]:"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def translate_segments(self, segments, target_lang="简体中文", context_size=None):
        """
        执行滑动窗口批量翻译 (Generator 模式)
        :param segments: Whisper 生成的字典列表 [{'start': 0, 'end': 2, 'text': '...'}]
        :param target_lang: 目标语言
        :param context_size: 允许 UI 传入新值覆盖默认的上下文大小
        :yield: 注入了 'translated' 字段的完整字典
        """
        if context_size is None:
            context_size = self.context_size

        total = len(segments)
        print(f"[*] 开始执行滑动窗口翻译，共 {total} 句，上下文范围: ±{context_size}")

        for i, segment in enumerate(segments):
            # 1. 提取滑动窗口的上下文句子
            start_idx = max(0, i - context_size)
            end_idx = min(total, i + context_size + 1)

            prev_context = [f"N-{i - j}: {segments[j]['text']}" for j in range(start_idx, i)]
            next_context = [f"N+{j - i}: {segments[j]['text']}" for j in range(i + 1, end_idx)]
            target_text = f"N: {segment['text']}"

            # 2. 构建对话结构
            messages = self._build_messages(prev_context, target_text, next_context, target_lang)

            # 3. 呼叫模型，开启 JSON 强制约束
            try:
                response = self.llm.create_chat_completion(
                    messages=messages,
                    response_format={
                        "type": "json_object",
                        "schema": {
                            "type": "object",
                            "properties": {"translation": {"type": "string"}},
                            "required": ["translation"],
                        }
                    },
                    temperature=0.1,  # 极低的温度，杜绝 AI 发散思维，要求极其确定性的输出
                )

                # 提取并解析 JSON
                raw_output = response["choices"][0]["message"]["content"]
                translated_text = json.loads(raw_output).get("translation", segment['text'])

            except Exception as e:
                print(f"[!] 警告：第 {i + 1} 句翻译失败或 JSON 解析异常: {e} | 已自动回退为原文")
                translated_text = segment['text']  # 极端的容错机制：宁可保留原文，也不能让程序崩溃

            # 4. 数据合并与状态回传
            segment['translated'] = translated_text
            progress_percent = min(100.0, ((i + 1) / total) * 100)

            yield {
                **segment,
                "translation_progress": progress_percent
            }