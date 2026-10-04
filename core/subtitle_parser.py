import json
import re
from pathlib import Path


class SubtitleParser:
    """
    核心字幕解析与归一化工具。
    职责：将各种格式的外部字幕（JSON, SRT, VTT）统一转换、填补为标准的内部字典列表（List[dict]）。
    这是保证翻译 Worker (TranslateCaptionWorker) 不受外部数据格式干扰的“防腐层”。
    """

    @classmethod
    def parse(cls, file_path: str) -> list:
        """入口方法：自动识别格式并归一化"""
        if not file_path or not Path(file_path).exists():
            raise FileNotFoundError(f"字幕文件不存在: {file_path}")

        ext = Path(file_path).suffix.lower()
        segments = []

        # 1. 路由到对应的解析器
        if ext == ".json":
            segments = cls._parse_json(file_path)
        elif ext == ".srt":
            segments = cls._parse_srt(file_path)
        elif ext == ".vtt":
            segments = cls._parse_vtt(file_path)
        else:
            raise ValueError(f"不支持的字幕文件格式: {ext}")

        # 2. 强制归一化（应用数据契约）
        return cls._normalize_segments(segments)

    @classmethod
    def _parse_json(cls, file_path: str) -> list:
        # 使用 utf-8-sig 兼容可能带有 BOM 头的 Windows 文件
        with open(file_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        # 兼容 Whisper 可能返回的根节点包裹格式
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "segments" in data:
            return data["segments"]
        return []

    @classmethod
    def _parse_srt(cls, file_path: str) -> list:
        segments = []
        with open(file_path, "r", encoding="utf-8-sig") as f:
            content = f.read()

        # 按双换行符分割字幕块
        blocks = re.split(r'\n\s*\n', content.strip())
        for block in blocks:
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if len(lines) >= 3:
                # SRT 标准结构: [0]序号, [1]时间轴, [2:]文本
                time_line = lines[1]
                text = " ".join(lines[2:])
                start, end = cls._extract_times(time_line)
                if start is not None and end is not None:
                    segments.append({"start": start, "end": end, "text": text})
        return segments

    @classmethod
    def _parse_vtt(cls, file_path: str) -> list:
        segments = []
        with open(file_path, "r", encoding="utf-8-sig") as f:
            content = f.read()

        blocks = re.split(r'\n\s*\n', content.strip())
        for block in blocks:
            if block.startswith("WEBVTT"):
                continue

            lines = [line.strip() for line in block.split('\n') if line.strip()]

            # 灵活寻找包含 "-->" 的时间行，防止部分 VTT 带有奇怪的标识符
            time_line_idx = -1
            for i, line in enumerate(lines):
                if "-->" in line:
                    time_line_idx = i
                    break

            if time_line_idx != -1 and time_line_idx + 1 < len(lines):
                time_line = lines[time_line_idx]
                text = " ".join(lines[time_line_idx + 1:])
                start, end = cls._extract_times(time_line)
                if start is not None and end is not None:
                    segments.append({"start": start, "end": end, "text": text})
        return segments

    @classmethod
    def _extract_times(cls, time_line: str) -> tuple:
        """内部方法：提取 SRT/VTT 的时间戳并转换为秒数 (float)"""
        try:
            parts = time_line.split("-->")
            if len(parts) != 2:
                return None, None
            start_sec = cls._time_str_to_seconds(parts[0].strip())
            end_sec = cls._time_str_to_seconds(parts[1].strip())
            return start_sec, end_sec
        except Exception:
            return None, None

    @classmethod
    def _time_str_to_seconds(cls, time_str: str) -> float:
        """将 00:00:01,000 或 00:00:01.000 转换为 1.0 秒"""
        # 清理 VTT 可能自带的坐标信息 (如: align:middle)
        time_str = time_str.split(" ")[0]
        # 统一将逗号(SRT)替换为点(VTT)，方便分割
        time_str = time_str.replace(",", ".")

        parts = time_str.split(":")
        if len(parts) == 3:
            h, m, s = parts
        elif len(parts) == 2:
            h = "0"
            m, s = parts
        else:
            return 0.0

        s_parts = s.split(".")
        sec = float(s_parts[0])
        ms = float(s_parts[1]) / 1000.0 if len(s_parts) > 1 else 0.0

        return float(h) * 3600 + float(m) * 60 + sec + ms

    @classmethod
    def _normalize_segments(cls, segments: list) -> list:
        """
        核心数据契约：不论来源，强制补齐所有缺失字段。
        保证返回给 Worker 和大模型的字典格式永远保持一致。
        """
        normalized = []
        for seg in segments:
            norm_seg = {
                # 必备基础字段
                "start": float(seg.get("start", 0.0)),
                "end": float(seg.get("end", 0.0)),
                "text": str(seg.get("text", "")).strip(),

                # --- 补齐占位符 (防呆设计) ---
                "language": seg.get("language", "auto"),  # 默认交由 LLM 自动推断
                "words": seg.get("words", []),  # 默认无词级时间戳
                "probability": seg.get("probability", 1.0)  # 默认满置信度
            }
            normalized.append(norm_seg)
        return normalized