from pathlib import Path


def run_translate_typeset_process(source_file_path: str, output_dir: str, target_langs: list,
                                  file_formats: list, export_modes: list, ipc_queue):
    """
    第二阶段打工人：大语言模型翻译独立进程入口 (重构为多进程目标函数)。

    职责：委托解析源文件 -> 唤醒 LLM -> 循环翻译 -> 格式化落盘 -> 进程终结。
    绝对不干涉 UI 展示，完全与 Qt 剥离。所有汇报均通过 ipc_queue (消息队列) 完成。
    """

    # ==========================================
    # 铁律落地：重型依赖与业务组件在进程内部按需导入！
    # 彻底杜绝主程序因 import 导致的显存幽灵占用和上下文冲突。
    # ==========================================
    from core.work_logic.translator import TranslatorEngine
    from core.work_logic.subtitle_writer import SubtitleWriter
    from core.work_logic.subtitle_parser import SubtitleParser

    def export_to_disk(segments_data: list, lang_code: str, active_modes: list):
        """内部闭包辅助方法：对接 SubtitleWriter 执行按文件夹分类落盘"""
        media_name = Path(source_file_path).stem
        if media_name.startswith("raw_segments_"):
            media_name = media_name.replace("raw_segments_", "").rsplit("_", 1)[0]

        base_out_dir = Path(output_dir) / media_name

        folder_mapping = {
            "original": "Original_原声音轨",
            "translated": "Translated_纯译文轨",
            "bilingual": "Bilingual_双语字幕轨"
        }

        for fmt in file_formats:
            for mode in active_modes:
                # 逻辑过滤：当处理原声时，跳过纯译文/双语的生成；当处理翻译时，跳过纯原声的生成
                if mode == "original" and lang_code != "orig":
                    continue
                if mode in ["translated", "bilingual"] and lang_code == "orig":
                    continue

                folder_name = folder_mapping.get(mode, mode)
                format_folder_name = f"{folder_name}_{fmt.upper()}"

                target_dir = base_out_dir / format_folder_name
                target_dir.mkdir(parents=True, exist_ok=True)

                file_prefix = str(target_dir / media_name)

                SubtitleWriter.export_subtitles(
                    segments=segments_data,
                    output_prefix=file_prefix,
                    modes=[mode],
                    file_format=fmt,
                    lang_code=lang_code if lang_code != "orig" else "en"
                )
                ipc_queue.put({"type": "log", "message": f"[写入器] 已生成文件: {format_folder_name} -> [{lang_code}]",
                               "level": "info"})

    try:
        # ==========================================
        # 步骤 1：智能数据解析
        # ==========================================
        ipc_queue.put({"type": "log", "message": "[系统] 正在解析并归一化源字幕文件...", "level": "info"})
        segments = SubtitleParser.parse(source_file_path)

        if not segments:
            raise RuntimeError("源文件解析失败或内容为空。")

        detected_source_lang = segments[0].get("language", "auto")

        # ==========================================
        # 步骤 1.5：原声字幕的顺手生成
        # ==========================================
        if "original" in export_modes:
            ipc_queue.put({"type": "log", "message": "[系统] 检测到纯原声需求，正在导出原声音轨...", "level": "info"})
            export_to_disk(segments, "orig", ["original"])
            ipc_queue.put({"type": "log", "message": "[系统] 原声字幕导出完毕。", "level": "success"})

        # ==========================================
        # 步骤 2：判断是否需要启动翻译引擎
        # ==========================================
        needs_translation = "translated" in export_modes or "bilingual" in export_modes
        if not needs_translation or not target_langs:
            ipc_queue.put({"type": "log", "message": "[系统] 无需大模型翻译任务，流程结束。", "level": "success"})
            ipc_queue.put({"type": "finished", "success": True, "message": output_dir})
            return

        ipc_queue.put({"type": "log", "message": "[系统] 正在唤醒大语言模型到显存...", "level": "warning"})

        # 此时显卡环境完全只属于当前独立运行的子进程
        translator = TranslatorEngine()

        # ==========================================
        # 步骤 3：多目标语言循环翻译
        # ==========================================
        total_langs = len(target_langs)

        for lang_idx, lang_code in enumerate(target_langs):
            ipc_queue.put({"type": "log",
                           "message": f"[ALMA] 开始翻译目标语言 ({lang_idx + 1}/{total_langs}): {lang_code.upper()}",
                           "level": "highlight"})

            translated_segments = []
            generator = translator.translate_segments(
                segments=segments,
                target_lang=lang_code,
                source_lang=detected_source_lang
            )

            for seg_idx, new_seg in enumerate(generator):
                translated_segments.append(new_seg)

                # 独立进度条计算并投递到消息队列：每门语言独立跑满 0-100%
                seg_progress = new_seg.get("translation_progress", 0)
                total_progress = int(seg_progress)

                ipc_queue.put({"type": "progress", "value": total_progress})

            # ==========================================
            # 步骤 4：当前语言成品格式化与落盘
            # ==========================================
            export_to_disk(translated_segments, lang_code, export_modes)

        ipc_queue.put({"type": "progress", "value": 100})
        ipc_queue.put({"type": "log", "message": "[系统] 翻译全流程执行完毕，即将释放显存！", "level": "success"})
        ipc_queue.put({"type": "finished", "success": True, "message": output_dir})

    except Exception as e:
        ipc_queue.put({"type": "error", "message": f"翻译阶段发生异常: {str(e)}"})
        ipc_queue.put({"type": "finished", "success": False, "message": str(e)})