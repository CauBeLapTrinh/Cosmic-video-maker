"""
Module 4: Video Compositor & Subtitles
Assembles per-scene visual clips (strictly matched to scene audio duration),
mixes layered voiceover and ducked background audio, burns stylish subtitles,
and exports high-bitrate broadcast MP4 videos without premature cutoffs.
"""

import os
import subprocess
import json
import time
from typing import List, Optional, Callable, Dict, Any


def get_video_info(file_path: str) -> Dict[str, Any]:
    """
    Returns metadata about a video file: width, height, duration, fps, size_mb.
    """
    if not os.path.exists(file_path):
        return {}

    info = {
        "path": file_path,
        "size_mb": round(os.path.getsize(file_path) / (1024 * 1024), 2),
        "duration": 0.0,
        "width": 0,
        "height": 0,
        "fps": 30.0
    }

    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,duration:format=duration",
            "-of", "json",
            file_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(result.stdout)
        
        streams = data.get("streams", [])
        if streams:
            v_stream = streams[0]
            info["width"] = int(v_stream.get("width", 0))
            info["height"] = int(v_stream.get("height", 0))
            if "duration" in v_stream and v_stream["duration"]:
                info["duration"] = round(float(v_stream["duration"]), 2)
            fps_str = v_stream.get("r_frame_rate", "30/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                if float(den) > 0:
                    info["fps"] = round(float(num) / float(den), 1)

        format_data = data.get("format", {})
        if info["duration"] == 0.0 and "duration" in format_data:
            info["duration"] = round(float(format_data["duration"]), 2)

    except Exception as e:
        print(f"[ffprobe warning] Could not parse video metadata: {e}")

    return info


def concatenate_clips_ffmpeg(
    clip_paths: List[str],
    output_path: str,
    target_width: int,
    target_height: int,
    fps: int = 30
) -> str:
    """
    Concatenates an arbitrary number of scene clips into one continuous video stream.
    Re-encodes with identical resolution, framerate, and pixel format to eliminate timestamp drift.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    concat_list_file = output_path.replace(".mp4", f"_concat_{int(time.time()*1000)}.txt")

    # Write concat manifest
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            safe_p = os.path.abspath(p).replace("\\", "/")
            f.write(f"file '{safe_p}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_file,
        "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,crop={target_width}:{target_height},fps={fps}",
        "-c:v", "libx264",
        "-preset", "faster",
        "-pix_fmt", "yuv420p",
        "-an",
        output_path
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    finally:
        if os.path.exists(concat_list_file):
            try:
                os.remove(concat_list_file)
            except Exception:
                pass

    return output_path


def _prepare_ffmpeg_subtitles_path(subtitles_path: str) -> str:
    """Safely formats subtitle path for FFmpeg filter on Windows without colon conflicts."""
    try:
        rel = os.path.relpath(subtitles_path).replace(os.sep, "/").replace("\\", "/")
        if ":" not in rel:
            return rel
    except Exception:
        pass
    return os.path.abspath(subtitles_path).replace(os.sep, "/").replace("\\", "/").replace(":", "\\:")


def render_final_video(
    scene_clips: List[str],
    audio_path: str,
    output_video_path: str,
    subtitles_path: Optional[str] = None,
    aspect_ratio: str = "16:9",
    target_total_duration: Optional[float] = None,
    fps: int = 30,
    video_bitrate: str = "4000k",
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> str:
    """
    Master video rendering pipeline:
    1. Validates scene clips and audio track.
    2. Sequentially concatenates scene visual clips.
    3. Merges audio track (narration + ducked BGM) matching exact duration.
    4. Burns styled ASS/SRT subtitles onto the video stream.
    5. Exports optimized YouTube MP4 (H.264 / AAC / FastStart / 4000k bitrate).
       Guarantees zero premature cutoffs!
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(output_video_path)), "temp_render")
    os.makedirs(temp_dir, exist_ok=True)

    if progress_callback:
        progress_callback(0.05, f"Validating {len(scene_clips)} scene clips and master audio...")

    if not scene_clips:
        raise ValueError("No scene visual clips provided for rendering.")
    if not os.path.exists(audio_path):
        raise ValueError(f"Master audio track not found: {audio_path}")

    # Inspect master audio duration
    from modules.audio_gen import get_audio_duration
    audio_dur = get_audio_duration(audio_path)
    final_target_duration = target_total_duration if target_total_duration and target_total_duration > 0 else audio_dur

    is_vertical = ("9:16" in aspect_ratio)
    target_width = 1080 if is_vertical else 1920
    target_height = 1920 if is_vertical else 1080

    # Step 1: Concatenate scene clips
    if progress_callback:
        progress_callback(0.25, f"Concatenating {len(scene_clips)} scene clips into continuous sequence...")

    concat_vid = os.path.join(temp_dir, f"concat_{int(time.time()*1000)}.mp4")
    if len(scene_clips) == 1:
        concat_vid = scene_clips[0]
    else:
        concatenate_clips_ffmpeg(scene_clips, concat_vid, target_width, target_height, fps=fps)

    # Step 2: Composite audio and burn subtitles
    if progress_callback:
        progress_callback(0.60, "Compositing master audio and burning subtitles...")


    vf_filters = []
    if subtitles_path and os.path.exists(subtitles_path):
        sub_safe_path = _prepare_ffmpeg_subtitles_path(subtitles_path)
        vf_filters.append(f"subtitles={sub_safe_path}")

    # Build primary FFmpeg command
    # NOTE: We DO NOT use -shortest blindly. We enforce exact duration -t {final_target_duration}
    # so narration is NEVER truncated!
    cmd = [
        "ffmpeg", "-y",
        "-i", concat_vid,
        "-i", audio_path,
    ]

    if vf_filters:
        cmd.extend(["-vf", ",".join(vf_filters)])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "medium",
        "-b:v", video_bitrate,
        "-maxrate", "5000k",
        "-bufsize", "8000k",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", f"{final_target_duration:.3f}",
        "-movflags", "+faststart",
        output_video_path
    ])

    if progress_callback:
        progress_callback(0.75, "Encoding high-efficiency H.264 broadcast stream (bitrate: 4000k)...")

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        err_msg = proc.stderr.decode("utf-8", errors="ignore")
        print(f"[FFmpeg Render Warning] Subtitle burn failed ({err_msg[-200:]}). Retrying without subtitles...")
        cmd_fallback = [
            "ffmpeg", "-y",
            "-i", concat_vid,
            "-i", audio_path,
            "-c:v", "libx264",
            "-preset", "faster",
            "-b:v", video_bitrate,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", f"{final_target_duration:.3f}",
            "-movflags", "+faststart",
            output_video_path
        ]
        subprocess.run(cmd_fallback, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Cleanup temporary concat file
    if concat_vid != scene_clips[0] and os.path.exists(concat_vid):
        try:
            os.remove(concat_vid)
        except Exception:
            pass

    if progress_callback:
        progress_callback(1.0, f"Rendering complete! Video duration: {final_target_duration:.1f}s.")

    return output_video_path


def render_with_moviepy(
    scene_clips: List[str],
    audio_path: str,
    output_video_path: str,
    fps: int = 30
) -> str:
    """
    Alternative compositor engine using MoviePy 2.x concatenate_videoclips(..., method='compose').
    """
    from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips

    clips = [VideoFileClip(p) for p in scene_clips]
    final_video = concatenate_videoclips(clips, method="compose")
    audio = AudioFileClip(audio_path)
    final_video = final_video.with_audio(audio)
    final_video.write_videofile(
        output_video_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        bitrate="4000k"
    )
    for c in clips:
        c.close()
    final_video.close()
    return output_video_path
