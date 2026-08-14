"""
VisuAIze - Nano Banana AI Image Engine v3.0
============================================
High-speed, style-consistent educational scene generation engine delivering
true NotebookLM-quality visuals.

Supports:
  1. Pollinations.ai Flux & Turbo diffusion endpoints (with User-Agent headers, 20s timeout, auto-retry)
  2. Hugging Face FLUX.1-schnell inference (when HF_TOKEN / HUGGINGFACE_API_KEY is present)
  3. Google Gemini / Imagen API (when GEMINI_API_KEY is available)
  4. High-fidelity Offline Blueprint & Architectural Flowchart Generator (100% offline fallback)
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
# STYLE PROMPT PRESETS
# ─────────────────────────────────────────────────────────────────────────────
STYLE_PROMPT_PRESETS = {
    "classic": (
        "cinematic 3D render, dark high-tech sci-fi atmosphere, obsidian and deep indigo palette, "
        "luminous volumetric lighting, glowing cyan and amber edge highlights, 8k octane render, "
        "hyper-detailed educational concept art, photorealistic masterpiece, no text, no watermark"
    ),
    "whiteboard": (
        "high-contrast technical blueprint and architectural sketch, crisp marker linework on clean white background, "
        "precision technical diagram, crisp vector aesthetic, minimal vivid cobalt and emerald ink accents, "
        "educational masterpiece, clean composition, no text watermark"
    ),
    "kawaii": (
        "vibrant modern anime style educational illustration, studio ghibli aesthetic, charming expressive characters, "
        "soft pastel gradients, clean digital linework, warm cozy cinematic lighting, masterpiece, no text"
    ),
    "watercolor": (
        "masterpiece watercolor and gouache conceptual illustration, expressive brushstrokes, dynamic educational artwork, "
        "elegant fluid textures, luminous color washes, textured paper grain, fine art, no watermark"
    ),
    "papercraft": (
        "layered 3D paper cut craft, tactile volumetric lighting, depth and soft ambient shadows, "
        "clean geometric paper sculpture art, rich tactile textures, modern architectural feel, no text"
    ),
    "retro": (
        "vintage 1960s scientific lithograph, retro risograph texture, mid-century educational infographic poster, "
        "halftone print aesthetic, stylized warm earth and terracotta palette, high fidelity, no watermark"
    ),
    "heritage": (
        "classical scientific illustration, Leonardo da Vinci anatomical sketchbook style, golden ratio, "
        "antique sepia and parchment tones, intricate cross-hatching, museum quality, no watermark"
    )
}

# Standard HTTP headers mimicking modern browser requests
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ─────────────────────────────────────────────────────────────────────────────
# FONT CACHE & HELPER
# ─────────────────────────────────────────────────────────────────────────────
_FONT_CACHE = {}

def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    
    candidates_bold = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "/System/Library/Fonts/HelveticaNeue-Bold.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    candidates_norm = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/System/Library/Fonts/HelveticaNeue.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    
    for p in (candidates_bold if bold else candidates_norm):
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


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    if not text:
        return []
    words = text.split()
    lines = []
    curr = []
    for w in words:
        test = " ".join(curr + [w])
        bb = draw.textbbox((0, 0), test, font=font)
        if (bb[2] - bb[0]) <= max_width:
            curr.append(w)
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def _build_nano_banana_prompt(step_title: str, visual_desc: str, style_name: str = "classic", arc_phase: str = "solution") -> str:
    """Builds an optimized, rich prompt for AI image generation models."""
    style_key = style_name.lower().strip()
    style_suffix = STYLE_PROMPT_PRESETS.get(style_key, STYLE_PROMPT_PRESETS["classic"])

    arc_tones = {
        "problem": "dramatic diagnostic focus, highlighting structural complexity and physical challenge",
        "analogy": "intuitive physical analogy, concrete real-world comparison, crystal clear visual metaphor",
        "solution": "crystal clear architectural breakthrough, functional harmony, luminous illuminated detail"
    }
    tone = arc_tones.get(arc_phase.lower(), "crystal clear educational visualization")

    clean_title = step_title.replace("\n", " ").strip()
    clean_desc = visual_desc.replace("\n", " ").strip()
    clean_desc = clean_desc.replace("no text", "").replace("No text", "").strip()

    full_prompt = f"{clean_title}: {clean_desc}. {tone}, {style_suffix}"
    return full_prompt


# ─────────────────────────────────────────────────────────────────────────────
# CORE GENERATION FUNCTION
# ─────────────────────────────────────────────────────────────────────────────
def generate_nano_banana_image(
    step_title: str,
    visual_desc: str,
    style_name: str = "classic",
    arc_phase: str = "solution",
    width: int = 1280,
    height: int = 720,
    seed: Optional[int] = None,
    timeout: int = 20
) -> Image.Image:
    """
    Generates a high-definition AI scene visual with robust fallbacks:
      1. Pollinations Flux endpoint (auto-retries, User-Agent, 20s timeout)
      2. Pollinations Turbo endpoint (fast fallback)
      3. Hugging Face FLUX.1-schnell (if HF token is present)
      4. High-fidelity Offline Blueprint & Architecture Diagram Generator
    """
    prompt = _build_nano_banana_prompt(step_title, visual_desc, style_name, arc_phase)
    img_seed = seed if seed is not None else random.randint(10000, 999999)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Pollinations AI (Flux & Turbo endpoints with retry & User-Agent)
    # ─────────────────────────────────────────────────────────────────────────
    encoded_prompt = urllib.parse.quote(prompt[:380])
    pollinations_models = ["flux", "turbo"]
    
    for model_name in pollinations_models:
        for attempt in range(2):
            try:
                pollinations_url = (
                    f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                    f"?width={width}&height={height}&model={model_name}&seed={img_seed}&nologo=true&enhance=true"
                )
                resp = requests.get(pollinations_url, headers=HTTP_HEADERS, timeout=timeout)
                if resp.status_code == 200 and len(resp.content) > 4000:
                    img = Image.open(BytesIO(resp.content)).convert("RGB")
                    if img.size != (width, height):
                        img = img.resize((width, height), Image.Resampling.LANCZOS)
                    # Clarity enhancement
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.05)
                    return img
            except Exception:
                time.sleep(0.3)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Hugging Face FLUX.1-schnell (if token is available)
    # ─────────────────────────────────────────────────────────────────────────
    hf_token = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY")
    if hf_token:
        try:
            hf_endpoints = [
                "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
                "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
            ]
            for hf_url in hf_endpoints:
                try:
                    headers = {
                        "Authorization": f"Bearer {hf_token}",
                        "Content-Type": "application/json",
                        **HTTP_HEADERS
                    }
                    payload = {"inputs": prompt[:300]}
                    resp = requests.post(hf_url, headers=headers, json=payload, timeout=timeout)
                    if resp.status_code == 200 and len(resp.content) > 4000:
                        img = Image.open(BytesIO(resp.content)).convert("RGB")
                        return img.resize((width, height), Image.Resampling.LANCZOS)
                except Exception:
                    continue
        except Exception as e:
            print(f"[NanoBanana/HuggingFace] Fallback: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. High-Fidelity Offline Technical Blueprint Generator
    # ─────────────────────────────────────────────────────────────────────────
    return generate_procedural_scene(step_title, visual_desc, style_name, arc_phase, width, height)


# ─────────────────────────────────────────────────────────────────────────────
# HIGH-FIDELITY OFFLINE BLUEPRINT DIAGRAM GENERATOR
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
    Generates an elegant, high-contrast dark/light theme educational technical diagram
    with real blueprint nodes, connecting vectors, and conceptual badges.
    Completely free of simplistic primitive boxes or green rectangles.
    """
    is_light = style_name.lower() in ["whiteboard", "kawaii", "watercolor", "papercraft", "retro_print"]
    
    # 1. Color System
    if is_light:
        bg_gradient_top = (248, 250, 252)
        bg_gradient_btm = (235, 240, 248)
        grid_line_col   = (210, 220, 235)
        cross_col       = (180, 195, 215)
        card_bg         = (255, 255, 255, 240)
        card_border     = (203, 213, 225, 255)
        text_primary    = (15, 23, 42)
        text_secondary  = (71, 85, 105)
        text_muted      = (148, 163, 184)
        bus_line_col    = (99, 102, 241, 180)
        blueprint_accent= (37, 99, 235)
    else:
        bg_gradient_top = (8, 12, 24)
        bg_gradient_btm = (14, 18, 38)
        grid_line_col   = (25, 34, 60)
        cross_col       = (45, 60, 95)
        card_bg         = (16, 22, 44, 230)
        card_border     = (55, 75, 125, 255)
        text_primary    = (248, 250, 252)
        text_secondary  = (203, 213, 225)
        text_muted      = (120, 140, 175)
        bus_line_col    = (99, 102, 241, 200)
        blueprint_accent= (56, 189, 248)

    phase_accents = {
        "problem":  ((239, 68, 68),  "DIAGNOSTIC & CHALLENGE VECTOR"),
        "analogy":  ((245, 158, 11), "CONCEPTUAL ANALOGY BRIDGE"),
        "solution": ((16, 185, 129), "SYSTEMIC BREAKTHROUGH MATRIX")
    }
    phase_accent_rgb, phase_tag = phase_accents.get(arc_phase.lower(), ((99, 102, 241), "SCHEMATIC ARCHITECTURE"))

    # Base Canvas
    canvas = Image.new("RGBA", (width, height), (*bg_gradient_top, 255))
    draw = ImageDraw.Draw(canvas)

    # Vertical gradient
    for y in range(height):
        ratio = y / max(1, height)
        r = int(bg_gradient_top[0] + (bg_gradient_btm[0] - bg_gradient_top[0]) * ratio)
        g = int(bg_gradient_top[1] + (bg_gradient_btm[1] - bg_gradient_top[1]) * ratio)
        b = int(bg_gradient_top[2] + (bg_gradient_btm[2] - bg_gradient_top[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # 2. Isometric / Blueprint Grid Lines & Crosshairs
    grid_spacing = 38
    for gx in range(0, width, grid_spacing):
        draw.line([(gx, 0), (gx, height)], fill=(*grid_line_col, 70), width=1)
    for gy in range(0, height, grid_spacing):
        draw.line([(0, gy), (width, gy)], fill=(*grid_line_col, 70), width=1)

    for gx in range(grid_spacing * 2, width, grid_spacing * 3):
        for gy in range(grid_spacing * 2, height, grid_spacing * 3):
            draw.line([(gx - 3, gy), (gx + 3, gy)], fill=(*cross_col, 150), width=1)
            draw.line([(gx, gy - 3), (gx, gy + 3)], fill=(*cross_col, 150), width=1)

    # 3. Technical Blueprint Header Ribbon (placed at y=48 so it clears any top branding bars)
    header_font_title = _get_font(12, bold=True)
    top_bar_y = 52
    draw.line([(24, top_bar_y), (width - 24, top_bar_y)], fill=(*blueprint_accent, 120), width=1)
    draw.text((26, top_bar_y - 16), f"BLUEPRINT // {phase_tag}", fill=phase_accent_rgb, font=header_font_title)

    # Extract meaningful concepts for node labels
    desc_words = [w.strip(".,;:\"'()[]") for w in visual_desc.split() if len(w) > 3]
    key_terms = []
    for w in desc_words:
        if w.lower() not in ["this", "that", "with", "from", "into", "showing", "concept", "visual", "step", "like", "will", "cinematic", "octane", "render"]:
            if w.title() not in key_terms:
                key_terms.append(w.title())
    
    default_terms = ["Structural Input", "Core Matrix", "Feedback Loop", "Terminal State"]
    for dt in default_terms:
        if len(key_terms) < 4:
            key_terms.append(dt)

    # 4. Render Architectural Schematic Nodes & Central Core
    # Check width to adapt layout gracefully
    if width <= 800:
        # Left column of nodes (35% width) + Right Core panel (55% width)
        node_w = int(width * 0.40)
        node_h = 92
        start_x = 24
        start_y = 78
        node_gap_y = 28
        core_x = start_x + node_w + 32
        core_w = width - core_x - 24
        core_y = start_y
        core_h = height - start_y - 48
    else:
        node_w = 260
        node_h = 105
        start_x = int(width * 0.06)
        start_y = 78
        node_gap_y = 36
        core_x = int(width * 0.44)
        core_w = int(width * 0.50)
        core_y = start_y
        core_h = int(height * 0.68)

    nodes_coords = []
    node_labels = [
        (f"01. {key_terms[0][:16].upper()}", "Input Vector & Structure Mapping", phase_accent_rgb),
        (f"02. {key_terms[1][:16].upper()}", "Process Transformation Dynamic", blueprint_accent),
        (f"03. {key_terms[2][:16].upper()}", "Synchronized Equilibrium State", (16, 185, 129))
    ]

    for idx, (n_title, n_sub, n_col) in enumerate(node_labels):
        nx = start_x
        ny = start_y + idx * (node_h + node_gap_y)
        nodes_coords.append((nx, ny, node_w, node_h, n_col))

        node_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        nod = ImageDraw.Draw(node_overlay)
        
        # Soft outer glow
        for g in range(3, 0, -1):
            nod.rounded_rectangle(
                [(nx - g, ny - g), (nx + node_w + g, ny + node_h + g)],
                radius=10 + g,
                outline=(*n_col, 20 // g),
                width=1
            )
            
        nod.rounded_rectangle([(nx, ny), (nx + node_w, ny + node_h)], radius=10, fill=card_bg)
        nod.rounded_rectangle([(nx, ny), (nx + node_w, ny + node_h)], radius=10, outline=card_border, width=1)
        nod.rounded_rectangle([(nx, ny), (nx + 4, ny + node_h)], radius=2, fill=(*n_col, 240))

        # Top mini badge
        badge_w = 44
        badge_h = 15
        nod.rounded_rectangle([(nx + 10, ny + 8), (nx + 10 + badge_w, ny + 8 + badge_h)], radius=3, fill=(*n_col, 35))
        nod.rounded_rectangle([(nx + 10, ny + 8), (nx + 10 + badge_w, ny + 8 + badge_h)], radius=3, outline=(*n_col, 140), width=1)
        canvas.alpha_composite(node_overlay)

        td = ImageDraw.Draw(canvas)
        td.text((nx + 14, ny + 9), f"NODE 0{idx+1}", fill=n_col, font=_get_font(8, bold=True))
        td.text((nx + 10, ny + 28), n_title, fill=text_primary, font=_get_font(12, bold=True))
        
        sub_lines = _wrap_text(n_sub, _get_font(9), node_w - 20, td)
        sub_y = ny + 48
        for sl in sub_lines[:2]:
            td.text((nx + 10, sub_y), sl, fill=text_secondary, font=_get_font(9))
            sub_y += 13
            
        td.ellipse([nx + node_w - 18, ny + 12, nx + node_w - 10, ny + 20], fill=n_col)

    # 5. Connecting Bus Vectors
    vector_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    vod = ImageDraw.Draw(vector_overlay)

    for i in range(len(nodes_coords) - 1):
        x1, y1, nw, nh, c1 = nodes_coords[i]
        x2, y2, _, _, c2 = nodes_coords[i + 1]

        cx = x1 + nw // 2
        cy1 = y1 + nh
        cy2 = y2

        vod.line([(cx, cy1), (cx, cy2)], fill=(*c1, 220), width=2)
        arrow_y = cy1 + (cy2 - cy1) // 2
        vod.polygon([(cx - 4, arrow_y - 5), (cx + 4, arrow_y - 5), (cx, arrow_y + 4)], fill=(*c1, 255))

    # Circuit bus traces connecting left nodes to central core
    for idx, (nx, ny, nw, nh, ncol) in enumerate(nodes_coords):
        from_x = nx + nw
        from_y = ny + nh // 2
        to_x = core_x
        to_y = core_y + int(core_h * (0.22 + idx * 0.28))
        mid_x = from_x + (to_x - from_x) // 2

        points = [(from_x, from_y), (mid_x, from_y), (mid_x, to_y), (to_x, to_y)]
        for pt_i in range(len(points) - 1):
            vod.line([points[pt_i], points[pt_i + 1]], fill=(*ncol, 160), width=2)
            
        vod.ellipse([from_x - 3, from_y - 3, from_x + 3, from_y + 3], fill=(*ncol, 255))
        vod.ellipse([to_x - 3, to_y - 3, to_x + 3, to_y + 3], fill=(*ncol, 255))

    canvas.alpha_composite(vector_overlay)

    # 6. Core Panel
    core_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    cod = ImageDraw.Draw(core_overlay)

    for g in range(4, 0, -1):
        cod.rounded_rectangle(
            [(core_x - g, core_y - g), (core_x + core_w + g, core_y + core_h + g)],
            radius=14 + g,
            outline=(*blueprint_accent, 16 // g),
            width=1
        )

    cod.rounded_rectangle([(core_x, core_y), (core_x + core_w, core_y + core_h)], radius=14, fill=card_bg)
    cod.rounded_rectangle([(core_x, core_y), (core_x + core_w, core_y + core_h)], radius=14, outline=card_border, width=1)
    cod.rounded_rectangle([(core_x, core_y), (core_x + core_w, core_y + 32)], radius=12, fill=(*blueprint_accent, 30))
    cod.line([(core_x, core_y + 32), (core_x + core_w, core_y + 32)], fill=(*blueprint_accent, 100), width=1)
    
    canvas.alpha_composite(core_overlay)

    cd = ImageDraw.Draw(canvas)
    cd.text((core_x + 14, core_y + 9), "CORE FUNCTIONAL DYNAMICS", fill=blueprint_accent, font=_get_font(10, bold=True))
    cd.text((core_x + core_w - 110, core_y + 9), "ACTIVE MATRIX", fill=text_muted, font=_get_font(9, bold=True))

    title_font = _get_font(15, bold=True)
    wrapped_title = _wrap_text(step_title, title_font, core_w - 28, cd)
    ty = core_y + 44
    for line in wrapped_title[:2]:
        cd.text((core_x + 14, ty), line, fill=text_primary, font=title_font)
        ty += 20
    ty += 6

    desc_font = _get_font(11)
    wrapped_desc = _wrap_text(visual_desc, desc_font, core_w - 28, cd)
    for line in wrapped_desc[:4]:
        cd.text((core_x + 14, ty), line, fill=text_secondary, font=desc_font)
        ty += 16

    # Badges at bottom of core
    badge_w = (core_w - 38) // 2
    badge_h = 58
    b1_x = core_x + 14
    b1_y = core_y + core_h - badge_h - 16
    
    badge_ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    bov = ImageDraw.Draw(badge_ov)
    bov.rounded_rectangle([(b1_x, b1_y), (b1_x + badge_w, b1_y + badge_h)], radius=8, fill=(*phase_accent_rgb, 20))
    bov.rounded_rectangle([(b1_x, b1_y), (b1_x + badge_w, b1_y + badge_h)], radius=8, outline=(*phase_accent_rgb, 100), width=1)
    
    b2_x = b1_x + badge_w + 10
    bov.rounded_rectangle([(b2_x, b1_y), (b2_x + badge_w, b1_y + badge_h)], radius=8, fill=(*blueprint_accent, 20))
    bov.rounded_rectangle([(b2_x, b1_y), (b2_x + badge_w, b1_y + badge_h)], radius=8, outline=(*blueprint_accent, 100), width=1)
    canvas.alpha_composite(badge_ov)

    bd = ImageDraw.Draw(canvas)
    bd.text((b1_x + 10, b1_y + 8), "VECTOR ALPHA", fill=phase_accent_rgb, font=_get_font(8, bold=True))
    bd.text((b1_x + 10, b1_y + 22), f"{key_terms[0][:14]}", fill=text_primary, font=_get_font(10, bold=True))
    bd.text((b1_x + 10, b1_y + 38), "Status: Active", fill=text_muted, font=_get_font(8))
    
    bd.text((b2_x + 10, b1_y + 8), "VECTOR BETA", fill=blueprint_accent, font=_get_font(8, bold=True))
    bd.text((b2_x + 10, b1_y + 22), f"{key_terms[1][:14]}", fill=text_primary, font=_get_font(10, bold=True))
    bd.text((b2_x + 10, b1_y + 38), "Phase: Sync", fill=text_muted, font=_get_font(8))

    # Bottom footer
    footer_y = height - 28
    cd.line([(24, footer_y), (width - 24, footer_y)], fill=(*grid_line_col, 160), width=1)
    cd.text((26, footer_y + 8), "VISUAIZE SCHEMATIC ENGINE • HIGH-FIDELITY ARCHITECTURE", fill=text_muted, font=_get_font(8, bold=True))

    return canvas.convert("RGB")
