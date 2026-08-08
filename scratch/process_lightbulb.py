from PIL import Image
import numpy as np
from pathlib import Path
import base64

upload_dir = Path(r'C:\Users\NaveenKumar\.gemini\antigravity\brain\b453550d-425c-4967-bdd2-f992548ebac6\.user_uploaded')
src_path = upload_dir / 'media_1786173185670.png'
dest_path = Path('d:/visuAlze/static/img/workflow_logo.png')
dest_svg = Path('d:/visuAlze/static/img/workflow_logo.svg')

img = Image.open(src_path).convert('RGBA')
arr = np.array(img)
r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
gray = 0.299 * r + 0.587 * g + 0.114 * b

# Invert black lines into pure white with smooth alpha transparency
alpha = np.clip((245 - gray) * 1.8, 0, 255).astype(np.uint8)

out_arr = np.zeros_like(arr)
out_arr[:,:,0] = 255 # R
out_arr[:,:,1] = 255 # G
out_arr[:,:,2] = 255 # B
out_arr[:,:,3] = alpha

out_img = Image.fromarray(out_arr, mode='RGBA')
bbox = out_img.getbbox()
if bbox:
    pad = 12
    w, h = out_img.size
    bbox = (max(0, bbox[0]-pad), max(0, bbox[1]-pad), min(w, bbox[2]+pad), min(h, bbox[3]+pad))
    out_img = out_img.crop(bbox)

out_img.save(dest_path, 'PNG')
print(f'Saved workflow_logo.png with size {out_img.size}')

# Save SVG
with open(dest_path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')
w, h = out_img.size
svg_content = f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <image href="data:image/png;base64,{b64}" width="{w}" height="{h}" />
</svg>'''
with open(dest_svg, 'w', encoding='utf-8') as f:
    f.write(svg_content)
print('Saved workflow_logo.svg')
