"""
VisuAIze - Main Pipeline
The central orchestrator that ties all modules together:
  1. Takes user input (question + optional image)
  2. Generates structured steps (Gemini AI)
  3. Generates images per step (Pollinations AI - FREE)
  4. Generates voice narrations (gTTS - FREE)
  5. Assembles final MP4 video (MoviePy + FFmpeg - FREE)

Usage:
  python main.py --question "How do I change a flat tyre?" --output output/
  python main.py --question "Explain photosynthesis" --image my_photo.jpg
  python main.py  (interactive mode)
"""

import argparse
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def print_providers():
    """Print a table of all available AI providers."""
    from ai_provider import list_providers
    providers = list_providers()

    print("\n" + "═" * 65)
    print("🧠  VisuAIze — Available AI Providers")
    print("═" * 65)
    print(f"  {'Provider':<15} {'Free?':<8} {'Local?':<8} {'Vision?':<10} {'Env Key'}")
    print("  " + "-" * 60)
    for key, info in providers.items():
        free = "✅ Yes" if info["free_tier"] else "❌ No"
        local = "✅ Yes" if info["local"] else "❌ No"
        vision = "✅ Yes" if info["vision"] else "❌ No"
        env_key = info["env_key"] or "(none needed)"
        print(f"  {key:<15} {free:<8} {local:<8} {vision:<10} {env_key}")

    print("\n📋  Models per provider:")
    for key, info in providers.items():
        models = ", ".join(info["models"][:3])
        print(f"  {key:<15} → {models}")

    print("\n💡  Switch provider: set AI_PROVIDER=<name> in your .env file")
    print("    Or use: python main.py --provider groq --question \"...\"")
    print("═" * 65 + "\n")

# Import our modules
from ai_provider import generate_steps
from image_generator import generate_all_images
from voice_generator import generate_all_voices
from video_assembler import assemble_video


def print_banner():
    """Prints the VisuAIze banner."""
    import sys
    import io
    # Ensure UTF-8 output on Windows
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    banner = """
+==============================================================+
|                                                              |
|   __   ___            _    ___ ___                          |
|   \\ \\ / (_)___ _   _/_\\  |_ _|_  )___                      |
|    \\ V /| (_-<| | | / _ \\ | | / // -_)                     |
|     \\_/ |_/__/ \\__/_/ \\_\\|___/___\\___|                     |
|                                                              |
|         Turning Questions into Visual Solutions              |
+==============================================================+
    """
    print(banner)



def check_requirements():
    """Checks that all required packages and tools are available."""
    print("🔍 Checking requirements...")
    issues = []

    # Check Python packages
    required_packages = {
        "google.generativeai": "google-generativeai",
        "gtts": "gtts",
        "PIL": "Pillow",
        "moviepy": "moviepy",
        "requests": "requests",
        "numpy": "numpy",
        "dotenv": "python-dotenv",
    }

    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - NOT FOUND")
            issues.append(f"pip install {package}")

    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("  ❌ GEMINI_API_KEY - NOT SET")
        issues.append("Set GEMINI_API_KEY in your .env file")
    else:
        masked = api_key[:8] + "..." + api_key[-4:]
        print(f"  ✅ GEMINI_API_KEY ({masked})")

    if issues:
        print("\n⚠️  Please fix these issues before running:")
        for issue in issues:
            print(f"   → {issue}")
        return False

    print("  ✅ All requirements met!\n")
    return True


def run_pipeline(
    question: str,
    image_path: str = None,
    output_dir: str = "output",
    keep_temp: bool = False,
) -> str:
    """
    Runs the full VisuAIze pipeline.

    Args:
        question: The user's question or problem.
        image_path: Optional path to an image.
        output_dir: Directory to save the final video.
        keep_temp: If True, keeps temporary files after completion.

    Returns:
        Path to the generated video file.
    """
    start_time = time.time()

    # Create a unique session folder for temp files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in question[:30] if c.isalnum() or c in " _-").strip().replace(" ", "_")
    session_name = f"{timestamp}_{safe_name}"

    temp_dir = Path("temp") / session_name
    temp_images_dir = temp_dir / "images"
    temp_audio_dir = temp_dir / "audio"

    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_images_dir.mkdir(parents=True, exist_ok=True)
    temp_audio_dir.mkdir(parents=True, exist_ok=True)

    # Final output path
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_video_path = str(Path(output_dir) / f"{session_name}.mp4")

    print(f"\n{'='*65}")
    print(f"📌 QUESTION: {question}")
    if image_path:
        print(f"🖼️  IMAGE: {image_path}")
    print(f"{'='*65}\n")

    try:
        # ─────────────────────────────────────────────────
        # STEP 1: Generate structured steps using Gemini
        # ─────────────────────────────────────────────────
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("PHASE 1/4: 🧠  Generating Steps with Gemini AI...")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        steps = generate_steps(question, image_path)

        print(f"\n📋 Generated {len(steps)} steps:")
        for step in steps:
            print(f"   {step['step_number']}. {step['title']}")

        # ─────────────────────────────────────────────────
        # STEP 2: Generate images for each step
        # ─────────────────────────────────────────────────
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("PHASE 2/4: 🖼️   Generating Images (Pollinations AI - FREE)...")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        image_paths = generate_all_images(steps, str(temp_images_dir))

        # ─────────────────────────────────────────────────
        # STEP 3: Generate voice narrations
        # ─────────────────────────────────────────────────
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("PHASE 3/4: 🎙️   Generating Voice Narrations (gTTS - FREE)...")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        audio_data = generate_all_voices(steps, str(temp_audio_dir))

        # ─────────────────────────────────────────────────
        # STEP 4: Assemble the final video
        # ─────────────────────────────────────────────────
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("PHASE 4/4: 🎬   Assembling Final Video...")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        final_video_path = assemble_video(
            steps=steps,
            image_paths=image_paths,
            audio_data=audio_data,
            output_path=output_video_path,
            topic=question,
        )

        # ─────────────────────────────────────────────────
        # Done!
        # ─────────────────────────────────────────────────
        elapsed = time.time() - start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)

        print("\n" + "═" * 65)
        print("🎉  VisuAIze VIDEO GENERATION COMPLETE!")
        print("═" * 65)
        print(f"   📹 Video: {final_video_path}")
        print(f"   ⏱️  Time: {minutes}m {seconds}s")
        print(f"   📊 Steps: {len(steps)}")

        file_size_mb = Path(final_video_path).stat().st_size / (1024 * 1024)
        print(f"   💾 Size:  {file_size_mb:.1f} MB")
        print("═" * 65)

        # Cleanup temp files
        if not keep_temp:
            print(f"\n🧹 Cleaning up temporary files...")
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"   ✅ Temp files removed.")

        return final_video_path

    except KeyboardInterrupt:
        print("\n\n⛔ Pipeline interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def interactive_mode():
    """Interactive command-line interface for VisuAIze."""
    print_banner()

    if not check_requirements():
        sys.exit(1)

    print("═" * 65)
    print("🚀  Welcome to VisuAIze! Let's create your instructional video.")
    print("═" * 65)

    # Get question
    print("\n💬  What do you want to learn or solve?")
    print("    (Examples: 'How to change a flat tyre?', 'Explain photosynthesis',")
    print("               'How to fix a leaking tap?', 'Python list comprehension')")
    print()
    question = input("  ➤  Your question: ").strip()

    if not question:
        print("❌ No question entered. Exiting.")
        sys.exit(1)

    # Optional image
    print("\n📎  Do you have an image to include? (press Enter to skip)")
    image_path = input("  ➤  Image path (optional): ").strip()
    if image_path and not Path(image_path).exists():
        print(f"  ⚠️  Image not found at '{image_path}'. Proceeding without image.")
        image_path = None

    # Output directory
    output_dir = "output"
    print(f"\n📁  Videos will be saved to: ./{output_dir}/")

    # Run the pipeline!
    video_path = run_pipeline(
        question=question,
        image_path=image_path if image_path else None,
        output_dir=output_dir,
    )

    print(f"\n▶  To play your video, open: {video_path}")
    print("\nThank you for using VisuAIze! 🚀\n")


def main():
    """Main entry point. Handles CLI args or falls back to interactive mode."""
    parser = argparse.ArgumentParser(
        description="VisuAIze - Turn any question into a step-by-step instructional video",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --question "How to change a flat tyre?"
  python main.py --question "Explain photosynthesis" --output my_videos/
  python main.py --question "Fix a leaking tap" --image tap_photo.jpg --keep-temp
  python main.py  (interactive mode)
        """,
    )
    parser.add_argument(
        "--question", "-q",
        type=str,
        help="The question or problem to generate a video for",
    )
    parser.add_argument(
        "--image", "-i",
        type=str,
        default=None,
        help="Optional path to an image to include as context",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output",
        help="Output directory for the generated video (default: output/)",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        default=False,
        help="Keep temporary image and audio files after completion",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Just check requirements and exit",
    )
    parser.add_argument(
        "--providers",
        action="store_true",
        help="List all available AI providers and exit",
    )
    parser.add_argument(
        "--provider", "-p",
        type=str,
        default=None,
        choices=["gemini", "groq", "huggingface", "hf", "ollama"],
        help="Override the AI provider for this run (without editing .env)",
    )

    args = parser.parse_args()

    if args.check:
        print_banner()
        check_requirements()
        sys.exit(0)

    if args.providers:
        print_banner()
        print_providers()
        sys.exit(0)

    # Override AI_PROVIDER from CLI flag if given
    if args.provider:
        os.environ["AI_PROVIDER"] = args.provider
        print(f"  🔀 Provider overridden to: {args.provider}")

    if not args.question:
        # No arguments given — run interactive mode
        interactive_mode()
    else:
        print_banner()
        if not check_requirements():
            sys.exit(1)
        run_pipeline(
            question=args.question,
            image_path=args.image,
            output_dir=args.output,
            keep_temp=args.keep_temp,
        )


if __name__ == "__main__":
    main()
