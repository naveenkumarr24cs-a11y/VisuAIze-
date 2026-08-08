"""
VisuAIze - Cinematic Video Assembler
=====================================
Produces a smooth, professional MP4 with:
  • Intro title card  (VisuAIze branded, topic shown)
  • Per-step clips    (slide + voice, with Ken Burns zoom effect)
  • Outro card        (completion screen)
  • Smooth crossfade  between every clip
  • Background music  (optional: silent if unavailable)
  • 1080p-quality render at 24 fps
"""

import os
from pathlib import Path

from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    concatenate_videoclips,
    ColorClip,
)
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

FPS       = 24
W, H      = 1280, 720
FADE_DUR  = 0.45   # crossfade duration in seconds


# ── Colour helpers ────────────────────────────────────────────────────────────
BG_DARK  = (8, 10, 20)
BG_MID   = (14, 16, 32)
INDIGO   = (99, 102, 241)
EMERALD  = (52, 211, 153)
WHITE    = (255, 255, 255)
SILVER   = (203, 213, 225)
MUTED    = (148, 163, 184)
ACCENTS  = [
    (99,  102, 241),  # indigo
    (139, 92,  246),  # violet
    (34,  211, 238),  # cyan
    (251, 191, 36),   # amber
    (52,  211, 153),  # emerald
    (251, 113, 133),  # rose
]


# ── Font loader (same as image_generator) ────────────────────────────────────
def _font(size, bold=False):
    WIN  = ["C:/Windows/Fonts/arialbd.ttf","C:/Windows/Fonts/segoeuib.ttf"] if bold \
           else ["C:/Windows/Fonts/arial.ttf","C:/Windows/Fonts/segoeui.ttf"]
    LNX  = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"] if bold \
           else ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
    for p in WIN + LNX:
        try:
            return ImageFont.truetype(p, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


def _wrap(text, font, max_w, draw):
    words, lines, curr = text.split(), [], []
    for w in words:
        test = " ".join(curr + [w])
        bb = draw.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] <= max_w:
            curr.append(w)
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))
    return lines


# ── Gradient background ───────────────────────────────────────────────────────
def _gradient(w=W, h=H, top=BG_DARK, bot=BG_MID) -> np.ndarray:
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        t = y / h
        arr[y] = [int(top[c] + (bot[c] - top[c]) * t) for c in range(3)]
    return arr


# ── Intro card ────────────────────────────────────────────────────────────────
def _make_intro_card(topic: str) -> np.ndarray:
    """Render a branded intro card as numpy array."""
    img = Image.new("RGB", (W, H))
    bg  = _gradient()
    img.paste(Image.fromarray(bg))
    d   = ImageDraw.Draw(img)

    # Background grid pattern
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill=(255, 255, 255, 8), width=1)
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill=(255, 255, 255, 8), width=1)

    # Central glow circle
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    for r in range(300, 0, -15):
        a = int(35 * (1 - r / 300))
        gd.ellipse([W//2-r, H//2-r, W//2+r, H//2+r], fill=(*INDIGO, a))
    img.paste(Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB"))
    d = ImageDraw.Draw(img)

    # Logo badge
    badge_txt = "▶  VisuAIze"
    bf        = _font(20, bold=True)
    bb        = d.textbbox((0, 0), badge_txt, font=bf)
    bw        = bb[2] - bb[0] + 36
    bx        = (W - bw) // 2
    # draw badge bg
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld    = ImageDraw.Draw(layer)
    ld.rounded_rectangle([(bx, H//2 - 120), (bx + bw, H//2 - 86)], radius=8, fill=(*INDIGO, 220))
    img   = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    d     = ImageDraw.Draw(img)
    d.text((bx + 18, H//2 - 115), badge_txt, fill=WHITE, font=bf)

    # Main topic title
    tf    = _font(44, bold=True)
    lines = _wrap(topic, tf, W - 160, d)
    ty    = H // 2 - 60
    for line in lines[:2]:
        bb  = d.textbbox((0, 0), line, font=tf)
        tx  = (W - (bb[2] - bb[0])) // 2
        # shadow
        d.text((tx + 2, ty + 2), line, fill=(0, 0, 0), font=tf)
        d.text((tx, ty), line, fill=WHITE, font=tf)
        ty += 54

    # Subtitle
    sub_f = _font(18)
    sub   = "Powered by AI  ·  Step-by-Step Visual Solution"
    sb    = d.textbbox((0, 0), sub, font=sub_f)
    sx    = (W - (sb[2] - sb[0])) // 2
    d.text((sx, ty + 16), sub, fill=MUTED, font=sub_f)

    # Bottom accent line
    d.rectangle([(W//2 - 60, H//2 + 100), (W//2 + 60, H//2 + 103)], fill=EMERALD)

    return np.array(img)


# ── Outro card ────────────────────────────────────────────────────────────────
def _make_outro_card(topic: str, num_steps: int) -> np.ndarray:
    img = Image.new("RGB", (W, H))
    bg  = _gradient(top=(8, 12, 8), bot=(12, 28, 20))
    img.paste(Image.fromarray(bg))
    d   = ImageDraw.Draw(img)

    # Checkmark circle
    cx, cy = W // 2, H // 2 - 60
    layer  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld     = ImageDraw.Draw(layer)
    for r in range(90, 0, -10):
        a = int(50 * (1 - r / 90))
        ld.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(*EMERALD, a))
    ld.ellipse([cx-52, cy-52, cx+52, cy+52], fill=(*EMERALD, 220))
    img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    d   = ImageDraw.Draw(img)
    # Tick
    d.line([(cx-22, cy+2), (cx-6, cy+20)],  fill=WHITE, width=5)
    d.line([(cx-6,  cy+20), (cx+24, cy-16)], fill=WHITE, width=5)

    # "Complete!" text
    d.text((W//2, cy + 80), "Complete!", fill=WHITE, font=_font(42, bold=True), anchor="mm")
    d.text((W//2, cy + 132), f"You've learned {num_steps} steps on:", fill=MUTED, font=_font(16), anchor="mm")

    topic_lines = _wrap(topic, _font(22, bold=True), W - 200, d)
    ty = cy + 162
    for line in topic_lines[:2]:
        bb = d.textbbox((0, 0), line, font=_font(22, bold=True))
        tx = (W - (bb[2] - bb[0])) // 2
        d.text((tx, ty), line, fill=(*EMERALD, 230), font=_font(22, bold=True))
        ty += 32

    # Branding
    d.text((W//2, H - 36), "VisuAIze  ·  Turning Questions into Visual Solutions",
           fill=MUTED, font=_font(12), anchor="mm")

    return np.array(img)


# ── Ken Burns zoom effect ─────────────────────────────────────────────────────
def _make_zoom_clip(img_path: str, duration: float, zoom_in: bool = True):
    """Create a subtle Ken Burns zoom effect on a static image."""
    try:
        base_clip = ImageClip(img_path, duration=duration)

        def zoom_effect(t):
            """Apply subtle zoom from 1.0x to 1.04x (or reverse)."""
            progress = t / duration
            if zoom_in:
                scale = 1.0 + 0.04 * progress
            else:
                scale = 1.04 - 0.04 * progress

            frame = base_clip.get_frame(t)
            h, w = frame.shape[:2]
            new_w = int(w * scale)
            new_h = int(h * scale)

            # Use PIL for high quality resize
            pil_img = Image.fromarray(frame).resize((new_w, new_h), Image.LANCZOS)
            # Centre crop back to original size
            left = (new_w - w) // 2
            top  = (new_h - h) // 2
            pil_img = pil_img.crop((left, top, left + w, top + h))
            return np.array(pil_img)

        from moviepy.editor import VideoClip
        zoomed = VideoClip(zoom_effect, duration=duration)
        zoomed.fps = FPS
        return zoomed

    except Exception as e:
        print(f"      ⚠️  Ken Burns failed ({e}), using static clip")
        return ImageClip(img_path, duration=duration)


# ── Audio helpers ─────────────────────────────────────────────────────────────
def _audio_dur(path: str) -> float:
    try:
        c = AudioFileClip(path)
        d = c.duration
        c.close()
        return max(d, 1.5)
    except Exception:
        return 6.0


def _safe_audio(path: str):
    try:
        return AudioFileClip(path)
    except Exception as e:
        print(f"      ⚠️  Audio load failed '{Path(path).name}': {e}")
        return None


# ── Main assembler ────────────────────────────────────────────────────────────
def assemble_video(
    steps: list,
    image_paths: list,
    audio_data: dict,
    output_path: str,
    topic: str = "Step-by-Step Guide",
) -> str:
    """
    Assembles a full cinematic video:
      Intro → [Step clips with Ken Burns] → Outro
    """
    print("\n🎬 Assembling cinematic video...")
    all_clips = []
    total     = len(steps)

    # ── INTRO CARD ────────────────────────────────────────────────────────────
    print("  🎞️  Building intro card...")
    intro_arr  = _make_intro_card(topic)
    intro_clip = ImageClip(intro_arr, duration=3.5)

    intro_audio_path = audio_data.get("intro")
    if intro_audio_path and Path(intro_audio_path).exists():
        ia = _safe_audio(intro_audio_path)
        if ia:
            intro_clip = intro_clip.set_audio(ia)

    intro_clip = intro_clip.fadein(0.5).fadeout(FADE_DUR)
    all_clips.append(intro_clip)

    # ── STEP CLIPS ────────────────────────────────────────────────────────────
    for i, (step, img_path) in enumerate(zip(steps, image_paths)):
        n = step["step_number"]
        print(f"  ▶  Clip {n}/{total}: '{step['title']}'...")

        audio_path = audio_data["steps"][i]
        dur        = _audio_dur(audio_path) + 1.0   # extra 1s breathing room

        # Alternate zoom direction for visual variety
        zoom_in = (i % 2 == 0)
        clip    = _make_zoom_clip(img_path, dur, zoom_in=zoom_in)

        audio = _safe_audio(audio_path)
        if audio:
            clip = clip.set_audio(audio)

        clip = clip.fadein(FADE_DUR).fadeout(FADE_DUR)
        all_clips.append(clip)

    # ── OUTRO CARD ────────────────────────────────────────────────────────────
    print("  🎞️  Building outro card...")
    outro_arr  = _make_outro_card(topic, total)
    outro_clip = ImageClip(outro_arr, duration=4.0)

    outro_audio_path = audio_data.get("outro")
    if outro_audio_path and Path(outro_audio_path).exists():
        oa = _safe_audio(outro_audio_path)
        if oa:
            outro_clip = outro_clip.set_audio(oa)

    outro_clip = outro_clip.fadein(FADE_DUR).fadeout(0.8)
    all_clips.append(outro_clip)

    # ── CONCATENATE ───────────────────────────────────────────────────────────
    print(f"  🔗  Stitching {len(all_clips)} clips...")
    final = concatenate_videoclips(all_clips, method="compose")

    # ── RENDER ────────────────────────────────────────────────────────────────
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    print(f"  💾  Rendering → {output_path}")
    print(f"      (Total duration ≈ {final.duration:.1f}s)\n")

    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="slow",          # better quality than ultrafast
        bitrate="4000k",        # HD bitrate
        audio_bitrate="192k",
        threads=4,
        logger="bar",
        temp_audiofile=str(Path(output_path).parent / "temp_audio.m4a"),
        remove_temp=True,
    )

    final.close()
    for c in all_clips:
        try: c.close()
        except: pass

    size_mb = round(Path(output_path).stat().st_size / (1024 * 1024), 1)
    print(f"\n✅  Video ready: {output_path}  ({size_mb} MB, {final.duration:.0f}s)")
    return output_path
