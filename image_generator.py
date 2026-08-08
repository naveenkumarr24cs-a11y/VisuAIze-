"""
VisuAIze - Ultra Realistic Google Flow Slide Generator
======================================================
Features:
  - Multi-tier Pollinations Flux AI fetching with full User-Agent headers
  - High-definition Google Flow visual diagramming engine for instant rich graphics
  - Crisp split-panel presentation layout (58.5% visual illustration, 41.5% narration panel)
  - Custom Koala Mascot branding in top bar
  - Multi-threaded parallel processing (ThreadPoolExecutor)
"""

import os
import random
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ── Canvas dimensions ────────────────────────────────────────────────────────
W = 1280
H = 720

# ── Color Palette (Pure Dark Black & Dark White Minimalist) ─────────────────
BG_DARK    = (8, 8, 11)
BG_MID     = (15, 15, 20)
BG_PANEL   = (17, 17, 23, 248)

INDIGO     = (255, 255, 255)       # Pure White Accent
INDIGO_LT  = (225, 225, 235)       # Silver White
VIOLET     = (200, 200, 215)       # Pale Silver
AMBER      = (240, 240, 245)       # Light Monochrome
EMERALD    = (255, 255, 255)       # Crisp White
ROSE       = (220, 220, 225)       # Light Gray
CYAN       = (210, 215, 225)       # Cool Silver

TXT_WHITE  = (255, 255, 255)
TXT_SILVER = (225, 225, 230)
TXT_MUTED  = (150, 150, 160)
TXT_DIM    = (90, 90, 100)

# ── Image Fetching Settings ──────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}

# ── Font Cache ───────────────────────────────────────────────────────────────
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
    """Fetch high quality AI image from Pollinations Flux with fast 3.5s timeout."""
    clean_p = urllib.parse.quote(f"{prompt}, 3d realistic educational illustration, highly detailed, 4k render")
    seed = random.randint(100, 99999)
    
    urls = [
        f"https://image.pollinations.ai/prompt/{clean_p}?width=768&height=512&model=flux&nologo=true&seed={seed}",
        f"https://image.pollinations.ai/prompt/{clean_p}?width=768&height=512&model=turbo&nologo=true",
    ]

    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=3.5)
            if r.status_code == 200 and len(r.content) > 6000:
                img = Image.open(BytesIO(r.content)).convert("RGBA")
                rgb = img.convert("RGB")
                rgb = ImageEnhance.Contrast(rgb).enhance(1.06)
                return rgb.convert("RGBA")
        except Exception:
            pass

    return None


def _draw_google_flow_diagram(canvas: Image.Image, step: dict, accent: tuple, panel_w: int, panel_h: int):
    """Draw a beautiful, high-tech Google Flow diagram card when offline."""
    n = step.get("step_number", 1)
    title = step.get("title", f"Step {n}")
    
    diag = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(diag)
    
    # 1. Subtle grid lines (Google Flow canvas)
    for gx in range(0, panel_w, 40):
        d.line([(gx, 0), (gx, panel_h)], fill=(255, 255, 255, 8), width=1)
    for gy in range(0, panel_h, 40):
        d.line([(0, gy), (panel_w, gy)], fill=(255, 255, 255, 8), width=1)

    # 2. Main Central Technical Flow Node
    cx, cy = panel_w // 2, panel_h // 2
    card_w, card_h = 440, 220
    x1, y1 = cx - card_w // 2, cy - card_h // 2
    x2, y2 = cx + card_w // 2, cy + card_h // 2
    
    # Ambient Card Glow
    for g in range(16, 0, -4):
        d.rounded_rectangle([(x1 - g, y1 - g), (x2 + g, y2 + g)], radius=18, outline=(*accent, 18 - g), width=2)
    
    # Solid Card Box
    d.rounded_rectangle([(x1, y1), (x2, y2)], radius=14, fill=(24, 28, 48, 240), outline=(*accent, 160), width=2)

    # Node Header Badge
    d.rounded_rectangle([(x1 + 20, y1 + 18), (x1 + 130, y1 + 44)], radius=6, fill=(*accent, 50))
    d.text((x1 + 30, y1 + 24), f"STAGE 0{n} · ACTIVE", fill=accent, font=_font(11, bold=True))

    # Node Step Title
    tf = _font(22, bold=True)
    title_lines = _wrap(title, tf, card_w - 40, d)
    ty = y1 + 56
    for l in title_lines[:2]:
        d.text((x1 + 20, ty), l, fill=TXT_WHITE, font=tf)
        ty += 28

    # Process Connectors / Schematic Nodes
    node_y = y1 + 132
    d.line([(x1 + 20, node_y), (x2 - 20, node_y)], fill=(*accent, 80), width=2)
    
    # 3 Progress Checkpoints inside card
    for k, (lbl, col) in enumerate([("1. Input", EMERALD), ("2. Execute", accent), ("3. Verify", CYAN)]):
        nx = x1 + 40 + k * 140
        d.ellipse([nx - 7, node_y - 7, nx + 7, node_y + 7], fill=(*col, 240))
        d.text((nx - 18, node_y + 12), lbl, fill=TXT_MUTED, font=_font(11))

    # 3. Surrounding Flow Arrows & Connection Dots
    for offset_x in [-180, 180]:
        d.ellipse([cx + offset_x - 4, cy - 130 - 4, cx + offset_x + 4, cy - 130 + 4], fill=(*accent, 180))
        d.line([(cx + offset_x, cy - 130), (cx, y1)], fill=(*accent, 40), width=1)

    canvas.alpha_composite(diag, (0, 56))


def build_slide(step: dict, total: int, output_path: str, preloaded_img: Image.Image = None) -> str:
    n          = step.get("step_number", 1)
    title      = step.get("title", f"Step {n}")
    narration  = step.get("narration", "")
    img_prompt = step.get("image_prompt", title)

    ACCENTS = [INDIGO, VIOLET, CYAN, AMBER, EMERALD, ROSE, INDIGO_LT]
    accent  = ACCENTS[(n - 1) % len(ACCENTS)]

    ai_img = preloaded_img if preloaded_img else _fetch_image(img_prompt)
    canvas = _new_canvas()

    IMG_X2 = int(W * 0.585)
    IMG_Y1 = 56
    IMG_Y2 = H - 36
    panel_w = IMG_X2
    panel_h = IMG_Y2 - IMG_Y1

    if ai_img:
        src_w, src_h = ai_img.size
        scale = max(panel_w / src_w, panel_h / src_h)
        ai_fit = ai_img.resize((int(src_w * scale), int(src_h * scale)), Image.BILINEAR)
        left = (ai_fit.width - panel_w) // 2
        top = (ai_fit.height - panel_h) // 2
        ai_fit = ai_fit.crop((left, top, left + panel_w, top + panel_h))
        canvas.paste(ai_fit, (0, IMG_Y1))

        # Blend right edge smoothly
        fade_w = 90
        fade = Image.new("RGBA", (fade_w, panel_h), (0, 0, 0, 0))
        fd = ImageDraw.Draw(fade)
        for x in range(fade_w):
            alpha = int((x / fade_w) * 230)
            fd.line([(x, 0), (x, panel_h)], fill=(*BG_MID, alpha))
        canvas.alpha_composite(fade, (IMG_X2 - fade_w, IMG_Y1))
    else:
        # Render high-detail Google Flow diagram
        _draw_google_flow_diagram(canvas, step, accent, panel_w, panel_h)

    # Right info panel
    PNL_X = IMG_X2 - 10
    _alpha_rect(canvas, PNL_X, 0, W, H, (*BG_DARK, 248))
    _alpha_rect(canvas, PNL_X, IMG_Y1, PNL_X + 3, IMG_Y2, (*accent, 220))

    # Top bar
    _alpha_rect(canvas, 0, 0, W, 56, (12, 14, 22, 235))
    _alpha_rect(canvas, 0, 55, W, 57, (*accent, 90))

    d = ImageDraw.Draw(canvas)

    # Brand in top bar
    logo_txt = "VisuAIze"
    logo_font = _font(15, bold=True)
    _alpha_rect(canvas, 14, 11, 100, 45, (*INDIGO, 220), radius=8)
    d.text((25, 18), logo_txt, fill=TXT_WHITE, font=logo_font)
    d.text((114, 19), "Step-by-Step Visual Learning Engine", fill=TXT_MUTED, font=_font(12))

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
    total = len(steps)
    print(f"\n🖼️  Generating {total} Google Flow HD slides (Parallel Engine)...")

    def _download_and_build(i, step):
        n = step.get("step_number", i + 1)
        out_path = os.path.join(output_dir, f"step_{n:02d}.png")
        img_prompt = step.get("image_prompt", step.get("title", f"Step {n}"))
        ai_img = _fetch_image(img_prompt)
        build_slide(step, total, out_path, preloaded_img=ai_img)
        return i, out_path

    paths = [None] * total
    with ThreadPoolExecutor(max_workers=min(total, 6)) as executor:
        futures = [executor.submit(_download_and_build, i, step) for i, step in enumerate(steps)]
        for f in as_completed(futures):
            idx, p = f.result()
            paths[idx] = p

    print(f"✅ All {total} Google Flow slides ready!")
    return paths
