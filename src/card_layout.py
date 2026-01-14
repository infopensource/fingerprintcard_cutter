from dataclasses import dataclass
from typing import List, Dict

MM_PER_INCH = 25.4
DEFAULT_DPI = 300


@dataclass
class MarkerSpec:
    id: str
    type: str  # 'square' or 'triangle'
    cx: float  # normalized [0,1]
    cy: float


@dataclass
class BoxSpec:
    name: str
    x: float   # normalized [0,1] (top-left origin)
    y: float
    w: float
    h: float


def mm_to_px(mm_value: float, dpi: int = DEFAULT_DPI) -> float:
    return mm_value / MM_PER_INCH * dpi


def _normalize_box(x_mm: float, y_mm_bottom: float, w_mm: float, h_mm: float,
                   page_w_mm: float, page_h_mm: float, dpi: int) -> BoxSpec:
    # Convert bottom-left origin (ReportLab style) to top-left origin (OpenCV/Pillow style)
    x_px = mm_to_px(x_mm, dpi)
    y_top_px = mm_to_px(page_h_mm - y_mm_bottom - h_mm, dpi)
    w_px = mm_to_px(w_mm, dpi)
    h_px = mm_to_px(h_mm, dpi)
    return x_px / mm_to_px(page_w_mm, dpi), y_top_px / mm_to_px(page_h_mm, dpi), w_px / mm_to_px(page_w_mm, dpi), h_px / mm_to_px(page_h_mm, dpi)


def _finger_layout(dpi: int = DEFAULT_DPI) -> Dict:
    # Constants in millimeters (must match lzypdf.py)
    page_w = 210.0
    page_h = 297.0
    left = 5.0
    right = 5.0
    top = 16.0
    bottom = 16.0
    msg_h = 36.0
    finger_h = 50.0
    char_h = 8.0
    scale_w = 20.0
    offset = 7.0

    # Derived dims (mm, bottom-left origin)
    palm_w = (page_w - right - left - 1.0) / 2.0
    palm_h = page_h - top - msg_h - 1.0 - 2 * finger_h - 2 * char_h - bottom

    finger_w = (page_w - left - right - 5.0 - scale_w) / 5.0
    finger_y_bottom_row = page_h - top - msg_h - 1.0 - 2 * finger_h - char_h
    finger_y_top_row = page_h - top - msg_h - 1.0 - finger_h

    info_x = left
    info_y = page_h - top - msg_h
    info_w = page_w - left - right - msg_h - scale_w - 1.0
    info_h = msg_h

    qr_size = msg_h
    qr_x = page_w - right - scale_w - qr_size  # left of ruler, aligned with drawing
    qr_y = info_y

    ruler_x = page_w - right - scale_w
    ruler_y = page_h - top - msg_h - 1.0 - 2 * finger_h - char_h - offset
    ruler_w = scale_w
    ruler_h = msg_h + 1.0 + 2 * finger_h + char_h + offset

    boxes: List[BoxSpec] = []

    # Palm flats (bottom area)
    boxes.append(BoxSpec('left_flat', *_normalize_box(left, bottom, palm_w, palm_h, page_w, page_h, dpi)))
    boxes.append(BoxSpec('right_flat', *_normalize_box(left + palm_w + 1.0, bottom, palm_w, palm_h, page_w, page_h, dpi)))

    # Fingers bottom row (6-10)
    for i in range(5):
        x_mm = left + i * (1.0 + finger_w)
        boxes.append(BoxSpec(f'finger_L_{i+1}', *_normalize_box(x_mm, finger_y_bottom_row, finger_w, finger_h, page_w, page_h, dpi)))

    # Fingers top row (1-5)
    for i in range(5):
        x_mm = left + i * (1.0 + finger_w)
        boxes.append(BoxSpec(f'finger_R_{i+1}', *_normalize_box(x_mm, finger_y_top_row, finger_w, finger_h, page_w, page_h, dpi)))

    # Info, QR, ruler
    boxes.append(BoxSpec('info_box', *_normalize_box(info_x, info_y, info_w, info_h, page_w, page_h, dpi)))
    boxes.append(BoxSpec('qr_box', *_normalize_box(qr_x, qr_y, qr_size, qr_size, page_w, page_h, dpi)))
    boxes.append(BoxSpec('ruler_finger', *_normalize_box(ruler_x, ruler_y, ruler_w, ruler_h, page_w, page_h, dpi)))

    # Corner markers (triangle at TL, squares elsewhere)
    fid_size_mm = 8.0
    fid_margin_mm = 3.0

    def marker_center(x_mm: float, y_mm_bottom: float) -> (float, float):
        cx_px = mm_to_px(x_mm + fid_size_mm / 2.0, dpi)
        cy_px = mm_to_px(page_h - (y_mm_bottom + fid_size_mm / 2.0), dpi)
        return cx_px / mm_to_px(page_w, dpi), cy_px / mm_to_px(page_h, dpi)

    markers: List[MarkerSpec] = []
    tl_x = fid_margin_mm
    tl_y = page_h - fid_margin_mm - fid_size_mm
    tr_x = page_w - fid_margin_mm - fid_size_mm
    tr_y = tl_y
    bl_x = fid_margin_mm
    bl_y = fid_margin_mm
    br_x = tr_x
    br_y = fid_margin_mm

    cx, cy = marker_center(tl_x, tl_y)
    markers.append(MarkerSpec('TL', 'triangle', cx, cy))
    cx, cy = marker_center(tr_x, tr_y)
    markers.append(MarkerSpec('TR', 'square', cx, cy))
    cx, cy = marker_center(br_x, br_y)
    markers.append(MarkerSpec('BR', 'square', cx, cy))
    cx, cy = marker_center(bl_x, bl_y)
    markers.append(MarkerSpec('BL', 'square', cx, cy))

    width_px = int(round(mm_to_px(page_w, dpi)))
    height_px = int(round(mm_to_px(page_h, dpi)))
    fid_size_px = mm_to_px(fid_size_mm, dpi)

    return {
        'width': width_px,
        'height': height_px,
        'fid_size': fid_size_px / width_px,
        'marker_order': ['TL', 'TR', 'BR', 'BL'],
        'markers': [m.__dict__ for m in markers],
        'boxes': [b.__dict__ for b in boxes],
    }


def _palm_layout(dpi: int = DEFAULT_DPI) -> Dict:
    page_w = 210.0
    page_h = 297.0
    top = 16.0
    bottom = 16.0
    left = 5.0
    right = 5.0
    scale_h = 20.0
    side_h = 30.0
    gap_small = 2.0
    char_w = 8.0  # reuse from first page

    y_ruler = page_h - top - scale_h
    ruler_w = page_w - left - right - scale_h
    ruler_h = scale_h

    qr_x = page_w - right - scale_h
    qr_y = y_ruler
    qr_size = scale_h

    y_side = y_ruler - gap_small - side_h
    side_w = (page_w - left - right - gap_small) / 2.0

    y_side_text = y_side - char_w
    available_h = y_side_text - gap_small - bottom
    palm_h = (available_h - 1.0) / 2.0

    y_palm_bottom = bottom
    y_palm_top = y_palm_bottom + palm_h + 1.0

    boxes: List[BoxSpec] = []

    # Ruler and QR slot
    boxes.append(BoxSpec('ruler_palm', *_normalize_box(left, y_ruler, ruler_w, ruler_h, page_w, page_h, dpi)))
    boxes.append(BoxSpec('qr_box', *_normalize_box(qr_x, qr_y, qr_size, qr_size, page_w, page_h, dpi)))

    # Side palms
    boxes.append(BoxSpec('side_left', *_normalize_box(left, y_side, side_w, side_h, page_w, page_h, dpi)))
    boxes.append(BoxSpec('side_right', *_normalize_box(left + side_w + gap_small, y_side, side_w, side_h, page_w, page_h, dpi)))

    # Palms
    palm_w = page_w - right - left - char_w
    boxes.append(BoxSpec('palm_right', *_normalize_box(left, y_palm_bottom, palm_w, palm_h, page_w, page_h, dpi)))
    boxes.append(BoxSpec('palm_left', *_normalize_box(left, y_palm_top, palm_w, palm_h, page_w, page_h, dpi)))

    fid_size_mm = 8.0
    fid_margin_mm = 3.0

    def marker_center(x_mm: float, y_mm_bottom: float) -> (float, float):
        cx_px = mm_to_px(x_mm + fid_size_mm / 2.0, dpi)
        cy_px = mm_to_px(page_h - (y_mm_bottom + fid_size_mm / 2.0), dpi)
        return cx_px / mm_to_px(page_w, dpi), cy_px / mm_to_px(page_h, dpi)

    markers: List[MarkerSpec] = []
    tl_x = fid_margin_mm
    tl_y = page_h - fid_margin_mm - fid_size_mm
    tr_x = page_w - fid_margin_mm - fid_size_mm
    tr_y = tl_y
    bl_x = fid_margin_mm
    bl_y = fid_margin_mm
    br_x = tr_x
    br_y = fid_margin_mm

    cx, cy = marker_center(tl_x, tl_y)
    markers.append(MarkerSpec('TL', 'triangle', cx, cy))
    cx, cy = marker_center(tr_x, tr_y)
    markers.append(MarkerSpec('TR', 'square', cx, cy))
    cx, cy = marker_center(br_x, br_y)
    markers.append(MarkerSpec('BR', 'square', cx, cy))
    cx, cy = marker_center(bl_x, bl_y)
    markers.append(MarkerSpec('BL', 'square', cx, cy))

    width_px = int(round(mm_to_px(page_w, dpi)))
    height_px = int(round(mm_to_px(page_h, dpi)))
    fid_size_px = mm_to_px(fid_size_mm, dpi)

    return {
        'width': width_px,
        'height': height_px,
        'fid_size': fid_size_px / width_px,
        'marker_order': ['TL', 'TR', 'BR', 'BL'],
        'markers': [m.__dict__ for m in markers],
        'boxes': [b.__dict__ for b in boxes],
    }


def build_templates(dpi: int = DEFAULT_DPI) -> Dict[str, Dict]:
    return {
        'finger': _finger_layout(dpi),
        'palm': _palm_layout(dpi),
    }
