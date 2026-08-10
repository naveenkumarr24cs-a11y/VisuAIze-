import math
import random
import textwrap
from typing import Dict, Any, List, Callable, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ==============================================================================
# VISUAL STYLES CONFIGURATION
# ==============================================================================
# This dictionary contains all the configuration parameters for the 7 visual
# art styles used by the VisuAIze presentation engine.
# 
# Each style defines:
#   - bg: The primary background color of the presentation.
#   - panel_bg: The background color of the side text panel.
#   - accent: The primary accent color for highlights, bullets, and borders.
#   - title_color: The color used for the step title text.
#   - text_color: The color used for the main body narration text.
#   - muted: A softer color used for step numbers and less important text.
#   - border_color: The color used for panel borders (if applicable).
#   - font_scale: A multiplier for font sizes to adjust proportions per style.
#   - rounded: A boolean indicating if the panel corners should be rounded.
# ==============================================================================

STYLES: Dict[str, Dict[str, Any]] = {
    'classic': {
        'bg': (8, 8, 11),          # Very dark near-black
        'panel_bg': (15, 15, 22),
        'accent': (99, 102, 241),  # Indigo
        'title_color': (255, 255, 255),
        'text_color': (220, 220, 235),
        'muted': (120, 120, 140),
        'border_color': (99, 102, 241),
        'font_scale': 1.0,
        'rounded': True,
    },
    'whiteboard': {
        'bg': (250, 250, 248),     # Off-white
        'panel_bg': (255, 255, 255),
        'accent': (30, 80, 200),   # Bold blue marker
        'title_color': (20, 20, 30),
        'text_color': (40, 40, 50),
        'muted': (120, 120, 130),
        'border_color': (30, 80, 200),
        'font_scale': 1.05,
        'rounded': False,
    },
    'kawaii': {
        'bg': (255, 230, 250),     # Light pink
        'panel_bg': (255, 245, 255),
        'accent': (230, 80, 180),  # Hot pink
        'title_color': (150, 20, 120),
        'text_color': (80, 30, 80),
        'muted': (180, 120, 170),
        'border_color': (230, 80, 180),
        'font_scale': 1.0,
        'rounded': True,
    },
    'watercolor': {
        'bg': (235, 245, 255),     # Pale sky blue
        'panel_bg': (245, 252, 255),
        'accent': (60, 160, 220),  # Ocean blue
        'title_color': (20, 60, 120),
        'text_color': (40, 70, 110),
        'muted': (120, 150, 180),
        'border_color': (60, 160, 220),
        'font_scale': 1.0,
        'rounded': True,
    },
    'papercraft': {
        'bg': (245, 235, 220),     # Warm paper
        'panel_bg': (255, 248, 238),
        'accent': (200, 90, 40),   # Terracotta
        'title_color': (100, 40, 20),
        'text_color': (80, 50, 30),
        'muted': (160, 130, 100),
        'border_color': (200, 90, 40),
        'font_scale': 0.95,
        'rounded': False,
    },
    'retro_print': {
        'bg': (240, 228, 195),     # Old newsprint
        'panel_bg': (248, 238, 208),
        'accent': (180, 40, 40),   # Vintage red
        'title_color': (30, 20, 10),
        'text_color': (50, 35, 20),
        'muted': (140, 120, 90),
        'border_color': (180, 40, 40),
        'font_scale': 1.0,
        'rounded': False,
    },
    'heritage': {
        'bg': (30, 15, 10),        # Deep mahogany
        'panel_bg': (45, 25, 15),
        'accent': (200, 160, 60),  # Gold
        'title_color': (220, 190, 120),
        'text_color': (200, 175, 140),
        'muted': (130, 100, 70),
        'border_color': (200, 160, 60),
        'font_scale': 1.0,
        'rounded': True,
    },
}

# ==============================================================================
# PUBLIC FUNCTIONS
# ==============================================================================

def get_style(style_name: str) -> Dict[str, Any]:
    """
    Retrieves the style configuration dictionary based on the provided style_name.
    
    If the requested style is not found in the STYLES dictionary, this function
    will log a warning and gracefully fall back to the 'classic' style, ensuring
    the renderer does not crash due to missing configuration.
    
    Args:
        style_name: The string identifier for the desired visual style.
        
    Returns:
        A dictionary containing the color palette and configuration for the style.
    """
    if not isinstance(style_name, str):
        print(f"Warning: style_name must be a string, got {type(style_name)}. Falling back to 'classic'.")
        return STYLES['classic'].copy()
        
    if style_name not in STYLES:
        print(f"Warning: Style '{style_name}' not found. Falling back to 'classic'.")
        return STYLES['classic'].copy()
        
    return STYLES[style_name].copy()


def apply_style_to_image_prompt(prompt: str, style_name: str) -> str:
    """
    Enhances AI image generation prompts by appending style-appropriate keywords.
    
    This ensures that the generated images match the visual aesthetic of the
    overall presentation. Each style has a specific set of keywords appended
    to guide the AI diffusion model toward the correct output.
    
    Args:
        prompt: The original image generation prompt describing the content.
        style_name: The visual style identifier.
        
    Returns:
        The enhanced prompt string with style keywords appended.
    """
    if not prompt:
        return prompt
        
    appendices = {
        'classic': 'cinematic lighting, highly detailed, high quality, 8k resolution, photorealistic',
        'whiteboard': 'hand-drawn whiteboard style, marker lines, clean white background, educational diagram, line art, simple',
        'kawaii': 'kawaii anime style, pastel colors, cute chibi aesthetic, soft lighting, vector art, adorable',
        'watercolor': 'soft watercolor painting, blended washes, artistic watercolor texture, painterly brushstrokes, traditional art',
        'papercraft': 'papercraft style, cut paper, origami, layered paper, drop shadows, flat colors, tactile',
        'retro_print': 'retro 1950s print style, vintage comic book, halftone dots, faded colors, nostalgic',
        'heritage': 'vintage etching, antique painting style, classical art, detailed engraving, golden hour lighting, masterful'
    }
    
    # Fallback to classic if style is unknown
    suffix = appendices.get(style_name, appendices['classic'])
    
    # Clean up the original prompt and append the suffix
    clean_prompt = prompt.strip()
    if clean_prompt.endswith(','):
        return f"{clean_prompt} {suffix}"
    else:
        return f"{clean_prompt}, {suffix}"


def apply_style_to_frame(frame: Image.Image, style_name: str, step_data: dict) -> Image.Image:
    """
    Applies the style decorators and panel overlays to a presentation frame.
    
    This function processes the full slide frame, applying a styled panel on
    the right side (41.5% width), drawing style-specific decorations (like
    borders, shadows, or accents), and optionally applying full-frame texture
    overlays (like halftone dots or watercolor blurs).
    
    Args:
        frame: The base background image to decorate. Expected size ~1280x720.
        style_name: The string identifier for the visual style.
        step_data: Dictionary containing presentation step details (unused here, but passed for API compliance).
        
    Returns:
        A new PIL Image object with the style applied.
    """
    if not isinstance(frame, Image.Image):
        print("Error: Input frame is not a valid PIL Image.")
        return frame
        
    try:
        # Work on an RGBA copy of the frame to support alpha blending
        img = frame.convert('RGBA')
        width, height = img.size
        
        # Get the style configuration, falling back to 'classic' if needed
        style = get_style(style_name)
        
        # Calculate panel boundaries based on 41.5% ratio
        panel_width_ratio = 0.415
        panel_w = int(width * panel_width_ratio)
        panel_x = width - panel_w
        
        # Create an overlay layer for the panel background to handle transparency
        panel_overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(panel_overlay)
        
        # Extract panel background color and determine alpha transparency
        p_bg = style['panel_bg']
        # Classic and Heritage styles use semi-transparent panels; others are opaque
        bg_alpha = 240 if style_name in ['classic', 'heritage'] else 255
        
        # Define the bounding box for the text panel
        panel_box = [panel_x, 0, width, height]
        
        # Draw the panel background shape (rounded or rectangular)
        if style.get('rounded', False):
            # Draw rectangle with rounded left corners
            radius = 30
            # Main central block
            draw_overlay.rectangle([panel_x + radius, 0, width, height], 
                                   fill=(p_bg[0], p_bg[1], p_bg[2], bg_alpha))
            # Left edge block
            draw_overlay.rectangle([panel_x, radius, panel_x + radius, height - radius], 
                                   fill=(p_bg[0], p_bg[1], p_bg[2], bg_alpha))
            # Top-left corner rounded slice
            draw_overlay.pieslice([panel_x, 0, panel_x + radius * 2, radius * 2], 
                                  180, 270, fill=(p_bg[0], p_bg[1], p_bg[2], bg_alpha))
            # Bottom-left corner rounded slice
            draw_overlay.pieslice([panel_x, height - radius * 2, panel_x + radius * 2, height], 
                                  90, 180, fill=(p_bg[0], p_bg[1], p_bg[2], bg_alpha))
        else:
            # Draw standard rectangular panel
            draw_overlay.rectangle(panel_box, fill=(p_bg[0], p_bg[1], p_bg[2], bg_alpha))
        
        # Composite panel background over the base frame
        img = Image.alpha_composite(img, panel_overlay)
        
        # Apply style-specific decorations (borders, shadows, lines, etc.)
        img = _apply_decorations(img, style_name, style, panel_x, panel_w, height)
        
        # Apply full-frame or panel-specific texture overlays (grain, blur, halftone)
        img = _add_texture_overlay(img, style_name)
        
        # Return as standard RGB image suitable for saving to JPEG/PNG
        return img.convert('RGB')
    
    except Exception as e:
        import traceback
        print(f"Error applying style to frame: {e}")
        traceback.print_exc()
        # Ensure we always return a valid image, even on failure
        return frame.convert('RGB') if isinstance(frame, Image.Image) else frame


def draw_style_text_panel(
    draw: ImageDraw.Draw, 
    style: dict, 
    x: int, 
    y: int, 
    w: int, 
    h: int, 
    title: str, 
    narration: str, 
    step_num: int, 
    components: List[str], 
    font_fn: Callable
) -> None:
    """
    Renders the text content onto the right-side panel using the specified style.
    
    This function handles the complex layout of the presentation slide, including:
    - Step number header
    - Slide Title (with automatic text wrapping)
    - Narration body text (with automatic text wrapping)
    - Bulleted list of key components
    
    Args:
        draw: The ImageDraw context to draw on.
        style: The style configuration dictionary.
        x: The X coordinate for the start of the panel.
        y: The Y coordinate for the start of the panel.
        w: The width of the panel.
        h: The height of the panel.
        title: The slide title text.
        narration: The main body text.
        step_num: The current presentation step number.
        components: A list of key component strings to render as bullets.
        font_fn: A factory function `font_fn(size, bold=False)` returning an ImageFont.
    """
    try:
        # Define layout margins
        margin_x = 40
        margin_y = 50
        current_y = y + margin_y
        
        # Retrieve the font scale modifier for this style
        font_scale = style.get('font_scale', 1.0)
        
        # Initialize fonts based on scaled sizes
        title_size = int(40 * font_scale)
        step_size = int(20 * font_scale)
        text_size = int(24 * font_scale)
        bullet_size = int(20 * font_scale)
        
        title_font = font_fn(title_size, bold=True)
        step_font = font_fn(step_size, bold=True)
        text_font = font_fn(text_size, bold=False)
        bullet_font = font_fn(bullet_size, bold=False)
        
        # ---------------------------------------------------------
        # 1. Render Step Number
        # ---------------------------------------------------------
        step_text = f"STEP {step_num}"
        draw.text((x + margin_x, current_y), step_text, font=step_font, fill=style['accent'])
        current_y += step_size + 15
        
        # ---------------------------------------------------------
        # 2. Render Title
        # ---------------------------------------------------------
        # Estimate the maximum number of characters that fit in the panel width
        # Average character width is approximated as half the font size
        char_w_title = title_size * 0.5
        wrap_width_title = max(10, int((w - margin_x * 2) / char_w_title))
        wrapped_title = textwrap.fill(title, width=wrap_width_title)
        
        draw.multiline_text(
            (x + margin_x, current_y), 
            wrapped_title, 
            font=title_font, 
            fill=style['title_color'], 
            spacing=10
        )
        
        # Calculate vertical advancement based on number of wrapped lines
        title_lines = wrapped_title.split('\n')
        current_y += len(title_lines) * (title_size + 10) + 30
        
        # ---------------------------------------------------------
        # 3. Render Narration Body Text
        # ---------------------------------------------------------
        char_w_text = text_size * 0.5
        wrap_width_text = max(15, int((w - margin_x * 2) / char_w_text))
        wrapped_narration = textwrap.fill(narration, width=wrap_width_text)
        
        draw.multiline_text(
            (x + margin_x, current_y), 
            wrapped_narration, 
            font=text_font, 
            fill=style['text_color'], 
            spacing=8
        )
        
        narr_lines = wrapped_narration.split('\n')
        current_y += len(narr_lines) * (text_size + 8) + 40
        
        # ---------------------------------------------------------
        # 4. Render Components List (Bullet Points)
        # ---------------------------------------------------------
        if components and isinstance(components, list) and len(components) > 0:
            # Draw the list header
            draw.text((x + margin_x, current_y), "Key Components:", font=step_font, fill=style['muted'])
            current_y += step_size + 15
            
            # Draw each bullet item
            for comp in components:
                # Wrap bullet text, subtracting space for the bullet dot indentation
                wrapped_comp = textwrap.fill(str(comp), width=wrap_width_text - 4)
                
                # Draw the bullet dot
                bullet_r = 6
                bx = x + margin_x + 10
                by = current_y + (bullet_size) / 2
                draw.ellipse(
                    [bx - bullet_r, by - bullet_r, bx + bullet_r, by + bullet_r], 
                    fill=style['accent']
                )
                
                # Draw the bullet text
                draw.multiline_text(
                    (x + margin_x + 30, current_y), 
                    wrapped_comp, 
                    font=bullet_font, 
                    fill=style['text_color'], 
                    spacing=6
                )
                
                comp_lines = wrapped_comp.split('\n')
                current_y += len(comp_lines) * (bullet_size + 6) + 15

    except Exception as e:
        import traceback
        print(f"Error drawing style text panel: {e}")
        traceback.print_exc()


# ==============================================================================
# INTERNAL HELPER FUNCTIONS
# ==============================================================================

def _apply_decorations(img: Image.Image, style_name: str, style: dict, panel_x: int, panel_w: int, height: int) -> Image.Image:
    """
    Applies custom graphical elements based on the selected style to the panel area.
    
    This handles all the vector-based drawing operations like lines, stars,
    borders, and drop shadows that define the unique look of each style.
    """
    draw = ImageDraw.Draw(img)
    width = img.width
    
    try:
        if style_name == 'whiteboard':
            # Add faint horizontal lines across the panel simulating a lined board
            line_color = (200, 200, 220, 100)
            y_start = 50
            spacing = 40
            for y in range(y_start, height, spacing):
                draw.line([(panel_x + 20, y), (width - 20, y)], fill=line_color, width=2)
                
        elif style_name == 'kawaii':
            # Draw cute pastel stars scattered in the panel background
            star_color = (255, 200, 220, 150)
            for _ in range(8):
                sx = random.randint(panel_x + 20, width - 20)
                sy = random.randint(20, height - 20)
                _draw_star(draw, sx, sy, 12, star_color)
                
        elif style_name == 'watercolor':
            # Simulate a soft, bleeding edge on the left side of the panel
            edge_color = style['accent']
            draw.line([(panel_x, 0), (panel_x, height)], 
                      fill=(edge_color[0], edge_color[1], edge_color[2], 100), width=10)
            draw.line([(panel_x + 2, 0), (panel_x + 2, height)], 
                      fill=(edge_color[0], edge_color[1], edge_color[2], 50), width=20)
            
        elif style_name == 'papercraft':
            # Draw a drop shadow on the left edge of the panel to look like cut paper
            shadow_color = (0, 0, 0, 40)
            draw.rectangle([panel_x - 12, 10, panel_x, height + 10], fill=shadow_color)
            
            # Add a flat color ribbon/tab overlapping the edge
            ribbon_color = style['accent']
            draw.polygon([
                (panel_x - 20, 30), 
                (panel_x + 100, 30), 
                (panel_x + 80, 70), 
                (panel_x - 20, 70)
            ], fill=ribbon_color)
            
        elif style_name == 'retro_print':
            # Vintage double border frame inside the panel
            border_col = style['border_color']
            m = 15
            # Outer thick border
            draw.rectangle([panel_x + m, m, width - m, height - m], outline=border_col, width=4)
            # Inner thin border
            draw.rectangle([panel_x + m + 5, m + 5, width - m - 5, height - m - 5], outline=border_col, width=1)
            
        elif style_name == 'heritage':
            # Ornate double line with heavy corner accent blocks
            gold = style['accent']
            m = 20
            # Outer frame
            draw.rectangle([panel_x + m, m, width - m, height - m], outline=gold, width=3)
            # Inner frame
            draw.rectangle([panel_x + m + 8, m + 8, width - m - 8, height - m - 8], outline=gold, width=1)
            
            # Corner decorative blocks
            cb = 12
            corners = [
                (panel_x + m, m),
                (width - m - cb, m),
                (panel_x + m, height - m - cb),
                (width - m - cb, height - m - cb)
            ]
            for cx, cy in corners:
                draw.rectangle([cx, cy, cx + cb, cy + cb], fill=gold)
                
    except Exception as e:
        print(f"Error applying decorations for {style_name}: {e}")

    return img


def _add_texture_overlay(img: Image.Image, style_name: str) -> Image.Image:
    """
    Applies image-wide or subtle texture filters based on the selected style.
    
    This function handles raster manipulations like blurring, noise generation,
    or pattern stamping that affect the overall image composition.
    """
    try:
        if style_name == 'retro_print':
            # Create a subtle halftone dot grid overlay across the whole image
            # Done on a transparent overlay to safely alpha_composite
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            dot_color = (0, 0, 0, 15)
            
            spacing = 6
            # Sparse grid pattern for performance and subtlety
            for x in range(0, img.width, spacing):
                for y in range(0, img.height, spacing):
                    if (x // spacing + y // spacing) % 2 == 0:
                        draw.point((x, y), fill=dot_color)
            
            return Image.alpha_composite(img.convert('RGBA'), overlay)
            
        elif style_name == 'papercraft':
            # Create a very faint fibrous paper grain texture using thin random lines
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            grain_color = (0, 0, 0, 6)
            
            for _ in range(800):
                x1 = random.randint(0, img.width)
                y1 = random.randint(0, img.height)
                length = random.randint(10, 50)
                angle = random.uniform(0, math.pi * 2)
                x2 = int(x1 + length * math.cos(angle))
                y2 = int(y1 + length * math.sin(angle))
                draw.line([(x1, y1), (x2, y2)], fill=grain_color, width=1)
                
            return Image.alpha_composite(img.convert('RGBA'), overlay)
            
        elif style_name == 'watercolor':
            # Apply a slight Gaussian blur and saturation bump to simulate wet paint blending
            
            # 1. Blur the image slightly
            blurred = img.filter(ImageFilter.GaussianBlur(radius=1.5))
            
            # 2. Blend back with original to maintain sharp edges but soft colors
            blended = Image.blend(img, blurred, alpha=0.35)
            
            # 3. Slightly enhance color saturation to mimic vivid watercolors
            enhancer = ImageEnhance.Color(blended)
            return enhancer.enhance(1.15)
            
    except Exception as e:
        print(f"Error applying texture overlay for {style_name}: {e}")
        
    # Return original if no specific texture is defined or an error occurred
    return img


def _draw_star(draw: ImageDraw.Draw, x: float, y: float, size: float, color: Tuple[int, int, int, int]) -> None:
    """
    Helper function to draw a precise 5-pointed geometric star.
    
    Args:
        draw: ImageDraw context.
        x: Center X coordinate.
        y: Center Y coordinate.
        size: Outer radius of the star.
        color: Fill color tuple (R, G, B, A).
    """
    points = []
    # A 5-pointed star requires 10 points (5 outer, 5 inner)
    for i in range(10):
        # Rotate by -pi/2 so the star points upwards
        angle = i * math.pi / 5 - math.pi / 2
        # Alternate between outer and inner radius
        r = size if i % 2 == 0 else size / 2
        px = x + r * math.cos(angle)
        py = y + r * math.sin(angle)
        points.append((px, py))
        
    draw.polygon(points, fill=color)

# ==============================================================================
# MODULE INITIALIZATION & SELF-TEST
# ==============================================================================
if __name__ == '__main__':
    # Simple self-test code block to verify the module loads without errors
    # and all styles are properly registered.
    print(f"VisuAIze Style Renderer - Loaded {len(STYLES)} styles successfully.")
    
    print("\nValidating prompt generation across all styles:")
    test_prompt = "A complex neural network architecture"
    for s_name in STYLES.keys():
        enhanced = apply_style_to_image_prompt(test_prompt, s_name)
        print(f"[{s_name:12s}] -> {enhanced}")
        
    print("\nStyle Renderer module is ready for production use.")
