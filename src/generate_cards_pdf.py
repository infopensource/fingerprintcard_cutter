import os
import uuid
from io import BytesIO
from pathlib import Path
from typing import List, Dict

from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import qrcode


PAGE_W_MM = 210.0
PAGE_H_MM = 297.0

# Page 1 constants (finger page)
P1_LEFT = 5.0
P1_RIGHT = 5.0
P1_TOP = 16.0
P1_BOTTOM = 16.0
P1_MSG_H = 36.0
P1_FINGER_H = 50.0
P1_CHAR = 8.0
P1_SCALE_W = 20.0
P1_OFFSET = 7.0

# Page 2 constants (palm page)
P2_TOP = 16.0
P2_BOTTOM = 16.0
P2_LEFT = 5.0
P2_RIGHT = 5.0
P2_SCALE_H = 20.0
P2_SIDE_H = 30.0
P2_GAP_SMALL = 2.0
P2_CHAR_W = P1_CHAR

# Marker constants (shared)
FID_SIZE_MM = 8.0
FID_MARGIN_MM = 3.0


_FONT_NAME = 'HWsong'


def _ensure_font_registered():
    if _FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return
    here = Path(__file__).resolve().parent
    font_path = here.parent / 'template_generator' / 'fontlib' / '华文宋体.ttf'
    pdfmetrics.registerFont(TTFont(_FONT_NAME, str(font_path)))


def _draw_triangle(canvas: Canvas, x: float, y: float, size: float):
    p = canvas.beginPath()
    p.moveTo(x, y)               # bottom-left
    p.lineTo(x, y + size)        # top-left
    p.lineTo(x + size, y + size) # top-right
    p.close()
    canvas.drawPath(p, stroke=0, fill=1)


def _draw_marker_set(canvas: Canvas):
    size = FID_SIZE_MM * mm
    margin = FID_MARGIN_MM * mm
    tl_x = margin
    tl_y = PAGE_H_MM * mm - margin - size
    tr_x = PAGE_W_MM * mm - margin - size
    tr_y = tl_y
    bl_x = margin
    bl_y = margin
    br_x = tr_x
    br_y = margin

    _draw_triangle(canvas, tl_x, tl_y, size)
    canvas.rect(tr_x, tr_y, size, size, stroke=0, fill=1)
    canvas.rect(br_x, br_y, size, size, stroke=0, fill=1)
    canvas.rect(bl_x, bl_y, size, size, stroke=0, fill=1)


def _make_qr_image_reader(data: str, box_size: int = 4) -> ImageReader:
    qr = qrcode.QRCode(border=1, box_size=box_size)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white').convert('RGB')
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return ImageReader(buf)


def draw_finger_page(canvas: Canvas, uid: str):
    _ensure_font_registered()
    canvas.setLineWidth(1)
    canvas.setFont(_FONT_NAME, 15, leading=None)

    t_width = PAGE_W_MM * mm
    t_length = PAGE_H_MM * mm
    t_left = P1_LEFT * mm
    t_right = P1_RIGHT * mm
    t_top = P1_TOP * mm
    t_bottom = P1_BOTTOM * mm
    t_message_height = P1_MSG_H * mm
    t_finger = P1_FINGER_H * mm
    t_character = P1_CHAR * mm
    t_scale_width = P1_SCALE_W * mm

    # Outer border to aid contour detection (does not shift existing layout)
    canvas.rect(0.5 * mm, 0.5 * mm, t_width - 1 * mm, t_length - 1 * mm, stroke=1, fill=0)

    # Bottom two flat prints
    w_flat = (t_width - t_right - t_left - 1 * mm) / 2
    canvas.rect(t_left, t_bottom, w_flat,
                t_length - t_top - t_message_height - 1 * mm - 2 * t_finger - 2 * t_character - t_bottom,
                stroke=1, fill=0)
    canvas.rect(t_left + w_flat + 1 * mm, t_bottom,
                w_flat,
                t_length - t_top - t_message_height - 1 * mm - 2 * t_finger - 2 * t_character - t_bottom,
                stroke=1, fill=0)
    canvas.drawCentredString(t_left + w_flat / 2, t_bottom - t_character, "左手平面捺印")
    canvas.drawCentredString(t_left + w_flat + 1 * mm + w_flat / 2, t_bottom - t_character, "右手平面捺印")

    # Finger boxes (bottom row)
    y_finger_start = t_length - t_top - t_message_height - 1 * mm - 2 * t_finger - t_character
    finger_w = (t_width - t_left - t_right - 5 * mm - t_scale_width) / 5
    for i in range(5):
        x = t_left + i * (1 * mm + finger_w)
        canvas.rect(x, y_finger_start, finger_w, t_finger, stroke=1, fill=0)
    canvas.drawString(t_left + 5, y_finger_start - t_character + 5, "6.左手拇指")
    canvas.drawString(t_left + 5 + 1 * mm + finger_w, y_finger_start - t_character + 5, "7.左手食指")
    canvas.drawString(t_left + 5 + 2 * (1 * mm + finger_w), y_finger_start - t_character + 5, "8.左手中指")
    canvas.drawString(t_left + 5 + 3 * (1 * mm + finger_w), y_finger_start - t_character + 5, "9.左手环指")
    canvas.drawString(t_left + 5 + 4 * (1 * mm + finger_w), y_finger_start - t_character + 5, "10.左手小指")

    # Finger boxes (top row)
    y_finger_start = t_length - t_top - t_message_height - 1 * mm - 1 * t_finger
    for i in range(5):
        x = t_left + i * (1 * mm + finger_w)
        canvas.rect(x, y_finger_start, finger_w, t_finger, stroke=1, fill=0)
    canvas.drawString(t_left + 5, y_finger_start - t_character + 5, "1.右手拇指")
    canvas.drawString(t_left + 5 + 1 * mm + finger_w, y_finger_start - t_character + 5, "2.右手食指")
    canvas.drawString(t_left + 5 + 2 * (1 * mm + finger_w), y_finger_start - t_character + 5, "3.右手中指")
    canvas.drawString(t_left + 5 + 3 * (1 * mm + finger_w), y_finger_start - t_character + 5, "4.右手环指")
    canvas.drawString(t_left + 5 + 4 * (1 * mm + finger_w), y_finger_start - t_character + 5, "5.右手小指")

    # Info box
    y_info = t_length - t_top - t_message_height
    canvas.rect(t_left, y_info, (t_width - t_left - t_right - t_message_height - t_scale_width - 1 * mm),
                t_message_height, stroke=1, fill=0)

    # QR slot (explicit box)
    qr_size = t_message_height
    qr_x = PAGE_W_MM * mm - P1_RIGHT * mm - P1_SCALE_W * mm - qr_size
    qr_y = y_info
    canvas.rect(qr_x, qr_y, qr_size, qr_size, stroke=1, fill=0)

    # Ruler box
    offset = P1_OFFSET * mm
    y_ruler = t_length - t_top - t_message_height - 1 * mm - 2 * t_finger - t_character - offset
    scale_height = t_message_height + 1 * mm + 2 * t_finger + t_character + offset
    canvas.rect(PAGE_W_MM * mm - P1_RIGHT * mm - t_scale_width, y_ruler, t_scale_width, scale_height, stroke=1, fill=0)

    # Marker set
    _draw_marker_set(canvas)

    # QR image draw
    qr_reader = _make_qr_image_reader(f"{uid}|finger")
    canvas.drawImage(qr_reader, qr_x + 1, qr_y + 1, qr_size - 2, qr_size - 2, preserveAspectRatio=True, mask='auto')


def draw_palm_page(canvas: Canvas, uid: str):
    _ensure_font_registered()
    canvas.setLineWidth(1)
    canvas.setFont(_FONT_NAME, 15, leading=None)

    t_width = PAGE_W_MM * mm
    t_length = PAGE_H_MM * mm

    # Outer border to aid contour detection
    canvas.rect(0.5 * mm, 0.5 * mm, t_width - 1 * mm, t_length - 1 * mm, stroke=1, fill=0)

    # 1) Top ruler strip
    y_ruler_start = t_length - P2_TOP * mm - P2_SCALE_H * mm
    canvas.rect(P2_LEFT * mm, y_ruler_start, (t_width - P2_LEFT * mm - P2_RIGHT * mm - P2_SCALE_H * mm), P2_SCALE_H * mm, stroke=1, fill=0)
    canvas.drawString(P2_LEFT * mm + 50 * mm, y_ruler_start + 10, "标  尺  粘  贴")

    # QR slot to the right of the ruler strip
    qr_size = P2_SCALE_H * mm
    qr_x = PAGE_W_MM * mm - P2_RIGHT * mm - qr_size
    qr_y = y_ruler_start
    canvas.rect(qr_x, qr_y, qr_size, qr_size, stroke=1, fill=0)

    # 2) Side palms
    y_side_start = y_ruler_start - P2_GAP_SMALL * mm - P2_SIDE_H * mm
    side_box_width = (t_width - P2_LEFT * mm - P2_RIGHT * mm - P2_GAP_SMALL * mm) / 2
    canvas.rect(P2_LEFT * mm, y_side_start, side_box_width, P2_SIDE_H * mm, stroke=1, fill=0)
    canvas.rect(P2_LEFT * mm + side_box_width + P2_GAP_SMALL * mm, y_side_start, side_box_width, P2_SIDE_H * mm, stroke=1, fill=0)

    # 侧掌文字下方
    y_side_text = y_side_start - P2_CHAR_W * mm
    canvas.drawString(P2_LEFT * mm + 10, y_side_text, "左手掌侧面")
    canvas.drawString(P2_LEFT * mm + side_box_width + P2_GAP_SMALL * mm + 10, y_side_text, "右手掌侧面")

    # 3) Palms (bottom and top)
    available_height = y_side_text - P2_GAP_SMALL * mm - P2_BOTTOM * mm
    palm_height = (available_height - 1 * mm) / 2

    y_print_bottom = P2_BOTTOM * mm
    palm_w = t_width - P2_RIGHT * mm - P2_LEFT * mm - P2_CHAR_W * mm
    palm_label_w = P2_CHAR_W * mm

    # bottom (right palm)
    canvas.rect(P2_LEFT * mm, y_print_bottom, palm_w, palm_height, stroke=1, fill=0)
    canvas.rect(P2_LEFT * mm + palm_w, y_print_bottom, palm_label_w, palm_height, stroke=1, fill=0)

    text_x = P2_LEFT * mm + 5 + palm_w
    text_center_y = y_print_bottom + palm_height / 2
    canvas.drawString(text_x, text_center_y + 3 * P2_CHAR_W * mm, "右")
    canvas.drawString(text_x, text_center_y + 1 * P2_CHAR_W * mm, "手")
    canvas.drawString(text_x, text_center_y - 1 * P2_CHAR_W * mm, "掌")
    canvas.drawString(text_x, text_center_y - 3 * P2_CHAR_W * mm, "纹")

    # top (left palm)
    y_print_top = y_print_bottom + palm_height + 1 * mm
    canvas.rect(P2_LEFT * mm, y_print_top, palm_w, palm_height, stroke=1, fill=0)
    canvas.rect(P2_LEFT * mm + palm_w, y_print_top, palm_label_w, palm_height, stroke=1, fill=0)

    text_center_y_top = y_print_top + palm_height / 2
    canvas.drawString(text_x, text_center_y_top + 3 * P2_CHAR_W * mm, "左")
    canvas.drawString(text_x, text_center_y_top + 1 * P2_CHAR_W * mm, "手")
    canvas.drawString(text_x, text_center_y_top - 1 * P2_CHAR_W * mm, "掌")
    canvas.drawString(text_x, text_center_y_top - 3 * P2_CHAR_W * mm, "纹")

    # Marker set
    _draw_marker_set(canvas)

    # QR image draw
    qr_reader = _make_qr_image_reader(f"{uid}|palm")
    canvas.drawImage(qr_reader, qr_x + 1, qr_y + 1, qr_size - 2, qr_size - 2, preserveAspectRatio=True, mask='auto')


def generate_cards(count: int, output_pdf: str = 'cards.pdf') -> List[Dict]:
    os.makedirs(os.path.dirname(output_pdf) or '.', exist_ok=True)
    canvas = Canvas(output_pdf, pagesize=(PAGE_W_MM * mm, PAGE_H_MM * mm))

    issued: List[Dict] = []
    for _ in range(count):
        uid = str(uuid.uuid4())
        draw_finger_page(canvas, uid)
        canvas.showPage()
        draw_palm_page(canvas, uid)
        canvas.showPage()
        issued.append({'uuid': uid})

    canvas.save()
    return issued


if __name__ == '__main__':
    cards = generate_cards(2, 'cards_demo.pdf')
    print('Generated cards_demo.pdf with', len(cards), 'UUIDs:')
    for c in cards:
        print(' -', c['uuid'])
