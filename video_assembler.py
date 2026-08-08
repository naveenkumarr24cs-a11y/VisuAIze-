"""
VisuAIze - Google Flow Video Assembler
Stitches high-definition Google Flow presentation slides, voiceover narrations,
and smooth fade transitions into a production-ready MP4 tutorial video.
"""

import os
from pathlib import Path
from moviepy.editor import (
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
)

FPS = 24


def _audio_duration(path: str) -> float:
    try:
        clip = AudioFileClip(path)
        dur = clip.duration
        clip.close()
        return max(dur, 1.0)
    except Exception:
        return 5.0


def _safe_audio(path: str):
    """Safely load audio file."""
    try:
        return AudioFileClip(path)
    except Exception as e:
        print(f"      ⚠️  Could not load audio '{Path(path).name}': {e}")
        return None


def assemble_video(
    steps: list,
    image_paths: list,
    audio_data: dict,
    output_path: str,
    topic: str = "Step-by-Step Guide",
) -> str:
    """
    Assembles Google Flow presentation slides and voiceovers into an MP4.
    """
    print("\n🎬 Assembling Google Flow Video Tutorial...")
    clips = []
    total = len(steps)

    # ── Step presentation clips ─────────────────────────────────────────
    for i, (step, img_path) in enumerate(zip(steps, image_paths)):
        n = step["step_number"]
        print(f"  ▶  Slide {n}: {step['title']}...")

        audio_path = audio_data["steps"][i]
        dur = _audio_duration(audio_path) + 0.6  # Natural speaking pause

        # Load Google Flow slide
        clip = ImageClip(img_path, duration=dur)
        audio = _safe_audio(audio_path)
        if audio:
            clip = clip.set_audio(audio)

        # Smooth slide transition
        clip = clip.fadein(0.2).fadeout(0.2)
        clips.append(clip)

    # ── Concatenate into single tutorial video ───────────────────────────
    print("  🔗  Stitching Google Flow sequence...")
    final = concatenate_videoclips(clips, method="compose")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    print(f"  💾  Rendering to {output_path}...")

    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4,
        logger="bar",
        temp_audiofile=str(Path(output_path).parent / "temp_audio.m4a"),
        remove_temp=True,
    )

    final.close()
    for c in clips:
        try: c.close()
        except: pass

    size_mb = round(Path(output_path).stat().st_size / (1024 * 1024), 1)
    print(f"\n✅  Google Flow Video ready: {output_path} ({size_mb} MB)")
    return output_path
