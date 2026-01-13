import json
from pathlib import Path
from typing import Dict
from PIL import Image, ImageDraw

from src.card_layout import build_templates, DEFAULT_DPI


def _draw_markers(draw: ImageDraw.ImageDraw, tpl: Dict):
    w = tpl['width']
    h = tpl['height']
    fid_px = int(round(tpl['fid_size'] * w))
    for m in tpl.get('markers', []):
        cx = m['cx'] * w
        cy = m['cy'] * h
        x0 = cx - fid_px / 2
        y0 = cy - fid_px / 2
        x1 = cx + fid_px / 2
        y1 = cy + fid_px / 2
        if m.get('type') == 'triangle':
            tri = [(x0, y1), (x0, y0), (x1, y0)]
            draw.polygon(tri, fill='black')
        else:
            draw.rectangle([x0, y0, x1, y1], fill='black')


def _draw_boxes(draw: ImageDraw.ImageDraw, tpl: Dict):
    w = tpl['width']
    h = tpl['height']
    for b in tpl.get('boxes', []):
        x0 = b['x'] * w
        y0 = b['y'] * h
        x1 = x0 + b['w'] * w
        y1 = y0 + b['h'] * h
        draw.rectangle([x0, y0, x1, y1], outline='black', width=3)


def save_template_assets(output_dir: str = '.', dpi: int = DEFAULT_DPI) -> Dict[str, Dict]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    templates = build_templates(dpi)

    for name, tpl in templates.items():
        json_path = Path(output_dir) / f'template_{name}.json'
        png_path = Path(output_dir) / f'template_{name}.png'

        with open(json_path, 'w') as f:
            json.dump(tpl, f, indent=2)

        img = Image.new('RGB', (tpl['width'], tpl['height']), 'white')
        draw = ImageDraw.Draw(img)
        _draw_markers(draw, tpl)
        _draw_boxes(draw, tpl)
        img.save(png_path)

    return templates


if __name__ == '__main__':
    assets = save_template_assets()
    print('Templates written:')
    for k in assets:
        print(f' - template_{k}.json / template_{k}.png')
