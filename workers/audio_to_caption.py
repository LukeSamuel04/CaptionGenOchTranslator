import os
import json
import time
from pathlib import Path


def run_audio_to_caption_process(media_path: str, cache_dir: str, ipc_queue):
    """
    第一阶段打工人：纯听写独立进程入口 (重构为多进程目标函数)。

    职责：剥离音频 -> Whisper 听写 -> 导出 JSON -> 进程终结。
    绝对不干涉 UI 展示，完全与 Qt 剥离。所有汇报均通过 ipc_queue (消息队列) 完成。
    """

    # ==========================================
    # 铁律落地：重型依赖在进程内部按需导入！
    # 这样主程序在导包时，绝对不会意外加载 PyTorch 占用显存。
    # ==========================================
    from core.whisper_engine import WhisperEngine
    from core.audio_processor import extract_audio

    try:
        # ==========================================
        # 步骤 1：准备工作与音频剥离
        # ==========================================
        os.makedirs(cache_dir, exist_ok=True)
        temp_audio_path = os.path.join(cache_dir, "temp_extract_audio.wav")

        media_name = Path(media_path).name
        ipc_queue.put({"type": "log", "message": f"[系统] 开始处理媒体文件: {media_name}", "level": "info"})
        ipc_queue.put({"type": "log", "message": "[系统] 正在抽离音频流...", "level": "warning"})

        success, result_msg = extract_audio(media_path, temp_audio_path)
        if not success:
            raise RuntimeError(f"音频提取失败: {result_msg}")

        ipc_queue.put({"type": "log", "message": "[系统] 音频抽离成功，准备载入听写引擎。", "level": "success"})

        # ==========================================
        # 步骤 2：加载 Whisper 引擎并执行听写
        # ==========================================
        ipc_queue.put({"type": "log", "message": "[系统] 正在载入 Whisper AI 模型到显存...", "level": "warning"})

        # 这里的显卡环境完全只属于当前子进程
        whisper_engine = WhisperEngine()

        segments = []
        transcription_generator = whisper_engine.transcribe_audio(temp_audio_path)

        for segment_data in transcription_generator:
            # 注: 多进程架构下，不需要再检测 self.is_running
            # 如果用户点取消，主程序会直接从操作系统层级 terminate 强杀本进程。
            segments.append(segment_data)

            # 通过 IPC 通道汇报 0-100 进度
            progress = int(segment_data.get("progress", 0))
            ipc_queue.put({"type": "progress", "value": progress})

        if not segments:
            raise RuntimeError("未提取到任何有效语音，请检查视频是否静音。")

        # 确保进度条走到 100%
        ipc_queue.put({"type": "progress", "value": 100})
        ipc_queue.put(
            {"type": "log", "message": f"[Whisper] 听写完成！共解析 {len(segments)} 句话。", "level": "success"})

        # ==========================================
        # 步骤 3：数据无损序列化落盘 (JSON 接力棒)
        # ==========================================
        video_stem = Path(media_path).stem
        json_filename = f"raw_segments_{video_stem}_{int(time.time())}.json"
        json_cache_path = os.path.join(cache_dir, json_filename)

        with open(json_cache_path, "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)

        ipc_queue.put({"type": "log", "message": "[系统] 听写数据已缓存，当前独立进程即将功成身退...", "level": "info"})

        # 打扫战场：删掉占硬盘的临时音频
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except Exception:
                pass

        # ==========================================
        # 步骤 4：任务圆满交接
        # ==========================================
        ipc_queue.put({"type": "finished", "success": True, "message": json_cache_path})

    except Exception as e:
        # 发生异常，通过错误管道上报给前台
        ipc_queue.put({"type": "error", "message": f"听写阶段发生异常: {str(e)}"})
        ipc_queue.put({"type": "finished", "success": False, "message": str(e)})

    # 注: 我们去掉了原来极其严苛的 gc.collect() 和 torch.cuda.empty_cache()。
    # 因为多进程最牛的地方就在于：只要这个函数执行完毕走到最后一行，
    # 操作系统就会直接回收该进程分配到的所有内存和显存。这是最物理、最干净的清理方式！