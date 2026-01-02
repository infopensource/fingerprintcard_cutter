"""
指纹采集卡模板生成器
Fingerprint Collection Card Template Generator

模板尺寸: A4 (210mm x 297mm) @ 300 DPI = 2480 x 3508 pixels
"""

from PIL import Image, ImageDraw, ImageFont
import json
import qrcode
import os

# A4 @ 300 DPI
TEMPLATE_W = 2480
TEMPLATE_H = 3508
MARGIN = 80
FID_SIZE = 100

# 字体设置
def get_font(size=28):
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
        except:
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


def build_fingerprint_template(output_png='fingerprint_template.png', 
                                output_json='fingerprint_template.json',
                                uuid_str=None,
                                save_image=True):
    """
    生成指纹采集卡模板
    
    布局参考:
    - 顶部: 信息栏 + UUID/二维码
    - 中间上部: 右手五指 (1.右拇指 - 5.右小指)
    - 中间下部: 左手五指 (6.左拇指 - 10.左小指)
    - 底部: 左手平面捺印 + 右手平面捺印
    - 右下角: 比例尺
    """
    img = Image.new('RGB', (TEMPLATE_W, TEMPLATE_H), 'white')
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(48)
    font_label = get_font(32)
    font_small = get_font(24)

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
    box_id = 0

    # ========== 信息栏 (顶部大方框) ==========
    info_x = 200
    info_y = 200
    info_w = 1200
    info_h = 350
    draw.rectangle([info_x, info_y, info_x + info_w, info_y + info_h], outline='black', width=3)
    draw.text((info_x + 20, info_y + 10), "信息", fill='black', font=font_label)
    boxes.append({'id': 'info', 'x': info_x, 'y': info_y, 'w': info_w, 'h': info_h, 'type': 'info'})
    box_id += 1

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

    # ========== 指纹采集区 ==========
    # 右手五指标签
    finger_labels_row1 = ['1.右拇指', '2.右食指', '3.右中指', '4.右环指', '5.右小指']
    finger_labels_row2 = ['6.左拇指', '7.左食指', '8.左中指', '9.左环指', '10.左小指']
    
    # 单指框尺寸
    box_w = 380
    box_h = 480
    spacing_x = 30
    spacing_y = 60
    
    # 第一行 (右手) 起始位置
    start_x = (TEMPLATE_W - (5 * box_w + 4 * spacing_x)) // 2
    row1_y = 650

    # 绘制右手五指
    draw.text((start_x, row1_y - 50), "右手", fill='black', font=font_title)
    for i, label in enumerate(finger_labels_row1):
        x = start_x + i * (box_w + spacing_x)
        y = row1_y
        draw.rectangle([x, y, x + box_w, y + box_h], outline='black', width=3)
        # 标签
        bbox = draw.textbbox((0, 0), label, font=font_label)
        text_w = bbox[2] - bbox[0]
        draw.text((x + (box_w - text_w) // 2, y + box_h + 10), label, fill='black', font=font_label)
        boxes.append({
            'id': f'finger_{i+1}',
            'x': x, 'y': y, 'w': box_w, 'h': box_h,
            'type': 'fingerprint',
            'label': label
        })

    # 第二行 (左手) 起始位置
    row2_y = row1_y + box_h + 120

    # 绘制左手五指
    draw.text((start_x, row2_y - 50), "左手", fill='black', font=font_title)
    for i, label in enumerate(finger_labels_row2):
        x = start_x + i * (box_w + spacing_x)
        y = row2_y
        draw.rectangle([x, y, x + box_w, y + box_h], outline='black', width=3)
        # 标签
        bbox = draw.textbbox((0, 0), label, font=font_label)
        text_w = bbox[2] - bbox[0]
        draw.text((x + (box_w - text_w) // 2, y + box_h + 10), label, fill='black', font=font_label)
        boxes.append({
            'id': f'finger_{i+6}',
            'x': x, 'y': y, 'w': box_w, 'h': box_h,
            'type': 'fingerprint',
            'label': label
        })

    # ========== 平面捺印区 (底部两个大框) ==========
    flat_y = row2_y + box_h + 150
    flat_w = 950
    flat_h = 650
    flat_spacing = 80

    # 左手平面捺印
    left_flat_x = (TEMPLATE_W - 2 * flat_w - flat_spacing) // 2
    draw.rectangle([left_flat_x, flat_y, left_flat_x + flat_w, flat_y + flat_h], outline='black', width=3)
    draw.text((left_flat_x + flat_w // 2 - 120, flat_y + flat_h + 15), "左手平面捺印", fill='black', font=font_label)
    boxes.append({
        'id': 'left_flat',
        'x': left_flat_x, 'y': flat_y, 'w': flat_w, 'h': flat_h,
        'type': 'flat_print',
        'label': '左手平面捺印'
    })

    # 右手平面捺印
    right_flat_x = left_flat_x + flat_w + flat_spacing
    draw.rectangle([right_flat_x, flat_y, right_flat_x + flat_w, right_flat_x + flat_h], outline='black', width=3)
    draw.text((right_flat_x + flat_w // 2 - 120, flat_y + flat_h + 15), "右手平面捺印", fill='black', font=font_label)
    boxes.append({
        'id': 'right_flat',
        'x': right_flat_x, 'y': flat_y, 'w': flat_w, 'h': flat_h,
        'type': 'flat_print',
        'label': '右手平面捺印'
    })

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
    # 归一化坐标
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
        'template_type': 'fingerprint',
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
    build_fingerprint_template(
        output_png='fingerprint_template.png',
        output_json='fingerprint_template.json',
        uuid_str=test_uuid
    )
    print(f'指纹模板已生成: fingerprint_template.png (UUID: {test_uuid})')
