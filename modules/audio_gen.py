"""
Module 2: Audio Engine
Scene-by-scene audio generation architecture using Microsoft Edge TTS (edge-tts).
Measures exact duration per scene, generates per-scene and global synchronized subtitles,
and seamlessly combines scene audio into a master voiceover with BGM ducking.
"""

import os
import asyncio
from datetime import timedelta
from typing import List, Dict, Any, Tuple, Optional, Callable
from dataclasses import dataclass
import subprocess
from pydub import AudioSegment


VOICE_PRESETS = {
    "Christopher (US Male - Deep Documentary)": "en-US-ChristopherNeural",
    "Guy (US Male - Natural & Engaging)": "en-US-GuyNeural",
    "Eric (US Male - Scientific Explainer)": "en-US-EricNeural",
    "Aria (US Female - Expressive & Rich)": "en-US-AriaNeural",
    "Jenny (US Female - Clear Documentary)": "en-US-JennyNeural",
    "Ryan (UK Male - BBC Cosmos Style)": "en-GB-RyanNeural",
    "Sonia (UK Female - British Narrator)": "en-GB-SoniaNeural",
}


@dataclass
class WordTiming:
    word: str
    start: float  # seconds
    end: float    # seconds


@dataclass
class SubtitleCue:
    index: int
    start: float  # seconds
    end: float    # seconds
    text: str


def format_srt_timestamp(seconds: float) -> str:
    """Formats float seconds into SRT timestamp string HH:MM:SS,mmm"""
    td = timedelta(seconds=max(0.0, seconds))
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_ass_timestamp(seconds: float) -> str:
    """Formats float seconds into ASS timestamp string H:MM:SS.cc (centiseconds)"""
    td = timedelta(seconds=max(0.0, seconds))
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    centis = int(td.microseconds / 10000)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def get_audio_duration(file_path: str) -> float:
    """
    Returns exact duration of an audio file in seconds with millisecond precision.
    """
    if not os.path.exists(file_path):
        return 0.0
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        dur = float(result.stdout.strip())
        if dur > 0.0:
            return round(dur, 3)
    except Exception:
        pass

    try:
        audio = AudioSegment.from_file(file_path)
        return round(len(audio) / 1000.0, 3)
    except Exception:
        return 0.0


def _interpolate_words_from_sentences(sentence_cues: List[SubtitleCue]) -> List[WordTiming]:
    """
    Interpolates word timings proportionally from sentence timestamps based on word character length.
    """
    word_timings: List[WordTiming] = []
    for sc in sentence_cues:
        words = sc.text.strip().split()
        if not words:
            continue
        duration = max(0.1, sc.end - sc.start)
        char_weights = [max(1, len(w)) for w in words]
        total_weight = sum(char_weights)
        
        curr_t = sc.start
        for w, weight in zip(words, char_weights):
            w_dur = (weight / total_weight) * duration
            word_timings.append(WordTiming(
                word=w,
                start=round(curr_t, 3),
                end=round(curr_t + w_dur, 3)
            ))
            curr_t += w_dur
    return word_timings


async def _generate_edge_tts_audio_async(
    text: str,
    output_path: str,
    voice: str = "en-US-ChristopherNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz"
) -> Tuple[List[WordTiming], List[SubtitleCue]]:
    """Internal async worker to stream TTS audio and harvest timing chunks."""
    import edge_tts

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    
    audio_data = bytearray()
    raw_word_cues: List[WordTiming] = []
    sentence_cues: List[SubtitleCue] = []

    async for chunk in communicate.stream():
        chunk_type = chunk.get("type")
        if chunk_type == "audio":
            audio_data.extend(chunk["data"])
        elif chunk_type == "WordBoundary":
            start_sec = (chunk["offset"] / 10) / 1_000_000
            dur_sec = (chunk["duration"] / 10) / 1_000_000
            raw_word_cues.append(WordTiming(
                word=chunk["text"],
                start=start_sec,
                end=start_sec + dur_sec
            ))
        elif chunk_type == "SentenceBoundary":
            start_sec = (chunk["offset"] / 10) / 1_000_000
            dur_sec = (chunk["duration"] / 10) / 1_000_000
            sentence_cues.append(SubtitleCue(
                index=len(sentence_cues) + 1,
                start=start_sec,
                end=start_sec + dur_sec,
                text=chunk["text"].strip()
            ))

    with open(output_path, "wb") as f:
        f.write(audio_data)

    if sentence_cues and not raw_word_cues:
        raw_word_cues = _interpolate_words_from_sentences(sentence_cues)
    elif not sentence_cues and not raw_word_cues:
        total_dur = get_audio_duration(output_path)
        sentence_cues = [SubtitleCue(index=1, start=0.0, end=total_dur, text=text)]
        raw_word_cues = _interpolate_words_from_sentences(sentence_cues)

    return raw_word_cues, sentence_cues


def generate_scene_voiceover_sync(
    text: str,
    output_path: str,
    voice: str = "en-US-ChristopherNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz"
) -> Tuple[float, List[WordTiming], List[SubtitleCue]]:
    """
    Synthesizes TTS audio for a single scene and returns (exact_duration, words, sentences).
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            words, sents = loop.run_until_complete(_generate_edge_tts_audio_async(text, output_path, voice, rate, pitch))
        else:
            words, sents = loop.run_until_complete(_generate_edge_tts_audio_async(text, output_path, voice, rate, pitch))
    except Exception:
        words, sents = asyncio.run(_generate_edge_tts_audio_async(text, output_path, voice, rate, pitch))

    duration = get_audio_duration(output_path)
    return duration, words, sents


def build_chunked_subtitles(
    word_timings: List[WordTiming],
    sentence_cues: List[SubtitleCue],
    chunk_size: int = 4,
    mode: str = "shorts_punchy",
    time_offset: float = 0.0,
    start_index: int = 1
) -> List[SubtitleCue]:
    """
    Builds timed subtitle cues with optional global time offset.
    """
    if mode == "sentence" and sentence_cues:
        return [
            SubtitleCue(
                index=start_index + i,
                start=round(c.start + time_offset, 3),
                end=round(c.end + time_offset, 3),
                text=c.text
            )
            for i, c in enumerate(sentence_cues)
        ]

    if not word_timings:
        return [
            SubtitleCue(
                index=start_index + i,
                start=round(c.start + time_offset, 3),
                end=round(c.end + time_offset, 3),
                text=c.text
            )
            for i, c in enumerate(sentence_cues)
        ]

    cues: List[SubtitleCue] = []
    idx = start_index
    for i in range(0, len(word_timings), chunk_size):
        chunk = word_timings[i:i + chunk_size]
        if not chunk:
            continue
        start_t = round(chunk[0].start + time_offset, 3)
        end_t = round(chunk[-1].end + time_offset, 3)
        if end_t - start_t < 0.6:
            end_t = round(start_t + 0.6, 3)
        text = " ".join([w.word for w in chunk])
        cues.append(SubtitleCue(index=idx, start=start_t, end=end_t, text=text))
        idx += 1

    return cues


def write_srt_file(cues: List[SubtitleCue], output_path: str) -> str:
    """Writes cues to an .srt format file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for idx, cue in enumerate(cues, 1):
            f.write(f"{idx}\n")
            f.write(f"{format_srt_timestamp(cue.start)} --> {format_srt_timestamp(cue.end)}\n")
            f.write(f"{cue.text}\n\n")
    return output_path


def write_ass_file(
    cues: List[SubtitleCue],
    output_path: str,
    aspect_ratio: str = "16:9",
    style_theme: str = "cyber_yellow"
) -> str:
    """Writes stylish ASS subtitles with custom positioning, outlines, and fonts."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    is_vertical = ("9:16" in aspect_ratio)
    res_x = 1080 if is_vertical else 1920
    res_y = 1920 if is_vertical else 1080
    font_size = 54 if is_vertical else 46
    margin_v = 340 if is_vertical else 75

    if style_theme == "cyber_yellow":
        primary_color = "&H002EFCFF"  # Vivid cosmic yellow/gold
        outline_color = "&H00050505"
    elif style_theme == "cosmic_cyan":
        primary_color = "&H00FFFF00"  # Electric cyan
        outline_color = "&H00101010"
    else:
        primary_color = "&H00FFFFFF"  # Crisp white
        outline_color = "&H00080808"

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {res_x}
PlayResY: {res_y}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: CosmicDefault,Arial,{font_size},{primary_color},&H000000FF,{outline_color},&H80000000,-1,0,0,0,100,100,1,0,1,3.5,1.5,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for cue in cues:
        start_str = format_ass_timestamp(cue.start)
        end_str = format_ass_timestamp(cue.end)
        clean_text = cue.text.replace("{", "\\{").replace("}", "\\}")
        events.append(f"Dialogue: 0,{start_str},{end_str},CosmicDefault,,0,0,0,,{clean_text}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events) + "\n")

    return output_path


def mix_voice_and_bgm(
    voice_path: str,
    bgm_path: Optional[str],
    output_path: str,
    bgm_volume_db: float = -22.0
) -> str:
    """
    Mixes voiceover with background music.
    Loops BGM to exact voiceover duration, ducks volume (-22dB = ~12% volume),
    and applies a 3.0s smooth outro fade.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    voice = AudioSegment.from_file(voice_path)
    voice_duration_ms = len(voice)

    if not bgm_path or not os.path.exists(bgm_path) or bgm_volume_db <= -60.0:
        voice.export(output_path, format="mp3", bitrate="192k")
        return output_path

    bgm = AudioSegment.from_file(bgm_path)
    
    # Loop BGM if shorter than voice
    if len(bgm) < voice_duration_ms:
        loops_needed = int(voice_duration_ms / len(bgm)) + 1
        bgm = bgm * loops_needed

    target_len = voice_duration_ms + 400
    bgm_trimmed = bgm[:target_len]
    bgm_ducked = bgm_trimmed + bgm_volume_db
    
    # Smooth 3.0s fade out
    fade_len = min(3000, len(bgm_ducked))
    bgm_ducked = bgm_ducked.fade_out(fade_len)

    combined = bgm_ducked.overlay(voice, position=0)
    combined.export(output_path, format="mp3", bitrate="192k")
    return output_path


def generate_all_scenes_audio(
    scenes: List[Any],
    output_dir: str = "output",
    voice: str = "en-US-ChristopherNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz",
    bgm_path: Optional[str] = None,
    bgm_volume_db: float = -22.0,
    aspect_ratio: str = "16:9",
    style_theme: str = "cyber_yellow",
    mode: str = "shorts_punchy",
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    Master Scene-by-Scene Audio Generator:
    1. Generates an individual .mp3 clip for EACH scene.
    2. Measures EXACT duration (scene_audio_duration) for each scene and attaches it to the scene object.
    3. Builds per-scene and master global synchronized subtitles.
    4. Seamlessly concatenates all scene audio into master_voiceover.mp3.
    5. Mixes master audio with ducked BGM into master_mixed_audio.mp3.
    """
    os.makedirs(output_dir, exist_ok=True)
    total_scenes = len(scenes)
    master_audio = AudioSegment.empty()
    all_global_cues: List[SubtitleCue] = []
    cumulative_offset = 0.0

    for idx, sc in enumerate(scenes):
        pct = (idx + 1) / total_scenes * 0.75
        if progress_callback:
            progress_callback(pct, f"Synthesizing Audio for Scene {sc.scene_id}/{total_scenes}...")

        scene_audio_file = os.path.join(output_dir, f"scene_{sc.scene_id}_audio.mp3")
        exact_dur, words, sents = generate_scene_voiceover_sync(
            text=sc.narration,
            output_path=scene_audio_file,
            voice=voice,
            rate=rate,
            pitch=pitch
        )

        sc.audio_path = scene_audio_file
        sc.audio_duration = exact_dur
        sc.duration_est = exact_dur  # synchronize estimate with reality

        # Generate global subtitle cues for this scene
        scene_cues = build_chunked_subtitles(
            word_timings=words,
            sentence_cues=sents,
            chunk_size=4,
            mode=mode,
            time_offset=cumulative_offset,
            start_index=len(all_global_cues) + 1
        )
        all_global_cues.extend(scene_cues)

        # Append to master audio stream
        scene_segment = AudioSegment.from_file(scene_audio_file)
        master_audio += scene_segment
        cumulative_offset += exact_dur

    if progress_callback:
        progress_callback(0.85, "Merging master audio stream and compiling subtitles...")

    # Export master voiceover
    master_voice_path = os.path.join(output_dir, "master_voiceover.mp3")
    master_audio.export(master_voice_path, format="mp3", bitrate="192k")

    # Export global subtitles
    master_ass_path = os.path.join(output_dir, "subtitles.ass")
    master_srt_path = os.path.join(output_dir, "subtitles.srt")
    write_ass_file(all_global_cues, master_ass_path, aspect_ratio=aspect_ratio, style_theme=style_theme)
    write_srt_file(all_global_cues, master_srt_path)

    if progress_callback:
        progress_callback(0.95, "Layering ambient cosmic music with volume ducking...")

    # Mix with BGM
    master_mixed_path = os.path.join(output_dir, "master_mixed_audio.mp3")
    mix_voice_and_bgm(
        voice_path=master_voice_path,
        bgm_path=bgm_path,
        output_path=master_mixed_path,
        bgm_volume_db=bgm_volume_db
    )

    if progress_callback:
        progress_callback(1.0, "Voiceover synthesis complete for all scenes!")

    return {
        "master_voice_path": master_voice_path,
        "master_mixed_audio_path": master_mixed_path,
        "master_ass_path": master_ass_path,
        "master_srt_path": master_srt_path,
        "total_duration": round(cumulative_offset, 3),
        "global_cues": all_global_cues,
        "scene_durations": {sc.scene_id: sc.audio_duration for sc in scenes},
        "scene_audio_paths": {sc.scene_id: sc.audio_path for sc in scenes}
    }


# Backwards compatibility wrapper
def generate_voiceover_sync(
    text: str,
    output_path: str,
    voice: str = "en-US-ChristopherNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz"
) -> Tuple[List[WordTiming], List[SubtitleCue]]:
    """Legacy helper function returning (words, sentences)."""
    _, words, sents = generate_scene_voiceover_sync(text, output_path, voice, rate, pitch)
    return words, sents
