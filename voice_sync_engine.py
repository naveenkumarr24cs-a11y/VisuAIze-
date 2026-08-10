"""
voice_sync_engine.py
====================
VisuAIze - Frame-Accurate Voice & Animation Sync Engine
Inspired by Manim-Voiceover (ManimCommunity/manim-voiceover).

Measures actual audio duration per step and calculates
exact frame counts so video clips lock precisely to narration speech.
"""

import os
import wave
import contextlib


FPS = 24  # Video frames per second


def get_audio_duration_sec(audio_path: str) -> float:
    """
    Measures the exact duration of a WAV audio file in seconds.
    Manim-Voiceover style: uses Python wave module for zero-dependency duration reading.
    """
    if not audio_path or not os.path.exists(audio_path):
        return 6.0  # Default fallback duration

    try:
        with contextlib.closing(wave.open(audio_path, "r")) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0 and frames > 0:
                duration = frames / float(rate)
                # Clamp to reasonable range
                return max(3.0, min(30.0, duration))
    except Exception:
        pass

    # Fallback: try mutagen if available
    try:
        from mutagen import File as MutagenFile
        audio = MutagenFile(audio_path)
        if audio and hasattr(audio, "info") and audio.info.length > 0:
            return max(3.0, min(30.0, audio.info.length))
    except Exception:
        pass

    return 6.0


def calc_frame_count(audio_path: str, padding_sec: float = 0.4) -> int:
    """
    Manim-Voiceover style: calculate exact frame count for a step clip.
    Adds a small padding so the last word isn't cut off.
    """
    duration = get_audio_duration_sec(audio_path) + padding_sec
    return max(72, int(duration * FPS))  # Minimum 3 seconds (72 frames)


def get_step_durations(audio_paths: list) -> list:
    """
    Returns a list of (duration_sec, frame_count) tuples for all steps.
    Used by video_assembler.py to lock each step clip to its narration.
    """
    result = []
    for path in audio_paths:
        dur = get_audio_duration_sec(path)
        frames = calc_frame_count(path)
        result.append({"duration_sec": dur, "frame_count": frames, "audio_path": path})
    return result
