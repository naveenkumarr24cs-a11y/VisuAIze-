import base64
from pathlib import Path
from PIL import Image

out_dir = Path('d:/visuAlze/static/img')

for name in ['main_logo', 'workflow_logo']:
    png_path = out_dir / f'{name}.png'
    svg_path = out_dir / f'{name}.svg'
    with open(png_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')
    
    im = Image.open(png_path)
    w, h = im.size
    
    svg_content = f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <image href="data:image/png;base64,{b64}" width="{w}" height="{h}" />
</svg>'''
    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print(f'Wrote {svg_path.name}')
