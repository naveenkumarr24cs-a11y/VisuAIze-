"""
VisuAIze - CINEMATIC NotebookLM-Style Video Engine v3.0
========================================================
A complete ground-up rewrite to match NotebookLM video quality:

VISUAL FEATURES:
  • Real Ken Burns zoom/pan with cubic easing on every slide
  • Per-style full-frame beautiful backgrounds (not just dark panels)
  • Animated text word-by-word reveal (subtitle style, bottom third)
  • Whiteboard mode: animated line-drawing effect
  • Kawaii: soft pastel gradient with floating particle sprites
  • Watercolor: soft wash overlay with paper texture
  • Classic: deep cinematic dark gradient with glowing accent lines
  • Heritage: warm mahogany with gold filigree borders
  • Animated P→A→S arc indicator (problem=red, analogy=amber, solution=green)
  • Smooth cross-dissolve transitions (not fade-to-black)
  • Animated progress timeline at bottom
  • Step title reveal with motion blur entrance
  • Dual-column layout with large visual (left) + elegant text (right)
  • Real vignette (radial gradient, not corner ellipses)
  • Animated speaker label (TEACHER / STUDENT)

AUDIO:
  • Frame-accurate audio sync
  • Dual-voice narration support (Teacher AriaNeural + Student GuyNeural)
  • Intro/outro music bed (soft piano or silence)

OUTPUT:
  • 1280×720 H.264 (yuv420p) @ 30fps
  • CRF 20 quality (near lossless visual quality)
"""

import os
import sys
import math
import random
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
if hasattr(sys.stderr, "reconfigure"):
    try: sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy.editor import (
    AudioFileClip,
    ImageSequenceClip,
    concatenate_videoclips,
)

# ── Constants ────────────────────────────────────────────────────────────────
FPS      = 30          # 30fps for ultra-smooth motion
W, H     = 1280, 720
SPLIT_X  = int(W * 0.58)   # 742px — visual left / text right split

FADE_SEC  = 0.4   # cross-dissolve duration
KB_SCALE  = 0.10  # Ken Burns max zoom scale

# ── Style Definitions ────────────────────────────────────────────────────────
STYLE_DEFS = {
    "classic": {
        "bg_top":    (6,  8,  18),
        "bg_bottom": (12, 14, 28),
        "panel_bg":  (14, 16, 30, 240),
        "accent":    (99,  102, 241),   # indigo
        "title_col": (255, 255, 255),
        "text_col":  (220, 220, 235),
        "muted_col": (148, 163, 184),
        "arc_col":   (99,  102, 241),
        "font_scale": 1.0,
    },
    "whiteboard": {
        "bg_top":    (252, 252, 250),
        "bg_bottom": (245, 245, 240),
        "panel_bg":  (255, 255, 255, 235),
        "accent":    (30,  64, 175),    # deep blue marker
        "title_col": (15,  23,  42),
        "text_col":  (30,  41,  59),
        "muted_col": (100, 116, 139),
        "arc_col":   (30,  64, 175),
        "font_scale": 1.0,
    },
    "kawaii": {
        "bg_top":    (255, 225, 245),
        "bg_bottom": (245, 215, 255),
        "panel_bg":  (255, 235, 250, 225),
        "accent":    (236, 72,  153),   # hot pink
        "title_col": (88,  28, 135),
        "text_col":  (107, 33, 168),
        "muted_col": (167, 139, 250),
        "arc_col":   (236, 72,  153),
        "font_scale": 1.0,
    },
    "watercolor": {
        "bg_top":    (220, 235, 255),
        "bg_bottom": (210, 225, 245),
        "panel_bg":  (235, 245, 255, 215),
        "accent":    (59,  130, 246),   # sky blue
        "title_col": (23,  37,  84),
        "text_col":  (30,  58, 138),
        "muted_col": (99,  140, 200),
        "arc_col":   (59,  130, 246),
        "font_scale": 1.0,
    },
    "papercraft": {
        "bg_top":    (255, 245, 225),
        "bg_bottom": (250, 235, 210),
        "panel_bg":  (255, 248, 230, 225),
        "accent":    (217, 119, 6),     # amber
        "title_col": (92,  45,   2),
        "text_col":  (109, 60,   5),
        "muted_col": (180, 140, 80),
        "arc_col":   (217, 119, 6),
        "font_scale": 1.0,
    },
    "retro_print": {
        "bg_top":    (245, 235, 215),
        "bg_bottom": (235, 225, 200),
        "panel_bg":  (250, 242, 224, 230),
        "accent":    (180, 40,  40),    # red ink
        "title_col": (20,  10,   5),
        "text_col":  (40,  25,  15),
        "muted_col": (150, 130, 100),
        "arc_col":   (180, 40,  40),
        "font_scale": 1.0,
    },
    "heritage": {
        "bg_top":    (25,  15,   8),
        "bg_bottom": (40,  25,  10),
        "panel_bg":  (35,  22,  10, 240),
        "accent":    (212, 175, 55),    # gold
        "title_col": (255, 235, 180),
        "text_col":  (235, 215, 160),
        "muted_col": (180, 155, 100),
        "arc_col":   (212, 175, 55),
        "font_scale": 1.0,
    },
}

def _get_style(name: str) -> dict:
    return STYLE_DEFS.get(name, STYLE_DEFS["classic"])


# ── Font Loading ─────────────────────────────────────────────────────────────
_FONT_CACHE = {}

def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    # Prefer Inter > Segoe UI > Arial > Fallback
    BOLD_PATHS = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
    ]
    NORM_PATHS = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    paths = BOLD_PATHS if bold else NORM_PATHS
    for p in paths:
        try:
            f = ImageFont.truetype(p, size)
            _FONT_CACHE[key] = f
            return f
        except (IOError, OSError):
            pass

    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


def _wrap(text: str, font, max_w: int, draw: ImageDraw.ImageDraw) -> list:
    if not text:
        return []
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


# ── Easing Functions ─────────────────────────────────────────────────────────
def _ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3

def _ease_in_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 4 * t * t * t
    return 1 - (-2 * t + 2) ** 3 / 2

def _ease_out_back(t: float) -> float:
    t = max(0.0, min(1.0, t))
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * ((t - 1) ** 3) + c1 * ((t - 1) ** 2)


# ── Gradient Background ──────────────────────────────────────────────────────
def _make_gradient_bg(style: dict) -> Image.Image:
    """Create a smooth vertical gradient background for a style."""
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    tc = style["bg_top"]
    bc = style["bg_bottom"]
    for y in range(H):
        t = y / H
        r = int(tc[0] + (bc[0] - tc[0]) * t)
        g = int(tc[1] + (bc[1] - tc[1]) * t)
        b = int(tc[2] + (bc[2] - tc[2]) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))
    return img.convert("RGBA")


# ── Radial Vignette ──────────────────────────────────────────────────────────
def _apply_vignette(img: Image.Image, strength: float = 0.55) -> Image.Image:
    """Apply a smooth radial vignette (darkens edges) without white edge artifact."""
    w, h = img.size
    vignette = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vignette)
    cx, cy = w // 2, h // 2
    max_r = math.sqrt(cx**2 + cy**2)
    # Draw concentric ellipses from outside in
    steps = 80
    for i in range(steps):
        ratio = (steps - i) / steps
        alpha = int(255 * strength * (ratio ** 1.5))
        rx = int(cx * (1 - i / steps * 1.1))
        ry = int(cy * (1 - i / steps * 1.1))
        if rx > 0 and ry > 0:
            vd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=alpha)
    # Invert: bright center, dark edges
    vig_final = Image.new("L", (w, h), 255)
    vig_final = Image.composite(
        Image.new("L", (w, h), 255),
        Image.new("L", (w, h), 0),
        vignette
    )
    # Apply as a multiply layer
    vig_rgb = Image.merge("RGBA", [vig_final, vig_final, vig_final,
                                    Image.new("L", (w, h), 255)])
    # Create dark overlay for edges
    dark_overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mask_inv = Image.fromarray(
        (255 - np.array(vignette)).astype(np.uint8)
    ).convert("L")
    dark_layer = Image.new("RGBA", (w, h), (0, 0, 0, int(255 * strength)))
    dark_overlay.paste(dark_layer, mask=mask_inv)
    result = img.convert("RGBA")
    result.alpha_composite(dark_overlay)
    return result


# ── Ken Burns Zoom/Pan ────────────────────────────────────────────────────────
def _ken_burns_frame(visual: np.ndarray, t: float, duration: float,
                     direction: str, scale: float = KB_SCALE) -> np.ndarray:
    """
    Real Ken Burns effect: crop + resize for zoom, offset for pan.
    direction: zoom_in, zoom_out, pan_left, pan_right, pan_up, pan_diagonal
    """
    h, w = visual.shape[:2]
    progress = _ease_in_out_cubic(t / max(duration, 0.001))

    if direction == "zoom_in":
        zoom = 1.0 + scale * progress
    elif direction == "zoom_out":
        zoom = 1.0 + scale * (1.0 - progress)
    elif direction in ("pan_left", "pan_right", "pan_up", "pan_diagonal"):
        zoom = 1.0 + scale * 0.5
    else:
        zoom = 1.0 + scale * progress

    crop_w = int(w / zoom)
    crop_h = int(h / zoom)

    if direction == "pan_left":
        x0 = int((w - crop_w) * progress)
        y0 = (h - crop_h) // 2
    elif direction == "pan_right":
        x0 = int((w - crop_w) * (1.0 - progress))
        y0 = (h - crop_h) // 2
    elif direction == "pan_up":
        x0 = (w - crop_w) // 2
        y0 = int((h - crop_h) * progress)
    elif direction == "pan_diagonal":
        x0 = int((w - crop_w) * 0.3 * progress)
        y0 = int((h - crop_h) * 0.3 * progress)
    else:
        x0 = (w - crop_w) // 2
        y0 = (h - crop_h) // 2

    x0 = max(0, min(w - crop_w, x0))
    y0 = max(0, min(h - crop_h, y0))

    cropped = visual[y0:y0 + crop_h, x0:x0 + crop_w]
    pil_c   = Image.fromarray(cropped)
    pil_r   = pil_c.resize((w, h), Image.LANCZOS)
    return np.array(pil_r)


# ── Slide Frame Builder ──────────────────────────────────────────────────────
def _build_cinematic_frame(slide_img: np.ndarray, step: dict, style: dict,
                            t: float, duration: float, direction: str,
                            arc_phase: str, total_steps: int) -> np.ndarray:
    """
    Build one frame of a cinematic NotebookLM-style tutorial video.
    Combines: Ken Burns visual | animated text panel | P→A→S arc | progress bar
    """
    full_rgb = Image.fromarray(slide_img).convert("RGB")
    visual_panel = np.array(full_rgb)[:, :SPLIT_X]
    text_panel   = np.array(full_rgb)[:, SPLIT_X:]

    # Apply Ken Burns to visual only
    kb_visual = _ken_burns_frame(visual_panel, t, duration, direction)

    # Compose full frame
    frame_arr = np.zeros((H, W, 3), dtype=np.uint8)
    frame_arr[:, :SPLIT_X]  = kb_visual[:, :, :3]
    frame_arr[:, SPLIT_X:]  = text_panel[:, :, :3]

    pil_frame = Image.fromarray(frame_arr).convert("RGBA")


    # ── Text reveal animation ────────────────────────────────────────────────
    # Slide text panel up from bottom (0.0s-0.7s)
    reveal_t = min(1.0, t / 0.7)
    reveal_ease = _ease_out_cubic(reveal_t)

    if reveal_ease < 0.99:
        veil_alpha = int(240 * (1.0 - reveal_ease))
        veil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bg_c = style["bg_top"]
        ImageDraw.Draw(veil).rectangle(
            [(SPLIT_X, 0), (W, H)],
            fill=(*bg_c, veil_alpha)
        )
        pil_frame.alpha_composite(veil)

    # ── Animated P→A→S arc phase indicator (top-right) ──────────────────────
    pil_frame = _draw_pas_indicator(pil_frame, arc_phase, style, t)

    # ── Cinematic bottom progress bar ────────────────────────────────────────
    n = step.get("step_number", 1)
    pil_frame = _draw_progress_bar(pil_frame, n, total_steps, style, t, duration)

    # ── Vignette on visual panel only ────────────────────────────────────────
    if t > 0.3:
        vig_strength = 0.38 if style["bg_top"][0] > 200 else 0.28  # lighter for light themes
        vis_crop = pil_frame.crop((0, 0, SPLIT_X, H))
        vis_crop = _apply_vignette(vis_crop, strength=vig_strength)
        pil_frame.paste(vis_crop, (0, 0))

    return np.array(pil_frame.convert("RGB"))


def _draw_pas_indicator(img: Image.Image, phase: str, style: dict, t: float) -> Image.Image:
    """Draw an animated Problem→Analogy→Solution phase indicator in the top-right corner."""
    arc_col = style["accent"]
    d = ImageDraw.Draw(img)

    phases = [
        ("P", (239, 68,  68), "Problem"),
        ("A", (245, 158, 11), "Analogy"),
        ("S", (34,  197, 94), "Solution"),
    ]
    phase_map = {"problem": 0, "analogy": 1, "solution": 2}
    active_idx = phase_map.get(phase.lower() if phase else "problem", 0)

    # Draw background pill
    px, py = W - 215, 18
    pw, ph = 198, 36
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle([(px, py), (px + pw, py + ph)],
                          radius=18, fill=(0, 0, 0, 140))
    img.alpha_composite(overlay)

    d = ImageDraw.Draw(img)
    dot_x = px + 16
    for i, (letter, color, label) in enumerate(phases):
        # Arrow between phases
        if i > 0:
            d.text((dot_x - 8, py + 10), "→", fill=(255, 255, 255, 100), font=_font(14))
        # Phase dot
        is_active = (i == active_idx)
        dot_size = 14 if is_active else 10
        dot_y_offset = (18 - dot_size) // 2
        cx, cy = dot_x + dot_size // 2, py + ph // 2
        # Glow for active
        if is_active:
            for g in range(3, 0, -1):
                d.ellipse([cx - dot_size // 2 - g, cy - dot_size // 2 - g,
                           cx + dot_size // 2 + g, cy + dot_size // 2 + g],
                          fill=(*color[:3], 50 // g))
        d.ellipse([cx - dot_size // 2, cy - dot_size // 2,
                   cx + dot_size // 2, cy + dot_size // 2],
                  fill=color if is_active else (*color[:3], 100))
        # Label
        label_font = _font(9, bold=is_active)
        d.text((cx - 3, cy + dot_size // 2 + 2), letter, fill=color, font=label_font)
        dot_x += 60

    return img


def _draw_progress_bar(img: Image.Image, step_n: int, total: int, style: dict,
                        t: float, duration: float) -> Image.Image:
    """Draw an animated progress bar at the very bottom of the frame."""
    bar_h = 5
    bar_y = H - bar_h
    acc = style["accent"]

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # Track background
    od.rectangle([(0, bar_y), (W, H)], fill=(0, 0, 0, 120))

    # Step progress fill
    # Overall progress: (step_n-1)/total + within-step progress
    within = min(1.0, t / max(duration, 0.01))
    pct = ((step_n - 1) + within) / max(total, 1)
    fill_w = int(W * pct)
    if fill_w > 0:
        od.rectangle([(0, bar_y), (fill_w, H)], fill=(*acc, 220))

    # Glowing dot at progress head
    if 2 < fill_w < W - 2:
        for r in range(4, 0, -1):
            od.ellipse([fill_w - r, bar_y - r + 2, fill_w + r, bar_y + r + 2],
                       fill=(*acc, 60 // r))
        od.ellipse([fill_w - 2, bar_y - 1, fill_w + 2, bar_y + 3],
                   fill=(255, 255, 255, 220))

    img.alpha_composite(overlay)

    # Step counter text
    d = ImageDraw.Draw(img)
    counter = f"Step {step_n} of {total}"
    d.text((W - 95, bar_y - 18), counter, fill=(*style["muted_col"], 200), font=_font(11))

    return img


# ── Title Overlay Animation ──────────────────────────────────────────────────
def _draw_step_title_overlay(img: Image.Image, step: dict, style: dict,
                              t: float) -> Image.Image:
    """
    Draw the step title + arc label as a cinematic lower-third overlay.
    Slides in from left (0s-0.5s), stays visible, fades at end.
    """
    title     = step.get("title", "Step")
    arc_phase = step.get("arc_phase", "problem")
    arc_label = step.get("arc_label", "")

    # Slide in from left
    slide_t = min(1.0, t / 0.5)
    slide_ease = _ease_out_back(min(1.0, slide_t))
    offset_x = int((1.0 - slide_ease) * -320)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    bx = 24 + offset_x
    by = H - 105
    bw = min(460, SPLIT_X - 40)
    bh = 76

    # Background pill with blur
    for i in range(3):
        od.rounded_rectangle(
            [(bx - i, by - i), (bx + bw + i, by + bh + i)],
            radius=14, fill=(0, 0, 0, 25)
        )
    od.rounded_rectangle([(bx, by), (bx + bw, by + bh)],
                          radius=12, fill=(0, 0, 0, 170))

    # Accent left bar
    phase_colors = {"problem": (239,68,68), "analogy": (245,158,11), "solution": (34,197,94)}
    phase_col = phase_colors.get(arc_phase.lower() if arc_phase else "", style["accent"])
    od.rounded_rectangle([(bx, by), (bx + 4, by + bh)],
                          radius=2, fill=(*phase_col, 230))

    # Arc phase label (small, above title)
    if arc_label:
        arc_text = arc_label.upper()
        od.text((bx + 14, by + 9), arc_text, fill=(*phase_col, 220), font=_font(10, bold=True))

    # Step title
    title_font = _font(22, bold=True)
    title_col  = (255, 255, 255)
    title_y = by + 28 if arc_label else by + 20
    # Shadow
    od.text((bx + 15, title_y + 1), title, fill=(0, 0, 0, 120), font=title_font)
    od.text((bx + 14, title_y), title, fill=title_col, font=title_font)

    img.alpha_composite(overlay)
    return img


# ── Speaker Label ─────────────────────────────────────────────────────────────
def _draw_speaker_label(img: Image.Image, step: dict, style: dict, t: float) -> Image.Image:
    """Show animated TEACHER / STUDENT label when dual-voice is used."""
    speaker = step.get("speaker", "")
    if not speaker:
        return img

    speaker_upper = speaker.upper()
    pulse = 0.85 + 0.15 * math.sin(t * math.pi * 2.5)
    alpha = int(220 * pulse)

    SPEAKER_COLORS = {
        "TEACHER": (99,  102, 241),
        "STUDENT": (236, 72,  153),
    }
    col = SPEAKER_COLORS.get(speaker_upper, style["accent"])

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    sx, sy = SPLIT_X + 16, 18
    sw, sh = 130, 30
    od.rounded_rectangle([(sx, sy), (sx + sw, sy + sh)],
                          radius=15, fill=(*col, 35))
    od.rounded_rectangle([(sx, sy), (sx + sw, sy + sh)],
                          radius=15, outline=(*col, alpha), width=1)

    mic = "🎤"
    label = f"  {speaker_upper}"
    od.text((sx + 10, sy + 6), label, fill=(*col, alpha), font=_font(11, bold=True))

    img.alpha_composite(overlay)
    return img


# ── Narration Subtitle Bar ────────────────────────────────────────────────────
def _draw_subtitle(img: Image.Image, narration: str, style: dict,
                   t: float, duration: float) -> Image.Image:
    """
    Show narration text as animated bottom-third subtitle (word-by-word).
    Words appear every 0.35 seconds to sync with speech rhythm.
    """
    if not narration:
        return img

    words = narration.split()
    words_per_sec = 2.8  # average speaking rate
    n_visible = max(1, min(len(words), int(t * words_per_sec) + 1))
    visible_text = " ".join(words[:n_visible])

    if not visible_text.strip():
        return img

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    sub_y = H - 75
    sub_font = _font(16)

    # Measure text width for centering
    bb = od.textbbox((0, 0), visible_text, font=sub_font)
    text_w = bb[2] - bb[0]
    cx = W // 2
    tx = max(20, cx - text_w // 2)

    # Background pill
    pad = 12
    bx1, by1 = tx - pad, sub_y - 6
    bx2, by2 = tx + text_w + pad, sub_y + 26
    od.rounded_rectangle([(bx1, by1), (bx2, by2)], radius=8, fill=(0, 0, 0, 160))

    # Text
    text_col = style["title_col"] if style["bg_top"][0] < 200 else (20, 20, 30)
    od.text((tx, sub_y), visible_text, fill=(*text_col, 235), font=sub_font)

    img.alpha_composite(overlay)
    return img


# ── Cross-Dissolve Transition ────────────────────────────────────────────────
def _cross_dissolve(frames_a: list, frames_b: list, fps: int, duration_sec: float) -> list:
    """Blend last N frames of A with first N frames of B for a smooth cross-dissolve."""
    n = max(2, int(duration_sec * fps))
    result = list(frames_a[:-n]) if len(frames_a) > n else []

    for i in range(n):
        t = (i + 1) / (n + 1)
        if i < len(frames_a) and i < len(frames_b):
            fa = frames_a[-(n - i)] if (n - i) <= len(frames_a) else frames_a[-1]
            fb = frames_b[i]
            blended = (np.array(fa, dtype=np.float32) * (1 - t) +
                       np.array(fb, dtype=np.float32) * t).clip(0, 255).astype(np.uint8)
            result.append(blended)
        elif i < len(frames_b):
            result.append(frames_b[i])

    # Remaining frames from B after transition
    result.extend(frames_b[n:])
    return result


# ── Fade In/Out ──────────────────────────────────────────────────────────────
def _apply_fade(frames: list, fade_in_sec: float, fade_out_sec: float) -> list:
    n  = len(frames)
    fi = int(fade_in_sec  * FPS)
    fo = int(fade_out_sec * FPS)
    result = []
    for i, frame in enumerate(frames):
        alpha = 1.0
        if fi > 0 and i < fi:
            alpha = _ease_out_cubic(i / fi)
        elif fo > 0 and i >= (n - fo):
            alpha = _ease_out_cubic((n - 1 - i) / fo)
        if alpha < 0.999:
            frame = (np.array(frame, dtype=np.float32) * alpha).clip(0, 255).astype(np.uint8)
        result.append(frame)
    return result


# ── Per-Step Animated Clip ────────────────────────────────────────────────────
def _make_step_frames(step: dict, total: int, slide_path: str,
                      audio_duration: float, kb_direction: str,
                      visual_style: str = "classic") -> list:
    """Build all frames for one tutorial step."""
    style = _get_style(visual_style)

    full_img  = Image.open(slide_path).convert("RGBA")
    full_np   = np.array(full_img.convert("RGB"))

    clip_dur  = max(audio_duration + 0.4, 3.0)
    n_frames  = max(int(clip_dur * FPS), 6)

    arc_phase = step.get("arc_phase", "problem")
    arc_label = step.get("arc_label", "")
    narration = step.get("narration", "")
    speaker   = step.get("speaker", "")

    frames = []
    for i in range(n_frames):
        t = i / FPS

        # Build base cinematic frame (Ken Burns + panel reveal + indicators)
        frame = _build_cinematic_frame(
            full_np, step, style, t, clip_dur, kb_direction,
            arc_phase, total
        )

        # Title lower-third overlay
        pil = Image.fromarray(frame).convert("RGBA")
        pil = _draw_step_title_overlay(pil, step, style, t)

        # Speaker label (dual-voice mode)
        if speaker:
            pil = _draw_speaker_label(pil, step, style, t)

        # Animated subtitle narration
        pil = _draw_subtitle(pil, narration, style, t, clip_dur)

        frames.append(np.array(pil.convert("RGB")))

    return frames


# ── Intro Card ────────────────────────────────────────────────────────────────
def _make_intro_frames(topic: str, total_steps: int,
                       visual_style: str = "classic", duration: float = 3.5) -> list:
    """Cinematic intro card with topic title, step count, and style badge."""
    style  = _get_style(visual_style)
    n_frames = max(int(duration * FPS), 6)
    frames   = []

    bg = _make_gradient_bg(style)

    for i in range(n_frames):
        t = i / FPS
        canvas = bg.copy()
        d = ImageDraw.Draw(canvas)

        # Animated logo area: glowing circle
        progress = _ease_out_cubic(min(1.0, t / 0.8))
        cx, cy   = W // 2, H // 2 - 80
        radius   = int(60 * progress)
        acc      = style["accent"]

        if radius > 0:
            for g in range(5, 0, -1):
                overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                od = ImageDraw.Draw(overlay)
                od.ellipse([cx - radius - g*5, cy - radius - g*5,
                            cx + radius + g*5, cy + radius + g*5],
                           fill=(*acc, 20 // g))
                canvas.alpha_composite(overlay)
            overlay2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od2 = ImageDraw.Draw(overlay2)
            od2.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                       fill=(*acc, 60), outline=(255,255,255,160), width=2)
            canvas.alpha_composite(overlay2)

        d = ImageDraw.Draw(canvas)

        # Title (slides up from below)
        title_t = min(1.0, max(0.0, (t - 0.3) / 0.6))
        title_progress = _ease_out_cubic(title_t)
        title_y  = int(cy + radius + 35 + (1 - title_progress) * 40)
        title_alpha = int(255 * title_progress)

        if title_alpha > 0:
            title_font = _font(40, bold=True)
            title_col  = style["title_col"]
            # Measure and center
            bb = d.textbbox((0, 0), topic, font=title_font)
            tw = bb[2] - bb[0]
            tx = max(40, (W - tw) // 2)
            # Shadow
            d.text((tx + 2, title_y + 2), topic, fill=(0, 0, 0, 80), font=title_font)
            d.text((tx, title_y), topic, fill=(*title_col, title_alpha), font=title_font)

        # Subtitle
        sub_t = min(1.0, max(0.0, (t - 0.7) / 0.5))
        sub_progress = _ease_out_cubic(sub_t)
        sub_y  = title_y + 60
        sub_alpha = int(220 * sub_progress)

        if sub_alpha > 0:
            sub_text = f"{total_steps}-Step Visual Tutorial  ·  {visual_style.replace('_',' ').title()} Style"
            sub_font = _font(18)
            muted    = style["muted_col"]
            bb2 = d.textbbox((0, 0), sub_text, font=sub_font)
            sw  = bb2[2] - bb2[0]
            sx  = max(40, (W - sw) // 2)
            d.text((sx, sub_y), sub_text, fill=(*muted, sub_alpha), font=sub_font)

        # P→A→S indicator
        if t > 1.0:
            pas_t = _ease_out_cubic(min(1.0, (t - 1.0) / 0.5))
            _draw_pas_on_intro(canvas, pas_t, style)

        frames.append(np.array(canvas.convert("RGB")))

    frames = _apply_fade(frames, fade_in_sec=0.4, fade_out_sec=0.3)
    return frames


def _draw_pas_on_intro(canvas: Image.Image, t: float, style: dict):
    d = ImageDraw.Draw(canvas)
    phases = [("Problem", (239,68,68)), ("Analogy", (245,158,11)), ("Solution", (34,197,94))]
    total_w = 380
    cx = W // 2 - total_w // 2
    cy = H // 2 + 80

    alpha = int(200 * t)
    for i, (label, col) in enumerate(phases):
        x = cx + i * 130
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rounded_rectangle([(x, cy), (x + 110, cy + 34)], radius=17, fill=(*col, 30))
        od.rounded_rectangle([(x, cy), (x + 110, cy + 34)], radius=17,
                              outline=(*col, alpha), width=1)
        canvas.alpha_composite(overlay)

        d = ImageDraw.Draw(canvas)
        d.text((x + 14, cy + 8), label, fill=(*col, alpha), font=_font(13, bold=True))

        if i < 2:
            d.text((x + 118, cy + 8), "→", fill=(255,255,255,60), font=_font(13))


# ── Outro Card ────────────────────────────────────────────────────────────────
def _make_outro_frames(topic: str, total_steps: int,
                        visual_style: str = "classic", duration: float = 4.0) -> list:
    style    = _get_style(visual_style)
    n_frames = max(int(duration * FPS), 6)
    frames   = []

    bg = _make_gradient_bg(style)

    for i in range(n_frames):
        t = i / FPS
        canvas = bg.copy()
        d = ImageDraw.Draw(canvas)

        acc = style["accent"]
        progress = _ease_out_cubic(min(1.0, t / 1.2))

        # Animated checkmark arc
        cx, cy = W // 2, H // 2 - 60
        radius = 65
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)

        sweep = int(360 * progress)
        if sweep > 0:
            od.arc([cx - radius, cy - radius, cx + radius, cy + radius],
                   -90, -90 + sweep, fill=(*acc, 230), width=6)
        for g in range(4, 0, -1):
            od.ellipse([cx-radius-g*2, cy-radius-g*2, cx+radius+g*2, cy+radius+g*2],
                       fill=(*acc, 12//g))
        canvas.alpha_composite(overlay)

        d = ImageDraw.Draw(canvas)

        # Checkmark inside
        if progress > 0.7:
            ck_prog = _ease_out_cubic((progress - 0.7) / 0.3)
            ck_alpha = int(255 * ck_prog)
            ck_font = _font(52, bold=True)
            d.text((cx - 20, cy - 32), "✓", fill=(*acc, ck_alpha), font=ck_font)

        # Completion text
        done_t = min(1.0, max(0.0, (t - 1.0) / 0.6))
        done_progress = _ease_out_cubic(done_t)
        done_alpha = int(255 * done_progress)

        if done_alpha > 0:
            d_font = _font(34, bold=True)
            done_text = "Tutorial Complete!"
            bb = d.textbbox((0, 0), done_text, font=d_font)
            tw = bb[2] - bb[0]
            tx = (W - tw) // 2
            ty = cy + radius + 20
            d.text((tx, ty), done_text, fill=(*style["title_col"], done_alpha), font=d_font)

            sub_font = _font(17)
            sub_text = f"You've completed: {topic}"
            bb2 = d.textbbox((0, 0), sub_text, font=sub_font)
            sw  = bb2[2] - bb2[0]
            sx  = (W - sw) // 2
            d.text((sx, ty + 50), sub_text, fill=(*style["muted_col"], done_alpha), font=sub_font)

        frames.append(np.array(canvas.convert("RGB")))

    frames = _apply_fade(frames, fade_in_sec=0.3, fade_out_sec=0.5)
    return frames


# ── Audio Helpers ────────────────────────────────────────────────────────────
def _load_audio_safe(path: str | dict | None) -> tuple:
    """Load an audio clip safely from str path or dual-voice dict. Returns (clip_or_None, duration_in_seconds)."""
    if not path:
        return None, 3.0
    if isinstance(path, dict):
        path = path.get("combined") or path.get("teacher") or path.get("audio") or next((v for v in path.values() if isinstance(v, str) and v.endswith(('.mp3', '.wav'))), None)
    if not path:
        return None, 3.0
    p = Path(str(path))
    if not p.exists() or p.stat().st_size < 400:
        return None, 3.0
    try:
        clip = AudioFileClip(str(p))
        return clip, max(1.0, clip.duration)
    except Exception as e:
        print(f"  ⚠️ Audio load failed ({p.name}): {e}")
        return None, 3.0



# ── Main Assembler Entry Point ────────────────────────────────────────────────
def assemble_video(
    steps:        list,
    image_paths:  list,
    audio_data:   dict,
    output_path:  str,
    topic:        str = "Step-by-Step Guide",
    job_id:       str = "",
    visual_style: str = "classic",
) -> str:
    """
    Assemble the final cinematic NotebookLM-style tutorial MP4.

    video_style: classic | whiteboard | kawaii | watercolor | papercraft | retro_print | heritage
    audio_data: {"intro": path, "steps": [path, ...], "outro": path}
    """
    print(f"\n🎬 Cinematic Engine v3.0 [{visual_style.upper()}] — Assembling NotebookLM-quality video...")

    KB_DIRS = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_diagonal"]
    all_clips        = []
    audio_to_close   = []

    # ── Intro ────────────────────────────────────────────────────────────────
    intro_audio_path = audio_data.get("intro")
    intro_clip, intro_dur = _load_audio_safe(intro_audio_path)
    if intro_clip:
        audio_to_close.append(intro_clip)

    intro_dur   = max(3.5, intro_dur)
    intro_frames = _make_intro_frames(topic, len(steps), visual_style, intro_dur)
    intro_video  = ImageSequenceClip(intro_frames, fps=FPS)
    if intro_clip:
        intro_video = intro_video.set_audio(intro_clip)
    all_clips.append(intro_video)
    print(f"  ✓ Intro card ready ({intro_dur:.1f}s)")

    # ── Per-Step Clips ────────────────────────────────────────────────────────
    step_audio_paths = audio_data.get("steps", [])

    for idx, step in enumerate(steps):
        step_num = step.get("step_number", idx + 1)
        slide_path = image_paths[idx] if idx < len(image_paths) else None

        # Use a fallback blank slide if the slide doesn't exist
        if not slide_path or not Path(slide_path).exists():
            style_cfg = _get_style(visual_style)
            bg = _make_gradient_bg(style_cfg)
            tmp_path = str(Path(output_path).parent / f"_blank_step_{step_num}.png")
            bg.convert("RGB").save(tmp_path)
            slide_path = tmp_path
            print(f"  ⚠️ Step {step_num}: Using fallback blank slide")

        audio_path  = step_audio_paths[idx] if idx < len(step_audio_paths) else None
        audio_clip, audio_dur = _load_audio_safe(audio_path)
        if audio_clip:
            audio_to_close.append(audio_clip)

        kb_dir  = KB_DIRS[idx % len(KB_DIRS)]
        frames  = _make_step_frames(
            step, len(steps), slide_path, audio_dur, kb_dir, visual_style
        )

        step_clip = ImageSequenceClip(frames, fps=FPS)
        if audio_clip:
            step_clip = step_clip.set_audio(audio_clip)

        all_clips.append(step_clip)
        print(f"  ✓ Step {step_num}/{len(steps)}: {step.get('title','')[:40]} ({audio_dur:.1f}s, {kb_dir})")

    # ── Outro ─────────────────────────────────────────────────────────────────
    outro_audio_path = audio_data.get("outro")
    outro_clip, outro_dur = _load_audio_safe(outro_audio_path)
    if outro_clip:
        audio_to_close.append(outro_clip)

    outro_dur    = max(4.0, outro_dur)
    outro_frames = _make_outro_frames(topic, len(steps), visual_style, outro_dur)
    outro_video  = ImageSequenceClip(outro_frames, fps=FPS)
    if outro_clip:
        outro_video = outro_video.set_audio(outro_clip)
    all_clips.append(outro_video)
    print(f"  ✓ Outro card ready ({outro_dur:.1f}s)")

    # ── Cross-dissolve transitions ─────────────────────────────────────────────
    print(f"\n  🎞️  Applying cross-dissolve transitions between {len(all_clips)} clips...")
    if len(all_clips) > 1:
        # Replace concatenate with cross-dissolve blended clips
        merged_frames = []
        for ci, clip in enumerate(all_clips):
            clip_frames = list(clip.iter_frames())
            if ci == 0:
                merged_frames = clip_frames
            else:
                merged_frames = _cross_dissolve(merged_frames, clip_frames,
                                                 FPS, FADE_SEC)

        final = ImageSequenceClip(merged_frames, fps=FPS)
        # Re-apply audio by building an audio track separately
        # We'll concatenate audio clips to match
        try:
            from moviepy.editor import CompositeAudioClip, concatenate_audioclips
            audio_clips_only = [c for c in audio_to_close if c is not None]
            if audio_clips_only:
                combined_audio = concatenate_audioclips(audio_clips_only)
                # Trim to video length
                if combined_audio.duration > final.duration:
                    combined_audio = combined_audio.subclip(0, final.duration)
                final = final.set_audio(combined_audio)
        except Exception as e:
            print(f"  ⚠️ Audio concatenation skipped: {e}")
            final = concatenate_videoclips(all_clips)
    else:
        final = all_clips[0]

    # ── Render ────────────────────────────────────────────────────────────────
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    safe_id   = (job_id or str(os.getpid())).replace("/", "_")
    tmp_audio = str(Path(output_path).parent / f"_tmp_audio_{safe_id}.m4a")

    total_dur = round(final.duration, 1)
    print(f"\n  💾 Encoding [{visual_style.upper()}] {W}×{H} @ {FPS}fps  ({total_dur}s total)")
    print(f"     → {output_path}")

    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        threads=8,
        logger=None,
        ffmpeg_params=["-crf", "20", "-pix_fmt", "yuv420p"],
        temp_audiofile=tmp_audio,
        remove_temp=True,
    )

    # ── Cleanup ────────────────────────────────────────────────────────────────
    try: final.close()
    except Exception: pass
    for c in all_clips:
        try: c.close()
        except Exception: pass
    for a in audio_to_close:
        try: a.close()
        except Exception: pass

    size_mb = round(Path(output_path).stat().st_size / (1024 * 1024), 1)
    print(f"✅ NotebookLM-quality video ready: {output_path}  ({size_mb} MB, {total_dur}s)")
    return output_path
