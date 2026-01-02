"""
掌纹采集卡模板生成器
Palm Print Collection Card Template Generator

模板尺寸: A4 (210mm x 297mm) @ 300 DPI = 2480 x 3508 pixels
"""

from PIL import Image, ImageDraw, ImageFont
import json
import qrcode

# A4 @ 300 DPI
TEMPLATE_W = 2480
TEMPLATE_H = 3508
MARGIN = 80
FID_SIZE = 100


def get_font(size=28):
    """获取可用字体"""
    font_paths = [
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def generate_qr_code(uuid_str, size=200):
    """生成UUID二维码"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(uuid_str)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img = qr_img.resize((size, size), Image.LANCZOS)
    return qr_img


def build_palmprint_template(output_png='palmprint_template.png', 
                              output_json='palmprint_template.json',
                              uuid_str=None,
                              save_image=True):
    """
    生成掌纹采集卡模板
    
    布局参考 (参考图片右侧):
    - 顶部: 信息栏 + UUID/二维码
    - 中间上部: 左手掌纹 + 左手指纹
    - 中间下部: 右手掌纹 + 右手指纹
    - 右下角: 比例尺
    """
    img = Image.new('RGB', (TEMPLATE_W, TEMPLATE_H), 'white')
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(48)
    font_label = get_font(32)
    font_small = get_font(24)
    font_vertical = get_font(36)

    # 外边框
    draw.rectangle([10, 10, TEMPLATE_W - 10, TEMPLATE_H - 10], outline='black', width=4)

    # ========== 角标记 (用于图像校正) ==========
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

    boxes = []

    # ========== 信息栏 (顶部大方框) ==========
    info_x = 200
    info_y = 200
    info_w = 1200
    info_h = 300
    draw.rectangle([info_x, info_y, info_x + info_w, info_y + info_h], outline='black', width=3)
    draw.text((info_x + 20, info_y + 10), "信息", fill='black', font=font_label)
    boxes.append({'id': 'info', 'x': info_x, 'y': info_y, 'w': info_w, 'h': info_h, 'type': 'info'})

    # ========== UUID/二维码区域 ==========
    qr_x = 1500
    qr_y = 200
    qr_size = 280
    draw.rectangle([qr_x, qr_y, qr_x + qr_size, qr_y + qr_size], outline='black', width=2)
    if uuid_str:
        qr_img = generate_qr_code(uuid_str, size=qr_size - 20)
        img.paste(qr_img, (qr_x + 10, qr_y + 10))
        # UUID文本
        draw.text((qr_x, qr_y + qr_size + 10), uuid_str[:18], fill='black', font=font_small)
        if len(uuid_str) > 18:
            draw.text((qr_x, qr_y + qr_size + 40), uuid_str[18:], fill='black', font=font_small)
    else:
        draw.text((qr_x + 20, qr_y + qr_size // 2 - 20), "UUID", fill='gray', font=font_label)
    boxes.append({'id': 'qrcode', 'x': qr_x, 'y': qr_y, 'w': qr_size, 'h': qr_size, 'type': 'qrcode'})

    # ========== 掌纹采集区 ==========
    # 左手区域 (上半部分)
    section_y = 580
    section_height = 1300
    
    # 大掌纹框
    palm_w = 900
    palm_h = 1100
    palm_x = 200
    
    # 小指纹框 (5个竖排)
    finger_w = 180
    finger_h = 200
    finger_spacing = 10
    finger_x = palm_x + palm_w + 80
    
    # === 左手掌纹区 ===
    draw.text((palm_x, section_y - 50), "左手掌纹", fill='black', font=font_title)
    left_palm_y = section_y
    draw.rectangle([palm_x, left_palm_y, palm_x + palm_w, left_palm_y + palm_h], 
                   outline='black', width=3)
    boxes.append({
        'id': 'left_palm',
        'x': palm_x, 'y': left_palm_y, 'w': palm_w, 'h': palm_h,
        'type': 'palmprint',
        'label': '左手掌纹'
    })

    # 左手五指 (竖排在掌纹右侧)
    left_finger_labels = ['左拇指', '左食指', '左中指', '左环指', '左小指']
    for i, label in enumerate(left_finger_labels):
        x = finger_x
        y = left_palm_y + i * (finger_h + finger_spacing)
        draw.rectangle([x, y, x + finger_w, y + finger_h], outline='black', width=2)
        # 标签
        bbox = draw.textbbox((0, 0), label, font=font_small)
        text_w = bbox[2] - bbox[0]
        draw.text((x + finger_w + 10, y + finger_h // 2 - 15), label, fill='black', font=font_small)
        boxes.append({
            'id': f'left_finger_{i+1}',
            'x': x, 'y': y, 'w': finger_w, 'h': finger_h,
            'type': 'fingerprint',
            'label': label
        })

    # 垂直标签 "左手掌纹"
    vertical_label_x = TEMPLATE_W - 150
    for i, char in enumerate("左手掌纹"):
        draw.text((vertical_label_x, left_palm_y + 100 + i * 60), char, fill='black', font=font_vertical)

    # === 右手掌纹区 ===
    right_section_y = section_y + section_height + 100
    draw.text((palm_x, right_section_y - 50), "右手掌纹", fill='black', font=font_title)
    right_palm_y = right_section_y
    draw.rectangle([palm_x, right_palm_y, palm_x + palm_w, right_palm_y + palm_h], 
                   outline='black', width=3)
    boxes.append({
        'id': 'right_palm',
        'x': palm_x, 'y': right_palm_y, 'w': palm_w, 'h': palm_h,
        'type': 'palmprint',
        'label': '右手掌纹'
    })

    # 右手五指 (竖排在掌纹右侧)
    right_finger_labels = ['右拇指', '右食指', '右中指', '右环指', '右小指']
    for i, label in enumerate(right_finger_labels):
        x = finger_x
        y = right_palm_y + i * (finger_h + finger_spacing)
        draw.rectangle([x, y, x + finger_w, y + finger_h], outline='black', width=2)
        draw.text((x + finger_w + 10, y + finger_h // 2 - 15), label, fill='black', font=font_small)
        boxes.append({
            'id': f'right_finger_{i+1}',
            'x': x, 'y': y, 'w': finger_w, 'h': finger_h,
            'type': 'fingerprint',
            'label': label
        })

    # 垂直标签 "右手掌纹"
    for i, char in enumerate("右手掌纹"):
        draw.text((vertical_label_x, right_palm_y + 100 + i * 60), char, fill='black', font=font_vertical)

    # ========== 比例尺 (右下角) ==========
    scale_x = TEMPLATE_W - 450
    scale_y = TEMPLATE_H - 250
    scale_w = 300
    scale_h = 100
    draw.rectangle([scale_x, scale_y, scale_x + scale_w, scale_y + scale_h], outline='black', width=2)
    draw.text((scale_x + 10, scale_y + 10), "比例尺", fill='black', font=font_small)
    # 绘制刻度 (1cm = 118px @ 300dpi)
    cm_px = 118
    for i in range(3):
        x1 = scale_x + 20 + i * cm_px
        y1 = scale_y + 50
        y2 = scale_y + 80
        draw.line([(x1, y1), (x1, y2)], fill='black', width=2)
        if i < 2:
            draw.line([(x1, y2), (x1 + cm_px, y2)], fill='black', width=2)
        draw.text((x1 - 5, y2 + 5), f"{i}cm", fill='black', font=font_small)
    boxes.append({
        'id': 'scale',
        'x': scale_x, 'y': scale_y, 'w': scale_w, 'h': scale_h,
        'type': 'scale'
    })

    if save_image:
        img.save(output_png)

    # ========== 保存JSON模板 ==========
    norm_boxes = []
    for b in boxes:
        norm_boxes.append({
            'id': b['id'],
            'x': b['x'] / TEMPLATE_W,
            'y': b['y'] / TEMPLATE_H,
            'w': b['w'] / TEMPLATE_W,
            'h': b['h'] / TEMPLATE_H,
            'type': b['type'],
            'label': b.get('label', b['id'])
        })

    # 角标记
    tri_cx = (tl_tri[0][0] + tl_tri[1][0] + tl_tri[2][0]) / 3.0
    tri_cy = (tl_tri[0][1] + tl_tri[1][1] + tl_tri[2][1]) / 3.0
    markers = [
        {'id': 'TL', 'type': 'triangle', 'cx': tri_cx / TEMPLATE_W, 'cy': tri_cy / TEMPLATE_H},
        {'id': 'TR', 'type': 'square', 'cx': (fid_positions['TR'][0] + FID_SIZE / 2) / TEMPLATE_W, 
         'cy': (fid_positions['TR'][1] + FID_SIZE / 2) / TEMPLATE_H},
        {'id': 'BR', 'type': 'square', 'cx': (fid_positions['BR'][0] + FID_SIZE / 2) / TEMPLATE_W, 
         'cy': (fid_positions['BR'][1] + FID_SIZE / 2) / TEMPLATE_H},
        {'id': 'BL', 'type': 'square', 'cx': (fid_positions['BL'][0] + FID_SIZE / 2) / TEMPLATE_W, 
         'cy': (fid_positions['BL'][1] + FID_SIZE / 2) / TEMPLATE_H},
    ]

    template = {
        'template_type': 'palmprint',
        'width': TEMPLATE_W,
        'height': TEMPLATE_H,
        'dpi': 300,
        'fid_size': FID_SIZE / TEMPLATE_W,
        'marker_order': ['TL', 'TR', 'BR', 'BL'],
        'markers': markers,
        'boxes': norm_boxes,
    }
    
    if output_json:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)

    return img, template


if __name__ == '__main__':
    import uuid
    test_uuid = str(uuid.uuid4())
    build_palmprint_template(
        output_png='palmprint_template.png',
        output_json='palmprint_template.json',
        uuid_str=test_uuid
    )
    print(f'掌纹模板已生成: palmprint_template.png (UUID: {test_uuid})')
