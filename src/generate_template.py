from PIL import Image, ImageDraw, ImageFont
import json

# Template parameters
TEMPLATE_W = 2000
TEMPLATE_H = 1400
MARGIN = 60
FID_SIZE = 80

# Finger box layout: 2 rows x 5 columns
ROWS = 2
COLS = 5
BOX_W = 220
BOX_H = 300
BOX_H_SPACING = 40
BOX_W_SPACING = 40

# Compute grid start
grid_total_w = COLS * BOX_W + (COLS - 1) * BOX_W_SPACING
grid_total_h = ROWS * BOX_H + (ROWS - 1) * BOX_H_SPACING
start_x = int((TEMPLATE_W - grid_total_w) / 2)
start_y = int((TEMPLATE_H - grid_total_h) / 2)

boxes = []
for r in range(ROWS):
    for c in range(COLS):
        x = start_x + c * (BOX_W + BOX_W_SPACING)
        y = start_y + r * (BOX_H + BOX_H_SPACING)
        boxes.append((x, y, BOX_W, BOX_H))


def build_template(output_png='template.png', output_json='template.json'):
    img = Image.new('RGB', (TEMPLATE_W, TEMPLATE_H), 'white')
    draw = ImageDraw.Draw(img)

    # outer border
    draw.rectangle([10, 10, TEMPLATE_W - 10, TEMPLATE_H - 10], outline='black', width=4)

    # Corner markers:
    # - TL: filled right-triangle (asymmetric) to disambiguate 180° rotation
    # - TR/BL/BR: filled squares
    # We store marker centers in template.json for homography estimation.
    tl_fx, tl_fy = (MARGIN, MARGIN)
    tl_tri = [(tl_fx, tl_fy + FID_SIZE), (tl_fx, tl_fy), (tl_fx + FID_SIZE, tl_fy)]
    draw.polygon(tl_tri, fill='black')

    fid_positions = {
        'TL': (MARGIN, MARGIN),
        'TR': (TEMPLATE_W - MARGIN - FID_SIZE, MARGIN),
        'BL': (MARGIN, TEMPLATE_H - MARGIN - FID_SIZE),
        'BR': (TEMPLATE_W - MARGIN - FID_SIZE, TEMPLATE_H - MARGIN - FID_SIZE),
    }
    for key, (fx, fy) in fid_positions.items():
        if key == 'TL':
            continue
        draw.rectangle([fx, fy, fx + FID_SIZE, fy + FID_SIZE], fill='black')

    # draw finger boxes and labels
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 28)
    except Exception:
        font = None

    labels = [
        'R-Thumb', 'R-Index', 'R-Middle', 'R-Ring', 'R-Little',
        'L-Thumb', 'L-Index', 'L-Middle', 'L-Ring', 'L-Little'
    ]

    for i, (x, y, w, h) in enumerate(boxes):
        draw.rectangle([x, y, x + w, y + h], outline='black', width=4)
        lbl = labels[i] if i < len(labels) else f'F{i+1}'
        try:
            # Pillow 8+ supports textbbox
            bbox = draw.textbbox((0, 0), lbl, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        except Exception:
            try:
                text_w, text_h = font.getsize(lbl) if font is not None else draw.textsize(lbl)
            except Exception:
                text_w = 0
        tx = x + (w - text_w) / 2
        ty = y + h + 8
        draw.text((tx, ty), lbl, fill='black', font=font)

    img.save(output_png)

    # save normalized boxes
    norm_boxes = []
    for (x, y, w, h) in boxes:
        norm_boxes.append({
            'x': x / TEMPLATE_W,
            'y': y / TEMPLATE_H,
            'w': w / TEMPLATE_W,
            'h': h / TEMPLATE_H,
        })

    # marker centers in absolute pixels
    # square center is (fx + s/2, fy + s/2)
    # right-triangle centroid is average of vertices
    tri_cx = (tl_tri[0][0] + tl_tri[1][0] + tl_tri[2][0]) / 3.0
    tri_cy = (tl_tri[0][1] + tl_tri[1][1] + tl_tri[2][1]) / 3.0
    markers = [
        {'id': 'TL', 'type': 'triangle', 'cx': tri_cx / TEMPLATE_W, 'cy': tri_cy / TEMPLATE_H},
        {'id': 'TR', 'type': 'square', 'cx': (fid_positions['TR'][0] + FID_SIZE / 2) / TEMPLATE_W, 'cy': (fid_positions['TR'][1] + FID_SIZE / 2) / TEMPLATE_H},
        {'id': 'BR', 'type': 'square', 'cx': (fid_positions['BR'][0] + FID_SIZE / 2) / TEMPLATE_W, 'cy': (fid_positions['BR'][1] + FID_SIZE / 2) / TEMPLATE_H},
        {'id': 'BL', 'type': 'square', 'cx': (fid_positions['BL'][0] + FID_SIZE / 2) / TEMPLATE_W, 'cy': (fid_positions['BL'][1] + FID_SIZE / 2) / TEMPLATE_H},
    ]

    template = {
        'width': TEMPLATE_W,
        'height': TEMPLATE_H,
        'fid_size': FID_SIZE / TEMPLATE_W,
        'marker_order': ['TL', 'TR', 'BR', 'BL'],
        'markers': markers,
        'boxes': norm_boxes,
    }
    with open(output_json, 'w') as f:
        json.dump(template, f, indent=2)


if __name__ == '__main__':
    build_template()
    print('Template written: template.png and template.json')
