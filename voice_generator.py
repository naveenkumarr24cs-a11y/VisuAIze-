"""
VisuAIze - Voice Generator (Upgraded with Dual-Voice Support)
=============================================================
Supports:
  - SINGLE VOICE: pyttsx3 → gTTS → silent fallback
  - DUAL VOICE: Teacher (AriaNeural) + Student (GuyNeural) via edge-tts
                Falls back to gTTS per speaker
Dual-voice mode is activated by DUAL_VOICE=true env variable or the dual_voice param.
"""

import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _clean_tts_text(text: str) -> str:
    """Strip emojis and unprintable unicode symbols for TTS engines."""
    if not text:
        return ""
    clean = re.sub(r'[^\x00-\x7F]+', ' ', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean or text


def _generate_pyttsx3(text: str, output_path: str, rate: int = 170) -> bool:
    """Generate audio using pyttsx3 (offline, Windows SAPI5). Thread-safe."""
    try:
        text = _clean_tts_text(text)
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', rate)
        engine.setProperty('volume', 0.95)

        voices = engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower() or 'zira' in voice.name.lower() or 'david' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break

        engine.save_to_file(text, output_path)
        engine.runAndWait()
        engine.stop()

        p = Path(output_path)
        return p.exists() and p.stat().st_size > 800
    except Exception as e:
        print(f"      pyttsx3 error: {e}")
        return False


def _generate_gtts_safe(text: str, output_path: str) -> bool:
    """Generate audio using gTTS."""
    try:
        text = _clean_tts_text(text)
        from gtts import gTTS
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(output_path)
        p = Path(output_path)
        return p.exists() and p.stat().st_size > 400
    except Exception as e:
        print(f"      gTTS error: {e}")
        return False


def _make_tone_wav(path: str, duration: float = 4.0) -> None:
    """Create a quiet WAV file as fallback."""
    import wave, struct
    sample_rate = 22050
    num_samples = int(sample_rate * duration)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = struct.pack('<' + 'h' * num_samples, *([10] * num_samples))
        wf.writeframes(data)


def generate_voice_for_step(step: dict, output_dir: str) -> str:
    step_num = step["step_number"]
    title = step["title"]
    narration = step["narration"]

    spoken_text = f"Step {step_num}. {title}. {narration}"
    wav_path = str(Path(output_dir) / f"step_{step_num:02d}.wav")
    mp3_path = str(Path(output_dir) / f"step_{step_num:02d}.mp3")

    # Try pyttsx3 first (offline, fast)
    if _generate_pyttsx3(spoken_text, wav_path):
        return wav_path

    # Try gTTS
    if _generate_gtts_safe(spoken_text, mp3_path):
        return mp3_path

    _make_tone_wav(wav_path, duration=max(3.0, len(spoken_text) * 0.06))
    return wav_path


def generate_intro_voice(topic: str, output_dir: str) -> str:
    text = f"Welcome to VisuAIze. Today we will learn: {topic}. Let's get started!"
    wav_path = str(Path(output_dir) / "intro.wav")
    mp3_path = str(Path(output_dir) / "intro.mp3")

    if _generate_pyttsx3(text, wav_path):
        return wav_path
    if _generate_gtts_safe(text, mp3_path):
        return mp3_path

    _make_tone_wav(wav_path, duration=3.5)
    return wav_path


def generate_outro_voice(output_dir: str) -> str:
    text = ("And that's it! You have successfully completed all the steps. "
            "Thank you for using VisuAIze. Turn any question into a visual solution!")
    wav_path = str(Path(output_dir) / "outro.wav")
    mp3_path = str(Path(output_dir) / "outro.mp3")

    if _generate_pyttsx3(text, wav_path):
        return wav_path
    if _generate_gtts_safe(text, mp3_path):
        return mp3_path

    _make_tone_wav(wav_path, duration=4.0)
    return wav_path


def generate_all_voices(steps: list, output_dir: str, topic: str = "", dual_voice: bool = False) -> dict:
    """
    Generate narrations for all steps.
    If dual_voice=True, uses dual_voice_engine for Teacher+Student voices.
    Falls back to single-voice if dual_voice_engine fails.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Check if any step has dual-voice fields
    has_dual_fields = any(
        step.get("teacher_line") and step.get("student_line")
        for step in steps
    )

    # Dual voice mode
    use_dual = dual_voice or os.getenv("DUAL_VOICE", "").lower() in ("true", "1", "yes")
    if use_dual and has_dual_fields:
        print(f"\n🎙️  Generating DUAL-VOICE narrations ({len(steps) + 2} clips)...")
        try:
            import dual_voice_engine
            t = topic or (steps[0].get("title", "Tutorial") if steps else "Tutorial")
            result = dual_voice_engine.generate_all_dual_voices(steps, output_dir, t)
            print(f"✅ Dual-voice narration complete!")
            return result
        except Exception as e:
            print(f"⚠️  Dual-voice failed ({e}), falling back to single-voice...")


    # Single voice mode (default / fallback)
    print(f"\n🎙️  Generating {len(steps) + 2} voice narrations (Single-Voice Engine)...")
    topic = steps[0].get("title", "step by step guide") if steps else "guide"
    intro_path = generate_intro_voice(topic, output_dir)

    step_audio_paths = []
    for step in steps:
        audio_path = generate_voice_for_step(step, output_dir)
        step_audio_paths.append(audio_path)

    outro_path = generate_outro_voice(output_dir)
    print(f"✅ All {len(step_audio_paths) + 2} voice narrations generated!")
    return {"intro": intro_path, "steps": step_audio_paths, "outro": outro_path}
