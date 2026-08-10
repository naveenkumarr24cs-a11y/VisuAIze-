"""
VisuAIze - Animated Cinematic Step-by-Step Video Engine
=======================================================
Transforms static slides into dynamic animated tutorial videos:

  • Ken Burns pan/zoom on every slide (5 randomised directions, eased motion)
  • Text panel cinematic reveal (dark fade lifts to expose content smoothly)
  • Animated intro card: logo zooms in + typewriter title effect
  • Animated outro card: progress arc draws + text fades in sequentially
  • Smooth fade-to-black transitions (baked into frames — no MoviePy fx bugs)
  • Frame-accurate audio-visual sync (duration locked to actual narration length)
  • Multi-threaded ultrafast H.264 encoding
"""

import os
import random
import sys
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

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    AudioFileClip,
    ImageSequenceClip,
    concatenate_videoclips,
)

# ── Constants ────────────────────────────────────────────────────────────────
FPS_ANIM  = 24          # animation frame rate - ultra smooth
FPS_OUT   = 24          # output video frame rate
W, H      = 1280, 720
VISUAL_X2 = int(W * 0.585)   # 748px — visual / text panel split

# Colour palette
BG_DARK  = (8,   8,   11)
BG_MID   = (15,  15,  20)
INDIGO   = (99,  102, 241)
EMERALD  = (52,  211, 153)
WHITE    = (255, 255, 255)
MUTED    = (148, 163, 184)
CYAN     = (34,  211, 238)
GOLD     = (251, 191,  36)

KB_DIRECTIONS = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_diagonal"]

FADE_DUR = 0.35   # seconds of fade-in / fade-out
KB_SCALE  = 0.12  # Ken Burns max zoom scale (12% zoom for subtle cinematic motion)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    WIN = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"] if bold \
          else ["C:/Windows/Fonts/segoeui.ttf",  "C:/Windows/Fonts/arial.ttf"]
    LNX = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if bold \
          else ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in WIN + LNX:
        try:
            return ImageFont.truetype(p, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


def _wrap(text: str, font, max_w: int, draw) -> list:
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


def _ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def _ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _apply_fade(frames: list, fade_in_sec: float, fade_out_sec: float) -> list:
    """
    Bake fade-from-black and fade-to-black directly into numpy frame arrays.
    This avoids MoviePy's fx system entirely (bypasses the 'NoneType.get_frame' bug).
    """
    result = []
    n = len(frames)
    fi_frames = int(fade_in_sec  * FPS_ANIM)
    fo_frames = int(fade_out_sec * FPS_ANIM)

    for i, frame in enumerate(frames):
        alpha = 1.0
        if fi_frames > 0 and i < fi_frames:
            alpha = _ease_out(i / fi_frames)
        elif fo_frames > 0 and i >= (n - fo_frames):
            alpha = _ease_out((n - 1 - i) / fo_frames)

        if alpha < 0.999:
            frame = (np.array(frame, dtype=np.float32) * alpha).clip(0, 255).astype(np.uint8)
        result.append(frame)

    return result


# ── Ken Burns Effect ─────────────────────────────────────────────────────────

def _ken_burns_frame(visual: np.ndarray, t: float, duration: float, direction: str) -> np.ndarray:
    """
    Return the visual panel completely fixed and static in place (no movement, zero zoom/pan).
    """
    return visual


# ── Text Panel Cinematic Reveal ───────────────────────────────────────────────

def _apply_panel_reveal(frame: np.ndarray, t: float, reveal_dur: float = 0.65) -> np.ndarray:
    """Lift a dark veil from the text panel to reveal content smoothly."""
    if t >= reveal_dur:
        return frame
    ratio         = 1.0 - _ease_out(t / reveal_dur)
    overlay_alpha = int(230 * ratio)
    pil = Image.fromarray(frame).convert("RGBA")
    veil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(veil).rectangle([(VISUAL_X2, 0), (W, H)], fill=(*BG_DARK, overlay_alpha))
    pil.alpha_composite(veil)
    return np.array(pil.convert("RGB"))


# ── Per-Step Animated Clip ────────────────────────────────────────────────────

def _make_step_clip(step: dict, total: int, slide_path: str,
                    audio_duration: float, kb_direction: str) -> list:
    """
    Build animated frames for one tutorial step:
      - Ken Burns camera motion on the visual (left) panel
      - Cinematic text reveal on the info (right) panel
      - Fade-in first FADE_DUR seconds, fade-out last FADE_DUR seconds
    Returns list of numpy frame arrays (for ImageSequenceClip).
    """
    full_img     = np.array(Image.open(slide_path).convert("RGB"))
    visual_panel = full_img[:, :VISUAL_X2].copy()
    text_panel   = full_img[:, VISUAL_X2:].copy()

    clip_dur = max(audio_duration + 0.3, 2.0)
    n_frames = max(int(clip_dur * FPS_ANIM), 3)

    frames = []
    for i in range(n_frames):
        t = i / FPS_ANIM
        kb_visual = _ken_burns_frame(visual_panel, t, clip_dur, kb_direction)
        frame = np.empty_like(full_img)
        frame[:, :VISUAL_X2] = kb_visual
        frame[:, VISUAL_X2:] = text_panel
        frame = _apply_panel_reveal(frame, t)

        # Add cinematic vignette overlay on the visual panel only
        if t > 0.2:
            pil_f = Image.fromarray(frame).convert("RGBA")
            vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            vd = ImageDraw.Draw(vig)
            # Subtle corner darken for cinematic look
            for r in range(60, 0, -10):
                alpha = max(0, 18 - r // 4)
                vd.ellipse([(0 - r, 0 - r), (r * 2, r * 2)], fill=(0, 0, 0, alpha))
                vd.ellipse([(VISUAL_X2 - r * 2, 0 - r), (VISUAL_X2 + r, r * 2)], fill=(0, 0, 0, alpha))
                vd.ellipse([(0 - r, H - r * 2), (r * 2, H + r)], fill=(0, 0, 0, alpha))
                vd.ellipse([(VISUAL_X2 - r * 2, H - r * 2), (VISUAL_X2 + r, H + r)], fill=(0, 0, 0, alpha))
            pil_f.alpha_composite(vig)
            frame = np.array(pil_f.convert("RGB"))

        frames.append(frame)

    frames = _apply_fade(frames, fade_in_sec=FADE_DUR, fade_out_sec=FADE_DUR)
    return frames


# ── Animated Intro Card ───────────────────────────────────────────────────────

def _render_intro_frame(topic: str, t: float, duration: float) -> np.ndarray:
    img = Image.new("RGB", (W, H), BG_DARK)
    d   = ImageDraw.Draw(img)

    # Cinematic gradient background
    for y in range(H):
        p = y / H
        r = int(BG_DARK[0] + 18 * p)
        g = int(BG_DARK[1] + 14 * p)
        b = int(BG_DARK[2] + 38 * p)
        d.line([(0, y), (W, y)], fill=(min(255, r), min(255, g), min(255, b)))

    img = img.convert("RGBA")
    d   = ImageDraw.Draw(img)

    # App Logo — large, bright, transparent logo (zoom in from 0 -> 0.8s, NO green circle background)
    cx, cy_logo = W // 2, H // 2 - 110
    lt = _ease_out(min(t / 0.8, 1.0))
    logo_path = Path("static/img/main_logo.png")
    logo_sz = max(8, int(130 * lt))   # 130px final size
    logo_y  = cy_logo - logo_sz // 2
    if logo_path.exists() and lt > 0.04:
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((logo_sz, logo_sz), Image.LANCZOS)
            from PIL import ImageEnhance as _IE
            logo_rgb = logo.convert("RGB")
            logo_rgb = _IE.Brightness(logo_rgb).enhance(1.4)
            logo_rgb = _IE.Contrast(logo_rgb).enhance(1.2)
            logo_alpha = logo.split()[3]
            logo_final = logo_rgb.convert("RGBA")
            logo_final.putalpha(logo_alpha)
            img.paste(logo_final, (W // 2 - logo_sz // 2, logo_y), logo_final)
        except Exception:
            pass

    # "VisuAIze" brand name typewriter effect (0.4 -> 1.1s)
    brand = "VisuAIze"
    bt = max(0.0, (t - 0.4) / 0.7)
    shown = brand[:int(bt * len(brand))]
    if shown:
        b_alpha = min(255, int(255 * bt))
        bf = _font(32, bold=True)
        bw = d.textbbox((0, 0), shown, font=bf)
        d.text(((W - (bw[2] - bw[0])) // 2, H // 2 - 28), shown, fill=(*WHITE, b_alpha), font=bf)

    # Topic title fade-in (0.9 -> 1.6s)
    tt = _ease_out(max(0.0, (t - 0.9) / 0.7))
    if tt > 0:
        t_alpha = int(255 * tt)
        tf    = _font(40, bold=True)
        lines = _wrap(topic, tf, W - 200, d)
        ty    = H // 2 + 28
        for line in lines[:2]:
            bb = d.textbbox((0, 0), line, font=tf)
            d.text(((W - (bb[2] - bb[0])) // 2, ty), line, fill=(*WHITE, t_alpha), font=tf)
            ty += 56

    # Subtitle (1.5s ->)
    st = min(1.0, max(0.0, (t - 1.5) / 0.5))
    if st > 0:
        sub = "Cinematic AI Step-by-Step Tutorial"
        sf  = _font(18)
        sb  = d.textbbox((0, 0), sub, font=sf)
        d.text(((W - (sb[2] - sb[0])) // 2, H // 2 + 155), sub, fill=(*EMERALD, int(200 * st)), font=sf)

    # Bottom letterbox bar
    d.rectangle([(0, H - 4), (W, H)], fill=(*EMERALD, 180))

    return np.array(img.convert("RGB"))


def _make_intro_frames(topic: str, audio_duration: float) -> list:
    clip_dur = max(audio_duration + 0.3, 3.5)
    frames   = [_render_intro_frame(topic, i / FPS_ANIM, clip_dur)
                for i in range(max(int(clip_dur * FPS_ANIM), 3))]
    # Bake fade-out only (no fade-in — intro starts the video)
    frames = _apply_fade(frames, fade_in_sec=0.0, fade_out_sec=FADE_DUR)
    return frames


# ── Animated Outro Card ───────────────────────────────────────────────────────

def _render_outro_frame(topic: str, num_steps: int, t: float, duration: float) -> np.ndarray:
    img = Image.new("RGB", (W, H), (8, 10, 22))
    d   = ImageDraw.Draw(img)

    # Deep cinematic gradient
    for y in range(H):
        p = y / H
        d.line([(0, y), (W, y)], fill=(int(8 + 12 * p), int(10 + 10 * p), int(22 + 20 * p)))

    img = img.convert("RGBA")
    d   = ImageDraw.Draw(img)

    cx = W // 2
    cy_logo = H // 2 - 120

    # App Logo — purely transparent at outro (0 -> 0.7s, NO green circle background)
    lt = _ease_out(min(t / 0.6, 1.0))
    logo_path = Path("static/img/main_logo.png")
    logo_sz = max(8, int(120 * lt))
    logo_y  = cy_logo - logo_sz // 2
    if logo_path.exists() and lt > 0.04:
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((logo_sz, logo_sz), Image.LANCZOS)
            from PIL import ImageEnhance as _IE2
            logo_rgb = logo.convert("RGB")
            logo_rgb = _IE2.Brightness(logo_rgb).enhance(1.5)
            logo_rgb = _IE2.Color(logo_rgb).enhance(1.3)
            logo_alpha = logo.split()[3]
            logo_final = logo_rgb.convert("RGBA")
            logo_final.putalpha(logo_alpha)
            img.paste(logo_final, (W // 2 - logo_sz // 2, logo_y), logo_final)
        except Exception:
            pass

    # "VisuAIze" brand (0.5s ->)
    bt = _ease_out(max(0.0, (t - 0.5) / 0.4))
    if bt > 0:
        bf = _font(28, bold=True)
        bw = d.textbbox((0, 0), "VisuAIze", font=bf)
        d.text(((W - (bw[2] - bw[0])) // 2, H // 2 - 30), "VisuAIze",
               fill=(*WHITE, int(255 * bt)), font=bf)

    # "Tutorial Complete!" (0.75s ->)
    dt = _ease_out(max(0.0, (t - 0.75) / 0.4))
    if dt > 0:
        d.text((W // 2, H // 2 + 18), "Tutorial Complete!",
               fill=(*EMERALD, int(255 * dt)),
               font=_font(36, bold=True), anchor="mm")

    # Step count info (1.0s ->)
    ct = min(1.0, max(0.0, (t - 1.0) / 0.35))
    if ct > 0:
        d.text((W // 2, H // 2 + 68),
               f"Completed all {num_steps} steps  ·  {topic[:48]}",
               fill=(*MUTED, int(220 * ct)), font=_font(16), anchor="mm")

    # Bottom accent bar
    bar_alpha = int(180 * min(1.0, max(0.0, (t - 1.2) / 0.3)))
    if bar_alpha > 0:
        d.rectangle([(0, H - 4), (W, H)], fill=(*EMERALD, bar_alpha))
        d.text((W // 2, H - 22), "VisuAIze  ·  AI Cinematic Video Generator",
               fill=(*MUTED, bar_alpha), font=_font(12), anchor="mm")

    return np.array(img.convert("RGB"))


def _make_outro_frames(topic: str, num_steps: int, audio_duration: float) -> list:
    clip_dur = max(audio_duration + 0.3, 3.5)
    frames   = [_render_outro_frame(topic, num_steps, i / FPS_ANIM, clip_dur)
                for i in range(max(int(clip_dur * FPS_ANIM), 3))]
    # Bake fade-in only (no fade-out — outro ends the video)
    frames = _apply_fade(frames, fade_in_sec=FADE_DUR, fade_out_sec=0.0)
    return frames


# ── Main Assembler Entry Point ────────────────────────────────────────────────

def assemble_video(
    steps:       list,
    image_paths: list,
    audio_data:  dict,
    output_path: str,
    topic:       str = "Step-by-Step Guide",
    job_id:      str = "",
) -> str:
    """
    Assemble the final animated tutorial MP4.
    All fades are baked into frame arrays — zero dependency on MoviePy fx effects.
    Audio clips are kept open until after write_videofile() completes.
    """
    print("\n🎬 Animated Video Engine — assembling step-by-step tutorial...")

    all_clips        = []
    audio_to_close   = []   # keep all audio refs alive until after rendering
    total            = len(steps)

    # ── 1. Animated Intro ─────────────────────────────────────────────────
    intro_audio_path = audio_data.get("intro")
    intro_audio      = None
    intro_dur        = 3.5
    if intro_audio_path and Path(intro_audio_path).exists():
        try:
            intro_audio = AudioFileClip(intro_audio_path)
            intro_dur   = intro_audio.duration
            audio_to_close.append(intro_audio)
        except Exception as e:
            print(f"  [WARN] Intro audio error: {e}")

    intro_frames = _make_intro_frames(topic, intro_dur)
    intro_clip   = ImageSequenceClip(intro_frames, fps=FPS_ANIM)
    if intro_audio:
        intro_clip = intro_clip.set_audio(intro_audio)
    all_clips.append(intro_clip)
    print("  ✓ Animated intro ready (logo zoom + typewriter)")

    # ── 2. Step Clips — Ken Burns + panel reveal + baked fades ───────────
    kb_pool = (KB_DIRECTIONS * ((total // len(KB_DIRECTIONS)) + 2))[:total]
    random.shuffle(kb_pool)

    for i, (step, img_path) in enumerate(zip(steps, image_paths)):
        step_audio = None
        step_dur   = max(float(step.get("duration_seconds", 6)), 3.0)

        if img_path and Path(img_path).exists():
            audio_path = audio_data["steps"][i]
            if audio_path and Path(audio_path).exists():
                try:
                    step_audio = AudioFileClip(audio_path)
                    step_dur   = step_audio.duration
                    audio_to_close.append(step_audio)
                except Exception as e:
                    print(f"  [WARN] Step {i+1} audio error: {e}")

            kb_dir   = kb_pool[i % len(KB_DIRECTIONS)]
            frames   = _make_step_clip(step, total, img_path, step_dur, kb_dir)
            clip     = ImageSequenceClip(frames, fps=FPS_ANIM)
            if step_audio:
                clip = clip.set_audio(step_audio)
            all_clips.append(clip)
            print(f"  ✓ Step {i+1}/{total} animated  [{kb_dir}]")
        else:
            print(f"  [SKIP] Step {i+1} — image not found: {img_path}")

    # ── 3. Animated Outro ─────────────────────────────────────────────────
    outro_audio_path = audio_data.get("outro")
    outro_audio      = None
    outro_dur        = 3.5
    if outro_audio_path and Path(outro_audio_path).exists():
        try:
            outro_audio = AudioFileClip(outro_audio_path)
            outro_dur   = outro_audio.duration
            audio_to_close.append(outro_audio)
        except Exception as e:
            print(f"  [WARN] Outro audio error: {e}")

    outro_frames = _make_outro_frames(topic, total, outro_dur)
    outro_clip   = ImageSequenceClip(outro_frames, fps=FPS_ANIM)
    if outro_audio:
        outro_clip = outro_clip.set_audio(outro_audio)
    all_clips.append(outro_clip)
    print("  ✓ Animated outro ready (arc draw + text reveal)")

    # ── 4. Concatenate (simple chain — all clips same size & fps) ─────────
    print("  🎞️  Concatenating clips...")
    if len(all_clips) == 1:
        final = all_clips[0]
    else:
        final = concatenate_videoclips(all_clips)

    # ── 5. Render ─────────────────────────────────────────────────────────
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    safe_id   = (job_id or str(os.getpid())).replace("/", "_")
    tmp_audio = str(Path(output_path).parent / f"_tmp_audio_{safe_id}.m4a")

    print(f"  💾 Encoding H.264 ultrafast (8 threads, {FPS_OUT}fps) → {output_path}")
    final.write_videofile(
        output_path,
        fps=FPS_OUT,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=8,
        logger=None,
        ffmpeg_params=["-tune", "fastdecode", "-pix_fmt", "yuv420p"],
        temp_audiofile=tmp_audio,
        remove_temp=True,
    )

    # ── 6. Cleanup — close all clips AFTER rendering is complete ──────────
    total_seconds = int(final.duration)
    try: final.close()
    except Exception: pass
    for c in all_clips:
        try: c.close()
        except Exception: pass
    # Close audio clips last (they must stay open during write_videofile)
    for a in audio_to_close:
        try: a.close()
        except Exception: pass

    size_mb = round(Path(output_path).stat().st_size / (1024 * 1024), 1)
    print(f"✅ Animated tutorial video ready: {output_path}  ({size_mb} MB, {total_seconds}s)")
    return output_path
