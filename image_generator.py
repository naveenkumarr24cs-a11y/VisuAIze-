"""
VisuAIze - Ultra Realistic Google Flow Slide Generator
======================================================
Creates cinema-quality 1280x720 slides that look like professional
Google Flow / Apple Keynote presentations:

Layout per slide:
  ┌─────────────────────────────────────────────────────────────┐
  │  TOP BAR  │ VisuAIze logo │ Topic title │ Step XX of XX   │
  ├───────────────────────────┬─────────────────────────────────┤
  │                           │  PHASE badge                    │
  │   REAL AI IMAGE           │  Step Title (large, bold)       │
  │   (left 58%)              │  ─────────────────────────      │
  │                           │  📌 Key Point bullets           │
  │   with soft vignette      │  Narration text                 │
  │   edge blend              │                                 │
  │                           │  [Step number icon]             │
  ├───────────────────────────┴─────────────────────────────────┤
  │  PROGRESS BAR  ████████████░░░░  67% · Step 4 of 6         │
  └─────────────────────────────────────────────────────────────┘

Every element uses anti-aliased rendering, glassmorphism panels,
gradient overlays, and pixel-perfect typography.
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

# ── Google Flow inspired palette ─────────────────────────────────────────────
# Backgrounds
BG_DARK    = (8, 10, 20)
BG_MID     = (14, 16, 32)
BG_PANEL   = (16, 19, 38, 240)    # right panel (RGBA)

# Accent colours
INDIGO     = (99, 102, 241)        # primary indigo
INDIGO_LT  = (129, 140, 248)       # light indigo
VIOLET     = (139, 92, 246)        # violet accent
AMBER      = (251, 191, 36)        # amber/gold
EMERALD    = (52, 211, 153)        # green progress
ROSE       = (251, 113, 133)       # rose accent
CYAN       = (34, 211, 238)        # cyan accent

# Text
TXT_WHITE  = (255, 255, 255)
TXT_SILVER = (203, 213, 225)
TXT_MUTED  = (148, 163, 184)
TXT_DIM    = (71, 85, 105)

# Glassmorphism
GLASS_BG   = (255, 255, 255, 12)
GLASS_BDR  = (255, 255, 255, 25)

# ── Pollinations API ──────────────────────────────────────────────────────────
POLL_URL = "https://image.pollinations.ai/prompt/{p}?width=800&height=600&nologo=true&enhance=true&model=flux"
TIMEOUT  = 70

# ── Font cache ────────────────────────────────────────────────────────────────
_FONT_CACHE: dict = {}

def _font(size: int, bold: bool = False, italic: bool = False) -> ImageFont.ImageFont:
    key = (size, bold, italic)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    WIN_PATHS = {
        (True,  False): ["C:/Windows/Fonts/arialbd.ttf",  "C:/Windows/Fonts/segoeuib.ttf",  "C:/Windows/Fonts/calibrib.ttf"],
        (False, False): ["C:/Windows/Fonts/arial.ttf",    "C:/Windows/Fonts/segoeui.ttf",   "C:/Windows/Fonts/calibri.ttf"],
        (True,  True):  ["C:/Windows/Fonts/arialbi.ttf",  "C:/Windows/Fonts/segoeuiz.ttf"],
        (False, True):  ["C:/Windows/Fonts/ariali.ttf",   "C:/Windows/Fonts/segoeuii.ttf"],
    }
    LNX_PATHS = {
        (True,  False): ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                         "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"],
        (False, False): ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                         "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"],
        (True,  True):  ["/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf"],
        (False, True):  ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"],
    }
    candidates = WIN_PATHS.get((bold, italic), []) + LNX_PATHS.get((bold, italic), [])
    for p in candidates:
        try:
            f = ImageFont.truetype(p, size)
            _FONT_CACHE[key] = f
            return f
        except (IOError, OSError):
            pass
    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


# ── Text utilities ────────────────────────────────────────────────────────────
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


def _text_w(text: str, font, draw: ImageDraw.ImageDraw) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


# ── Canvas helpers ────────────────────────────────────────────────────────────
def _new_canvas() -> Image.Image:
    """Create a deep dark gradient base canvas."""
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
    """Draw a semi-transparent rounded rectangle."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if radius:
        d.rounded_rectangle([(x1, y1), (x2, y2)], radius=radius, fill=color)
    else:
        d.rectangle([(x1, y1), (x2, y2)], fill=color)
    canvas.alpha_composite(layer)


def _glow_line(canvas: Image.Image, x1, y1, x2, y2, color: tuple, width: int = 2):
    """Draw a glowing coloured line."""
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for offset in range(4, 0, -1):
        alpha = int(color[3] * (offset / 4) * 0.4) if len(color) > 3 else 30
        gd.line([(x1, y1), (x2, y2)], fill=(*color[:3], alpha), width=width + offset * 2)
    gd.line([(x1, y1), (x2, y2)], fill=color[:3] + (255,) if len(color) == 3 else color, width=width)
    canvas.alpha_composite(glow)


# ── Pollinations image fetch ──────────────────────────────────────────────────
def _fetch_image(prompt: str) -> Image.Image | None:
    """Fetch real AI image from Pollinations. Returns None on failure."""
    enhanced = (
        f"{prompt}, ultra detailed, professional educational illustration, "
        "vibrant and clear, cinematic lighting, 4k quality, "
        "clean background, no watermarks, no text"
    )
    url = POLL_URL.format(p=urllib.parse.quote(enhanced))

    for attempt in range(3):
        try:
            print(f"      🌐 Fetching AI image (attempt {attempt + 1}/3)...")
            r = requests.get(url, timeout=TIMEOUT)
            if r.status_code == 200 and len(r.content) > 8000:
                img = Image.open(BytesIO(r.content)).convert("RGBA")
                # Enhance: slightly increase contrast and saturation
                img_rgb = img.convert("RGB")
                img_rgb = ImageEnhance.Contrast(img_rgb).enhance(1.15)
                img_rgb = ImageEnhance.Color(img_rgb).enhance(1.2)
                print(f"      ✅ Image ready ({len(r.content)//1024} KB)")
                return img_rgb.convert("RGBA")
            else:
                print(f"      ⚠️  Bad response {r.status_code} ({len(r.content)} bytes)")
        except Exception as e:
            print(f"      ⚠️  Attempt {attempt+1} failed: {e}")
        if attempt < 2:
            time.sleep(4)

    print("      ❌ Could not fetch image, using fallback design.")
    return None


# ── Core slide builder ────────────────────────────────────────────────────────
def build_slide(step: dict, total: int, output_path: str) -> str:
    """
    Builds one ultra-realistic Google Flow HD slide (1280×720).
    """
    n          = step.get("step_number", 1)
    title      = step.get("title", f"Step {n}")
    narration  = step.get("narration", "")
    img_prompt = step.get("image_prompt", title)

    # Pick accent colour per step (cycles through palette)
    ACCENTS = [INDIGO, VIOLET, CYAN, AMBER, EMERALD, ROSE, INDIGO_LT]
    accent  = ACCENTS[(n - 1) % len(ACCENTS)]

    print(f"\n  🎨 Slide {n}/{total}: '{title}'")

    # ── 1. Fetch real AI image ────────────────────────────────────────────────
    ai_img = _fetch_image(img_prompt)

    # ── 2. Build base canvas ──────────────────────────────────────────────────
    canvas = _new_canvas()

    # ── 3. Compose image panel (LEFT 58%) ─────────────────────────────────────
    IMG_X2 = int(W * 0.585)   # image panel ends here
    IMG_Y1 = 56               # below top bar
    IMG_Y2 = H - 36           # above progress bar

    if ai_img:
        # Crop AI image to fill exactly the image panel area
        panel_w = IMG_X2
        panel_h = IMG_Y2 - IMG_Y1
        ai_fit  = _smart_crop(ai_img, panel_w, panel_h)

        # Paste it
        canvas.paste(ai_fit, (0, IMG_Y1))

        # ── Soft vignette on all 4 edges of image panel ──────────────────────
        _add_vignette(canvas, 0, IMG_Y1, panel_w, panel_h, strength=180)

        # ── Strong gradient on RIGHT edge to blend into info panel ────────────
        fade_w = 110
        fade   = Image.new("RGBA", (fade_w, panel_h), (0, 0, 0, 0))
        fd     = ImageDraw.Draw(fade)
        for x in range(fade_w):
            alpha = int((x / fade_w) ** 1.5 * 230)
            fd.line([(x, 0), (x, panel_h)], fill=(*BG_MID, alpha))
        canvas.alpha_composite(fade, (IMG_X2 - fade_w, IMG_Y1))

        # Subtle colour tint on the image (step accent glow top-left corner)
        tint = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        td   = ImageDraw.Draw(tint)
        td.ellipse([(-60, IMG_Y1 - 60), (300, IMG_Y1 + 300)], fill=(*accent, 22))
        canvas.alpha_composite(tint)

    else:
        # Fallback: draw a stylised abstract pattern on left panel
        _draw_abstract_bg(canvas, 0, IMG_Y1, IMG_X2, IMG_Y2, accent)

    # ── 4. Right info panel ───────────────────────────────────────────────────
    PNL_X = IMG_X2 - 12    # slight overlap for seamless blend
    PNL_W = W - PNL_X

    _alpha_rect(canvas, PNL_X, 0, W, H, (*BG_DARK, 248))

    # Glowing left border of panel
    _glow_line(canvas, PNL_X + 3, IMG_Y1, PNL_X + 3, IMG_Y2, (*accent, 180), width=3)

    # ── 5. TOP NAVIGATION BAR ─────────────────────────────────────────────────
    _alpha_rect(canvas, 0, 0, W, 56, (0, 0, 0, 200))
    # Thin accent line under top bar
    _alpha_rect(canvas, 0, 55, W, 57, (*accent, 80))

    d = ImageDraw.Draw(canvas)

    # Logo pill
    logo_txt  = "▶  VisuAIze"
    logo_font = _font(15, bold=True)
    lw        = _text_w(logo_txt, logo_font, d) + 28
    _alpha_rect(canvas, 12, 10, 12 + lw, 46, (*INDIGO, 220), radius=8)
    d.text((24, 17), logo_txt, fill=TXT_WHITE, font=logo_font)

    # Subtitle
    d.text((22 + lw, 19), "Step-by-Step Visual Learning Engine",
           fill=TXT_MUTED, font=_font(12))

    # Step pill (top right)
    pill_txt  = f"STEP  {n:02d}  /  {total:02d}"
    pill_font = _font(12, bold=True)
    pw        = _text_w(pill_txt, pill_font, d) + 30
    px        = W - pw - 14
    _alpha_rect(canvas, px, 11, px + pw, 45, (*accent, 200), radius=20)
    d.text((px + 15, 18), pill_txt, fill=TXT_WHITE, font=pill_font)

    # ── 6. INFO PANEL CONTENT ─────────────────────────────────────────────────
    TX  = PNL_X + 28          # text left margin inside panel
    TW  = W - TX - 20         # text max width

    ty  = IMG_Y1 + 18         # running y cursor

    # Phase badge
    badge     = f"  PHASE {n}  "
    badge_fnt = _font(11, bold=True)
    bw        = _text_w(badge, badge_fnt, d) + 4
    _alpha_rect(canvas, TX, ty, TX + bw, ty + 22, (*accent, 55), radius=5)
    _alpha_rect(canvas, TX, ty, TX + bw, ty + 22, (*accent, 90), radius=5)
    d = ImageDraw.Draw(canvas)
    d.text((TX + 6, ty + 4), badge.strip(), fill=accent, font=badge_fnt)
    ty += 32

    # Step title
    title_font  = _font(30, bold=True)
    title_lines = _wrap(title, title_font, TW, d)
    for line in title_lines[:2]:
        # Subtle text shadow
        d.text((TX + 1, ty + 1), line, fill=(0, 0, 0, 180), font=title_font)
        d.text((TX, ty), line, fill=TXT_WHITE, font=title_font)
        ty += 38
    ty += 6

    # Divider with accent dot
    _alpha_rect(canvas, TX, ty, TX + TW, ty + 1, (*accent, 60))
    _alpha_rect(canvas, TX, ty - 3, TX + 8, ty + 4, accent, radius=3)
    ty += 14

    # "EXPLANATION" micro-label
    d.text((TX, ty), "EXPLANATION", fill=(*accent, 180), font=_font(10, bold=True))
    ty += 18

    # Narration text
    narr_font  = _font(17)
    narr_lines = _wrap(narration, narr_font, TW, d)
    for line in narr_lines[:6]:
        d.text((TX, ty), line, fill=TXT_SILVER, font=narr_font)
        ty += 27
    ty += 10

    # Key facts bullet strip (if room)
    if ty < IMG_Y2 - 70:
        _alpha_rect(canvas, TX, ty, W - 16, ty + 1, (*TXT_DIM, 80))
        ty += 10
        d.text((TX, ty), "KEY INSIGHT", fill=TXT_MUTED, font=_font(10, bold=True))
        ty += 16
        # Extract first sentence of narration as key insight
        key = (narration.split(".")[0] + ".") if "." in narration else narration[:80]
        key_lines = _wrap(f"→  {key}", _font(15), TW, d)
        for kl in key_lines[:2]:
            d.text((TX, ty), kl, fill=(*EMERALD, 230), font=_font(15))
            ty += 22

    # Step number watermark (bottom-right of panel, decorative)
    num_txt  = f"{n:02d}"
    num_font = _font(72, bold=True)
    nb       = d.textbbox((0, 0), num_txt, font=num_font)
    nw, nh   = nb[2] - nb[0], nb[3] - nb[1]
    nx       = W - nw - 18
    ny       = IMG_Y2 - nh - 10
    d.text((nx, ny), num_txt, fill=(*accent, 18), font=num_font)

    # ── 7. BOTTOM PROGRESS BAR ────────────────────────────────────────────────
    BAR_Y  = H - 30
    BAR_X  = 0
    BAR_W  = W
    BAR_H  = 8
    pct    = n / total
    fill_w = int(BAR_W * pct)

    # Dark base strip
    _alpha_rect(canvas, BAR_X, BAR_Y, BAR_X + BAR_W, BAR_Y + BAR_H, (0, 0, 0, 180))
    # Track
    _alpha_rect(canvas, BAR_X, BAR_Y, BAR_X + BAR_W, BAR_Y + BAR_H, (255, 255, 255, 20))
    # Fill with gradient look
    if fill_w > 0:
        _alpha_rect(canvas, BAR_X, BAR_Y, BAR_X + fill_w, BAR_Y + BAR_H, (*EMERALD, 220))
        # Bright tip glow
        tip_x = min(fill_w, BAR_W - 6)
        _alpha_rect(canvas, tip_x - 4, BAR_Y - 1, tip_x + 4, BAR_Y + BAR_H + 1, (*TXT_WHITE, 160), radius=3)

    d = ImageDraw.Draw(canvas)
    pct_lbl = f"  {int(pct * 100)}%  ·  Step {n} of {total}  ·  VisuAIze"
    d.text((10, BAR_Y - 16), pct_lbl, fill=TXT_MUTED, font=_font(11))

    # ── 8. Corner accent marks ────────────────────────────────────────────────
    # Top-left corner L bracket
    _alpha_rect(canvas, 0, 56, 3, 80, (*accent, 140))
    _alpha_rect(canvas, 0, 56, 24, 59, (*accent, 140))

    # ── 9. Save ───────────────────────────────────────────────────────────────
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, "PNG", quality=97)
    print(f"      💾 Saved → {Path(output_path).name}")
    return output_path


# ── Helpers ───────────────────────────────────────────────────────────────────
def _smart_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize + centre-crop to exactly target_w × target_h."""
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    img   = img.resize((new_w, new_h), Image.LANCZOS)
    left  = (new_w - target_w) // 2
    top   = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _add_vignette(canvas: Image.Image, x: int, y: int, w: int, h: int, strength: int = 160):
    """Add a soft dark vignette inside a rectangle region."""
    vig = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    vd  = ImageDraw.Draw(vig)
    for i in range(0, min(w, h) // 3, 2):
        a = int(strength * (1 - i / (min(w, h) // 3)))
        vd.rectangle([i, i, w - i, h - i], outline=(0, 0, 0, a))
    canvas.alpha_composite(vig, (x, y))


def _draw_abstract_bg(canvas, x1, y1, x2, y2, accent):
    """Draw a stylised gradient + circles fallback when no AI image."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld    = ImageDraw.Draw(layer)
    # Radial circles
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    for r in range(300, 0, -30):
        a = int(40 * (1 - r / 300))
        ld.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*accent, a), width=1)
    # Grid dots
    for gx in range(x1 + 20, x2, 40):
        for gy in range(y1 + 20, y2, 40):
            ld.ellipse([gx - 1, gy - 1, gx + 1, gy + 1], fill=(*accent, 40))
    canvas.alpha_composite(layer)


# ── Public API ────────────────────────────────────────────────────────────────
def generate_all_images(steps: list, output_dir: str) -> list[str]:
    """
    Generates one ultra-realistic visual slide per step.
    Returns list of PNG file paths in step order.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    paths = []
    total = len(steps)

    print(f"\n🖼️  Generating {total} Google Flow HD slides...")
    print("    (Each image ~15-40s due to AI generation)\n")

    for i, step in enumerate(steps):
        n        = step.get("step_number", i + 1)
        filename = f"step_{n:02d}.png"
        out_path = os.path.join(output_dir, filename)

        build_slide(step, total, out_path)
        paths.append(out_path)

        if i < total - 1:
            print(f"      ⏳ Cooling down 5s before next image...")
            time.sleep(5)

    print(f"\n✅  All {total} slides generated!")
    return paths
