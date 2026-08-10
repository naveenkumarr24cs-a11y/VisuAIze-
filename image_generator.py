"""
VisuAIze - Ultra Realistic Google Flow Slide Generator
======================================================
Features:
  - Multi-tier Pollinations Flux AI fetching with full User-Agent headers
  - Dual-View Visual Diagram (3D kinetic visual representation & technical schematic node network)
  - Sleek AI Teacher Host Avatar badge with high-tech border & live status indicator
  - Crisp split-panel presentation layout (58.5% visual illustration, 41.5% narration panel)
  - Custom Koala Mascot branding in top bar & crystal-clear text contrast
  - Multi-threaded parallel processing (ThreadPoolExecutor)
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

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import sora_animatediff_engine as sora_engine

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
    """Fetch high-detail AI visual illustration using multi-tier Pollinations Flux models & retries."""
    clean_p = urllib.parse.quote(f"{prompt}, high quality 3D educational illustration, detailed 4k render, clear subjects")
    seed1 = random.randint(100, 99999)
    seed2 = random.randint(100, 99999)

    urls = [
        f"https://image.pollinations.ai/prompt/{clean_p}?width=768&height=512&model=flux&nologo=true&seed={seed1}",
        f"https://image.pollinations.ai/prompt/{clean_p}?width=768&height=512&model=turbo&nologo=true&seed={seed2}",
        f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=768&height=512&nologo=true",
    ]

    for url in urls:
        for attempt in range(2):
            try:
                r = requests.get(url, headers=HEADERS, timeout=9.0)
                if r.status_code == 200 and len(r.content) > 5000:
                    img = Image.open(BytesIO(r.content)).convert("RGBA")
                    rgb = img.convert("RGB")
                    rgb = ImageEnhance.Contrast(rgb).enhance(1.05)
                    return rgb.convert("RGBA")
            except Exception:
                time.sleep(0.4)

    return None


def _draw_teacher_avatar(canvas: Image.Image, panel_w: int, accent: tuple):
    """Draw a sleek AI Teacher Host Avatar badge in top-right of visual panel."""
    bw, bh = 180, 44
    bx = panel_w - bw - 18
    by = 56 + 14

    _alpha_rect(canvas, bx, by, bx + bw, by + bh, (10, 14, 24, 220), radius=22)
    _alpha_rect(canvas, bx, by, bx + bw, by + bh, (*accent, 150), radius=22)
    _alpha_rect(canvas, bx + 1, by + 1, bx + bw - 1, by + bh - 1, (15, 19, 32, 245), radius=21)

    badge_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge_layer)

    av_cx, av_cy = bx + 23, by + 22
    av_r = 14

    for g in range(4, 0, -1):
        bd.ellipse([av_cx - av_r - g, av_cy - av_r - g, av_cx + av_r + g, av_cy + av_r + g], outline=(*accent, 40 // g), width=1)
    bd.ellipse([av_cx - av_r, av_cy - av_r, av_cx + av_r, av_cy + av_r], fill=(22, 28, 48, 255), outline=(*accent, 220), width=2)

    bd.ellipse([av_cx - 4, av_cy - 8, av_cx + 4, av_cy], fill=TXT_WHITE)
    bd.arc([av_cx - 8, av_cy - 1, av_cx + 8, av_cy + 11], 180, 360, fill=TXT_WHITE, width=2)
    bd.ellipse([av_cx - 2, av_cy - 4, av_cx + 2, av_cy], fill=accent)

    dot_x, dot_y = av_cx + 10, av_cy + 9
    bd.ellipse([dot_x - 5, dot_y - 5, dot_x + 5, dot_y + 5], fill=(16, 185, 129, 90))
    bd.ellipse([dot_x - 3, dot_y - 3, dot_x + 3, dot_y + 3], fill=(16, 185, 129, 255), outline=(255, 255, 255, 220), width=1)

    bd.text((bx + 45, by + 8), "AI TEACHER HOST", fill=TXT_WHITE, font=_font(10, bold=True))
    bd.text((bx + 45, by + 23), "LIVE INSTRUCTOR", fill=(*accent, 230), font=_font(9, bold=True))

    canvas.alpha_composite(badge_layer)


def _draw_google_flow_diagram(canvas: Image.Image, step: dict, accent: tuple, panel_w: int, panel_h: int):
    """Draw a visual flowchart diagram with node boxes, directional arrows, and step components."""
    n = step.get("step_number", 1)
    title = step.get("title", f"Step {n}")
    components = step.get("components", [])

    comp_names = [c.get("name") for c in components if isinstance(c, dict) and c.get("name")]
    if not comp_names or len(comp_names) < 2:
        comp_names = [title[:18], "Core Engine", "Process Logic", "Output Verification"]

    diag = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(diag)

    # 0. Subtle Flow Grid
    for gx in range(0, panel_w, 28):
        d.line([(gx, 0), (gx, panel_h)], fill=(255, 255, 255, 6), width=1)
    for gy in range(0, panel_h, 28):
        d.line([(0, gy), (panel_w, gy)], fill=(255, 255, 255, 6), width=1)

    tcx, tcy = panel_w // 2, 135

    # 1. Flowchart Step Nodes (Horizontal chain with arrows)
    node_w, node_h = 130, 48
    gap = 25
    total_w = len(comp_names[:3]) * node_w + (len(comp_names[:3]) - 1) * gap
    start_x = tcx - total_w // 2

    for idx, cname in enumerate(comp_names[:3]):
        nx = start_x + idx * (node_w + gap)
        ny = tcy - node_h // 2
        is_current = (idx == ((n - 1) % len(comp_names[:3])))
        border_col = EMERALD if is_current else accent
        bg_col = (20, 26, 46, 235) if is_current else (12, 16, 28, 220)

        # Draw Node Box
        d.rounded_rectangle([(nx, ny), (nx + node_w, ny + node_h)], radius=10, fill=bg_col, outline=(*border_col, 220), width=2)

        # Node Index Circle
        d.ellipse([nx + 8, ny + 12, nx + 30, ny + 34], fill=(*border_col, 200))
        d.text((nx + 14, ny + 15), f"{idx + 1}", fill=TXT_WHITE, font=_font(11, bold=True))

        # Node Label with auto truncation & wrap safety
        clean_lbl = cname[:15].upper()
        d.text((nx + 36, ny + 17), clean_lbl, fill=TXT_WHITE, font=_font(9, bold=True))

        # Flow Connector Line & Arrow to next node
        if idx < len(comp_names[:3]) - 1:
            ax1 = nx + node_w
            ax2 = ax1 + gap
            ay = tcy
            d.line([(ax1, ay), (ax2, ay)], fill=(*border_col, 180), width=2)
            d.polygon([(ax2, ay), (ax2 - 6, ay - 4), (ax2 - 6, ay + 4)], fill=(*border_col, 220))

    # Flowchart Section Badge
    d.rounded_rectangle([(16, 12), (230, 32)], radius=6, fill=(*BG_DARK, 220), outline=(*accent, 140))
    d.text((24, 16), f"FLOWCHART · PHASE 0{n}", fill=TXT_SILVER, font=_font(9, bold=True))

    # Divider Line
    div_y = 280
    d.line([(20, div_y), (panel_w - 20, div_y)], fill=(*accent, 90), width=1)
    
    div_cx = panel_w // 2
    d.rounded_rectangle([(div_cx - 105, div_y - 10), (div_cx + 105, div_y + 10)], radius=10, fill=(10, 12, 20, 240), outline=(*accent, 180))
    d.text((div_cx - 93, div_y - 6), "SYSTEM SCHEMATIC ARCHITECTURE", fill=TXT_WHITE, font=_font(9, bold=True))

    # 2. Bottom Schematic Radial Network
    bcx, bcy = panel_w // 2, 445
    core_r = 38
    d.ellipse([bcx - core_r, bcy - core_r, bcx + core_r, bcy + core_r], fill=(16, 20, 38, 240), outline=(*accent, 230), width=3)
    d.ellipse([bcx - 16, bcy - 16, bcx + 16, bcy + 16], fill=(*accent, 220))
    d.text((bcx - 8, bcy - 10), f"0{n}", fill=TXT_WHITE, font=_font(14, bold=True))

    node_angles = [0, 60, 120, 180, 240, 300]
    display_nodes = comp_names + ["INPUT", "EXECUTE", "VERIFY"]

    for idx, ang in enumerate(node_angles):
        rad = math.radians(ang)
        x_end = bcx + int(115 * math.cos(rad))
        y_end = bcy + int(115 * math.sin(rad))

        d.line([(bcx, bcy), (x_end, y_end)], fill=(*accent, 140), width=2)
        nr = 8
        col = EMERALD if idx == ((n - 1) % 6) else accent
        d.ellipse([x_end - nr, y_end - nr, x_end + nr, y_end + nr], fill=(16, 20, 34, 240), outline=(*col, 240), width=2)

        lbl = display_nodes[idx % len(display_nodes)].upper()[:12]
        badge_w = min(100, max(50, len(lbl) * 7 + 12))
        lbl_x = x_end + 12 if math.cos(rad) >= 0 else x_end - badge_w - 12
        lbl_y = y_end - 9

        d.rounded_rectangle([(lbl_x, lbl_y), (lbl_x + badge_w, lbl_y + 18)], radius=5, fill=(10, 14, 24, 220), outline=(*col, 160))
        d.text((lbl_x + 6, lbl_y + 3), lbl, fill=TXT_WHITE, font=_font(8, bold=True))

    canvas.alpha_composite(diag, (0, 56))


def build_slide(step: dict, total: int, output_path: str, preloaded_img: Image.Image = None, topic: str = "") -> str:
    n         = step.get("step_number", 1)
    title     = step.get("title", f"Step {n}")
    narration = step.get("narration", "")

    ACCENTS = [(99, 102, 241), (139, 92, 246), (34, 211, 238), (245, 158, 11), (16, 185, 129), (244, 63, 94), (224, 231, 255)]
    accent  = ACCENTS[(n - 1) % len(ACCENTS)]

    # Agnes+Sora+AnimateDiff: generate_cinematic_visual ALWAYS returns an image
    # (either Pollinations photorealistic AI image or rich cinematic PIL scene)
    ai_img = preloaded_img or sora_engine.generate_cinematic_visual(topic or title, step)
    if ai_img is None:  # ultimate safety net
        ai_img = _fetch_image(step.get("image_prompt", title))

    canvas = _new_canvas()

    # ── Cinematic widescreen layout: 68% visual | 32% narration panel ────────
    IMG_X2 = int(W * 0.68)
    IMG_Y1 = 52
    IMG_Y2 = H - 44
    panel_w = IMG_X2
    panel_h = IMG_Y2 - IMG_Y1

    if ai_img:
        src_w, src_h = ai_img.size
        scale = max(panel_w / src_w, panel_h / src_h)
        ai_fit = ai_img.resize((int(src_w * scale), int(src_h * scale)), Image.LANCZOS)
        left = (ai_fit.width - panel_w) // 2
        top  = (ai_fit.height - panel_h) // 2
        ai_fit = ai_fit.crop((left, top, left + panel_w, top + panel_h))
        canvas.paste(ai_fit, (0, IMG_Y1))

        # Cinematic gradient blend on right edge
        fade_w = 110
        fade = Image.new("RGBA", (fade_w, panel_h), (0, 0, 0, 0))
        fd = ImageDraw.Draw(fade)
        for x in range(fade_w):
            alpha = int((x / fade_w) * 240)
            fd.line([(x, 0), (x, panel_h)], fill=(*BG_DARK, alpha))
        canvas.alpha_composite(fade, (IMG_X2 - fade_w, IMG_Y1))

        # Bottom cinematic vignette on visual panel
        vig_h = 100
        vig = Image.new("RGBA", (panel_w, vig_h), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vig)
        for y in range(vig_h):
            alpha = int((y / vig_h) * 180)
            vd.line([(0, y), (panel_w, y)], fill=(*BG_DARK, alpha))
        canvas.alpha_composite(vig, (0, IMG_Y2 - vig_h))


    # ── Cinematic Step Label overlay on bottom-left of visual panel ──────────
    ovl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ovl)
    step_lbl = f"STEP {n:02d}  ·  {title.upper()[:40]}"
    od.rounded_rectangle([(14, IMG_Y2 - 38), (min(len(step_lbl)*9 + 30, panel_w - 20), IMG_Y2 - 10)],
                         radius=6, fill=(8, 8, 11, 210), outline=(*accent, 180))
    od.text((24, IMG_Y2 - 32), step_lbl, fill=TXT_WHITE, font=_font(12, bold=True))
    canvas.alpha_composite(ovl)

    # AI Teacher Host Avatar badge
    _draw_teacher_avatar(canvas, panel_w, accent)

    # ── Right narration panel ─────────────────────────────────────────────────
    PNL_X = IMG_X2 - 12
    _alpha_rect(canvas, PNL_X, 0, W, H, (*BG_DARK, 252))
    _alpha_rect(canvas, PNL_X, IMG_Y1, PNL_X + 3, IMG_Y2, (*accent, 230))

    # ── Top bar ───────────────────────────────────────────────────────────────
    _alpha_rect(canvas, 0, 0, W, IMG_Y1, (8, 8, 11, 240))
    _alpha_rect(canvas, 0, IMG_Y1 - 2, W, IMG_Y1, (*accent, 100))

    d = ImageDraw.Draw(canvas)

    # Brand
    _alpha_rect(canvas, 14, 10, 110, 42, (20, 22, 38, 240), radius=8)
    _alpha_rect(canvas, 14, 10, 110, 42, (*accent, 170), radius=8)
    d.text((24, 16), "VisuAIze", fill=TXT_WHITE, font=_font(16, bold=True))
    d.text((124, 17), "AI Problem-Solving Video Engine", fill=TXT_SILVER, font=_font(12, bold=True))

    # Step counter pill (top-right)
    pill = f"STEP {n:02d} / {total:02d}"
    _alpha_rect(canvas, W - 138, 10, W - 12, 42, (20, 22, 38, 240), radius=20)
    _alpha_rect(canvas, W - 138, 10, W - 12, 42, (*accent, 170), radius=20)
    d.text((W - 126, 17), pill, fill=TXT_WHITE, font=_font(12, bold=True))

    # ── Narration panel content ───────────────────────────────────────────────
    TX = PNL_X + 24
    TW = W - TX - 18
    ty = IMG_Y1 + 16

    # Phase badge
    _alpha_rect(canvas, TX, ty, TX + 78, ty + 22, (*accent, 55), radius=5)
    d.text((TX + 6, ty + 4), f"PHASE {n}", fill=accent, font=_font(11, bold=True))
    ty += 30

    # Step title (large, bold)
    title_font = _font(26, bold=True)
    title_lines = _wrap(title, title_font, TW, d)
    for line in title_lines[:2]:
        d.text((TX + 1, ty + 1), line, fill=(0, 0, 0, 160), font=title_font)
        d.text((TX, ty), line, fill=TXT_WHITE, font=title_font)
        ty += 34
    ty += 6

    # Divider
    _alpha_rect(canvas, TX, ty, TX + TW, ty + 1, (*accent, 60))
    ty += 14

    # Narration label
    d.text((TX, ty), "NARRATION", fill=(*accent, 180), font=_font(10, bold=True))
    ty += 18

    # Narration text
    narr_font = _font(15)
    narr_lines = _wrap(narration, narr_font, TW, d)
    for line in narr_lines[:6]:
        d.text((TX, ty), line, fill=TXT_SILVER, font=narr_font)
        ty += 24

    # ── Bottom progress bar ───────────────────────────────────────────────────
    BAR_Y = H - 18
    pct    = n / total
    fill_w = int(W * pct)
    _alpha_rect(canvas, 0, BAR_Y, W, BAR_Y + 8, (255, 255, 255, 20))
    if fill_w > 0:
        _alpha_rect(canvas, 0, BAR_Y, fill_w, BAR_Y + 8, (*accent, 230))
    d = ImageDraw.Draw(canvas)
    d.text((14, BAR_Y - 18), f"{int(pct * 100)}% complete  ·  Step {n} of {total}", fill=TXT_MUTED, font=_font(11))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, "PNG", quality=92)
    return output_path


def generate_all_images(steps: list, output_dir: str, topic: str = "",
                        visual_style: str = "classic") -> list[str]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    total = len(steps)
    if total == 0:
        return []

    print(f"\n🎨 Generating {total} {visual_style.upper()} style AI Visual Slides...")

    # Load style renderer
    try:
        import style_renderer
        style_cfg = style_renderer.get_style(visual_style)
        use_style = True
    except Exception as e:
        print(f"  [Style] style_renderer unavailable: {e} — using classic")
        style_cfg = None
        use_style = False

    paths = []
    for i, step in enumerate(steps):
        n = step.get("step_number", i + 1)
        out_path = os.path.join(output_dir, f"step_{n:02d}.png")
        print(f"  [Visual Engine] Step {n}/{total}: {step.get('title', '')}...")

        # Enhance AI image prompt with style keywords
        if use_style:
            try:
                step = dict(step)
                orig_prompt = step.get("motion_prompt") or step.get("image_prompt", "")
                step["motion_prompt"] = style_renderer.apply_style_to_image_prompt(
                    orig_prompt, visual_style
                )
                step["image_prompt"] = step["motion_prompt"]
            except Exception:
                pass

        ai_img = sora_engine.generate_cinematic_visual(topic or step.get("title", ""), step)
        build_slide(step, total, out_path, preloaded_img=ai_img, topic=topic)

        # Apply style overlay to finished slide
        if use_style:
            try:
                from PIL import Image as PilImg
                img = PilImg.open(out_path).convert("RGBA")
                img = style_renderer.apply_style_to_frame(img, visual_style, step)
                img.convert("RGB").save(out_path, "PNG", quality=92)
            except Exception as se:
                print(f"  [Style] Overlay skipped for step {n}: {se}")

        paths.append(out_path)
        if i < total - 1:
            time.sleep(0.5)

    print(f"✅ All {total} {visual_style.title()} Visual Slides Ready!")
    return paths

