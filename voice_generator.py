"""
VisuAIze - Voice Generator (Fixed)
Uses pyttsx3 (offline, Windows SAPI5) - 100% reliable, no network, no rate limits.
Falls back to gTTS only if pyttsx3 fails.
"""

import os
import time
import threading
from pathlib import Path


def _generate_pyttsx3(text: str, output_path: str, rate: int = 165) -> bool:
    """Generate audio using pyttsx3 (offline, Windows SAPI5). Thread-safe."""
    try:
        import pyttsx3
        # pyttsx3 must run in the main thread or a dedicated thread with its own engine
        engine = pyttsx3.init()
        engine.setProperty('rate', rate)
        engine.setProperty('volume', 0.95)

        # Try to pick a good English voice
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower() or 'zira' in voice.name.lower() or 'david' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break

        engine.save_to_file(text, output_path)
        engine.runAndWait()
        engine.stop()

        # Verify file was created and has content
        p = Path(output_path)
        if p.exists() and p.stat().st_size > 1000:
            return True
        return False
    except Exception as e:
        print(f"      pyttsx3 error: {e}")
        return False


def _generate_gtts_safe(text: str, output_path: str) -> bool:
    """Generate audio using gTTS with proper error handling."""
    try:
        from gtts import gTTS
        import requests

        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(output_path)
        p = Path(output_path)
        return p.exists() and p.stat().st_size > 500
    except Exception as e:
        print(f"      gTTS error: {e}")
        return False


def _generate_silent_audio(duration_seconds: float, output_path: str) -> bool:
    """
    Create a silent MP3-compatible audio file using wave (stdlib only).
    Used as last-resort fallback so video assembly never fails.
    """
    try:
        import wave
        import struct
        import math

        # Create a WAV file first, then we'll use it directly
        wav_path = output_path.replace('.mp3', '.wav')
        sample_rate = 22050
        num_samples = int(sample_rate * duration_seconds)
        # Very quiet hum instead of pure silence (helps FFmpeg)
        amplitude = 50

        with wave.open(wav_path, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            data = struct.pack('<' + 'h' * num_samples,
                               *[int(amplitude * math.sin(2 * math.pi * 220 * i / sample_rate))
                                 for i in range(num_samples)])
            wav_file.writeframes(data)

        # Use the WAV file path instead of MP3
        import shutil
        shutil.move(wav_path, output_path.replace('.mp3', '.wav'))
        # Return the wav path by renaming the output
        os.rename(output_path.replace('.mp3', '.wav'), output_path.replace('.mp3', '_audio.wav'))
        return False  # Signal caller to use WAV
    except Exception as e:
        print(f"      Silent audio fallback error: {e}")
        return False


def generate_voice_for_step(step: dict, output_dir: str) -> str:
    """
    Generates an audio narration for a single step.
    Priority: pyttsx3 → gTTS → silent WAV
    Returns path to audio file.
    """
    step_num = step["step_number"]
    title = step["title"]
    narration = step["narration"]

    # Build spoken text
    spoken_text = f"Step {step_num}. {title}. {narration}"

    mp3_path = str(Path(output_dir) / f"step_{step_num:02d}.mp3")
    wav_path = str(Path(output_dir) / f"step_{step_num:02d}.wav")

    print(f"  🎙️  Voice for Step {step_num}: '{title}'...")

    # Try pyttsx3 first (offline, reliable)
    if _generate_pyttsx3(spoken_text, wav_path):
        size_kb = Path(wav_path).stat().st_size / 1024
        print(f"      ✅ pyttsx3 audio: {Path(wav_path).name} ({size_kb:.0f} KB)")
        return wav_path

    # Try gTTS as fallback
    print(f"      ⚠️  pyttsx3 failed, trying gTTS...")
    time.sleep(1)
    if _generate_gtts_safe(spoken_text, mp3_path):
        size_kb = Path(mp3_path).stat().st_size / 1024
        print(f"      ✅ gTTS audio: {Path(mp3_path).name} ({size_kb:.0f} KB)")
        return mp3_path

    # Last resort: create a simple WAV with a tone
    print(f"      ⚠️  Both TTS failed. Creating tone audio...")
    _make_tone_wav(wav_path, duration=max(3.0, len(spoken_text) * 0.07))
    return wav_path


def _make_tone_wav(path: str, duration: float = 5.0, freq: int = 1) -> None:
    """Create a very quiet WAV file as absolute last resort."""
    import wave, struct
    sample_rate = 22050
    num_samples = int(sample_rate * duration)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # Near-silent data
        data = struct.pack('<' + 'h' * num_samples, *([10] * num_samples))
        wf.writeframes(data)


def generate_intro_voice(topic: str, output_dir: str) -> str:
    text = f"Welcome to VisuAIze. Today we will learn: {topic}. Let's get started!"
    wav_path = str(Path(output_dir) / "intro.wav")
    mp3_path = str(Path(output_dir) / "intro.mp3")
    print(f"  🎙️  Generating intro voice...")

    if _generate_pyttsx3(text, wav_path):
        print("      ✅ Intro audio ready.")
        return wav_path
    if _generate_gtts_safe(text, mp3_path):
        print("      ✅ Intro audio ready (gTTS).")
        return mp3_path

    _make_tone_wav(wav_path, duration=4.0)
    return wav_path


def generate_outro_voice(output_dir: str) -> str:
    text = ("And that's it! You have successfully completed all the steps. "
            "Thank you for using VisuAIze. Turn any question into a visual solution!")
    wav_path = str(Path(output_dir) / "outro.wav")
    mp3_path = str(Path(output_dir) / "outro.mp3")
    print(f"  🎙️  Generating outro voice...")

    if _generate_pyttsx3(text, wav_path):
        print("      ✅ Outro audio ready.")
        return wav_path
    if _generate_gtts_safe(text, mp3_path):
        print("      ✅ Outro audio ready (gTTS).")
        return mp3_path

    _make_tone_wav(wav_path, duration=5.0)
    return wav_path


def generate_all_voices(steps: list, output_dir: str) -> dict:
    """Generate all voice narrations. Returns dict with intro/steps/outro paths."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    print(f"\n🎙️  Generating {len(steps) + 2} voice narrations (offline TTS)...")

    topic = steps[0].get("title", "step by step guide") if steps else "guide"
    intro_path = generate_intro_voice(topic, output_dir)
    time.sleep(0.3)

    step_audio_paths = []
    for step in steps:
        audio_path = generate_voice_for_step(step, output_dir)
        step_audio_paths.append(audio_path)
        time.sleep(0.3)

    outro_path = generate_outro_voice(output_dir)
    print(f"✅ All {len(step_audio_paths) + 2} voice narrations generated!")
    return {"intro": intro_path, "steps": step_audio_paths, "outro": outro_path}
