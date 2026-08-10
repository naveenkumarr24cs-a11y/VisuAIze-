"""
VisuAIze - Cinematic Slide Generator v3.0
==========================================
Generates NotebookLM-quality visual slides using:

  • Full-frame AI-generated imagery (Pollinations Flux, 1280×720)
  • Per-style beautiful art rendering (Classic/Whiteboard/Kawaii/Watercolor etc.)
  • Large elegant text overlaid on the right panel — NOT a 50/50 split
  • Dynamic arc-phase color coding (Problem=red, Analogy=amber, Solution=green)
  • Multi-layer glass panel with blur, shadow and gradient
  • Professional typography with proper hierarchy (Title / Body / Muted)
  • Animated step number badge with arc phase color
  • Beautiful top bar with VisuAIze branding
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

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
if hasattr(sys.stderr, "reconfigure"):
    try: sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

try:
    import sora_animatediff_engine as sora_engine
    SORA_AVAILABLE = True
except ImportError:
    SORA_AVAILABLE = False

# ── Canvas dimensions ─────────────────────────────────────────────────────────
W, H    = 1280, 720
SPLIT_X = int(W * 0.58)   # 742px — AI visual left | text panel right

# ── Arc Phase Colors ──────────────────────────────────────────────────────────
ARC_COLORS = {
    "problem":  (239, 68,  68),
    "analogy":  (245, 158, 11),
    "solution": (34,  197, 94),
}

# ── Style Definitions ─────────────────────────────────────────────────────────
STYLE_DEFS = {
    "classic": {
        "bg_top":   (6,   8,  18),
        "bg_btm":   (14,  16, 36),
        "panel_bg": (12,  15, 30, 235),
        "accent":   (99,  102, 241),
        "title_c":  (255, 255, 255),
        "body_c":   (214, 218, 240),
        "muted_c":  (148, 163, 184),
        "border_c": (99,  102, 241, 60),
        "is_dark":  True,
    },
    "whiteboard": {
        "bg_top":   (252, 252, 250),
        "bg_btm":   (242, 242, 238),
        "panel_bg": (255, 255, 255, 238),
        "accent":   (30,  64, 175),
        "title_c":  (15,  23,  42),
        "body_c":   (30,  41,  59),
        "muted_c":  (100, 116, 139),
        "border_c": (30,  64, 175, 40),
        "is_dark":  False,
    },
    "kawaii": {
        "bg_top":   (255, 220, 248),
        "bg_btm":   (245, 208, 255),
        "panel_bg": (255, 230, 252, 230),
        "accent":   (236, 72,  153),
        "title_c":  (88,  28, 135),
        "body_c":   (107, 33, 168),
        "muted_c":  (167, 139, 250),
        "border_c": (236, 72, 153, 40),
        "is_dark":  False,
    },
    "watercolor": {
        "bg_top":   (215, 232, 255),
        "bg_btm":   (205, 225, 248),
        "panel_bg": (230, 242, 255, 220),
        "accent":   (37,  99, 235),
        "title_c":  (23,  37,  84),
        "body_c":   (30,  58, 138),
        "muted_c":  (99,  140, 200),
        "border_c": (59, 130, 246, 40),
        "is_dark":  False,
    },
    "papercraft": {
        "bg_top":   (255, 248, 226),
        "bg_btm":   (252, 238, 210),
        "panel_bg": (255, 248, 230, 228),
        "accent":   (217, 119,  6),
        "title_c":  (92,  45,   2),
        "body_c":   (109, 60,   5),
        "muted_c":  (180, 140, 80),
        "border_c": (217, 119, 6, 40),
        "is_dark":  False,
    },
    "retro_print": {
        "bg_top":   (248, 238, 218),
        "bg_btm":   (238, 228, 205),
        "panel_bg": (252, 244, 228, 228),
        "accent":   (180, 40,  40),
        "title_c":  (20,  10,   5),
        "body_c":   (40,  25,  15),
        "muted_c":  (150, 130, 100),
        "border_c": (180, 40, 40, 40),
        "is_dark":  False,
    },
    "heritage": {
        "bg_top":   (25,  15,   8),
        "bg_btm":   (42,  26,  10),
        "panel_bg": (35,  22,  10, 238),
        "accent":   (212, 175, 55),
        "title_c":  (255, 235, 180),
        "body_c":   (240, 215, 155),
        "muted_c":  (180, 155, 100),
        "border_c": (212, 175, 55, 60),
        "is_dark":  True,
    },
}

def _get_style(name: str) -> dict:
    return STYLE_DEFS.get(name, STYLE_DEFS["classic"])


# ── Font Loading ──────────────────────────────────────────────────────────────
_FONT_CACHE = {}

def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    BOLD = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf"]
    NORM = ["C:/Windows/Fonts/segoeui.ttf",  "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf"]
    for p in (BOLD if bold else NORM):
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
            if curr: lines.append(" ".join(curr))
            curr = [w]
    if curr: lines.append(" ".join(curr))
    return lines


# ── Image Fetching ────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}

STYLE_PROMPT_SUFFIXES = {
    "classic":    "cinematic digital art, dark background, glowing neon accents, 4K ultra detail",
    "whiteboard": "clean whiteboard illustration, hand-drawn marker sketch, educational diagram, clean white background",
    "kawaii":     "kawaii anime style, pastel colors, cute chibi characters, pink and purple, adorable",
    "watercolor": "watercolor painting, soft wash, beautiful brushstrokes, artistic, dreamy",
    "papercraft": "papercraft flat design, cut paper art, warm cream tones, layered depth",
    "retro_print": "vintage newspaper illustration, halftone print, 1950s educational poster, sepia tones",
    "heritage":   "classical oil painting, mahogany and gold, detailed Renaissance style, regal",
}

def _fetch_ai_image(prompt: str, style: str = "classic") -> Image.Image | None:
    """Fetch a full 1280×720 AI image from Pollinations with style-specific prompt."""
    suffix = STYLE_PROMPT_SUFFIXES.get(style, STYLE_PROMPT_SUFFIXES["classic"])
    full_prompt = f"{prompt}, {suffix}, no text, no watermark, photorealistic educational visual"

    # Try sora engine first (has its own retry logic)
    if SORA_AVAILABLE:
        try:
            step_mock = {"title": prompt, "motion_prompt": full_prompt}
            img = sora_engine.generate_cinematic_visual(prompt, step_mock)
            if img is not None:
                return img.resize((SPLIT_X, H), Image.LANCZOS)
        except Exception:
            pass

    # Direct Pollinations fetch
    clean_p = urllib.parse.quote(full_prompt[:350])
    seed = random.randint(100, 99999)

    urls = [
        f"https://image.pollinations.ai/prompt/{clean_p}?width={SPLIT_X}&height={H}&model=turbo&nologo=true&seed={seed}",
        f"https://image.pollinations.ai/prompt/{clean_p}?width={SPLIT_X}&height={H}&model=flux&nologo=true&seed={seed}",
        f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt[:150])}?width={SPLIT_X}&height={H}&nologo=true",
    ]

    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=6.0)
            if r.status_code == 200 and len(r.content) > 4000:
                img = Image.open(BytesIO(r.content)).convert("RGBA")
                img = ImageEnhance.Contrast(img.convert("RGB")).enhance(1.08)
                return img.convert("RGBA").resize((SPLIT_X, H), Image.LANCZOS)
        except Exception:
            continue

    return None



# ── Gradient Background ───────────────────────────────────────────────────────
def _make_gradient(style_def: dict, width: int = W, height: int = H) -> Image.Image:
    img = Image.new("RGBA", (width, height))
    d = ImageDraw.Draw(img)
    tc, bc = style_def["bg_top"], style_def["bg_btm"]
    for y in range(height):
        t = y / height
        r = int(tc[0] + (bc[0] - tc[0]) * t)
        g = int(tc[1] + (bc[1] - tc[1]) * t)
        b = int(tc[2] + (bc[2] - tc[2]) * t)
        d.line([(0, y), (width, y)], fill=(r, g, b, 255))
    return img


# ── Glass Panel ───────────────────────────────────────────────────────────────
def _draw_glass_panel(canvas: Image.Image, x: int, y: int, w: int, h: int,
                       style_def: dict, radius: int = 20):
    """Draw a beautiful frosted glass panel with border and shadow."""
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    panel_bg = style_def["panel_bg"]  # RGBA

    # Shadow layers
    for i in range(5, 0, -1):
        shadow_alpha = 30 - i * 4
        if shadow_alpha > 0:
            od.rounded_rectangle(
                [(x + i, y + i), (x + w + i, y + h + i)],
                radius=radius, fill=(0, 0, 0, shadow_alpha)
            )

    # Panel body
    od.rounded_rectangle([(x, y), (x + w, y + h)], radius=radius, fill=panel_bg)

    # Border
    border_c = style_def.get("border_c", (255, 255, 255, 40))
    od.rounded_rectangle([(x, y), (x + w, y + h)],
                          radius=radius, outline=border_c, width=1)

    # Top specular highlight
    highlight = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(highlight)
    hd.rounded_rectangle([(x + 1, y + 1), (x + w - 1, y + 22)],
                          radius=radius, fill=(255, 255, 255, 18))
    canvas.alpha_composite(highlight)
    canvas.alpha_composite(overlay)


# ── Step Number Badge ─────────────────────────────────────────────────────────
def _draw_step_badge(canvas: Image.Image, n: int, arc_phase: str, style_def: dict,
                      x: int, y: int):
    """Draw a beautiful step number badge with arc-phase color."""
    phase_col = ARC_COLORS.get(arc_phase.lower() if arc_phase else "", style_def["accent"])
    radius    = 28

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # Glow
    for g in range(5, 0, -1):
        od.ellipse([x - radius - g*2, y - radius - g*2,
                    x + radius + g*2, y + radius + g*2],
                   fill=(*phase_col, 18 // g))

    # Circle
    od.ellipse([x - radius, y - radius, x + radius, y + radius],
               fill=(*phase_col, 220))
    od.ellipse([x - radius, y - radius, x + radius, y + radius],
               outline=(255, 255, 255, 140), width=2)

    canvas.alpha_composite(overlay)

    # Step number
    d = ImageDraw.Draw(canvas)
    num_str  = str(n)
    num_font = _font(22, bold=True)
    bb = d.textbbox((0, 0), num_str, font=num_font)
    nx = x - (bb[2] - bb[0]) // 2
    ny = y - (bb[3] - bb[1]) // 2
    d.text((nx + 1, ny + 1), num_str, fill=(0, 0, 0, 100), font=num_font)
    d.text((nx, ny), num_str, fill=(255, 255, 255), font=num_font)


# ── Step Tag Label ──────────────────────────────────────────────────────────
def _draw_arc_phase_label(canvas: Image.Image, n: int, total: int,
                            style_def: dict, x: int, y: int):
    """Draw clean step progress tag badge."""
    acc = style_def["accent"]
    label_text = f"STEP {n} OF {total}"

    d = ImageDraw.Draw(canvas)
    lf = _font(11, bold=True)
    bb = d.textbbox((0, 0), label_text, font=lf)
    lw = bb[2] - bb[0]

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    pad = 10
    od.rounded_rectangle([(x - pad, y - 4), (x + lw + pad, y + 18)],
                          radius=10, fill=(*acc, 30))
    od.rounded_rectangle([(x - pad, y - 4), (x + lw + pad, y + 18)],
                          radius=10, outline=(*acc, 120), width=1)
    canvas.alpha_composite(overlay)

    d = ImageDraw.Draw(canvas)
    d.text((x, y), label_text, fill=(*acc, 230), font=lf)



# ── Main Slide Builder ────────────────────────────────────────────────────────
def build_cinematic_slide(step: dict, total: int, output_path: str,
                           ai_image: Image.Image | None, topic: str,
                           visual_style: str = "classic") -> str:
    """
    Build a single beautiful NotebookLM-quality slide image.
    """
    style_def  = _get_style(visual_style)
    n          = step.get("step_number", 1)
    title      = step.get("title", f"Step {n}")
    narration  = step.get("narration", "")
    arc_phase  = step.get("arc_phase", "problem")
    arc_label  = step.get("arc_label", "")
    teacher    = step.get("teacher_line", "")
    student    = step.get("student_line", "")
    components = step.get("components", [])

    phase_col = ARC_COLORS.get(arc_phase.lower() if arc_phase else "", style_def["accent"])

    # ── Full-frame gradient background ────────────────────────────────────────
    canvas = _make_gradient(style_def)

    # ── AI Visual Image (left 58%) ─────────────────────────────────────────────
    if ai_image is not None:
        ai_img = ai_image.convert("RGBA").resize((SPLIT_X, H), Image.LANCZOS)
        canvas.paste(ai_img.convert("RGB"), (0, 0))
        canvas = canvas.convert("RGBA")

        # Darken right edge of AI image for smooth blend into text panel
        blend = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bd    = ImageDraw.Draw(blend)
        for x in range(80):
            alpha = int(200 * (x / 80) ** 1.5)
            bd.line([(SPLIT_X - 80 + x, 0), (SPLIT_X - 80 + x, H)],
                    fill=(style_def["bg_top"][0], style_def["bg_top"][1],
                          style_def["bg_top"][2], alpha))
        canvas.alpha_composite(blend)
    else:
        # Fallback: nice gradient with step-specific tint
        canvas = _make_gradient(style_def)

    # ── Separator line ─────────────────────────────────────────────────────────
    sep = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd  = ImageDraw.Draw(sep)
    acc = style_def["accent"]
    for i, alpha in enumerate([30, 80, 140, 80, 30]):
        sd.line([(SPLIT_X - 2 + i, 0), (SPLIT_X - 2 + i, H)], fill=(*acc, alpha))
    canvas.alpha_composite(sep)

    # ── Text Panel (right 42%) ─────────────────────────────────────────────────
    TX = SPLIT_X + 28
    TW = W - TX - 24
    ty = 52

    # Glass panel for text
    _draw_glass_panel(canvas, SPLIT_X + 10, 16, W - SPLIT_X - 20, H - 32, style_def, radius=18)

    d = ImageDraw.Draw(canvas)

    # ── Step number badge + arc phase label ───────────────────────────────────
    badge_x = TX + 22
    badge_y = ty + 22
    _draw_step_badge(canvas, n, arc_phase, style_def, badge_x, badge_y)
    d = ImageDraw.Draw(canvas)

    # Step tag label next to badge
    arc_lx = badge_x + 38
    arc_ly = badge_y - 7
    _draw_arc_phase_label(canvas, n, total, style_def, arc_lx, arc_ly)


    ty = badge_y + 40

    # ── Thin accent divider ────────────────────────────────────────────────────
    d = ImageDraw.Draw(canvas)
    d.line([(TX + 4, ty), (TX + TW, ty)], fill=(*acc, 40), width=1)
    ty += 14

    # ── Title ─────────────────────────────────────────────────────────────────
    title_font  = _font(26, bold=True)
    title_col   = style_def["title_c"]
    title_lines = _wrap(title, title_font, TW - 8, d)
    for line in title_lines[:2]:
        # Shadow
        d.text((TX + 1, ty + 1), line, fill=(0, 0, 0, 80), font=title_font)
        d.text((TX, ty), line, fill=title_col, font=title_font)
        ty += 34
    ty += 8

    # ── Teacher/Student dialogue (if available) ────────────────────────────────
    if teacher or student:
        speakers = []
        if teacher:
            speakers.append(("TEACHER", teacher, (99, 102, 241)))
        if student:
            speakers.append(("STUDENT", student, (236, 72, 153)))

        for speaker_label, line_text, s_col in speakers[:2]:
            if ty > H - 120:
                break

            # Speaker badge
            sf = _font(9, bold=True)
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            bb_s = od.textbbox((0, 0), speaker_label, font=sf)
            sw_s = bb_s[2] - bb_s[0]
            od.rounded_rectangle([(TX, ty - 2), (TX + sw_s + 12, ty + 16)],
                                  radius=8, fill=(*s_col, 30))
            od.rounded_rectangle([(TX, ty - 2), (TX + sw_s + 12, ty + 16)],
                                  radius=8, outline=(*s_col, 100), width=1)
            canvas.alpha_composite(overlay)
            d = ImageDraw.Draw(canvas)
            d.text((TX + 6, ty), speaker_label, fill=(*s_col, 220), font=sf)
            ty += 20

            # Dialogue line
            lf  = _font(13)
            bc  = style_def["body_c"]
            lns = _wrap(f'"{line_text}"', lf, TW - 8, d)
            for ln in lns[:3]:
                d.text((TX + 4, ty), ln, fill=bc, font=lf)
                ty += 20
            ty += 6

    else:
        # ── Plain narration ────────────────────────────────────────────────────
        nar_font  = _font(15)
        nar_col   = style_def["body_c"]
        nar_lines = _wrap(narration, nar_font, TW - 8, d)
        for line in nar_lines[:7]:
            d.text((TX, ty), line, fill=nar_col, font=nar_font)
            ty += 24
        ty += 8

    # ── Components / key points ────────────────────────────────────────────────
    if components and ty < H - 100:
        d.line([(TX + 4, ty), (TX + TW, ty)], fill=(*acc, 30), width=1)
        ty += 12

        comp_font = _font(12)
        muted_col = style_def["muted_c"]
        d.text((TX, ty), "KEY POINTS", fill=(*acc, 170), font=_font(9, bold=True))
        ty += 18

        for comp in (components if isinstance(components, list) else [])[:4]:
            if ty > H - 40:
                break
            c_name = comp.get("name", str(comp)) if isinstance(comp, dict) else str(comp)
            c_desc = comp.get("description", "") if isinstance(comp, dict) else ""

            # Bullet point
            d.ellipse([TX - 1, ty + 4, TX + 7, ty + 12], fill=(*acc, 180))
            d.text((TX + 14, ty), c_name[:40], fill=muted_col, font=comp_font)
            ty += 20

    # ── Topic label in top bar ─────────────────────────────────────────────────
    bar_h = 46
    bar_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bo = ImageDraw.Draw(bar_overlay)

    # Top bar gradient
    for y in range(bar_h):
        ba = int(180 * (1 - y / bar_h) ** 0.6)
        bg_c = style_def["bg_top"]
        bo.line([(0, y), (W, y)], fill=(*bg_c, ba))

    # Brand text
    bo.text((20, 13), "VisuAIze", fill=(255, 255, 255, 140), font=_font(14, bold=True))
    bo.text((94, 14), "·", fill=(255, 255, 255, 60), font=_font(14))

    # Topic (truncated)
    topic_short = topic[:55] + "..." if len(topic) > 55 else topic
    bo.text((108, 14), topic_short, fill=(255, 255, 255, 100), font=_font(13))

    # Step counter in top-right
    counter_text = f"{n} / {total}"
    cf = _font(12, bold=True)
    bb_c = bo.textbbox((0, 0), counter_text, font=cf)
    cw   = bb_c[2] - bb_c[0]
    bo.text((W - cw - 16, 14), counter_text, fill=(*acc, 200), font=cf)

    canvas.alpha_composite(bar_overlay)

    # ── Bottom progress bar (static on slide) ─────────────────────────────────
    bar_overlay2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    b2 = ImageDraw.Draw(bar_overlay2)
    bar_y = H - 6
    b2.rectangle([(0, bar_y), (W, H)], fill=(0, 0, 0, 100))
    fill_w = int(W * (n / total))
    if fill_w > 0:
        b2.rectangle([(0, bar_y), (fill_w, H)], fill=(*acc, 200))
    canvas.alpha_composite(bar_overlay2)

    # ── Save ──────────────────────────────────────────────────────────────────
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, "PNG", quality=95)
    return output_path


# ── AI Image Prompt Builder ────────────────────────────────────────────────────
def _build_image_prompt(step: dict, topic: str, visual_style: str) -> str:
    """Build an optimized visual prompt for AI image generation."""
    arc_phase = step.get("arc_phase", "problem")
    title     = step.get("title", "")
    motion_p  = step.get("motion_prompt") or step.get("image_prompt", "")

    # Use motion_prompt if it's detailed enough
    if motion_p and len(motion_p) > 40:
        base = motion_p
    else:
        # Build from title + topic
        base = f"{title} concept, {topic}"

    # Style enhancement
    style_suffix = {
        "classic":     "cinematic dark background, glowing light effects, 4K professional",
        "whiteboard":  "clean educational whiteboard diagram, hand-drawn markers, no background",
        "kawaii":      "kawaii anime illustration, pastel colors, cute kawaii style",
        "watercolor":  "beautiful watercolor painting, artistic washes, soft colors",
        "papercraft":  "papercraft art, layered paper, flat design, warm colors",
        "retro_print": "vintage educational illustration, 1950s print style, halftone",
        "heritage":    "classical oil painting style, warm mahogany tones, detailed",
    }.get(visual_style, "professional educational illustration")

    # Phase-specific visual guidance
    phase_hints = {
        "problem":  "showing a challenge, confusion, or obstacle",
        "analogy":  "showing a real-world comparison or metaphor",
        "solution": "showing a clear resolution, success, achievement",
    }
    phase_hint = phase_hints.get(arc_phase.lower() if arc_phase else "", "")

    return f"{base}, {phase_hint}, {style_suffix}, no text overlay, no watermarks"


# ── Main Entry Point ──────────────────────────────────────────────────────────
def generate_all_images(steps: list, output_dir: str, topic: str = "",
                        visual_style: str = "classic") -> list[str]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    total = len(steps)
    if total == 0:
        return []

    print(f"\n🎨 Generating {total} high-definition [{visual_style.upper()}] visual slides in parallel...")

    paths = [None] * total

    def _render_one(idx: int, step: dict):
        n = step.get("step_number", idx + 1)
        out_path = str(Path(output_dir) / f"step_{n:02d}.png")
        print(f"  🖼  Generating slide {n}/{total}: {step.get('title', '')[:45]}...")

        # Build style-aware image prompt
        img_prompt = _build_image_prompt(step, topic, visual_style)

        # Fetch AI image
        ai_img = _fetch_ai_image(img_prompt, style=visual_style)

        # Build cinematic slide
        build_cinematic_slide(
            step=step, total=total, output_path=out_path,
            ai_image=ai_img, topic=topic, visual_style=visual_style
        )
        paths[idx] = out_path
        print(f"  ✓ Slide {n}/{total} ready")

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_render_one, i, step) for i, step in enumerate(steps)]
        for f in futures:
            try: f.result()
            except Exception as e: print(f"  ⚠️ Slide generation warning: {e}")

    valid_paths = [p for p in paths if p is not None and Path(p).exists()]
    print(f"✅ All {len(valid_paths)} [{visual_style.title()}] visual slides ready!")
    return valid_paths

