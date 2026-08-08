"""
VisuAIze - Real AI Image Generator (Pollinations API - 100% FREE)
================================================================
For each step, this module:
  1. Takes the AI-generated "image_prompt" from the step
  2. Calls Pollinations AI (free, no API key) to get a REAL image
  3. Resizes it to 1280x720 (HD)
  4. Overlays a split layout:
       - LEFT 55%  : real AI image
       - RIGHT 45% : dark glass panel with step title + narration
  5. Adds top navbar (VisuAIze branding + step counter)
  6. Adds bottom progress bar
  7. Falls back to a clean gradient slide if API fails
"""

import os
import time
import urllib.parse
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Canvas ──────────────────────────────────────────────────────────────────
WIDTH  = 1280
HEIGHT = 720

# ── Color Palette ───────────────────────────────────────────────────────────
C_BG_TOP      = (10, 12, 22)
C_BG_BOT      = (20, 23, 42)
C_PANEL_BG    = (18, 21, 38, 230)   # RGBA dark glass right panel
C_PRIMARY     = (88, 101, 242)
C_PRIMARY_LGT = (124, 136, 245)
C_ACCENT      = (255, 184, 0)
C_GREEN       = (52, 211, 153)
C_WHITE       = (255, 255, 255)
C_MUTED       = (160, 166, 190)

# ── Pollinations API ─────────────────────────────────────────────────────────
POLL_BASE = "https://image.pollinations.ai/prompt/{prompt}?width=768&height=512&nologo=true&enhance=true"
TIMEOUT   = 60   # seconds to wait for each image
RETRY_GAP = 3    # seconds between retries


# ── Font loader ──────────────────────────────────────────────────────────────
def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    win_bold  = ["C:/Windows/Fonts/arialbd.ttf",  "C:/Windows/Fonts/segoeuib.ttf"]
    win_reg   = ["C:/Windows/Fonts/arial.ttf",    "C:/Windows/Fonts/segoeui.ttf"]
    linux_bold = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                  "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                  "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"]
    linux_reg  = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                  "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                  "/usr/share/fonts/truetype/freefont/FreeSans.ttf"]
    candidates = (win_bold + linux_bold) if bold else (win_reg + linux_reg)
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


# ── Text wrapper ─────────────────────────────────────────────────────────────
def _wrap(text: str, font, max_w: int, draw: ImageDraw.ImageDraw) -> list:
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


# ── Gradient background (fallback) ──────────────────────────────────────────
def _gradient_bg() -> Image.Image:
    img = Image.new("RGBA", (WIDTH, HEIGHT))
    d = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(C_BG_TOP[0] + (C_BG_BOT[0] - C_BG_TOP[0]) * t)
        g = int(C_BG_TOP[1] + (C_BG_BOT[1] - C_BG_TOP[1]) * t)
        b = int(C_BG_TOP[2] + (C_BG_BOT[2] - C_BG_TOP[2]) * t)
        d.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))
    return img


# ── Fetch real image from Pollinations ──────────────────────────────────────
def _fetch_pollinations(prompt: str) -> Image.Image | None:
    """
    Downloads a real AI image from Pollinations (free, no key needed).
    Returns PIL Image or None on failure.
    """
    # Enhance the prompt for educational/visual clarity
    enhanced = (
        f"{prompt}, educational illustration, highly detailed, "
        "bright and clear, professional infographic style, "
        "vibrant colors, no text overlays, photorealistic or vector art"
    )
    encoded = urllib.parse.quote(enhanced)
    url = POLL_BASE.format(prompt=encoded)

    for attempt in range(2):
        try:
            print(f"      🌐 Pollinations API call (attempt {attempt+1})...")
            resp = requests.get(url, timeout=TIMEOUT)
            if resp.status_code == 200 and len(resp.content) > 5000:
                img = Image.open(BytesIO(resp.content)).convert("RGBA")
                print(f"      ✅ Real AI image downloaded ({len(resp.content)//1024} KB)")
                return img
            else:
                print(f"      ⚠️  Bad response: {resp.status_code}, size={len(resp.content)}")
        except Exception as e:
            print(f"      ⚠️  Pollinations error: {e}")
        if attempt == 0:
            time.sleep(RETRY_GAP)

    return None


# ── Compose the final slide frame ─────────────────────────────────────────────
def build_visual_slide(step: dict, total_steps: int, output_path: str) -> str:
    """
    Builds one HD video frame (1280x720) with:
      - Real AI image filling the LEFT 55% of the frame
      - Dark glass info panel on the RIGHT 45%
      - Top navbar: VisuAIze logo + step counter
      - Bottom progress bar
    Falls back to full-screen gradient if image fetch fails.
    """
    n         = step.get("step_number", 1)
    title     = step.get("title", f"Step {n}")
    narration = step.get("narration", "")
    img_prompt = step.get("image_prompt", title)

    print(f"\n  🎨 Building visual slide {n}/{total_steps}: '{title}'")

    # ── 1. Try to get real AI image ─────────────────────────────────────────
    ai_image = _fetch_pollinations(img_prompt)

    # ── 2. Create base canvas ───────────────────────────────────────────────
    canvas = _gradient_bg()

    if ai_image:
        # ── 3A. Split layout: image LEFT (55%), panel RIGHT (45%) ──────────
        img_w = int(WIDTH * 0.57)
        img_h = HEIGHT

        # Resize AI image to fill left panel (crop to fit)
        ai_resized = ai_image.resize((img_w, img_h), Image.LANCZOS)

        # Slightly blur edges for smooth blend
        canvas.paste(ai_resized.convert("RGBA"), (0, 0))

        # Gradient overlay on right edge of image (for smooth blend into panel)
        blend = Image.new("RGBA", (120, img_h), (0, 0, 0, 0))
        bd = ImageDraw.Draw(blend)
        for x in range(120):
            alpha = int((x / 120) * 200)
            bd.line([(x, 0), (x, img_h)], fill=(*C_BG_BOT, alpha))
        canvas.alpha_composite(blend, dest=(img_w - 120, 0))

        # ── 4A. Right glass panel ───────────────────────────────────────────
        panel_x = img_w - 60
        panel   = Image.new("RGBA", (WIDTH - panel_x, HEIGHT), C_PANEL_BG)
        canvas.alpha_composite(panel, dest=(panel_x, 0))

        # Left accent border on panel
        acc = Image.new("RGBA", (4, HEIGHT - 100), (*C_PRIMARY_LGT, 255))
        canvas.alpha_composite(acc, dest=(panel_x + 20, 50))

    else:
        # ── 3B. Fallback: full-screen gradient with centered text ───────────
        print(f"      ℹ️  Using gradient fallback for step {n}")
        panel_x = 0

    # ── 5. Draw all text on final canvas ────────────────────────────────────
    d = ImageDraw.Draw(canvas)

    # ── TOP NAVBAR ──────────────────────────────────────────────────────────
    # Semi-transparent top bar
    top_bar = Image.new("RGBA", (WIDTH, 58), (0, 0, 0, 160))
    canvas.alpha_composite(top_bar, dest=(0, 0))
    d = ImageDraw.Draw(canvas)

    # Logo pill
    d.rounded_rectangle([(12, 10), (130, 44)], radius=6, fill=(*C_PRIMARY, 200))
    d.text((20, 17), "▶  VisuAIze", fill=C_WHITE, font=_font(14, bold=True))
    d.text((142, 18), "Step-by-Step Visual Learning", fill=C_MUTED, font=_font(13))

    # Step counter pill (top right)
    pill_txt  = f"STEP {n:02d} OF {total_steps:02d}"
    pill_font = _font(13, bold=True)
    pb        = d.textbbox((0, 0), pill_txt, font=pill_font)
    pw        = (pb[2] - pb[0]) + 28
    px        = WIDTH - pw - 16
    d.rounded_rectangle([(px, 10), (px + pw, 44)], radius=20, fill=(*C_PRIMARY, 230))
    d.text((px + 14, 18), pill_txt, fill=C_WHITE, font=pill_font)

    # ── RIGHT PANEL TEXT (or center if fallback) ─────────────────────────────
    if ai_image:
        tx = panel_x + 36   # text x inside right panel
        tw = WIDTH - tx - 30 # text max width
    else:
        tx = 60
        tw = WIDTH - 120

    # Step phase badge
    badge_txt = f"PHASE {n}"
    d.rounded_rectangle([(tx, 80), (tx + 100, 108)],
                         radius=6, fill=(*C_ACCENT, 50), outline=(*C_ACCENT, 160))
    d.text((tx + 10, 86), badge_txt, fill=C_ACCENT, font=_font(12, bold=True))

    # Step title
    title_font  = _font(34, bold=True)
    title_lines = _wrap(title, title_font, tw, d)
    ty = 118
    for line in title_lines[:2]:
        d.text((tx, ty), line, fill=C_WHITE, font=title_font, stroke_width=1,
               stroke_fill=(0, 0, 0))
        ty += 42

    # Divider line
    d.line([(tx, ty + 8), (WIDTH - 30, ty + 8)], fill=(*C_PRIMARY_LGT, 80), width=1)
    ty += 22

    # "EXPLANATION" label
    d.text((tx, ty), "EXPLANATION", fill=C_PRIMARY_LGT, font=_font(11, bold=True))
    ty += 22

    # Narration body text
    body_font  = _font(19)
    body_lines = _wrap(narration, body_font, tw, d)
    for line in body_lines[:6]:
        d.text((tx, ty), line, fill=C_WHITE, font=body_font)
        ty += 30

    # ── BOTTOM PROGRESS BAR ──────────────────────────────────────────────────
    bar_h   = HEIGHT - 28
    bar_x   = 16
    bar_w   = WIDTH - 32
    bar_thk = 5

    # Track
    d.rounded_rectangle([(bar_x, bar_h), (bar_x + bar_w, bar_h + bar_thk)],
                         radius=3, fill=(255, 255, 255, 40))
    # Fill
    pct    = n / total_steps
    fill_w = int(bar_w * pct)
    if fill_w > 0:
        d.rounded_rectangle([(bar_x, bar_h), (bar_x + fill_w, bar_h + bar_thk)],
                             radius=3, fill=C_GREEN)

    # % complete labels
    d.text((bar_x, bar_h - 18), f"{int(pct*100)}% Complete",
           fill=C_MUTED, font=_font(11, bold=True))
    d.text((bar_x + bar_w, bar_h - 18), f"Step {n} of {total_steps}",
           fill=C_MUTED, font=_font(11), anchor="ra")

    # ── SAVE ─────────────────────────────────────────────────────────────────
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, "PNG", quality=95)
    print(f"      💾 Saved → {Path(output_path).name}")
    return output_path


# ── Public entry point ────────────────────────────────────────────────────────
def generate_all_images(steps: list, output_dir: str) -> list[str]:
    """
    Generates one visual HD frame per step.
    Uses real Pollinations AI images where possible.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    paths = []
    total = len(steps)

    print(f"\n🖼️  Generating {total} real visual slides (Pollinations AI - FREE)...")
    print("    Each image may take 10-30s to generate. Please wait.\n")

    for i, step in enumerate(steps):
        n        = step.get("step_number", i + 1)
        filename = f"step_{n:02d}.png"
        out_path = os.path.join(output_dir, filename)

        build_visual_slide(step, total, out_path)
        paths.append(out_path)

        # Polite delay between API calls to avoid rate limiting
        if i < total - 1:
            print(f"      ⏳ Waiting 4s before next image...")
            time.sleep(4)

    print(f"\n✅  All {total} visual slides ready!")
    return paths
