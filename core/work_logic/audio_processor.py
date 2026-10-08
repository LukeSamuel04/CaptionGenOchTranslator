import os
import subprocess
import imageio_ffmpeg as ffmpeg


def extract_audio(video_path: str, output_audio_path: str) -> tuple[bool, str]:
    """
    从视频中提取音频，并转换为 Whisper 最佳格式 (16kHz, 单声道, 16-bit PCM WAV)

    :param video_path: 源视频文件的绝对路径
    :param output_audio_path: 提取出的音频保存路径
    :return: (是否成功, 成功时返回音频路径 / 失败时返回具体的错误信息)
    """
    # 1. 基础校验：确认视频文件真的存在
    if not os.path.exists(video_path):
        return False, f"找不到视频文件: {video_path}"

    try:
        # 2. 动态获取 imageio-ffmpeg 内置的 ffmpeg.exe 路径 (完美避开环境变量配置)
        ffmpeg_exe = ffmpeg.get_ffmpeg_exe()

        # 3. 构造 FFmpeg 处理命令
        cmd = [
            ffmpeg_exe,
            '-y',  # 强制覆盖输出路径已存在的文件
            '-i', video_path,  # 输入的视频文件
            '-vn',  # 核心：丢弃视频流，只处理音频
            '-acodec', 'pcm_s16le',  # 音频编码器设为 16-bit PCM (WAV)
            '-ar', '16000',  # 强制采样率为 16kHz (这是 Whisper 模型训练时用的标准)
            '-ac', '1',  # 强制转为单声道 (进一步减小文件体积)
            output_audio_path
        ]

        # 4. 执行命令
        # stdout=subprocess.PIPE 和 stderr=subprocess.PIPE 意思是把 FFmpeg 的输出“截获”下来
        # 这样它就不会在用户的界面/控制台里乱弹黑框框和乱码了
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # 5. 校验执行结果
        if result.returncode == 0:
            # 哪怕 returncode 是 0，为了绝对安全，我们再查一遍文件到底生成了没
            if os.path.exists(output_audio_path):
                return True, output_audio_path
            else:
                return False, "处理流程走完了，但未能生成音频文件，可能是视频中没有声音轨道。"
        else:
            # 如果出错了，抓取 FFmpeg 报错信息里的最后几句话返回，方便定位问题
            error_msg = result.stderr.strip().split('\n')[-3:]
            return False, f"FFmpeg 提取失败: {' | '.join(error_msg)}"

    except Exception as e:
        # 捕获所有其它意料之外的报错（比如权限不足、磁盘满了等）
        return False, f"提取音频时发生系统错误: {str(e)}"