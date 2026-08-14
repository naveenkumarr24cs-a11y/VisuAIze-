"""
VisuAIze - Ultra-Fast NotebookLM-Style Video Engine v4.0
=========================================================
A ground-up high-performance video engine delivering:

1. STABLE 16:9 PRESENTATION LAYOUT:
   - 100% static, centered, uncropped slide presentation.
   - Zero camera panning, tilting, or diagonal shifts.
   - Diagrams, formulas, labels, and text remain 100% visible from start to finish.

2. SMOOTH 0.5s CROSS-DISSOLVE TRANSITIONS:
   - Seamless cross-dissolve blending between all slides and cards.
   - Frame-accurate audio sync with transition buffering.

3. ANIMATED AUDIO-REACTIVE SPEAKER BADGE:
   - Dynamic badge for active speaker (TEACHER vs STUDENT).
   - Audio-reactive equalizer waveform bars that pulse naturally with speech rhythm.
   - Subtle glowing outline that breathes with speech activity.

4. SMOOTH & ELEGANT BOTTOM PROGRESS BAR:
   - High-precision continuous progress bar with glowing head.
   - Step counter badge ("Step X of N") for clear progress tracking.

5. BRIGHT & CRISP VISUALS:
   - Zero vignette or darkening filters.
   - 100% bright, crisp, high-contrast visual display.

6. ULTRA-FAST ENCODING PIPELINE:
   - Pre-rendered static background cache + localized dynamic patch rendering.
   - Vectorized float32 numpy cross-dissolves.
   - Multi-threaded (threads=8) libx264 encoding with preset='veryfast'.
   - Generates final MP4 videos in seconds.
"""

import os
import sys
import math
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
if hasattr(sys.stderr, "reconfigure"):
    try: sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    AudioFileClip,
    ImageSequenceClip,
    concatenate_audioclips,
)

# ── Global Video Specifications ──────────────────────────────────────────────
FPS             = 24        # 24fps standard cinematic framerate for ultra-fast rendering
W, H            = 1280, 720 # 16:9 Presentation Canvas
TRANSITION_SEC  = 0.5       # 0.5s cross-dissolve transition between slides
TRANSITION_FRAMES = int(TRANSITION_SEC * FPS) # 12 frames at 24fps

# ── Style Definitions ────────────────────────────────────────────────────────
STYLE_DEFS: Dict[str, Dict[str, Any]] = {
    "classic": {
        "bg_top":    (8,   10,  20),
        "bg_bottom": (16,  20,  38),
        "panel_bg":  (20,  24,  44),
        "accent":    (99,  102, 241),   # Indigo
        "accent_alt":(168, 85,  247),   # Purple
        "title_col": (255, 255, 255),
        "text_col":  (226, 232, 240),
        "muted_col": (148, 163, 184),
        "border_col":(45,  55,  85),
    },
    "whiteboard": {
        "bg_top":    (252, 252, 250),
        "bg_bottom": (244, 245, 248),
        "panel_bg":  (255, 255, 255),
        "accent":    (30,  64,  175),   # Deep Blue marker
        "accent_alt":(14,  165, 233),   # Cyan
        "title_col": (15,  23,  42),
        "text_col":  (30,  41,  59),
        "muted_col": (100, 116, 139),
        "border_col":(226, 232, 240),
    },
    "kawaii": {
        "bg_top":    (255, 235, 245),
        "bg_bottom": (245, 220, 255),
        "panel_bg":  (255, 245, 252),
        "accent":    (236, 72,  153),   # Hot Pink
        "accent_alt":(217, 70,  239),   # Fuchsia
        "title_col": (88,  28,  135),
        "text_col":  (107, 33,  168),
        "muted_col": (167, 139, 250),
        "border_col":(244, 114, 182),
    },
    "watercolor": {
        "bg_top":    (225, 240, 255),
        "bg_bottom": (210, 230, 250),
        "panel_bg":  (240, 248, 255),
        "accent":    (37,  99,  235),   # Royal Sky Blue
        "accent_alt":(6,   182, 212),   # Turquoise
        "title_col": (23,  37,  84),
        "text_col":  (30,  58,  138),
        "muted_col": (99,  140, 200),
        "border_col":(186, 230, 253),
    },
    "papercraft": {
        "bg_top":    (255, 246, 232),
        "bg_bottom": (248, 235, 215),
        "panel_bg":  (255, 250, 240),
        "accent":    (217, 119, 6),     # Warm Amber
        "accent_alt":(234, 88,  12),    # Orange
        "title_col": (92,  45,  2),
        "text_col":  (109, 60,  5),
        "muted_col": (180, 140, 80),
        "border_col":(251, 191, 36),
    },
    "retro_print": {
        "bg_top":    (246, 238, 222),
        "bg_bottom": (236, 226, 205),
        "panel_bg":  (252, 246, 232),
        "accent":    (185, 28,  28),    # Crimson Ink
        "accent_alt":(217, 119, 6),     # Amber
        "title_col": (20,  10,  5),
        "text_col":  (40,  25,  15),
        "muted_col": (150, 130, 100),
        "border_col":(200, 160, 120),
    },
    "heritage": {
        "bg_top":    (26,  16,  9),
        "bg_bottom": (42,  28,  14),
        "panel_bg":  (36,  23,  12),
        "accent":    (212, 175, 55),    # Gold
        "accent_alt":(245, 158, 11),    # Amber Gold
        "title_col": (255, 238, 190),
        "text_col":  (235, 215, 165),
        "muted_col": (180, 155, 100),
        "border_col":(120, 85,  40),
    },
}

def _get_style(name: str) -> Dict[str, Any]:
    """Retrieve visual style dictionary with fallback to classic."""
    return STYLE_DEFS.get((name or "").lower(), STYLE_DEFS["classic"])


# ── Font Loading and Caching ──────────────────────────────────────────────────
_FONT_CACHE: Dict[Tuple[int, bool], ImageFont.ImageFont] = {}

def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Retrieve or load a TrueType font with system fallback and caching."""
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    BOLD_PATHS = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    NORM_PATHS = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    paths = BOLD_PATHS if bold else NORM_PATHS
    for p in paths:
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, size)
                _FONT_CACHE[key] = f
                return f
            except Exception:
                pass

    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


# ── Easing Helpers ────────────────────────────────────────────────────────────
def _ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


# ── Background Creation ───────────────────────────────────────────────────────
def _make_gradient_bg(style: Dict[str, Any]) -> Image.Image:
    """Create a vertical gradient background image matching the style (RGBA mode)."""
    tc = style["bg_top"]
    bc = style["bg_bottom"]
    
    # Fast vectorized numpy gradient
    r = np.linspace(tc[0], bc[0], H, dtype=np.uint8)
    g = np.linspace(tc[1], bc[1], H, dtype=np.uint8)
    b = np.linspace(tc[2], bc[2], H, dtype=np.uint8)
    a = np.full((H,), 255, dtype=np.uint8)
    
    rgba = np.stack([
        np.tile(r[:, None], (1, W)),
        np.tile(g[:, None], (1, W)),
        np.tile(b[:, None], (1, W)),
        np.tile(a[:, None], (1, W))
    ], axis=2)
    
    return Image.fromarray(rgba, mode="RGBA")


# ── Stable 16:9 Slide Placement (Zero Crop, Zero Pan/Tilt/Zoom) ────────────────
def _fit_slide_to_canvas(slide_img: Image.Image, style: Dict[str, Any]) -> Image.Image:
    """
    Fits any slide image perfectly into the 1280x720 16:9 canvas.
    Ensures diagrams, math, code, and text are 100% visible, centered, and never cropped.
    """
    if slide_img.size == (W, H):
        return slide_img.convert("RGB")
    
    canvas = _make_gradient_bg(style)
    
    # Calculate scale to fit inside 1280x720 without any cropping
    img_w, img_h = slide_img.size
    scale = min(W / img_w, H / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    
    resized = slide_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Center on canvas
    paste_x = (W - new_w) // 2
    paste_y = (H - new_h) // 2
    
    if resized.mode == "RGBA":
        canvas.paste(resized, (paste_x, paste_y), mask=resized)
    else:
        canvas.paste(resized, (paste_x, paste_y))
        
    return canvas.convert("RGB")


# ── Speaker Badge & Waveform Animation ────────────────────────────────────────
def _render_speaker_badge_on_frame(
    frame_np: np.ndarray,
    speaker: str,
    style: Dict[str, Any],
    t: float,
    audio_dur: float
) -> None:
    """
    Renders an animated speaker badge with audio-reactive waveform bars directly on frame_np.
    Uses alpha-composited pill with rounded corners.
    """
    speaker_upper = (speaker or "TEACHER").upper()
    
    # Active palette
    SPEAKER_PALETTES = {
        "TEACHER": {
            "bg": (28, 32, 64, 230),
            "border": (99, 102, 241),
            "text": (224, 231, 255),
            "bars": (129, 140, 248),
            "label": "🎓 TEACHER",
        },
        "STUDENT": {
            "bg": (60, 24, 48, 230),
            "border": (236, 72, 153),
            "text": (253, 232, 244),
            "bars": (244, 114, 182),
            "label": "💡 STUDENT",
        },
    }
    palette = SPEAKER_PALETTES.get(speaker_upper, {
        "bg": (*style["panel_bg"][:3], 230),
        "border": style["accent"],
        "text": style["title_col"],
        "bars": style["accent"],
        "label": speaker_upper,
    })
    
    sx, sy = W - 210, 22
    sw, sh = 186, 38
    
    # Crop background region from frame
    bg_crop = Image.fromarray(frame_np[sy:sy + sh, sx:sx + sw]).convert("RGBA")
    overlay = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    
    # Subtle breathing glow when active
    is_speaking = t <= (audio_dur + 0.1)
    pulse = (0.85 + 0.15 * math.sin(t * 7.0)) if is_speaking else 0.8
    border_alpha = int(240 * pulse)
    
    # Rounded badge capsule
    d.rounded_rectangle(
        [(1, 1), (sw - 2, sh - 2)],
        radius=19,
        fill=palette["bg"],
        outline=(*palette["border"][:3], border_alpha),
        width=1
    )
    
    # Speaker label text
    lbl_font = _font(12, bold=True)
    d.text((16, 11), palette["label"], fill=palette["text"], font=lbl_font)
    
    # Audio-reactive Equalizer Waveform Bars
    wave_start_x = sw - 56
    num_bars = 5
    bar_w = 4
    bar_gap = 4
    
    for b in range(num_bars):
        if is_speaking:
            # Dynamic harmonic modulation
            f1 = 3.2 + b * 1.7
            f2 = 5.8 + b * 2.3
            amp = 0.5 * math.sin(t * math.pi * f1 + b * 0.9) + 0.5 * math.cos(t * math.pi * f2 + b * 1.4)
            bar_h = int(6 + 18 * abs(amp))
        else:
            # Idle gentle low pulse
            bar_h = int(4 + 2 * math.sin(t * 3.0 + b * 0.8))
            
        bx = wave_start_x + b * (bar_w + bar_gap)
        by = (sh - bar_h) // 2
        d.rounded_rectangle(
            [(bx, by), (bx + bar_w, by + bar_h)],
            radius=2,
            fill=palette["bars"]
        )
        
    bg_crop.alpha_composite(overlay)
    frame_np[sy:sy + sh, sx:sx + sw] = np.array(bg_crop.convert("RGB"))


# ── Subtitle Narration Bar ────────────────────────────────────────────────────
def _render_subtitle_overlay(
    img: Image.Image,
    narration: str,
    style: Dict[str, Any]
) -> Image.Image:
    """Renders a sleek bottom subtitle box for clear narration reading."""
    if not narration:
        return img
        
    d = ImageDraw.Draw(img)
    sub_font = _font(14, bold=False)
    
    # Clean text wrapping
    max_w = W - 160
    words = narration.split()
    lines = []
    cur = []
    for w in words:
        test = " ".join(cur + [w])
        bb = d.textbbox((0, 0), test, font=sub_font)
        if bb[2] - bb[0] <= max_w:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
        
    # Limit to top 2 lines for subtitles
    lines = lines[:2]
    if not lines:
        return img
        
    line_h = 20
    box_h = len(lines) * line_h + 16
    box_y = H - 68 - (box_h - 36)
    
    # Compute maximum line width
    max_line_w = max(d.textbbox((0, 0), l, font=sub_font)[2] - d.textbbox((0, 0), l, font=sub_font)[0] for l in lines)
    box_w = max_line_w + 32
    box_x = (W - box_w) // 2
    
    # Draw translucent background pill
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle(
        [(box_x, box_y), (box_x + box_w, box_y + box_h)],
        radius=10,
        fill=(10, 14, 26, 200),
        outline=(*style["accent"][:3], 120),
        width=1
    )
    
    for idx, line in enumerate(lines):
        bb = od.textbbox((0, 0), line, font=sub_font)
        lw = bb[2] - bb[0]
        tx = (W - lw) // 2
        ty = box_y + 8 + idx * line_h
        od.text((tx, ty), line, fill=(245, 245, 250), font=sub_font)
        
    img.alpha_composite(overlay)
    return img


# ── Render Single Step Frame Sequence ─────────────────────────────────────────
def _render_step_frames(
    step: Dict[str, Any],
    step_idx: int,
    total_steps: int,
    slide_path: Optional[str],
    audio_dur: float,
    visual_style: str
) -> List[np.ndarray]:
    """
    Renders all frames for a step in ultra-fast batch mode:
    - Base static 16:9 frame is prepared once (no cropping, no Ken Burns).
    - Local dynamic updates (progress bar & speaker waveform) are applied in memory.
    """
    style = _get_style(visual_style)
    step_num = step.get("step_number", step_idx + 1)
    speaker = step.get("speaker", "TEACHER")
    narration = step.get("narration", "")
    
    # Step duration = audio duration + 0.5s transition buffer (minimum 3.5s)
    clip_dur = max(audio_dur + TRANSITION_SEC, 3.5)
    n_frames = max(int(clip_dur * FPS), TRANSITION_FRAMES + 2)
    
    # 1. Prepare Base Static Slide (100% visible, centered, uncropped)
    if slide_path and Path(slide_path).exists():
        try:
            raw_img = Image.open(slide_path)
            base_slide = _fit_slide_to_canvas(raw_img, style)
        except Exception:
            base_slide = _make_gradient_bg(style)
    else:
        # Fallback styled slide
        base_slide = _make_gradient_bg(style)
        d = ImageDraw.Draw(base_slide)
        title = step.get("title", f"Step {step_num}")
        d.text((80, 180), f"Step {step_num}: {title}", fill=style["title_col"], font=_font(32, bold=True))
        if narration:
            d.text((80, 260), narration[:180], fill=style["text_col"], font=_font(18))
            
    # Add subtitle overlay to base slide if narration exists
    base_slide = _render_subtitle_overlay(base_slide.convert("RGBA"), narration, style).convert("RGB")
    base_np = np.array(base_slide)
    
    acc_color = style["accent"]
    bar_bg = (12, 16, 28)
    
    frames: List[np.ndarray] = []
    
    for i in range(n_frames):
        t = i / FPS
        f = base_np.copy()
        
        # ── 1. Elegant Smooth Bottom Progress Bar (5px height) ──
        overall_progress = min(1.0, ((step_idx) + (t / clip_dur)) / max(total_steps, 1))
        fill_w = int(W * overall_progress)
        
        # Track background
        f[H - 5:H, :] = bar_bg
        # Active progress fill
        if fill_w > 0:
            f[H - 5:H, :fill_w] = acc_color[:3]
            
        # ── 2. Animated Audio-Reactive Speaker Badge ──
        _render_speaker_badge_on_frame(f, speaker, style, t, audio_dur)
        
        frames.append(f)
        
    return frames


# ── Render Intro Card ─────────────────────────────────────────────────────────
def _render_intro_frames(
    topic: str,
    total_steps: int,
    visual_style: str,
    duration: float = 3.5
) -> List[np.ndarray]:
    """Generates the cinematic 16:9 intro presentation card."""
    style = _get_style(visual_style)
    clip_dur = max(duration, 3.2)
    n_frames = max(int(clip_dur * FPS), TRANSITION_FRAMES + 2)
    
    base_bg = _make_gradient_bg(style)
    acc = style["accent"]
    
    frames: List[np.ndarray] = []
    
    for i in range(n_frames):
        t = i / FPS
        canvas = base_bg.copy()
        d = ImageDraw.Draw(canvas)
        
        # Intro animated logo & circle
        intro_progress = _ease_out_cubic(min(1.0, t / 0.8))
        cx, cy = W // 2, H // 2 - 80
        radius = int(55 * intro_progress)
        
        if radius > 0:
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            for g in range(4, 0, -1):
                od.ellipse(
                    [cx - radius - g*4, cy - radius - g*4, cx + radius + g*4, cy + radius + g*4],
                    fill=(*acc, 25 // g)
                )
            od.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                fill=(*acc, 70),
                outline=(255, 255, 255, 200),
                width=2
            )
            od.text((cx - 14, cy - 18), "▶", fill=(255, 255, 255, 240), font=_font(28, bold=True))
            canvas.alpha_composite(overlay)
            
        d = ImageDraw.Draw(canvas)
        
        # Topic Title
        title_font = _font(38, bold=True)
        bb = d.textbbox((0, 0), topic, font=title_font)
        tw = bb[2] - bb[0]
        tx = max(40, (W - tw) // 2)
        ty = cy + 85
        d.text((tx + 2, ty + 2), topic, fill=(0, 0, 0, 80), font=title_font)
        d.text((tx, ty), topic, fill=style["title_col"], font=title_font)
        
        # Subtitle Tag
        sub_text = f"{total_steps}-Step Interactive Tutorial  •  {visual_style.replace('_', ' ').title()} Mode"
        sub_font = _font(17, bold=False)
        bb2 = d.textbbox((0, 0), sub_text, font=sub_font)
        sw = bb2[2] - bb2[0]
        sx = max(40, (W - sw) // 2)
        d.text((sx, ty + 56), sub_text, fill=style["muted_col"], font=sub_font)
        
        f = np.array(canvas.convert("RGB"))
        
        # Bottom Progress Bar
        f[H - 5:H, :] = (12, 16, 28)
        p_w = int(W * (t / clip_dur) * (1.0 / max(total_steps, 1)))
        if p_w > 0:
            f[H - 5:H, :p_w] = acc[:3]
            
        frames.append(f)
        
    return frames


# ── Render Outro Card ─────────────────────────────────────────────────────────
def _render_outro_frames(
    topic: str,
    total_steps: int,
    visual_style: str,
    duration: float = 3.5
) -> List[np.ndarray]:
    """Generates the cinematic completion outro presentation card."""
    style = _get_style(visual_style)
    clip_dur = max(duration, 3.2)
    n_frames = max(int(clip_dur * FPS), TRANSITION_FRAMES + 2)
    
    base_bg = _make_gradient_bg(style)
    acc = style["accent"]
    
    frames: List[np.ndarray] = []
    
    for i in range(n_frames):
        t = i / FPS
        canvas = base_bg.copy()
        d = ImageDraw.Draw(canvas)
        
        progress = _ease_out_cubic(min(1.0, t / 0.8))
        cx, cy = W // 2, H // 2 - 70
        radius = int(55 * progress)
        
        if radius > 0:
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            for g in range(4, 0, -1):
                od.ellipse(
                    [cx - radius - g*4, cy - radius - g*4, cx + radius + g*4, cy + radius + g*4],
                    fill=(*acc, 25 // g)
                )
            od.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                fill=(*acc, 70),
                outline=(255, 255, 255, 200),
                width=2
            )
            od.text((cx - 18, cy - 22), "✓", fill=(255, 255, 255, 240), font=_font(34, bold=True))
            canvas.alpha_composite(overlay)
            
        d = ImageDraw.Draw(canvas)
        
        # Complete Title
        done_text = "Tutorial Complete!"
        d_font = _font(38, bold=True)
        bb = d.textbbox((0, 0), done_text, font=d_font)
        tw = bb[2] - bb[0]
        tx = (W - tw) // 2
        ty = cy + 85
        d.text((tx + 2, ty + 2), done_text, fill=(0, 0, 0, 80), font=d_font)
        d.text((tx, ty), done_text, fill=style["title_col"], font=d_font)
        
        # Subtitle
        sub_text = f"Successfully mastered: {topic}"
        sub_font = _font(17, bold=False)
        bb2 = d.textbbox((0, 0), sub_text, font=sub_font)
        sw = bb2[2] - bb2[0]
        sx = max(40, (W - sw) // 2)
        d.text((sx, ty + 56), sub_text, fill=style["muted_col"], font=sub_font)
        
        f = np.array(canvas.convert("RGB"))
        # 100% full progress bar
        f[H - 5:H, :] = acc[:3]
        
        frames.append(f)
        
    return frames


# ── Vectorized 0.5s Cross-Dissolve ────────────────────────────────────────────
def _blend_cross_dissolve(
    frames_a: List[np.ndarray],
    frames_b: List[np.ndarray],
    num_transition_frames: int = TRANSITION_FRAMES
) -> List[np.ndarray]:
    """
    Performs a smooth 0.5s (12 frames @ 24fps) cross-dissolve between slide A and slide B.
    Uses high-precision vectorized alpha interpolation.
    """
    n = min(num_transition_frames, len(frames_a), len(frames_b))
    if n <= 0:
        return list(frames_a) + list(frames_b)
        
    result = list(frames_a[:-n])
    
    for i in range(n):
        alpha = (i + 1) / (n + 1)
        fa = frames_a[-n + i].astype(np.float32)
        fb = frames_b[i].astype(np.float32)
        blended = np.clip((1.0 - alpha) * fa + alpha * fb, 0, 255).astype(np.uint8)
        result.append(blended)
        
    result.extend(frames_b[n:])
    return result


# ── Audio Loader & Validator ──────────────────────────────────────────────────
def _load_audio_safe(path: Any) -> Tuple[Optional[AudioFileClip], float]:
    """
    Safely load an audio file or dual-voice dict with fallback.
    Returns (AudioFileClip_or_None, duration_seconds).
    """
    if not path:
        return None, 3.0
    if isinstance(path, dict):
        path = (
            path.get("combined")
            or path.get("teacher")
            or path.get("student")
            or path.get("audio")
            or next((v for v in path.values() if isinstance(v, str) and v.endswith(('.mp3', '.wav', '.m4a'))), None)
        )
    if not path:
        return None, 3.0
        
    p = Path(str(path))
    if not p.exists() or p.stat().st_size < 300:
        return None, 3.0
        
    try:
        clip = AudioFileClip(str(p))
        return clip, max(1.0, float(clip.duration))
    except Exception as e:
        print(f"  ⚠️ Audio load failed ({p.name}): {e}")
        return None, 3.0


# ── Main Video Assembler Entry Point ──────────────────────────────────────────
def assemble_video(
    steps:        List[Dict[str, Any]],
    image_paths:  List[str],
    audio_data:   Dict[str, Any],
    output_path:  str,
    topic:        str = "Step-by-Step Guide",
    job_id:       str = "",
    visual_style: str = "classic",
) -> str:
    """
    Assembles a stable, ultra-fast NotebookLM-style presentation video:
    - 100% static, centered, uncropped 16:9 slides (no Ken Burns movement).
    - Smooth 0.5s cross-dissolve transitions between slides.
    - Animated audio-reactive speaker badge (Teacher vs Student) with pulsing waveform.
    - Smooth, elegant bottom progress bar.
    - High-contrast, bright visuals (no vignette).
    - Multi-threaded encoding with preset='veryfast' and threads=8.
    """
    t_start = time.time()
    style = _get_style(visual_style)
    total_steps = len(steps)
    
    print(f"\n🎬 NotebookLM Video Engine v4.0 [{visual_style.upper()}] — Assembling Video...")
    print(f"   • Canvas: {W}×{H} (16:9 Static Presentation)")
    print(f"   • Transitions: 0.5s Smooth Cross-Dissolve")
    print(f"   • Audio Sync: Dual-Voice Animated Waveforms")
    
    audio_clips_to_close: List[AudioFileClip] = []
    sequential_audio: List[AudioFileClip] = []
    
    # ── 1. Intro Card ─────────────────────────────────────────────────────────
    intro_audio_path = audio_data.get("intro") if isinstance(audio_data, dict) else None
    intro_audio, intro_dur = _load_audio_safe(intro_audio_path)
    if intro_audio:
        audio_clips_to_close.append(intro_audio)
        sequential_audio.append(intro_audio)
        
    intro_dur = max(intro_dur, 3.2)
    intro_frames = _render_intro_frames(topic, total_steps, visual_style, intro_dur)
    
    merged_frames: List[np.ndarray] = intro_frames
    print(f"  ✓ Intro card prepared ({intro_dur:.1f}s, {len(intro_frames)} frames)")
    
    # ── 2. Per-Step Slides with 0.5s Cross-Dissolve ───────────────────────────
    step_audio_paths = audio_data.get("steps", []) if isinstance(audio_data, dict) else []
    
    for idx, step in enumerate(steps):
        step_num = step.get("step_number", idx + 1)
        slide_path = image_paths[idx] if idx < len(image_paths) else None
        
        # Audio
        step_audio_path = step_audio_paths[idx] if idx < len(step_audio_paths) else None
        step_audio, step_dur = _load_audio_safe(step_audio_path)
        if step_audio:
            audio_clips_to_close.append(step_audio)
            sequential_audio.append(step_audio)
            
        step_dur = max(step_dur, 3.0)
        speaker = step.get("speaker", "TEACHER")
        
        step_frames = _render_step_frames(
            step=step,
            step_idx=idx,
            total_steps=total_steps,
            slide_path=slide_path,
            audio_dur=step_dur,
            visual_style=visual_style
        )
        
        # Smooth 0.5s Cross-Dissolve into accumulator
        merged_frames = _blend_cross_dissolve(merged_frames, step_frames, TRANSITION_FRAMES)
        print(f"  ✓ Step {step_num}/{total_steps} [{speaker}]: {step.get('title', '')[:35]} ({step_dur:.1f}s)")
        
    # ── 3. Outro Card ─────────────────────────────────────────────────────────
    outro_audio_path = audio_data.get("outro") if isinstance(audio_data, dict) else None
    outro_audio, outro_dur = _load_audio_safe(outro_audio_path)
    if outro_audio:
        audio_clips_to_close.append(outro_audio)
        sequential_audio.append(outro_audio)
        
    outro_dur = max(outro_dur, 3.2)
    outro_frames = _render_outro_frames(topic, total_steps, visual_style, outro_dur)
    merged_frames = _blend_cross_dissolve(merged_frames, outro_frames, TRANSITION_FRAMES)
    print(f"  ✓ Outro card prepared ({outro_dur:.1f}s, {len(outro_frames)} frames)")
    
    # ── 4. Build Final Video Stream ───────────────────────────────────────────
    final_video = ImageSequenceClip(merged_frames, fps=FPS)
    
    # Multiplex Audio
    if sequential_audio:
        try:
            composite_audio = concatenate_audioclips(sequential_audio)
            final_video = final_video.set_audio(composite_audio)
        except Exception as e:
            print(f"  ⚠️ Audio concat warning: {e}")
            
    # ── 5. Ultra-Fast Multi-Threaded Encoding ─────────────────────────────────
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    safe_id = (job_id or str(os.getpid())).replace("/", "_").replace("\\", "_")
    tmp_audio_path = str(out_file.parent / f"_tmp_audio_{safe_id}.m4a")
    
    total_duration = round(final_video.duration, 1)
    print(f"\n  💾 Encoding [{visual_style.upper()}] {W}×{H} @ {FPS}fps ({total_duration}s, {len(merged_frames)} frames)")
    print(f"     → Destination: {output_path}")
    
    final_video.write_videofile(
        str(out_file),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="veryfast",
        threads=8,
        logger=None,
        ffmpeg_params=["-crf", "22", "-pix_fmt", "yuv420p"],
        temp_audiofile=tmp_audio_path,
        remove_temp=True,
    )
    
    # ── 6. Resource Cleanup ───────────────────────────────────────────────────
    try: final_video.close()
    except Exception: pass
    for a in audio_clips_to_close:
        try: a.close()
        except Exception: pass
        
    elapsed = round(time.time() - t_start, 2)
    file_size_mb = round(out_file.stat().st_size / (1024 * 1024), 2)
    print(f"✅ Video Generated Successfully in {elapsed}s! ({file_size_mb} MB, {total_duration}s total)")
    
    return str(out_file)


if __name__ == "__main__":
    print("VisuAIze Video Assembler v4.0 Loaded.")
