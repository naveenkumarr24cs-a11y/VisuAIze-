"""
VisuAIze - NotebookLM-Quality Visual Presentation Slide Generator v3.0
========================================================================
Composes clean, static 16:9 widescreen presentation slides (1280x720):

  • Left 58% (742px): Full-height, crisp AI visual artwork with subtle right-edge blend into background.
  • Right 42% (538px): Beautiful frosted glass teaching panel featuring:
      - Arc Phase & Step Tag badge (e.g. 'STEP 1 OF 4 • ANALOGY BRIDGE')
      - Bold, legible concept title
      - Teacher & Student dialogue cards with distinct color-coded speaker badges and audio waveform indicators
      - Key Concept insight box
  • Professional typography, high contrast, crisp styling, and zero text cutoff.
"""

import math
import os
import random
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
import sys
import re
from typing import Optional, Dict, Any, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
if hasattr(sys.stderr, "reconfigure"):
    try: sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ── Canvas Dimensions ─────────────────────────────────────────────────────────
W, H    = 1280, 720
SPLIT_X = 742  # Exact 58% of 1280px

# ── Arc Phase Styling ─────────────────────────────────────────────────────────
ARC_PHASES = {
    "problem": {
        "title": "PROBLEM HOOK",
        "color": (239, 68, 68),       # Crimson / Coral
        "bg_tint": (239, 68, 68, 30),
        "tag": "DIAGNOSTIC FOCUS"
    },
    "analogy": {
        "title": "ANALOGY BRIDGE",
        "color": (245, 158, 11),      # Amber / Warm Gold
        "bg_tint": (245, 158, 11, 30),
        "tag": "CONCEPTUAL METAPHOR"
    },
    "solution": {
        "title": "SOLUTION BREAKTHROUGH",
        "color": (16, 185, 129),      # Emerald Green
        "bg_tint": (16, 185, 129, 30),
        "tag": "CORE MECHANISM"
    },
    "deep_dive": {
        "title": "DEEP DIVE ANALYSIS",
        "color": (99, 102, 241),      # Indigo
        "bg_tint": (99, 102, 241, 30),
        "tag": "SYSTEMIC ARCHITECTURE"
    }
}

# ── Visual Style Themes ───────────────────────────────────────────────────────
STYLE_DEFS = {
    "classic": {
        "bg_top":       (6, 9, 20),
        "bg_btm":       (12, 16, 36),
        "panel_bg":     (11, 15, 32, 235),
        "panel_border": (99, 102, 241, 70),
        "accent":       (99, 102, 241),
        "title_c":      (255, 255, 255),
        "body_c":       (226, 232, 240),
        "muted_c":      (148, 163, 184),
        "card_teacher": (79, 70, 229, 28),
        "card_student": (236, 72, 153, 28),
        "insight_bg":   (15, 23, 42, 240),
        "is_dark":      True,
    },
    "whiteboard": {
        "bg_top":       (250, 252, 255),
        "bg_btm":       (240, 244, 250),
        "panel_bg":     (255, 255, 255, 242),
        "panel_border": (37, 99, 235, 50),
        "accent":       (37, 99, 235),
        "title_c":      (15, 23, 42),
        "body_c":       (30, 41, 59),
        "muted_c":      (100, 116, 139),
        "card_teacher": (37, 99, 235, 18),
        "card_student": (225, 29, 72, 18),
        "insight_bg":   (241, 245, 249, 245),
        "is_dark":      False,
    },
    "kawaii": {
        "bg_top":       (255, 235, 248),
        "bg_btm":       (245, 220, 255),
        "panel_bg":     (255, 245, 253, 240),
        "panel_border": (236, 72, 153, 60),
        "accent":       (236, 72, 153),
        "title_c":      (88, 28, 135),
        "body_c":       (107, 33, 168),
        "muted_c":      (167, 139, 250),
        "card_teacher": (124, 58, 237, 20),
        "card_student": (236, 72, 153, 22),
        "insight_bg":   (250, 232, 255, 245),
        "is_dark":      False,
    },
    "watercolor": {
        "bg_top":       (225, 238, 255),
        "bg_btm":       (210, 228, 250),
        "panel_bg":     (240, 248, 255, 235),
        "panel_border": (37, 99, 235, 55),
        "accent":       (37, 99, 235),
        "title_c":      (23, 37, 84),
        "body_c":       (30, 58, 138),
        "muted_c":      (99, 140, 200),
        "card_teacher": (37, 99, 235, 20),
        "card_student": (13, 148, 136, 20),
        "insight_bg":   (225, 240, 255, 245),
        "is_dark":      False,
    },
    "papercraft": {
        "bg_top":       (255, 248, 230),
        "bg_btm":       (250, 238, 215),
        "panel_bg":     (255, 250, 238, 240),
        "panel_border": (217, 119, 6, 50),
        "accent":       (217, 119, 6),
        "title_c":      (92, 45, 2),
        "body_c":       (109, 60, 5),
        "muted_c":      (180, 140, 80),
        "card_teacher": (217, 119, 6, 20),
        "card_student": (180, 83, 9, 20),
        "insight_bg":   (254, 243, 199, 245),
        "is_dark":      False,
    },
    "retro": {
        "bg_top":       (38, 28, 48),
        "bg_btm":       (60, 34, 54),
        "panel_bg":     (45, 30, 50, 240),
        "panel_border": (244, 63, 94, 60),
        "accent":       (244, 63, 94),
        "title_c":      (255, 241, 242),
        "body_c":       (254, 205, 211),
        "muted_c":      (225, 145, 160),
        "card_teacher": (244, 63, 94, 25),
        "card_student": (251, 146, 60, 25),
        "insight_bg":   (55, 32, 58, 245),
        "is_dark":      True,
    },
    "heritage": {
        "bg_top":       (24, 18, 12),
        "bg_btm":       (38, 26, 16),
        "panel_bg":     (30, 22, 14, 240),
        "panel_border": (212, 175, 55, 60),
        "accent":       (212, 175, 55),
        "title_c":      (255, 245, 220),
        "body_c":       (240, 220, 180),
        "muted_c":      (185, 160, 120),
        "card_teacher": (212, 175, 55, 25),
        "card_student": (180, 120, 60, 25),
        "insight_bg":   (38, 28, 18, 245),
        "is_dark":      True,
    }
}

def _get_style(name: str) -> dict:
    return STYLE_DEFS.get(name.lower(), STYLE_DEFS["classic"])

# ── Font Loading ──────────────────────────────────────────────────────────────
_FONT_CACHE = {}

def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    
    BOLD_FONTS = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "/System/Library/Fonts/HelveticaNeue-Bold.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    NORM_FONTS = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/System/Library/Fonts/HelveticaNeue.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    
    for p in (BOLD_FONTS if bold else NORM_FONTS):
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, size)
                _FONT_CACHE[key] = f
                return f
            except Exception:
                pass
    
    try:
        f = ImageFont.load_default()
    except Exception:
        f = None
    _FONT_CACHE[key] = f
    return f


def _wrap(text: str, font: ImageFont.ImageFont, max_w: int, draw: ImageDraw.ImageDraw) -> List[str]:
    if not text:
        return []
    words = text.split()
    lines = []
    curr = []
    for w in words:
        test = " ".join(curr + [w])
        bb = draw.textbbox((0, 0), test, font=font)
        if (bb[2] - bb[0]) <= max_w:
            curr.append(w)
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))
    return lines


# ── AI Visual Retrieval ───────────────────────────────────────────────────────
def _fetch_ai_image(prompt: str, style: str = "classic", arc_phase: str = "solution") -> Image.Image:
    """Fetch AI image via nano_banana_engine with high-fidelity fallback."""
    try:
        import nano_banana_engine
        img = nano_banana_engine.generate_nano_banana_image(
            step_title=prompt[:60],
            visual_desc=prompt,
            style_name=style,
            arc_phase=arc_phase,
            width=SPLIT_X,
            height=H,
            timeout=20
        )
        if img:
            return img.convert("RGBA").resize((SPLIT_X, H), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"[ImageGenerator] NanoBanana engine notice: {e}")

    # Direct fallback to offline procedural blueprint
    import nano_banana_engine
    return nano_banana_engine.generate_procedural_scene(
        step_title=prompt[:60],
        visual_desc=prompt,
        style_name=style,
        arc_phase=arc_phase,
        width=SPLIT_X,
        height=H
    ).convert("RGBA")


# ── Background Gradient ───────────────────────────────────────────────────────
def _make_gradient(style_def: dict, width: int = W, height: int = H) -> Image.Image:
    img = Image.new("RGBA", (width, height))
    d = ImageDraw.Draw(img)
    tc, bc = style_def["bg_top"], style_def["bg_btm"]
    for y in range(height):
        t = y / max(1, height)
        r = int(tc[0] + (bc[0] - tc[0]) * t)
        g = int(tc[1] + (bc[1] - tc[1]) * t)
        b = int(tc[2] + (bc[2] - tc[2]) * t)
        d.line([(0, y), (width, y)], fill=(r, g, b, 255))
    return img


# ── Audio Waveform Drawing ────────────────────────────────────────────────────
def _draw_waveform(draw: ImageDraw.ImageDraw, x: int, y: int, color: Tuple[int, int, int], is_teacher: bool = True):
    """Draws a crisp, lively 7-bar audio waveform EQ indicator."""
    if is_teacher:
        bar_heights = [5, 12, 17, 9, 15, 11, 6]
    else:
        bar_heights = [6, 14, 8, 16, 12, 15, 7]
        
    bar_width = 3
    spacing = 3
    for i, h in enumerate(bar_heights):
        bx = x + i * (bar_width + spacing)
        by = y - h // 2
        draw.rounded_rectangle([(bx, by), (bx + bar_width, by + h)], radius=2, fill=(*color, 240))


# ── Frosted Glass Teaching Panel ──────────────────────────────────────────────
def _draw_frosted_panel(canvas: Image.Image, x: int, y: int, w: int, h: int, style_def: dict, radius: int = 16):
    """Draws a multi-layer frosted glass teaching panel with soft depth & specular border."""
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    panel_bg = style_def["panel_bg"]

    # Soft ambient drop shadow
    for i in range(6, 0, -1):
        shadow_alpha = 36 - i * 5
        if shadow_alpha > 0:
            od.rounded_rectangle(
                [(x + i, y + i), (x + w + i, y + h + i)],
                radius=radius + 2,
                fill=(0, 0, 0, shadow_alpha)
            )

    # Panel Body
    od.rounded_rectangle([(x, y), (x + w, y + h)], radius=radius, fill=panel_bg)

    # Glass Outer Border
    border_c = style_def.get("panel_border", (99, 102, 241, 60))
    od.rounded_rectangle([(x, y), (x + w, y + h)], radius=radius, outline=border_c, width=1)

    # Top Specular Highlight line
    od.rounded_rectangle([(x + 2, y + 2), (x + w - 2, y + 24)], radius=radius, fill=(255, 255, 255, 14))

    canvas.alpha_composite(overlay)


# ── Arc Phase & Step Tag Badge ────────────────────────────────────────────────
def _draw_step_tag_badge(
    canvas: Image.Image,
    step_num: int,
    total_steps: int,
    arc_phase: str,
    style_def: dict,
    x: int,
    y: int
) -> int:
    """
    Renders the modern NotebookLM-style step badge:
    e.g. 'STEP 1 OF 4 • ANALOGY BRIDGE' with glowing accent pill container.
    Returns the bottom Y coordinate.
    """
    phase_info = ARC_PHASES.get(arc_phase.lower(), ARC_PHASES["solution"])
    phase_title = phase_info["title"]
    phase_color = phase_info["color"]

    badge_text = f"STEP {step_num} OF {total_steps} • {phase_title}"
    badge_font = _font(11, bold=True)

    d = ImageDraw.Draw(canvas)
    bb = d.textbbox((0, 0), badge_text, font=badge_font)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]

    pad_x = 12
    pad_y = 6
    pill_w = tw + pad_x * 2
    pill_h = th + pad_y * 2

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # Glow
    for g in range(3, 0, -1):
        od.rounded_rectangle(
            [(x - g, y - g), (x + pill_w + g, y + pill_h + g)],
            radius=pill_h // 2 + g,
            outline=(*phase_color, 25 // g),
            width=1
        )

    # Background
    od.rounded_rectangle(
        [(x, y), (x + pill_w, y + pill_h)],
        radius=pill_h // 2,
        fill=(*phase_color, 35)
    )
    # Border
    od.rounded_rectangle(
        [(x, y), (x + pill_w, y + pill_h)],
        radius=pill_h // 2,
        outline=(*phase_color, 180),
        width=1
    )

    canvas.alpha_composite(overlay)

    # Text
    td = ImageDraw.Draw(canvas)
    td.text((x + pad_x, y + pad_y - 1), badge_text, fill=(*phase_color, 255), font=badge_font)

    return y + pill_h


# ── Dialogue Card ─────────────────────────────────────────────────────────────
def _draw_dialogue_card(
    canvas: Image.Image,
    speaker: str,
    dialogue_text: str,
    x: int,
    y: int,
    w: int,
    style_def: dict,
    is_teacher: bool = True
) -> int:
    """
    Renders a Teacher or Student dialogue card with distinct color-coded speaker badge,
    audio waveform indicator, and high-contrast dialogue typography.
    Returns the bottom Y coordinate.
    """
    if is_teacher:
        speaker_label = "TEACHER"
        accent_color = (99, 102, 241)     # Indigo / Electric Blue
        card_bg = style_def["card_teacher"]
    else:
        speaker_label = "STUDENT"
        accent_color = (236, 72, 153)    # Rose / Hot Pink
        card_bg = style_def["card_student"]

    font_badge = _font(10, bold=True)
    font_text  = _font(13, bold=False)

    d = ImageDraw.Draw(canvas)

    text_content = f'"{dialogue_text.strip()}"'
    lines = _wrap(text_content, font_text, w - 28, d)
    if len(lines) > 3:
        lines = lines[:2] + [lines[2][:len(lines[2])-3] + "..."]

    line_h = 18
    text_block_h = len(lines) * line_h
    card_h = 32 + text_block_h + 12

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # Card background & border
    od.rounded_rectangle([(x, y), (x + w, y + card_h)], radius=10, fill=card_bg)
    od.rounded_rectangle([(x, y), (x + w, y + card_h)], radius=10, outline=(*accent_color, 110), width=1)
    
    # Left accent indicator bar
    od.rounded_rectangle([(x, y + 4), (x + 4, y + card_h - 4)], radius=2, fill=(*accent_color, 240))

    # Speaker Pill Badge
    bb = od.textbbox((0, 0), speaker_label, font=font_badge)
    badge_w = (bb[2] - bb[0]) + 14
    badge_h = 18
    badge_x = x + 14
    badge_y = y + 8
    od.rounded_rectangle([(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)], radius=5, fill=(*accent_color, 45))
    od.rounded_rectangle([(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)], radius=5, outline=(*accent_color, 160), width=1)

    canvas.alpha_composite(overlay)

    td = ImageDraw.Draw(canvas)
    td.text((badge_x + 7, badge_y + 2), speaker_label, fill=(*accent_color, 255), font=font_badge)

    # Active Audio Waveform Indicator
    waveform_x = x + w - 54
    waveform_y = y + 17
    _draw_waveform(td, waveform_x, waveform_y, accent_color, is_teacher=is_teacher)

    # Dialogue Lines
    ty = y + 34
    body_color = style_def["body_c"]
    for ln in lines:
        td.text((x + 14, ty), ln, fill=body_color, font=font_text)
        ty += line_h

    return y + card_h


# ── Key Concept Insight Box ───────────────────────────────────────────────────
def _draw_key_concept_box(
    canvas: Image.Image,
    step: dict,
    x: int,
    y: int,
    w: int,
    max_h: int,
    style_def: dict,
    arc_phase: str
) -> int:
    """
    Renders an elegant Key Concept insight callout container at the bottom of the teaching panel.
    """
    phase_info = ARC_PHASES.get(arc_phase.lower(), ARC_PHASES["solution"])
    phase_color = phase_info["color"]

    components = step.get("components", [])
    narration = step.get("narration", "")
    
    insight_items = []
    if components and isinstance(components, list):
        for c in components[:2]:
            if isinstance(c, dict):
                c_name = c.get("name", "")
                c_desc = c.get("desc") or c.get("description", "")
                if c_name:
                    insight_items.append(f"{c_name}: {c_desc}" if c_desc else c_name)
            elif isinstance(c, str):
                insight_items.append(c)

    if not insight_items and narration:
        sentences = [s.strip() for s in narration.split(".") if len(s.strip()) > 10]
        if sentences:
            insight_items.append(sentences[-1])
        else:
            insight_items.append(narration[:120])

    box_h = min(max_h, 112)
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    od.rounded_rectangle([(x, y), (x + w, y + box_h)], radius=10, fill=style_def["insight_bg"])
    od.rounded_rectangle([(x, y), (x + w, y + box_h)], radius=10, outline=(*phase_color, 80), width=1)
    od.rounded_rectangle([(x, y + 4), (x + 4, y + box_h - 4)], radius=2, fill=(*phase_color, 240))
    
    canvas.alpha_composite(overlay)

    td = ImageDraw.Draw(canvas)
    header_font = _font(10, bold=True)
    body_font   = _font(12, bold=False)
    
    # Draw header with crisp vector diamond icon
    diamond_pts = [(x + 14, y + 16), (x + 19, y + 11), (x + 24, y + 16), (x + 19, y + 21)]
    td.polygon(diamond_pts, fill=phase_color)
    td.text((x + 30, y + 10), "KEY CONCEPT INSIGHT", fill=phase_color, font=header_font)

    cy = y + 32
    for item in insight_items[:2]:
        wrapped = _wrap(item, body_font, w - 42, td)
        for wl in wrapped[:2]:
            if cy > y + box_h - 18:
                break
            # Crisp vector circular bullet
            td.ellipse([x + 14, cy + 4, x + 20, cy + 10], fill=phase_color)
            td.text((x + 26, cy), wl, fill=style_def["body_c"], font=body_font)
            cy += 18
        cy += 4

    return y + box_h


# ── Main Slide Builder ────────────────────────────────────────────────────────
def build_cinematic_slide(
    step: dict,
    total: int,
    output_path: str,
    ai_image: Optional[Image.Image],
    topic: str,
    visual_style: str = "classic"
) -> str:
    """
    Composes a pristine, static 16:9 widescreen presentation slide (1280x720):
      • Left 58% (742px): Crisp AI visual artwork with smooth right-edge blend into background.
      • Right 42% (538px): Frosted glass teaching panel with Step Tag badge, Concept Title,
        Teacher/Student dialogue cards with audio waveforms, and Key Concept insight box.
    """
    style_def = _get_style(visual_style)
    n         = step.get("step_number", 1)
    title     = step.get("title", f"Step {n}")
    narration = step.get("narration", "")
    arc_phase = step.get("arc_phase", "solution")
    teacher   = step.get("teacher_line", "").strip()
    student   = step.get("student_line", "").strip()

    # 1. Base Gradient Canvas (1280x720)
    canvas = _make_gradient(style_def)

    # 2. Left AI Visual Artwork (742px wide)
    if ai_image is not None:
        ai_img = ai_image.convert("RGBA").resize((SPLIT_X, H), Image.Resampling.LANCZOS)
        
        # Subtle right-edge alpha gradient blend (smoothly dissolves right 90px of AI image)
        blend_mask = Image.new("L", (SPLIT_X, H), 255)
        bmd = ImageDraw.Draw(blend_mask)
        blend_w = 90
        for i in range(blend_w):
            alpha = int(255 * (1.0 - (i / blend_w) ** 1.6))
            bmd.line([(SPLIT_X - blend_w + i, 0), (SPLIT_X - blend_w + i, H)], fill=alpha)
            
        ai_img.putalpha(blend_mask)
        canvas.alpha_composite(ai_img, (0, 0))

    # 3. Right Frosted Glass Teaching Panel
    panel_x = SPLIT_X - 10   # 732px
    panel_y = 16
    panel_w = W - panel_x - 16  # 520px
    panel_h = H - 32            # 688px

    _draw_frosted_panel(canvas, panel_x, panel_y, panel_w, panel_h, style_def, radius=16)

    # 4. Content within the Teaching Panel
    content_x = panel_x + 22
    content_w = panel_w - 44
    curr_y    = panel_y + 18

    # A. Arc Phase & Step Tag Badge (e.g. 'STEP 1 OF 4 • ANALOGY BRIDGE')
    curr_y = _draw_step_tag_badge(
        canvas=canvas,
        step_num=n,
        total_steps=total,
        arc_phase=arc_phase,
        style_def=style_def,
        x=content_x,
        y=curr_y
    )
    curr_y += 14

    # B. Bold, Legible Concept Title
    title_draw = ImageDraw.Draw(canvas)
    title_font = _font(22, bold=True)
    title_lines = _wrap(title, title_font, content_w, title_draw)
    
    for tl in title_lines[:2]:
        title_draw.text((content_x + 1, curr_y + 1), tl, fill=(0, 0, 0, 90), font=title_font)
        title_draw.text((content_x, curr_y), tl, fill=style_def["title_c"], font=title_font)
        curr_y += 28
    curr_y += 8

    # Subtle divider line
    title_draw.line([(content_x, curr_y), (content_x + content_w, curr_y)], fill=(*style_def["accent"], 40), width=1)
    curr_y += 14

    # C. Teacher & Student Dialogue Cards (or structured narration)
    if teacher or student:
        if teacher:
            curr_y = _draw_dialogue_card(
                canvas=canvas,
                speaker="Teacher",
                dialogue_text=teacher,
                x=content_x,
                y=curr_y,
                w=content_w,
                style_def=style_def,
                is_teacher=True
            )
            curr_y += 10

        if student and curr_y < H - 200:
            curr_y = _draw_dialogue_card(
                canvas=canvas,
                speaker="Student",
                dialogue_text=student,
                x=content_x,
                y=curr_y,
                w=content_w,
                style_def=style_def,
                is_teacher=False
            )
            curr_y += 12
    else:
        nar_draw = ImageDraw.Draw(canvas)
        nar_font = _font(13)
        nar_lines = _wrap(narration, nar_font, content_w, nar_draw)
        for nl in nar_lines[:6]:
            if curr_y > H - 180:
                break
            nar_draw.text((content_x, curr_y), nl, fill=style_def["body_c"], font=nar_font)
            curr_y += 20
        curr_y += 12

    # D. Key Concept Insight Box (Anchored at bottom of panel)
    insight_y = max(curr_y + 6, panel_y + panel_h - 128)
    _draw_key_concept_box(
        canvas=canvas,
        step=step,
        x=content_x,
        y=insight_y,
        w=content_w,
        max_h=panel_y + panel_h - insight_y - 12,
        style_def=style_def,
        arc_phase=arc_phase
    )

    # 5. Top Subtle Branding Bar
    bar_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bod = ImageDraw.Draw(bar_overlay)
    brand_main = (*style_def["title_c"][:3], 180)
    brand_sub  = (*style_def["muted_c"][:3], 140)
    bod.text((22, 14), "VisuAIze", fill=brand_main, font=_font(13, bold=True))
    bod.text((90, 14), "•", fill=brand_sub, font=_font(13))
    
    clean_topic = topic[:50] + "..." if len(topic) > 50 else topic
    bod.text((104, 14), clean_topic, fill=brand_sub, font=_font(12))
    canvas.alpha_composite(bar_overlay)

    # 6. Bottom Sleek Progress Line
    prog_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pod = ImageDraw.Draw(prog_overlay)
    prog_y = H - 4
    pod.rectangle([(0, prog_y), (W, H)], fill=(0, 0, 0, 120))
    fill_w = int(W * (n / max(1, total)))
    if fill_w > 0:
        phase_color = ARC_PHASES.get(arc_phase.lower(), ARC_PHASES["solution"])["color"]
        pod.rectangle([(0, prog_y), (fill_w, H)], fill=(*phase_color, 240))
    canvas.alpha_composite(prog_overlay)

    # 7. Save Output Image
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, "PNG", quality=95)
    return output_path


# ── AI Image Prompt Builder ───────────────────────────────────────────────────
def _build_image_prompt(step: dict, topic: str, visual_style: str) -> str:
    """Build an optimized visual prompt for AI image generation."""
    arc_phase = step.get("arc_phase", "solution")
    title     = step.get("title", "")
    motion_p  = step.get("motion_prompt") or step.get("image_prompt", "")

    if motion_p and len(motion_p) > 30:
        base = motion_p
    else:
        base = f"Detailed 3D scientific visualization of {title}, {topic}"

    style_suffix = {
        "classic":     "cinematic dark background, glowing neon highlights, 8k octane render",
        "whiteboard":  "clean educational blueprint diagram, precision linework, white background",
        "kawaii":      "modern anime style educational art, studio ghibli aesthetic, soft pastel colors",
        "watercolor":  "watercolor painting, beautiful fluid textures, expressive brushwork",
        "papercraft":  "layered 3D cut paper art, tactile volumetric lighting, depth and shadows",
        "retro":       "vintage 1960s scientific lithograph, retro risograph texture, halftone print",
        "heritage":    "classical oil painting, Leonardo da Vinci anatomical sketchbook style",
    }.get(visual_style.lower(), "cinematic educational visual, high fidelity")

    return f"{base}, {style_suffix}, masterpiece, no text overlay, no watermarks"


# ── Main Entry Point ──────────────────────────────────────────────────────────
def generate_all_images(
    steps: list,
    output_dir: str,
    topic: str = "",
    visual_style: str = "classic"
) -> list[str]:
    """
    Generates all presentation slides in parallel.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    total = len(steps)
    if total == 0:
        return []

    print(f"\n🎨 Generating {total} NotebookLM-quality [{visual_style.upper()}] presentation slides...")

    paths = [None] * total

    def _render_one(idx: int, step: dict):
        n = step.get("step_number", idx + 1)
        out_path = str(Path(output_dir) / f"step_{n:02d}.png")
        print(f"  🖼  Rendering slide {n}/{total}: {step.get('title', '')[:45]}...")

        img_prompt = _build_image_prompt(step, topic, visual_style)
        arc_phase  = step.get("arc_phase", "solution")

        # Fetch AI image
        ai_img = _fetch_ai_image(img_prompt, style=visual_style, arc_phase=arc_phase)

        # Build cinematic slide
        build_cinematic_slide(
            step=step,
            total=total,
            output_path=out_path,
            ai_image=ai_img,
            topic=topic,
            visual_style=visual_style
        )
        paths[idx] = out_path
        print(f"  ✓ Slide {n}/{total} ready")

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_render_one, i, step) for i, step in enumerate(steps)]
        for f in futures:
            try:
                f.result()
            except Exception as e:
                print(f"  ⚠️ Slide generation warning: {e}")

    valid_paths = [p for p in paths if p is not None and Path(p).exists()]
    print(f"✅ All {len(valid_paths)} [{visual_style.title()}] presentation slides ready!")
    return valid_paths
