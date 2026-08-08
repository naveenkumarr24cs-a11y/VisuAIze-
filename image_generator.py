"""
VisuAIze - Ultra Fast & High Quality Google Flow Slide Generator
===============================================================
Generates clean, aesthetic 1280x720 slides in seconds with:
  - Real AI visuals via Pollinations Flux API
  - Ultra-fast image processing
  - Glassmorphic panels and crisp typography
"""

import os
import time
import urllib.parse
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ── Canvas dimensions ────────────────────────────────────────────────────────
W = 1280
H = 720

# ── Colors ───────────────────────────────────────────────────────────────────
BG_DARK    = (8, 10, 20)
BG_MID     = (14, 16, 32)
BG_PANEL   = (16, 19, 38, 240)    # right panel (RGBA)

INDIGO     = (99, 102, 241)        # primary indigo
INDIGO_LT  = (129, 140, 248)       # light indigo
VIOLET     = (139, 92, 246)        # violet accent
AMBER      = (251, 191, 36)        # amber/gold
EMERALD    = (52, 211, 153)        # green progress
ROSE       = (251, 113, 133)       # rose accent
CYAN       = (34, 211, 238)        # cyan accent

TXT_WHITE  = (255, 255, 255)
TXT_SILVER = (203, 213, 225)
TXT_MUTED  = (148, 163, 184)
TXT_DIM    = (71, 85, 105)

# ── Pollinations API (Fast & Enhanced) ───────────────────────────────────────
POLL_URL = "https://image.pollinations.ai/prompt/{p}?width=768&height=512&nologo=true&enhance=true"
TIMEOUT  = 20   # Fast timeout so generation doesn't block

# ── Font cache ────────────────────────────────────────────────────────────────
_FONT_CACHE: dict = {}

def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    WIN_PATHS = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"] if bold \
                else ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]
    LNX_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if bold \
                else ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]

    for p in WIN_PATHS + LNX_PATHS:
        try:
            f = ImageFont.truetype(p, size)
            _FONT_CACHE[key] = f
            return f
        except (IOError, OSError):
            pass
    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


def _wrap(text: str, font, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
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


def _new_canvas() -> Image.Image:
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(BG_DARK[0] + (BG_MID[0] - BG_DARK[0]) * t)
        g = int(BG_DARK[1] + (BG_MID[1] - BG_DARK[1]) * t)
        b = int(BG_DARK[2] + (BG_MID[2] - BG_DARK[2]) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b, 255))
    return img


def _alpha_rect(canvas: Image.Image, x1, y1, x2, y2, color: tuple, radius: int = 0):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if radius:
        d.rounded_rectangle([(x1, y1), (x2, y2)], radius=radius, fill=color)
    else:
        d.rectangle([(x1, y1), (x2, y2)], fill=color)
    canvas.alpha_composite(layer)


def _fetch_image(prompt: str) -> Image.Image | None:
    enhanced = f"{prompt}, high quality educational illustration, vivid colors, clean lighting, 4k resolution, no text"
    url = POLL_URL.format(p=urllib.parse.quote(enhanced))

    try:
        r = requests.get(url, timeout=TIMEOUT)
        if r.status_code == 200 and len(r.content) > 5000:
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            img_rgb = img.convert("RGB")
            img_rgb = ImageEnhance.Contrast(img_rgb).enhance(1.1)
            img_rgb = ImageEnhance.Color(img_rgb).enhance(1.15)
            return img_rgb.convert("RGBA")
    except Exception:
        pass
    return None


def build_slide(step: dict, total: int, output_path: str) -> str:
    n          = step.get("step_number", 1)
    title      = step.get("title", f"Step {n}")
    narration  = step.get("narration", "")
    img_prompt = step.get("image_prompt", title)

    ACCENTS = [INDIGO, VIOLET, CYAN, AMBER, EMERALD, ROSE, INDIGO_LT]
    accent  = ACCENTS[(n - 1) % len(ACCENTS)]

    ai_img = _fetch_image(img_prompt)
    canvas = _new_canvas()

    IMG_X2 = int(W * 0.585)
    IMG_Y1 = 56
    IMG_Y2 = H - 36

    if ai_img:
        panel_w = IMG_X2
        panel_h = IMG_Y2 - IMG_Y1
        # Crop & resize
        src_w, src_h = ai_img.size
        scale = max(panel_w / src_w, panel_h / src_h)
        ai_fit = ai_img.resize((int(src_w * scale), int(src_h * scale)), Image.BILINEAR)
        left = (ai_fit.width - panel_w) // 2
        top = (ai_fit.height - panel_h) // 2
        ai_fit = ai_fit.crop((left, top, left + panel_w, top + panel_h))
        canvas.paste(ai_fit, (0, IMG_Y1))

        # Blend right edge
        fade_w = 90
        fade = Image.new("RGBA", (fade_w, panel_h), (0, 0, 0, 0))
        fd = ImageDraw.Draw(fade)
        for x in range(fade_w):
            alpha = int((x / fade_w) * 230)
            fd.line([(x, 0), (x, panel_h)], fill=(*BG_MID, alpha))
        canvas.alpha_composite(fade, (IMG_X2 - fade_w, IMG_Y1))
    else:
        # Fallback abstract pattern
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        cx, cy = IMG_X2 // 2, (IMG_Y1 + IMG_Y2) // 2
        for r in range(250, 0, -35):
            a = int(35 * (1 - r / 250))
            ld.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*accent, a), width=2)
        canvas.alpha_composite(layer)

    # Right info panel
    PNL_X = IMG_X2 - 10
    _alpha_rect(canvas, PNL_X, 0, W, H, (*BG_DARK, 248))
    _alpha_rect(canvas, PNL_X, IMG_Y1, PNL_X + 3, IMG_Y2, (*accent, 220))

    # Top bar
    _alpha_rect(canvas, 0, 0, W, 56, (0, 0, 0, 210))
    _alpha_rect(canvas, 0, 55, W, 57, (*accent, 90))

    d = ImageDraw.Draw(canvas)

    # Animal Logo in top bar
    logo_txt = "VisuAIze"
    logo_font = _font(15, bold=True)
    _alpha_rect(canvas, 12, 10, 110, 46, (*INDIGO, 220), radius=8)
    d.text((20, 17), "🦊 " + logo_txt, fill=TXT_WHITE, font=logo_font)
    d.text((124, 19), "Step-by-Step Visual Learning Engine", fill=TXT_MUTED, font=_font(12))

    # Step pill
    pill_txt = f"STEP {n:02d} / {total:02d}"
    pill_font = _font(12, bold=True)
    _alpha_rect(canvas, W - 140, 11, W - 14, 45, (*accent, 200), radius=20)
    d.text((W - 128, 18), pill_txt, fill=TXT_WHITE, font=pill_font)

    # Info panel content
    TX = PNL_X + 28
    TW = W - TX - 20
    ty = IMG_Y1 + 18

    # Phase badge
    badge = f"  PHASE {n}  "
    _alpha_rect(canvas, TX, ty, TX + 80, ty + 22, (*accent, 60), radius=5)
    d = ImageDraw.Draw(canvas)
    d.text((TX + 6, ty + 4), badge.strip(), fill=accent, font=_font(11, bold=True))
    ty += 32

    # Step title
    title_font = _font(28, bold=True)
    title_lines = _wrap(title, title_font, TW, d)
    for line in title_lines[:2]:
        d.text((TX + 1, ty + 1), line, fill=(0, 0, 0, 180), font=title_font)
        d.text((TX, ty), line, fill=TXT_WHITE, font=title_font)
        ty += 36
    ty += 8

    # Divider
    _alpha_rect(canvas, TX, ty, TX + TW, ty + 1, (*accent, 70))
    ty += 16

    # Explanation text
    d.text((TX, ty), "EXPLANATION", fill=(*accent, 190), font=_font(10, bold=True))
    ty += 18

    narr_font = _font(16)
    narr_lines = _wrap(narration, narr_font, TW, d)
    for line in narr_lines[:5]:
        d.text((TX, ty), line, fill=TXT_SILVER, font=narr_font)
        ty += 25

    # Bottom Progress Bar
    BAR_Y = H - 28
    BAR_W = W
    BAR_H = 6
    pct = n / total
    fill_w = int(BAR_W * pct)

    _alpha_rect(canvas, 0, BAR_Y, BAR_W, BAR_Y + BAR_H, (255, 255, 255, 25))
    if fill_w > 0:
        _alpha_rect(canvas, 0, BAR_Y, fill_w, BAR_Y + BAR_H, (*EMERALD, 230))

    d = ImageDraw.Draw(canvas)
    d.text((12, BAR_Y - 16), f"{int(pct * 100)}% · Step {n} of {total} · 1080p HD", fill=TXT_MUTED, font=_font(11))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, "PNG", quality=90)
    return output_path


def generate_all_images(steps: list, output_dir: str) -> list[str]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    paths = []
    total = len(steps)

    print(f"\n🖼️  Generating {total} Google Flow HD slides (Fast Engine)...")
    for i, step in enumerate(steps):
        n = step.get("step_number", i + 1)
        out_path = os.path.join(output_dir, f"step_{n:02d}.png")
        build_slide(step, total, out_path)
        paths.append(out_path)
        if i < total - 1:
            time.sleep(1)

    print(f"✅  All {total} slides generated successfully!")
    return paths
