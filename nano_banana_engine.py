"""
VisuAIze - Nano Banana AI Image Engine v4.0
============================================
Delivers authentic, high-definition AI scene artwork for step-by-step problem-solving tutorials.

Multi-tier Generation Strategy:
  1. Fast Cloud Diffusion (Pollinations Turbo & Flux with multi-endpoint failover)
  2. Hugging Face Inference API (when HF_TOKEN is present)
  3. High-grade Procedural Visualizer (clean geometric schematics & diagrams, never raw prompt dumping)
"""

import os
import sys
import time
import math
import random
import urllib.parse
import requests
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
if hasattr(sys.stderr, "reconfigure"):
    try: sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

# ─────────────────────────────────────────────────────────────────────────────
# STYLE PROMPTS
# ─────────────────────────────────────────────────────────────────────────────
STYLE_PROMPT_PRESETS = {
    "classic": (
        "cinematic 3D render, dark high-tech obsidian atmosphere, luminous volumetric lighting, "
        "glowing cyan and amber edge highlights, 8k octane render, detailed educational concept art, photorealistic"
    ),
    "whiteboard": (
        "crisp architectural diagram and blueprint sketch, clean marker linework, vivid cobalt and emerald accents, "
        "clean white background, precision vector illustration, educational diagram"
    ),
    "kawaii": (
        "vibrant modern anime style educational illustration, studio ghibli aesthetic, charming visual elements, "
        "soft pastel gradients, clean digital linework, warm cozy cinematic lighting"
    ),
    "watercolor": (
        "masterpiece watercolor and gouache conceptual illustration, expressive brushstrokes, dynamic educational artwork, "
        "elegant fluid textures, luminous color washes, fine art"
    ),
    "papercraft": (
        "layered 3D paper cut craft, tactile volumetric lighting, depth and soft ambient shadows, "
        "clean geometric paper sculpture art, modern tactile textures"
    ),
    "retro_print": (
        "vintage scientific lithograph, retro risograph texture, mid-century educational infographic poster, "
        "halftone print aesthetic, stylized warm earth and terracotta palette"
    ),
    "heritage": (
        "classical scientific illustration, Leonardo da Vinci anatomical sketchbook style, golden ratio, "
        "antique sepia and parchment tones, intricate cross-hatching, museum quality"
    )
}

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}

_FONT_CACHE = {}

def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
    ]
    for p in candidates:
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


def _build_nano_banana_prompt(step_title: str, visual_desc: str, style_name: str = "classic", arc_phase: str = "solution") -> str:
    """Builds a concise, high-impact prompt for AI diffusion."""
    style_key = style_name.lower().strip()
    style_suffix = STYLE_PROMPT_PRESETS.get(style_key, STYLE_PROMPT_PRESETS["classic"])

    clean_title = step_title.replace("\n", " ").strip()
    clean_desc = visual_desc.replace("\n", " ").strip()
    for rm in ["no text", "no watermark", "no labels", "prompt", "showing", "concept"]:
        clean_desc = clean_desc.replace(rm, "").strip()

    prompt = f"{clean_title}, {clean_desc[:120]}, {style_suffix}, masterpiece, 16:9 composition, no text watermark"
    return prompt


# ─────────────────────────────────────────────────────────────────────────────
# CORE IMAGE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def generate_nano_banana_image(
    step_title: str,
    visual_desc: str,
    style_name: str = "classic",
    arc_phase: str = "solution",
    width: int = 1280,
    height: int = 720,
    seed: Optional[int] = None,
    timeout: int = 15
) -> Image.Image:
    """
    Generates a high-definition AI scene visual with robust fallbacks:
      1. Pollinations Turbo (Ultra-fast, reliable)
      2. Pollinations Flux (High-fidelity)
      3. Hugging Face Inference API
      4. High-Grade Procedural Diagram Visualizer
    """
    prompt = _build_nano_banana_prompt(step_title, visual_desc, style_name, arc_phase)
    img_seed = seed if seed is not None else random.randint(10000, 999999)
    encoded_prompt = urllib.parse.quote(prompt[:280])

    # 1. Fast Pollinations Endpoints
    models_to_try = ["turbo", "flux"]
    for model_name in models_to_try:
        try:
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={model_name}&seed={img_seed}&nologo=true"
            resp = requests.get(url, headers=HTTP_HEADERS, timeout=timeout)
            if resp.status_code == 200 and len(resp.content) > 4000:
                img = Image.open(BytesIO(resp.content)).convert("RGB")
                if img.size != (width, height):
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
                return img
        except Exception:
            continue

    # 2. Hugging Face FLUX.1-schnell (if token present)
    hf_token = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY")
    if hf_token:
        try:
            hf_url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
            headers = {"Authorization": f"Bearer {hf_token}", **HTTP_HEADERS}
            payload = {"inputs": prompt[:260]}
            resp = requests.post(hf_url, headers=headers, json=payload, timeout=timeout)
            if resp.status_code == 200 and len(resp.content) > 4000:
                img = Image.open(BytesIO(resp.content)).convert("RGB")
                return img.resize((width, height), Image.Resampling.LANCZOS)
        except Exception:
            pass

    # 3. High-grade Procedural Visualizer
    return generate_procedural_scene(step_title, visual_desc, style_name, arc_phase, width, height)


# ─────────────────────────────────────────────────────────────────────────────
# HIGH-GRADE PROCEDURAL VISUALIZER (Clean Graphic Artwork, No Prompt Text Dumping)
# ─────────────────────────────────────────────────────────────────────────────
def generate_procedural_scene(
    step_title: str,
    visual_desc: str,
    style_name: str = "classic",
    arc_phase: str = "solution",
    width: int = 1280,
    height: int = 720
) -> Image.Image:
    """
    Generates a clean, aesthetic educational graphic illustration:
      • Beautiful isometric 3D concept shapes and luminous energy nodes
      • Clean schematic connections
      • Zero raw prompt text dumping
    """
    is_light = style_name.lower() in ["whiteboard", "kawaii", "watercolor", "papercraft"]
    
    if is_light:
        bg_top = (250, 252, 255)
        bg_btm = (235, 242, 250)
        grid_col = (215, 225, 240)
        accent_col = (37, 99, 235)      # Royal Blue
        accent_alt = (16, 185, 129)     # Emerald
        card_fill = (255, 255, 255, 230)
        card_border = (200, 215, 235)
        text_col = (15, 23, 42)
    else:
        bg_top = (8, 12, 24)
        bg_btm = (14, 18, 38)
        grid_col = (25, 35, 65)
        accent_col = (99, 102, 241)     # Indigo
        accent_alt = (236, 72, 153)     # Rose/Pink
        card_fill = (18, 24, 48, 235)
        card_border = (60, 80, 130)
        text_col = (248, 250, 252)

    # 1. Base Gradient
    canvas = Image.new("RGBA", (width, height), (*bg_top, 255))
    draw = ImageDraw.Draw(canvas)
    for y in range(height):
        r = int(bg_top[0] + (bg_btm[0] - bg_top[0]) * (y / height))
        g = int(bg_top[1] + (bg_btm[1] - bg_top[1]) * (y / height))
        b = int(bg_top[2] + (bg_btm[2] - bg_top[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # 2. Isometric Technical Grid
    spacing = 40
    for gx in range(0, width, spacing):
        draw.line([(gx, 0), (gx, height)], fill=(*grid_col, 50), width=1)
    for gy in range(0, height, spacing):
        draw.line([(0, gy), (width, gy)], fill=(*grid_col, 50), width=1)

    # 3. Dynamic Center Diagram / Concept Hub
    cx = width // 2
    cy = height // 2

    # Luminous background glow rings
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    
    for r in range(160, 40, -25):
        od.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(*accent_col, 12),
            outline=(*accent_col, 35),
            width=1
        )
    
    # Draw 3 Interlocking Concept Nodes
    node_radius = 52
    angles = [-math.pi / 2, math.pi / 6, 5 * math.pi / 6]
    orbit_dist = 110
    node_centers = []

    for i, ang in enumerate(angles):
        nx = int(cx + orbit_dist * math.cos(ang))
        ny = int(cy + orbit_dist * math.sin(ang))
        node_centers.append((nx, ny))
        
        # Connect to center
        od.line([(cx, cy), (nx, ny)], fill=(*accent_col, 120), width=2)
        
        # Glow pulse around node
        col = accent_col if i % 2 == 0 else accent_alt
        od.ellipse([nx - node_radius - 8, ny - node_radius - 8, nx + node_radius + 8, ny + node_radius + 8],
                   fill=(*col, 20), outline=(*col, 70), width=1)
        od.ellipse([nx - node_radius, ny - node_radius, nx + node_radius, ny + node_radius],
                   fill=card_fill, outline=card_border, width=2)

    # Center Hub
    center_r = 65
    od.ellipse([cx - center_r - 10, cy - center_r - 10, cx + center_r + 10, cy + center_r + 10],
               fill=(*accent_col, 30), outline=(*accent_col, 100), width=2)
    od.ellipse([cx - center_r, cy - center_r, cx + center_r, cy + center_r],
               fill=card_fill, outline=card_border, width=2)

    canvas.alpha_composite(overlay)

    # 4. Iconography and Text in Hubs
    td = ImageDraw.Draw(canvas)
    
    # Center Title
    clean_topic = step_title.split(":")[0].strip()[:24]
    c_font = _get_font(13, bold=True)
    c_bb = td.textbbox((0, 0), clean_topic, font=c_font)
    cw = c_bb[2] - c_bb[0]
    td.text((cx - cw // 2, cy - 8), clean_topic, fill=text_col, font=c_font)
    
    # Top badge
    arc_labels = {
        "problem": "DIAGNOSTIC FOCUS",
        "analogy": "CONCEPTUAL ANALOGY",
        "solution": "SOLUTION BREAKTHROUGH"
    }
    phase_text = arc_labels.get(arc_phase.lower(), "KEY MECHANISM")
    p_font = _get_font(11, bold=True)
    td.text((28, 28), f"● {phase_text}", fill=accent_col, font=p_font)

    # Node Labels
    sub_labels = ["Core Input", "Processing", "Target State"]
    for i, (nx, ny) in enumerate(node_centers):
        label = sub_labels[i]
        l_font = _get_font(11, bold=True)
        l_bb = td.textbbox((0, 0), label, font=l_font)
        lw = l_bb[2] - l_bb[0]
        td.text((nx - lw // 2, ny - 6), label, fill=text_col, font=l_font)

    return canvas.convert("RGB")
