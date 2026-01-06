import cv2
import numpy as np
import json
import os


def load_template(template_json='template.json'):
    with open(template_json, 'r') as f:
        return json.load(f)


def find_card_corners(img_gray):
    # Try to find the largest quadrilateral contour (the card)
    blurred = cv2.GaussianBlur(img_gray, (5, 5), 0)
    _, th = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    th = cv2.bitwise_not(th)
    contours, _ = cv2.findContours(th, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    height, width = img_gray.shape
    best = None
    best_area = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 0.01 * width * height:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and area > best_area:
            best_area = area
            best = approx
    if best is not None:
        pts = best.reshape(4, 2)
        # order points
        rect = order_points(pts)
        return rect
    return None


def order_points(pts):
    rect = np.zeros((4, 2), dtype='float32')
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # top-left
    rect[2] = pts[np.argmax(s)]  # bottom-right
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right
    rect[3] = pts[np.argmax(diff)]  # bottom-left
    return rect


def warp_to_template(img, src_pts, template_w, template_h):
    dst = np.array([[0, 0], [template_w - 1, 0], [template_w - 1, template_h - 1], [0, template_h - 1]], dtype='float32')
    M = cv2.getPerspectiveTransform(src_pts, dst)
    warped = cv2.warpPerspective(img, M, (template_w, template_h))
    return warped


def crop_boxes_from_warp(warped_rgb, template_json='template.json', out_dir='crops'):
    tpl = load_template(template_json)
    H, W = tpl['height'], tpl['width']
    boxes = tpl['boxes']
    os.makedirs(out_dir, exist_ok=True)
    crops = []
    for i, b in enumerate(boxes):
        x = int(b['x'] * W)
        y = int(b['y'] * H)
        w = int(b['w'] * W)
        h = int(b['h'] * H)
        crop = warped_rgb[y:y+h, x:x+w]
        out_path = os.path.join(out_dir, f'finger_{i+1}.png')
        cv2.imwrite(out_path, cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
        crops.append(out_path)
    return crops


def _binarize_for_markers(img_gray):
    # Make dark printed markers become white blobs.
    blurred = cv2.GaussianBlur(img_gray, (5, 5), 0)
    th = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=2)
    return th


def detect_corner_markers(img_gray):
    """Detect corner markers: 3 squares + 1 triangle (asymmetric).

    Returns a list of dicts: {type: 'square'|'triangle', cx, cy, area}
    """
    def detect_on_mask(th, img_area):
        contours, _ = cv2.findContours(th, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        found = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < img_area * 0.000005:
                continue
            if area > img_area * 0.2:
                continue

            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)
            if not cv2.isContourConvex(approx):
                continue

            m = cv2.moments(cnt)
            if m['m00'] == 0:
                continue
            cx = m['m10'] / m['m00']
            cy = m['m01'] / m['m00']

            x, y, bw, bh = cv2.boundingRect(approx)
            if bw <= 0 or bh <= 0:
                continue
            rect_fill = area / float(bw * bh)

            # Use minAreaRect to handle rotated squares (diamond shape after rotation)
            box = cv2.minAreaRect(cnt)
            (w_min, h_min) = box[1]
            if w_min <= 0 or h_min <= 0:
                continue
            min_rect_area = w_min * h_min
            min_rect_aspect = max(w_min, h_min) / min(w_min, h_min)
            min_rect_fill = area / float(min_rect_area)

            # Triangle likeness: area should be close to its minimum enclosing triangle.
            tri_area = 0.0
            try:
                tri_area, _tri = cv2.minEnclosingTriangle(cnt)
            except Exception:
                tri_area = 0.0
            tri_fill = (area / float(tri_area)) if tri_area and tri_area > 1e-6 else 0.0
            tri_rect_ratio = tri_fill / max(rect_fill, 1e-6)

            if tri_rect_ratio > 1.05 and rect_fill <= 0.9:
                found.append({'type': 'triangle', 'cx': cx, 'cy': cy, 'area': area})
            elif (0.55 <= min_rect_aspect <= 1.8) and min_rect_fill >= 0.2:
                found.append({'type': 'square', 'cx': cx, 'cy': cy, 'area': area})
        return found

    h, w = img_gray.shape
    img_area = float(h * w)

    # Pass 1: Otsu-based binarization (default)
    th1 = _binarize_for_markers(img_gray)
    markers = detect_on_mask(th1, img_area)

    # Pass 2: Adaptive threshold (handles uneven lighting) if needed
    if len(markers) < 4:
        th2 = cv2.adaptiveThreshold(img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY_INV, 35, 5)
        markers.extend(detect_on_mask(th2, img_area))

    # Merge close duplicates (within 12 px)
    merged = []
    for m in markers:
        merged_to_existing = False
        for e in merged:
            if (abs(m['cx'] - e['cx']) < 12) and (abs(m['cy'] - e['cy']) < 12) and (m['type'] == e['type']):
                merged_to_existing = True
                break
        if not merged_to_existing:
            merged.append(m)

    return merged


def _assign_best_marker_per_corner(markers, img_w, img_h):
    # Choose one marker per image corner (TL, TR, BR, BL) based on area & proximity.
    corners = np.array(
        [[0.0, 0.0], [img_w - 1.0, 0.0], [img_w - 1.0, img_h - 1.0], [0.0, img_h - 1.0]],
        dtype=np.float32,
    )

    # Maximum distance a marker can be from its corner to be considered (fraction of image diagonal)
    max_corner_dist = 0.5 * min(img_w, img_h)

    buckets = {0: [], 1: [], 2: [], 3: []}
    for m in markers:
        p = np.array([m['cx'], m['cy']], dtype=np.float32)
        d2 = np.sum((corners - p) ** 2, axis=1)
        corner_idx = int(np.argmin(d2))
        dist = np.sqrt(d2[corner_idx])
        if dist > max_corner_dist:
            continue
        score = float(m['area']) / (float(d2[corner_idx]) + 1.0)
        buckets[corner_idx].append((score, m))

    chosen = [None, None, None, None]

    # Force-place the triangle first (if present), so 180° disambiguation works.
    for cidx in (0, 1, 2, 3):
        tri_candidates = [(s, m) for (s, m) in buckets[cidx] if m.get('type') == 'triangle']
        if tri_candidates:
            tri_candidates.sort(key=lambda t: t[0], reverse=True)
            chosen[cidx] = tri_candidates[0][1]

    # Fill remaining with best-scoring markers per corner.
    for cidx in (0, 1, 2, 3):
        if chosen[cidx] is not None:
            continue
        if not buckets[cidx]:
            return None
        buckets[cidx].sort(key=lambda t: t[0], reverse=True)
        chosen[cidx] = buckets[cidx][0][1]

    return chosen  # [TL, TR, BR, BL] in image coordinates


def _template_marker_points(tpl):
    # Returns dst points in template pixel coordinates in TL, TR, BR, BL order.
    tw, th = tpl['width'], tpl['height']
    id_to_marker = {m['id']: m for m in tpl.get('markers', [])}
    order = tpl.get('marker_order', ['TL', 'TR', 'BR', 'BL'])
    pts = []
    for mid in order:
        mk = id_to_marker.get(mid)
        if mk is None:
            raise ValueError(f"template.json missing marker '{mid}'")
        pts.append([mk['cx'] * tw, mk['cy'] * th])
    return np.array(pts, dtype='float32')


def _rotate_list_left(lst, k):
    k = k % len(lst)
    return lst[k:] + lst[:k]


def _filter_markers_by_size(markers, tpl, img_width):
    """Filter markers by expected size, scaled to input image dimensions."""
    if not markers or 'fid_size' not in tpl:
        return markers
    # Scale expected marker size to input image, not template size
    # fid_size is the ratio of marker size to template width
    fid_ratio = tpl['fid_size']                    # e.g., 0.04 (80/2000)
    fid_px = fid_ratio * img_width                 # scale to actual input image width
    expected_square_area = fid_px * fid_px
    min_area = expected_square_area * 0.05         # allow smaller (aliasing/rotation/low-res)
    max_area = expected_square_area * 4.0          # exclude finger boxes
    filtered = [m for m in markers if min_area <= m['area'] <= max_area]
    return filtered or markers  # if filtered empty, fall back to original


def preprocess_image(input_path, template_json='template.json', output_dir='crops'):
    img_bgr = cv2.imread(input_path)
    if img_bgr is None:
        raise FileNotFoundError(input_path)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    tpl = load_template(template_json)
    TW, TH = tpl['width'], tpl['height']
    img_h, img_w = img_gray.shape  # input image dimensions

    warped_rgb = None

    # 1) Preferred: detect corner markers (3 squares + 1 triangle) and compute homography
    markers = detect_corner_markers(img_gray)
    markers = _filter_markers_by_size(markers, tpl, img_w)  # use input image width for scaling
    chosen = _assign_best_marker_per_corner(markers, img_w, img_h) if markers else None
    if chosen is not None and tpl.get('markers'):
        idx_triangle = None
        for i, m in enumerate(chosen):
            if m.get('type') == 'triangle':
                idx_triangle = i
                break

        src_pts = np.array([[m['cx'], m['cy']] for m in chosen], dtype='float32')
        dst_pts = _template_marker_points(tpl)

        if idx_triangle is None:
            # Still warp using squares, but 180° ambiguity can't be resolved reliably.
            rotation_needed_deg = None
            src_pts_aligned = src_pts
        else:
            # Rotate TL/TR/BR/BL list so that the triangle corner maps to template TL.
            rotation_needed_deg = int(((4 - idx_triangle) % 4) * 90)
            src_pts_aligned = np.roll(src_pts, -idx_triangle, axis=0)

        if rotation_needed_deg is None:
            print("Corner markers detected (no triangle). Rotation ambiguous.")
        else:
            print(f"Corner markers detected. rotation_needed_deg={rotation_needed_deg}")

        H = cv2.getPerspectiveTransform(src_pts_aligned, dst_pts)
        warped_rgb = cv2.warpPerspective(img_rgb, H, (TW, TH))
    else:
        print("Markers not detected (or template missing marker metadata). Falling back to largest contour.")

    # 2) Fallback: use largest contour as card boundary and warp to template corners
    if warped_rgb is None:
        corners = find_card_corners(img_gray)
        if corners is None:
            h, w = img_gray.shape
            corners = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype='float32')
        warped_rgb = warp_to_template(img_rgb, corners.astype('float32'), TW, TH)

    crops = crop_boxes_from_warp(warped_rgb, template_json, output_dir)
    return crops


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='input image (photo of card)')
    parser.add_argument('--template', default='template.json')
    parser.add_argument('--out', default='crops')
    args = parser.parse_args()
    croplist = preprocess_image(args.input, args.template, args.out)
    print('Wrote crops:')
    for p in croplist:
        print(' -', p)
