import os
from typing import List, Dict, Any


class SubtitleWriter:
    """
    工业级字幕排版与导出模块。
    支持 SRT 与 VTT 格式，可灵活导出纯原文、纯译文以及双语合并字幕。
    """

    @staticmethod
    def format_timestamp(seconds: float, fmt: str = "srt") -> str:
        """
        将浮点数秒数精确转换为标准时间戳格式。
        - SRT 格式: HH:MM:SS,mmm (毫秒为逗号)
        - VTT 格式: HH:MM:SS.mmm (毫秒为点号)
        """
        seconds = max(0.0, float(seconds))
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int(round((seconds - int(seconds)) * 1000))

        # 毫秒满千进位处理
        if millisecs >= 1000:
            millisecs -= 1000
            secs += 1
            if secs >= 60:
                secs -= 60
                minutes += 1
                if minutes >= 60:
                    minutes -= 60
                    hours += 1

        separator = "," if fmt.lower() == "srt" else "."
        return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millisecs:03d}"

    @classmethod
    def generate_srt_content(cls, segments: List[Dict[str, Any]], mode: str = "translated") -> str:
        """
        生成标准 SRT 文本内容。
        :param segments: 字幕段列表 [{'start': float, 'end': float, 'text': str, 'translated': str}]
        :param mode: 导出模式
                     - 'original': 仅源语言
                     - 'translated': 仅目标译文
                     - 'bilingual': 双语合并 (上译文下原文，或按需求调整)
        """
        entries = []
        index = 1

        for seg in segments:
            start_time = cls.format_timestamp(seg.get("start", 0.0), fmt="srt")
            end_time = cls.format_timestamp(seg.get("end", 0.0), fmt="srt")
            orig_text = seg.get("text", "").strip()
            trans_text = seg.get("translated", "").strip()

            if mode == "original":
                content = orig_text
            elif mode == "translated":
                content = trans_text if trans_text else orig_text
            elif mode == "bilingual":
                # 双语排版：上行为译文，下行为原文
                if trans_text and orig_text:
                    content = f"{trans_text}\n{orig_text}"
                else:
                    content = trans_text or orig_text
            else:
                raise ValueError(f"未知的字幕模式: {mode}")

            # 过滤纯空段落
            if not content.strip():
                continue

            entry = f"{index}\n{start_time} --> {end_time}\n{content}\n"
            entries.append(entry)
            index += 1

        return "\n".join(entries) + "\n"

    @classmethod
    def generate_vtt_content(cls, segments: List[Dict[str, Any]], mode: str = "translated") -> str:
        """
        生成标准 WebVTT 文本内容。
        """
        entries = ["WEBVTT\n"]

        for index, seg in enumerate(segments, start=1):
            start_time = cls.format_timestamp(seg.get("start", 0.0), fmt="vtt")
            end_time = cls.format_timestamp(seg.get("end", 0.0), fmt="vtt")
            orig_text = seg.get("text", "").strip()
            trans_text = seg.get("translated", "").strip()

            if mode == "original":
                content = orig_text
            elif mode == "translated":
                content = trans_text if trans_text else orig_text
            elif mode == "bilingual":
                if trans_text and orig_text:
                    content = f"{trans_text}\n{orig_text}"
                else:
                    content = trans_text or orig_text
            else:
                raise ValueError(f"未知的字幕模式: {mode}")

            if not content.strip():
                continue

            entry = f"{index}\n{start_time} --> {end_time}\n{content}\n"
            entries.append(entry)

        return "\n".join(entries) + "\n"

    @classmethod
    def write_file(cls, filepath: str, content: str, encoding: str = "utf-8") -> str:
        """
        安全写入本地磁盘，若目标目录不存在则自动创建。
        """
        out_dir = os.path.dirname(os.path.abspath(filepath))
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        with open(filepath, "w", encoding=encoding) as f:
            f.write(content)

        return filepath

    @classmethod
    def export_subtitles(
        cls,
        segments: List[Dict[str, Any]],
        output_prefix: str,
        modes: List[str] = None,
        file_format: str = "srt",
        lang_code: str = "trans"
    ) -> Dict[str, str]:
        """
        一键导出多轨道字幕文件。

        :param segments: 翻译完成的数据列表
        :param output_prefix: 输出文件的前缀或基础路径 (例如 "output/my_video")
        :param modes: 需要导出的模式列表，默认包含 ['original', 'translated', 'bilingual']
        :param file_format: 'srt' 或 'vtt'
        :param lang_code: 译文轨道的语种标识 (例如 'zh', 'ar', 'de' 等)
        :return: 生成的文件路径映射表 {'original': 'path/to/my_video.orig.srt', ...}
        """
        if modes is None:
            modes = ["original", "translated", "bilingual"]

        file_format = file_format.lower()
        if file_format not in ["srt", "vtt"]:
            raise ValueError(f"不支持的字幕格式: {file_format}，仅支持 srt 或 vtt")

        generated_files = {}

        mode_suffix_map = {
            "original": "orig",
            "translated": lang_code,
            "bilingual": f"bilingual.{lang_code}"
        }

        for mode in modes:
            suffix = mode_suffix_map.get(mode, mode)
            target_path = f"{output_prefix}.{suffix}.{file_format}"

            if file_format == "srt":
                content = cls.generate_srt_content(segments, mode=mode)
            else:
                content = cls.generate_vtt_content(segments, mode=mode)

            cls.write_file(target_path, content, encoding="utf-8")
            generated_files[mode] = target_path
            print(f"[+] 字幕生成成功 [{mode}]: {target_path}")

        return generated_files