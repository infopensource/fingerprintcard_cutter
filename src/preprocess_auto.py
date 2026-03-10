from pathlib import Path
from functools import lru_cache
from time import perf_counter
import cv2
import numpy as np
from src import preprocess_card


# Reduce thread oversubscription inside each worker; main parallelism is at process level.
cv2.setUseOptimized(True)
try:
    cv2.setNumThreads(1)
except Exception:
    pass

_WECHAT_MODEL_DIR = Path(__file__).resolve().parent.parent / 'models' / 'wechat_qrcode'
_WECHAT_INIT_MSG_SHOWN = False


class LowQualityError(RuntimeError):
    """Raised when input is too ambiguous/low-quality to classify reliably."""


@lru_cache(maxsize=8)
def _load_template_cached(template_json: str):
    return preprocess_card.load_template(template_json)


@lru_cache(maxsize=8)
def _build_fill_mask(template_json: str, margin_px: int = 0) -> np.ndarray:
    tpl = _load_template_cached(template_json)
    W, H = tpl['width'], tpl['height']
    mask = np.zeros((H, W), dtype=np.uint8)

    # Use a small margin to tolerate slight misalignment after warp.
    margin = max(margin_px, int(0.01 * min(W, H)))

    for b in tpl.get('boxes', []):
        x0 = int(b['x'] * W) - margin
        y0 = int(b['y'] * H) - margin
        x1 = int((b['x'] + b['w']) * W) + margin
        y1 = int((b['y'] + b['h']) * H) + margin
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(W - 1, x1)
        y1 = min(H - 1, y1)
        cv2.rectangle(mask, (x0, y0), (x1, y1), 255, thickness=-1)

    return mask


@lru_cache(maxsize=8)
def _build_named_mask(template_json: str, names: tuple, margin_px: int = 0) -> np.ndarray:
    tpl = _load_template_cached(template_json)
    W, H = tpl['width'], tpl['height']
    mask = np.zeros((H, W), dtype=np.uint8)
    margin = max(margin_px, int(0.005 * min(W, H)))
    for b in tpl.get('boxes', []):
        if b.get('name') in names:
            x0 = int(b['x'] * W) - margin
            y0 = int(b['y'] * H) - margin
            x1 = int((b['x'] + b['w']) * W) + margin
            y1 = int((b['y'] + b['h']) * H) + margin
            x0 = max(0, x0)
            y0 = max(0, y0)
            x1 = min(W - 1, x1)
            y1 = min(H - 1, y1)
            cv2.rectangle(mask, (x0, y0), (x1, y1), 255, thickness=-1)
    return mask


def _warp_to_template(img_rgb: np.ndarray, tpl_json: str):
    tpl = _load_template_cached(tpl_json)
    TW, TH = tpl['width'], tpl['height']

    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    markers = preprocess_card.detect_corner_markers(img_gray)
    markers = preprocess_card._filter_markers_by_size(markers, tpl, img_rgb.shape[1]) if markers else []
    chosen = preprocess_card._assign_best_marker_per_corner(markers, img_rgb.shape[1], img_rgb.shape[0], tpl) if markers else None
    if chosen is None:
        raise RuntimeError('Markers not detected for warp')

    src_pts = np.array([[m['cx'], m['cy']] for m in chosen], dtype=np.float32)
    dst_pts = preprocess_card._template_marker_points(tpl)

    # Resolve 180° ambiguity using asymmetric triangle marker, same strategy as preprocess_card.
    idx_triangle = None
    for i, marker in enumerate(chosen):
        if marker.get('type') == 'triangle':
            idx_triangle = i
            break
    if idx_triangle is not None:
        src_pts = np.roll(src_pts, -idx_triangle, axis=0)

    tw_scaled, th_scaled, scale = preprocess_card._scaled_template_dims(img_rgb, TW, TH)
    dst_pts_scaled = dst_pts * scale

    H = cv2.getPerspectiveTransform(src_pts, dst_pts_scaled)
    warped_rgb = cv2.warpPerspective(img_rgb, H, (tw_scaled, th_scaled))
    warp_info = {
        'markers_found': len(markers),
        'markers_used': len([m for m in chosen if m is not None]),
        'template': Path(tpl_json).name,
        'scale': scale,
    }
    return warped_rgb, warp_info


@lru_cache(maxsize=1)
def _get_wechat_detector():
    global _WECHAT_INIT_MSG_SHOWN
    det_proto = _WECHAT_MODEL_DIR / 'detect.prototxt'
    det_model = _WECHAT_MODEL_DIR / 'detect.caffemodel'
    sr_proto = _WECHAT_MODEL_DIR / 'sr.prototxt'
    sr_model = _WECHAT_MODEL_DIR / 'sr.caffemodel'
    if not (det_proto.exists() and det_model.exists() and sr_proto.exists() and sr_model.exists()):
        if not _WECHAT_INIT_MSG_SHOWN:
            print(f"[qr] wechat models missing at {_WECHAT_MODEL_DIR}")
            _WECHAT_INIT_MSG_SHOWN = True
        return None
    if not hasattr(cv2, 'wechat_qrcode'):
        if not _WECHAT_INIT_MSG_SHOWN:
            print("[qr] OpenCV built without wechat_qrcode module")
            _WECHAT_INIT_MSG_SHOWN = True
        return None
    try:
        detector = cv2.wechat_qrcode.WeChatQRCode(str(det_proto), str(det_model), str(sr_proto), str(sr_model))
        if not _WECHAT_INIT_MSG_SHOWN:
            print("[qr] WeChat QR detector initialized")
            _WECHAT_INIT_MSG_SHOWN = True
        return detector
    except Exception as e:
        if not _WECHAT_INIT_MSG_SHOWN:
            print(f"[qr] failed to init WeChat QR: {e}")
            _WECHAT_INIT_MSG_SHOWN = True
        return None


def _wechat_decode_bgr(img_bgr):
    det = _get_wechat_detector()
    if det is None:
        return None
    try:
        texts, _ = det.detectAndDecode(img_bgr)
    except Exception:
        return None
    if not texts:
        return None
    return texts[0]


def _decode_qr_from_box(warped_rgb: np.ndarray, tpl_json: str):
    tpl = _load_template_cached(tpl_json)
    qr_box = None
    for b in tpl.get('boxes', []):
        if b.get('name') == 'qr_box':
            qr_box = b
            break
    if qr_box is None:
        return None, None

    H, W = warped_rgb.shape[:2]
    margin = int(0.02 * min(W, H))
    x0 = int(qr_box['x'] * W) - margin
    y0 = int(qr_box['y'] * H) - margin
    x1 = int((qr_box['x'] + qr_box['w']) * W) + margin
    y1 = int((qr_box['y'] + qr_box['h']) * H) + margin
    x0 = max(0, min(W, x0))
    y0 = max(0, min(H, y0))
    x1 = max(0, min(W, x1))
    y1 = max(0, min(H, y1))
    if x1 - x0 < 16 or y1 - y0 < 16:
        return None, None

    crop = warped_rgb[y0:y1, x0:x1]

    def try_decode(img_bgr):
        data = _wechat_decode_bgr(img_bgr)
        if data:
            return data
        detector = cv2.QRCodeDetector()
        data1, _, _ = detector.detectAndDecode(img_bgr)
        if data1:
            return data1
        try:
            data_multi, _, _ = detector.detectAndDecodeMulti(img_bgr)
            if data_multi:
                return data_multi[0]
        except Exception:
            pass
        return None

    crop_bgr = cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)

    # Build attempts: adaptive to crop size to avoid excessive upscales
    attempts = [crop_bgr]
    min_side = min(crop_bgr.shape[:2])
    scales = [1.5] if min_side >= 400 else [1.5, 2.0] if min_side >= 250 else [1.5, 2.0, 3.0]
    for scale in scales:
        up = cv2.resize(crop_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        attempts.append(up)
        gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
        thr_adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 5)
        attempts.append(cv2.cvtColor(thr_adapt, cv2.COLOR_GRAY2BGR))
        _, thr_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        attempts.append(cv2.cvtColor(thr_otsu, cv2.COLOR_GRAY2BGR))

    for img in attempts:
        data = _wechat_decode_bgr(img)
        if data:
            parts = data.split('|')
            uid = parts[0]
            page = parts[1].lower() if len(parts) > 1 else None
            return uid, page

    for img in attempts:
        data = try_decode(img)
        if data:
            parts = data.split('|')
            uid = parts[0]
            page = parts[1].lower() if len(parts) > 1 else None
            return uid, page

    return None, None


def _decode_qr_full_image(img_rgb: np.ndarray):
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

    data_wc = _wechat_decode_bgr(img_bgr)
    if data_wc:
        parts = data_wc.split('|')
        uid = parts[0]
        page = parts[1].lower() if len(parts) > 1 else None
        return uid, page

    def try_decode(img_bgr):
        detector = cv2.QRCodeDetector()
        data, pts, _ = detector.detectAndDecode(img_bgr)
        if data:
            return data
        try:
            data_multi, _, _ = detector.detectAndDecodeMulti(img_bgr)
            if data_multi:
                return data_multi[0]
        except Exception:
            pass
        return None

    attempts = [img_bgr]
    h, w = img_bgr.shape[:2]
    if min(h, w) < 1200:
        up = cv2.resize(img_bgr, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC)
        attempts.append(up)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    thr_adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 5)
    attempts.append(cv2.cvtColor(thr_adapt, cv2.COLOR_GRAY2BGR))
    _, thr_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    attempts.append(cv2.cvtColor(thr_otsu, cv2.COLOR_GRAY2BGR))

    for img in attempts:
        data = _wechat_decode_bgr(img)
        if data:
            parts = data.split('|')
            uid = parts[0]
            page = parts[1].lower() if len(parts) > 1 else None
            return uid, page

    for img in attempts:
        data = try_decode(img)
        if data:
            parts = data.split('|')
            uid = parts[0]
            page = parts[1].lower() if len(parts) > 1 else None
            return uid, page
    return None, None


def _score_warp(warped_rgb: np.ndarray, tpl_json: str):
    gray = cv2.cvtColor(warped_rgb, cv2.COLOR_RGB2GRAY)
    _, warped_bin = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    mask = _build_fill_mask(tpl_json)
    H, W = warped_rgb.shape[:2]
    if mask.shape[:2] != (H, W):
        mask = cv2.resize(mask, (W, H), interpolation=cv2.INTER_NEAREST)
    area = float(cv2.countNonZero(mask))
    ink = float(cv2.countNonZero(warped_bin))
    inter = float(cv2.countNonZero(cv2.bitwise_and(mask, warped_bin))) if area > 0 else 0.0
    cov = (inter / area) if area > 0 else 0.0
    prec = (inter / ink) if ink > 0 else 0.0
    score = 0.6 * cov + 0.4 * prec
    return {'score': score, 'cov': cov, 'prec': prec, 'area': area, 'ink': ink}


def _classify_page(img_rgb: np.ndarray, finger_template: str, palm_template: str):
    def warp_and_score(name, tpl_json):
        try:
            warped, info = _warp_to_template(img_rgb, tpl_json)
        except Exception:
            return None
        metrics = _score_warp(warped, tpl_json)
        metrics.update({'warp': warped, 'warp_info': info, 'template': tpl_json, 'name': name})
        return metrics

    res_f = warp_and_score('finger', finger_template)
    res_p = warp_and_score('palm', palm_template)

    if not res_f and not res_p:
        raise LowQualityError('warp_failed_both')

    if res_f and res_p:
        chosen = res_f if res_f['score'] >= res_p['score'] else res_p
    else:
        chosen = res_f or res_p

    # Keep both for QR validation/switch if needed
    return chosen, res_f, res_p


def preprocess_auto(input_path: str, finger_template: str, palm_template: str, output_dir: str = 'crops', allow_contour_fallback: bool = False):
    t0 = perf_counter()
    img_bgr = cv2.imread(input_path)
    if img_bgr is None:
        raise FileNotFoundError(input_path)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    info = {'file': Path(input_path).name}
    # 1) 先按墨迹/布局分类，拿到首选模板和 warp
    chosen, res_f, res_p = _classify_page(img_rgb, finger_template, palm_template)
    tpl_path = chosen['template']
    warped_rgb = chosen['warp']
    warp_info = chosen['warp_info']
    uid = None

    def _pick_by_page(page_name: str):
        nonlocal tpl_path, warped_rgb, warp_info, chosen, res_f, res_p
        if page_name not in ('finger', 'palm'):
            return False

        if page_name == 'finger':
            target = res_f
            target_tpl = finger_template
        else:
            target = res_p
            target_tpl = palm_template

        if target is None:
            try:
                target_warp, target_info = _warp_to_template(img_rgb, target_tpl)
                target = {
                    'warp': target_warp,
                    'warp_info': target_info,
                    'template': target_tpl,
                    'name': page_name,
                }
            except Exception:
                return False

        tpl_path = target['template']
        warped_rgb = target['warp']
        warp_info = target['warp_info']
        chosen = target
        return True

    print(
        f"[classify] {info['file']} score_f={res_f['score'] if res_f else 0:.3f} "
        f"score_p={res_p['score'] if res_p else 0:.3f} -> {chosen['name']}"
    )

    # 1.5) Full-image QR precheck: if page is available, use it as high-priority template hint.
    uid_full, page_full = _decode_qr_full_image(img_rgb)
    if uid_full and page_full in ('finger', 'palm'):
        switched = _pick_by_page(page_full)
        if switched:
            uid = uid_full
            print(f"[full-qr] {info['file']} page={page_full} -> use {Path(tpl_path).name}")

    # 2) 用首选模板位置裁 QR 做验证，失败则尝试另一模板
    if not uid:
        uid, page_dec = _decode_qr_from_box(warped_rgb, tpl_path)
    else:
        page_dec = chosen.get('name')

    # QR payload page has higher priority than visual classification.
    if uid and page_dec in ('finger', 'palm') and page_dec != chosen['name']:
        switched = _pick_by_page(page_dec)
        if switched:
            print(f"[qr-page] {info['file']} override classify -> {page_dec}")

    if not uid:
        alt = res_p if chosen['name'] == 'finger' else res_f
        if alt is None:
            try:
                alt_warp, alt_info = _warp_to_template(img_rgb, palm_template if chosen['name'] == 'finger' else finger_template)
                alt = {
                    'warp': alt_warp,
                    'warp_info': alt_info,
                    'template': palm_template if chosen['name'] == 'finger' else finger_template,
                    'name': 'palm' if chosen['name'] == 'finger' else 'finger',
                }
            except Exception:
                alt = None
        if alt:
            uid_alt, page_alt = _decode_qr_from_box(alt['warp'], alt['template'])
            if uid_alt:
                uid = uid_alt
                if page_alt in ('finger', 'palm'):
                    switched = _pick_by_page(page_alt)
                    if switched:
                        print(f"[qr-page] {info['file']} override classify -> {page_alt}")
                else:
                    tpl_path = alt['template']
                    warped_rgb = alt['warp']
                    warp_info = alt['warp_info']
                    chosen = alt

    if not uid:
        raise LowQualityError('qr_decode_failed_both_templates')

    if warp_info and warp_info.get('markers_used', 0) < 3:
        reason = f"markers_used={warp_info.get('markers_used', 0)}"
        print(f"[reject] {info['file']} {reason}")
        raise LowQualityError(reason)

    name_suffix = uid
    info.update({'page_source': 'classify+qr', 'page': chosen['name'], 'tpl': Path(tpl_path).name})

    if warped_rgb is not None:
        crops = preprocess_card.crop_boxes_from_warp(
            warped_rgb,
            template_json=tpl_path,
            out_dir=output_dir,
            name_suffix=name_suffix,
        )
        print(
            f"[done] {info['file']} {info['page_source']} tpl={info['tpl']} uid={uid} "
            f"warp scale={warp_info.get('scale', 1.0):.2f} -> {len(crops)} crops ({perf_counter() - t0:.2f}s)"
        )
        return crops

    # Should not reach here, but keep safe fallback
    print(f"[fallback] {info['file']} warp missing after QR decode")
    crops = preprocess_card.preprocess_image(
        input_path,
        template_json=tpl_path,
        output_dir=output_dir,
        name_suffix=name_suffix,
        allow_contour_fallback=allow_contour_fallback,
    )
    print(f"[done] {info['file']} fallback -> {len(crops)} crops ({perf_counter() - t0:.2f}s)")
    return crops


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='input image')
    parser.add_argument('--finger', required=True, help='finger template json')
    parser.add_argument('--palm', required=True, help='palm template json')
    parser.add_argument('--out', default='crops')
    parser.add_argument('--allow-contour-fallback', action='store_true')
    args = parser.parse_args()
    crops = preprocess_auto(args.input, args.finger, args.palm, args.out, allow_contour_fallback=args.allow_contour_fallback)
    print('Wrote crops:')
    for p in crops:
        print(' -', p)
