import os
import sys
import asyncio
import wave
import struct
import shutil
import random
from concurrent.futures import ThreadPoolExecutor


if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
if hasattr(sys.stderr, "reconfigure"):
    try: sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass


try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


SPEAKER_CONFIG = {
    'teacher': {
        'edge_voice': 'en-US-AriaNeural',
        'edge_rate': '+5%',
        'gtts_lang': 'en',
        'gtts_tld': 'com', # accent
        'pyttsx3_voice': 0 # Fallback index
    },
    'student': {
        'edge_voice': 'en-US-GuyNeural',
        'edge_rate': '+10%',
        'gtts_lang': 'en',
        'gtts_tld': 'co.uk',
        'pyttsx3_voice': 1
    }
}

def install_edge_tts():
    """Helper to suggest installing edge-tts if missing."""
    if not EDGE_TTS_AVAILABLE:
        print("⚠️ edge-tts is not installed. For high-quality voices, run: pip install edge-tts")
    if not GTTS_AVAILABLE:
        print("⚠️ gTTS is not installed. For fallback voices, run: pip install gTTS")
    if not PYDUB_AVAILABLE:
        print("⚠️ pydub is not installed. For audio concatenation, run: pip install pydub")
    if not PYTTSX3_AVAILABLE:
        print("⚠️ pyttsx3 is not installed. For offline fallback, run: pip install pyttsx3")

def _make_silence_wav(path: str, duration: float = 1.0) -> str:
    """Creates a silent WAV file of specified duration."""
    try:
        sample_rate = 44100
        num_samples = int(duration * sample_rate)
        
        with wave.open(path, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            
            # Write silence (zeros)
            for _ in range(num_samples):
                wav_file.writeframes(struct.pack('h', 0))
        print(f"🤫 Created {duration}s silence at {path}")
        return path
    except Exception as e:
        print(f"❌ Failed to create silence WAV: {e}")
        return path

async def _async_generate_edge_tts(text: str, voice: str, output_path: str, rate: str) -> bool:
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"❌ EdgeTTS async error: {e}")
        return False

def generate_edge_tts(text: str, voice: str, output_path: str, rate: str = '+0%') -> bool:
    """Synchronous wrapper for edge_tts generation."""
    if not EDGE_TTS_AVAILABLE:
        return False
    
    try:
        success = asyncio.run(_async_generate_edge_tts(text, voice, output_path, rate))
        if success:
            print(f"🌟 EdgeTTS successfully generated: {output_path}")
        return success
    except Exception as e:
        print(f"❌ EdgeTTS wrapper error: {e}")
        return False


def generate_gtts(text: str, output_path: str, lang: str, tld: str) -> bool:
    """Generates audio using gTTS as a fallback."""
    if not GTTS_AVAILABLE:
        return False
    try:
        tts = gTTS(text=text, lang=lang, tld=tld, slow=False)
        tts.save(output_path)
        print(f"🎙️ gTTS successfully generated: {output_path}")
        return True
    except Exception as e:
        print(f"❌ gTTS error: {e}")
        return False

def generate_pyttsx3(text: str, output_path: str, voice_idx: int) -> bool:
    """Generates audio using pyttsx3 as a second fallback."""
    if not PYTTSX3_AVAILABLE:
        return False
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        if voice_idx < len(voices):
            engine.setProperty('voice', voices[voice_idx].id)
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        print(f"🤖 pyttsx3 successfully generated: {output_path}")
        return True
    except Exception as e:
        print(f"❌ pyttsx3 error: {e}")
        return False

def generate_speaker_voice(text: str, role: str, output_path: str) -> str:
    """
    Generates voice for a specific role (teacher/student) with multiple fallbacks.
    """
    if role not in SPEAKER_CONFIG:
        role = 'teacher' # default
        
    config = SPEAKER_CONFIG[role]
    print(f"🗣️ Generating voice for {role} (len: {len(text)}) -> {output_path}")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # 1. Try EdgeTTS
    if EDGE_TTS_AVAILABLE:
        success = generate_edge_tts(
            text, 
            config['edge_voice'], 
            output_path, 
            config['edge_rate']
        )
        if success and os.path.exists(output_path):
            return output_path
            
    print(f"⚠️ EdgeTTS failed for {role}, falling back to gTTS...")
    
    # 2. Try gTTS
    if GTTS_AVAILABLE:
        success = generate_gtts(
            text, 
            output_path, 
            config['gtts_lang'], 
            config['gtts_tld']
        )
        if success and os.path.exists(output_path):
            return output_path
            
    print(f"⚠️ gTTS failed for {role}, falling back to pyttsx3...")
    
    # 3. Try pyttsx3
    if PYTTSX3_AVAILABLE:
        success = generate_pyttsx3(
            text, 
            output_path, 
            config['pyttsx3_voice']
        )
        if success and os.path.exists(output_path):
            return output_path
            
    print(f"⚠️ pyttsx3 failed for {role}, falling back to silence...")
    
    # 4. Fallback to Silent WAV
    temp_wav = output_path + ".wav"
    _make_silence_wav(temp_wav, duration=2.0)
    if os.path.exists(temp_wav):
        if output_path.endswith('.mp3'):
            try:
                shutil.move(temp_wav, output_path)
            except:
                pass
        return output_path
        
    return output_path

def combine_audio_files(file_paths: list, output_path: str) -> str:
    """Concatenates multiple audio files into one using bundled ffmpeg for perfect audio alignment."""
    valid_files = [f for f in file_paths if os.path.exists(f)]
    
    if not valid_files:
        _make_silence_wav(output_path, duration=1.0)
        return output_path
        
    if len(valid_files) == 1:
        shutil.copy(valid_files[0], output_path)
        return output_path

    # Try bundled ffmpeg from imageio_ffmpeg
    try:
        import imageio_ffmpeg
        import subprocess
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        
        # Create a concat list file with forward slashes for Windows ffmpeg compatibility
        concat_txt = os.path.join(os.path.dirname(output_path), f"_concat_{os.getpid()}_{random.randint(100,999)}.txt")
        with open(concat_txt, "w", encoding="utf-8") as f:
            for vp in valid_files:
                clean_p = os.path.abspath(vp).replace("\\", "/")
                f.write(f"file '{clean_p}'\n")

                
        cmd = [
            ffmpeg_exe, "-y", "-f", "concat", "-safe", "0",
            "-i", concat_txt, "-c", "copy", output_path
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=10)
        try: os.remove(concat_txt)
        except Exception: pass
        
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 400:
            print(f"✅ Successfully combined {len(valid_files)} audio files via ffmpeg: {output_path}")
            return output_path
    except Exception as e:
        print(f"⚠️ ffmpeg concat notice: {e}")

    # Fallback to binary concatenation
    try:
        with open(output_path, 'wb') as outfile:
            for fp in valid_files:
                with open(fp, 'rb') as infile:
                    outfile.write(infile.read())
        return output_path
    except Exception as e:
        _make_silence_wav(output_path, duration=1.0)
        return output_path


def generate_dual_voice_for_step(step: dict, output_dir: str, step_index: int) -> dict:
    """Generates teacher and student voices for a specific step."""
    os.makedirs(output_dir, exist_ok=True)
    
    teacher_text = step.get('teacher_line', '')
    student_text = step.get('student_line', '')
    
    teacher_path = os.path.join(output_dir, f"teacher_{step_index:02d}.mp3")
    student_path = os.path.join(output_dir, f"student_{step_index:02d}.mp3")
    combined_path = os.path.join(output_dir, f"step_{step_index:02d}_combined.mp3")
    
    generated_files = []
    
    if teacher_text:
        res = generate_speaker_voice(teacher_text, 'teacher', teacher_path)
        if os.path.exists(res):
            generated_files.append(res)
            
    if student_text:
        res = generate_speaker_voice(student_text, 'student', student_path)
        if os.path.exists(res):
            generated_files.append(res)
            
    if generated_files:
        combine_audio_files(generated_files, combined_path)
    else:
        _make_silence_wav(combined_path, duration=1.0)
        
    return {
        'teacher': teacher_path if os.path.exists(teacher_path) else None,
        'student': student_path if os.path.exists(student_path) else None,
        'combined': combined_path if os.path.exists(combined_path) else None
    }

def generate_all_dual_voices(steps: list, output_dir: str, topic: str = "Topic") -> dict:
    """Generates all voices for a series of steps in parallel."""
    print(f"🚀 Starting dual voice generation for '{topic}' ({len(steps)} steps)")
    os.makedirs(output_dir, exist_ok=True)
    
    install_edge_tts()
    
    intro_text = f"Welcome to the module on {topic}. Let's begin."
    intro_path = os.path.join(output_dir, "intro.mp3")
    generate_speaker_voice(intro_text, 'teacher', intro_path)
    
    outro_text = f"That concludes the module on {topic}. Thanks for listening!"
    outro_path = os.path.join(output_dir, "outro.mp3")
    generate_speaker_voice(outro_text, 'teacher', outro_path)
    
    step_results = [None] * len(steps)
    
    def process_step(index, step):
        print(f"⚙️ Processing step {index+1}/{len(steps)}...")
        res = generate_dual_voice_for_step(step, output_dir, index)
        step_results[index] = res
        print(f"✅ Finished step {index+1}/{len(steps)}")
        
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_step, i, step) for i, step in enumerate(steps)]
        for f in futures:
            try:
                f.result()
            except Exception as e:
                print(f"  ⚠️ Step voice error: {e}")
            
    return {
        'intro': intro_path if os.path.exists(intro_path) else None,
        'steps': step_results,
        'outro': outro_path if os.path.exists(outro_path) else None
    }


if __name__ == "__main__":
    install_edge_tts()
    test_dir = tempfile.mkdtemp()
    
    sample_steps = [
        {
            'teacher_line': "Today we'll learn about photosynthesis.",
            'student_line': "What exactly is photosynthesis?"
        },
        {
            'teacher_line': "It's the process by which plants make their own food.",
            'student_line': "Wow, that's really interesting!"
        }
    ]
    
    try:
        results = generate_all_dual_voices(sample_steps, test_dir, "Photosynthesis")
        print("🎉 Generation complete!")
        print(results)
    finally:
        try:
            shutil.rmtree(test_dir)
        except:
            pass
