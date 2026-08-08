"""
VisuAIze - Google Flow Presentation Slide Generator
Renders crisp, high-definition (1280x720) Google Flow style presentation slides
with glassmorphism cards, structured takeaways, step badges, and dynamic progress bars.
No external stock photo dependencies needed.
"""

import math
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Color Palette (Google Flow Dark Theme) ──────────────────────────────────
C_BG_TOP       = (13, 15, 26)       # Deep slate blue
C_BG_BOT       = (22, 25, 44)       # Indigo slate
C_CARD_BG      = (30, 34, 58, 220)  # Glass card
C_CARD_BORDER  = (255, 255, 255, 30)
C_PRIMARY      = (88, 101, 242)     # Vivid Indigo
C_PRIMARY_LGT  = (124, 136, 245)
C_ACCENT       = (255, 184, 0)      # Amber gold
C_GREEN        = (52, 211, 153)     # Emerald
C_TEXT_MAIN    = (255, 255, 255)
C_TEXT_MUTED   = (160, 166, 190)
C_TEXT_DIM     = (110, 116, 140)

WIDTH  = 1280
HEIGHT = 720


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Load robust system fonts across Windows/Linux."""
    candidates = (
        ["arialbd.ttf", "segoeuib.ttf", "Arial Bold.ttf"] if bold
        else ["arial.ttf", "segoeui.ttf", "Arial.ttf"]
    )
    candidates += [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


def _draw_ambient_glow(img: Image.Image, cx: int, cy: int, radius: int, color: tuple):
    """Draws a subtle ambient background glow."""
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    for r in range(radius, 0, -8):
        alpha = int((1 - r / radius) * color[3])
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(color[0], color[1], color[2], alpha))
    return Image.alpha_composite(img, glow)


def _draw_gradient_background() -> Image.Image:
    """Creates a sleek vertical gradient background with ambient light."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(C_BG_TOP[0] + (C_BG_BOT[0] - C_BG_TOP[0]) * t)
        g = int(C_BG_TOP[1] + (C_BG_BOT[1] - C_BG_TOP[1]) * t)
        b = int(C_BG_TOP[2] + (C_BG_BOT[2] - C_BG_TOP[2]) * t)
        d.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

    # Add ambient glow accents
    img = _draw_ambient_glow(img, WIDTH - 200, 150, 280, (*C_PRIMARY, 40))
    img = _draw_ambient_glow(img, 150, HEIGHT - 150, 220, (*C_ACCENT, 25))
    return img


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Wraps text cleanly into multiple lines that fit within max_width."""
    words = text.split()
    lines = []
    curr = []
    for w in words:
        test = " ".join(curr + [w])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            curr.append(w)
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))
    return lines


def build_google_flow_slide(step: dict, total_steps: int, output_path: str) -> str:
    """
    Renders a dedicated Google Flow presentation slide for a single step.
    Features:
      - Top branding and step counter pill
      - Large hero Step Title
      - Glassmorphism action card with key instructions & narration
      - Bottom interactive progress bar & timestamp indicator
    """
    n = step.get("step_number", 1)
    title = step.get("title", f"Step {n}")
    narration = step.get("narration", "")

    # Base background
    img = _draw_gradient_background()
    d = ImageDraw.Draw(img)

    # ── 1. Top Navigation Bar ──────────────────────────────────────────────
    d.line([(0, 64), (WIDTH, 64)], fill=(255, 255, 255, 20), width=1)

    # Logo / Badge
    d.rounded_rectangle([(36, 18), (140, 48)], radius=6, fill=(*C_PRIMARY, 60))
    d.text((50, 25), "▶ VisuAIze", fill=C_TEXT_MAIN, font=_get_font(14, bold=True))
    d.text((156, 26), "Google Flow Presentation Engine", fill=C_TEXT_MUTED, font=_get_font(13))

    # Step Counter Pill (Top Right)
    pill_text = f"STEP {n:02d} OF {total_steps:02d}"
    pill_font = _get_font(13, bold=True)
    pill_bbox = d.textbbox((0, 0), pill_text, font=pill_font)
    pw = (pill_bbox[2] - pill_bbox[0]) + 24
    px = WIDTH - pw - 36
    d.rounded_rectangle([(px, 18), (px + pw, 48)], radius=20, fill=(*C_PRIMARY, 220))
    d.text((px + 12, 25), pill_text, fill=C_TEXT_MAIN, font=pill_font)

    # ── 2. Hero Step Header ────────────────────────────────────────────────
    # Step Badge
    d.rounded_rectangle([(48, 96), (140, 126)], radius=6, fill=(*C_ACCENT, 40), outline=(*C_ACCENT, 140))
    d.text((58, 103), f"PHASE {n}", fill=C_ACCENT, font=_get_font(12, bold=True))

    # Main Step Title (Large & Bold)
    title_font = _get_font(38, bold=True)
    title_lines = _wrap_text(title, title_font, WIDTH - 120, d)
    ty = 142
    for line in title_lines[:2]:
        d.text((48, ty), line, fill=C_TEXT_MAIN, font=title_font)
        ty += 46

    # ── 3. Main Glassmorphism Action Card ──────────────────────────────────
    card_top = max(ty + 16, 250)
    card_bot = HEIGHT - 90
    card_w = WIDTH - 96
    card_rect = [(48, card_top), (48 + card_w, card_bot)]

    # Draw frosted glass card
    glass_card = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glass_card)
    gd.rounded_rectangle(card_rect, radius=16, fill=C_CARD_BG, outline=C_CARD_BORDER, width=2)
    img = Image.alpha_composite(img, glass_card)
    d = ImageDraw.Draw(img)

    # Card Accent Left Bar
    d.rounded_rectangle([(48, card_top + 16), (54, card_bot - 16)], radius=3, fill=C_PRIMARY_LGT)

    # Card Header
    d.text((76, card_top + 24), "KEY ACTION & NARRATION", fill=C_PRIMARY_LGT, font=_get_font(13, bold=True))

    # Narration / Instruction Body
    body_font = _get_font(21)
    body_lines = _wrap_text(narration, body_font, card_w - 64, d)
    by = card_top + 56
    for line in body_lines[:4]:
        d.text((76, by), line, fill=C_TEXT_MAIN, font=body_font)
        by += 32

    # ── 4. Bottom Interactive Progress Bar ─────────────────────────────────
    bar_x = 48
    bar_y = HEIGHT - 40
    bar_w = WIDTH - 96
    bar_h = 6

    # Track
    d.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], radius=3, fill=(255, 255, 255, 40))

    # Fill
    pct = n / total_steps
    fill_w = int(bar_w * pct)
    if fill_w > 0:
        d.rounded_rectangle([(bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h)], radius=3, fill=C_GREEN)

    # Completion text
    d.text((bar_x, bar_y - 20), f"{int(pct * 100)}% Complete", fill=C_TEXT_MUTED, font=_get_font(12, bold=True))
    d.text((bar_x + bar_w, bar_y - 20), f"Step {n} of {total_steps}", fill=C_TEXT_MUTED, font=_get_font(12), anchor="ra")

    # Save final image
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "PNG", quality=95)
    return output_path


def generate_all_images(steps: list, output_dir: str) -> list[str]:
    """
    Renders Google Flow presentation slides for all steps.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    paths = []
    total = len(steps)

    print(f"\n📊 Rendering {total} Google Flow presentation slides...")
    for i, step in enumerate(steps):
        n = step.get("step_number", i + 1)
        filename = f"step_{n:02d}.png"
        out_path = os.path.join(output_dir, filename)

        build_google_flow_slide(step, total, out_path)
        print(f"  ✅ Slide {n}/{total} created → {filename}")
        paths.append(out_path)

    print(f"🎉 All {total} Google Flow slides ready!")
    return paths
