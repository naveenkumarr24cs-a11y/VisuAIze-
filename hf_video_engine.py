"""
hf_video_engine.py  (v4 - Multi-Model Video Generation Pipeline)
===================================================================
Integrates all 4 top Hugging Face Video Models:
  1. CogVideoX-5B (THUDM/CogVideoX-5B-Space)
  2. Wan 2.1 / 2.2 (Wan-AI/Wan2.1-T2V-14B)
  3. LTX-Video (Lightricks/LTX-Video)
  4. HunyuanVideo (tencent/HunyuanVideo)
"""

import os
import shutil
import sys
import time
from pathlib import Path


def _get_token():
    return os.getenv("HF_VIDEO_TOKEN") or os.getenv("HUGGINGFACE_API_KEY", "")


def generate_hf_video_clip(prompt: str, output_path: str) -> str | None:
    """
    Tries generating a real .mp4 video clip using the 4 top models:
    CogVideoX-5B -> Wan 2.1 -> LTX-Video -> HunyuanVideo
    """
    token = _get_token()
    if not token:
        print("  [HF-Video] No HF token found.")
        return None

    headers = {"Authorization": f"Bearer {token}"}

    # Model waterfall configuration
    models = [
        ("CogVideoX-5B", "THUDM/CogVideoX-5B-Space", "/generate", (prompt, None, None, 0.8, -1, False, False)),
        ("Wan 2.1", "Wan-AI/Wan2.1-T2V-14B", "/generate", (prompt,)),
        ("LTX-Video", "Lightricks/LTX-Video", "/predict", (prompt,)),
        ("HunyuanVideo", "tencent/HunyuanVideo", "/generate", (prompt,)),
    ]

    for name, space_id, endpoint, args in models:
        try:
            from gradio_client import Client

            print(f"  [HF-Video] Trying {name} ({space_id})...")
            client = Client(space_id, headers=headers, verbose=False)
            result = client.predict(*args, api_name=endpoint)

            # Extract video path from result
            video_file = None
            if isinstance(result, tuple):
                for item in result:
                    if isinstance(item, str) and item.endswith(".mp4") and os.path.exists(item):
                        video_file = item
                        break
                    elif isinstance(item, dict) and item.get("video") and os.path.exists(item["video"]):
                        video_file = item["video"]
                        break
            elif isinstance(result, str) and result.endswith(".mp4") and os.path.exists(result):
                video_file = result

            if video_file:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(video_file, output_path)
                print(f"  [{name}] SUCCESS! Video clip generated: {output_path}")
                return output_path
        except Exception as e:
            print(f"  [{name}] Skipped / Busy ({str(e)[:80]})")

    return None
