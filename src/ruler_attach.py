import cv2
import numpy as np
from pathlib import Path
import argparse


def _load_image(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    return img


def _center_crop_or_pad(img: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    h, w = img.shape[:2]
    # Crop if larger
    y0 = max((h - target_h) // 2, 0)
    x0 = max((w - target_w) // 2, 0)
    y1 = min(y0 + target_h, h)
    x1 = min(x0 + target_w, w)
    cropped = img[y0:y1, x0:x1]

    # Pad if smaller
    pad_top = max((target_h - cropped.shape[0]) // 2, 0)
    pad_bottom = target_h - cropped.shape[0] - pad_top
    pad_left = max((target_w - cropped.shape[1]) // 2, 0)
    pad_right = target_w - cropped.shape[1] - pad_left

    if pad_top or pad_bottom or pad_left or pad_right:
        cropped = cv2.copyMakeBorder(cropped, pad_top, pad_bottom, pad_left, pad_right,
                                     borderType=cv2.BORDER_CONSTANT, value=[255, 255, 255])
    return cropped


def attach_ruler(part_path: str, ruler_path: str, out_path: str, position: str = 'right') -> str:
    """Attach ruler to a part image without scaling.

    position: 'left' | 'right' | 'top' | 'bottom'
    - For vertical rulers (height > width), center-crop/pad ruler to part height, then concat horizontally.
    - For horizontal rulers, center-crop/pad to part width, then concat vertically.
    """
    pos = position.lower()
    if pos not in {'left', 'right', 'top', 'bottom'}:
        raise ValueError("position must be one of: left, right, top, bottom")

    part = _load_image(part_path)
    ruler = _load_image(ruler_path)

    ph, pw = part.shape[:2]
    rh, rw = ruler.shape[:2]
    vertical = rh >= rw * 1.2  # heuristic: finger-page ruler is tall and thin

    if vertical:
        ruler_adj = _center_crop_or_pad(ruler, ph, rw)
        # Ensure same height
        if pos in ('left', 'right'):
            # heights already matched; widths can differ
            pass
        else:
            # If requested top/bottom with vertical ruler, still need matching width
            ruler_adj = _center_crop_or_pad(ruler_adj, ph, pw)
    else:
        # horizontal ruler
        ruler_adj = _center_crop_or_pad(ruler, rh, pw)
        if pos in ('top', 'bottom'):
            pass
        else:
            ruler_adj = _center_crop_or_pad(ruler_adj, ph, pw)

    if pos == 'left':
        combined = np.concatenate([ruler_adj, part], axis=1)
    elif pos == 'right':
        combined = np.concatenate([part, ruler_adj], axis=1)
    elif pos == 'top':
        combined = np.concatenate([ruler_adj, part], axis=0)
    else:  # bottom
        combined = np.concatenate([part, ruler_adj], axis=0)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(out_path, combined)
    return out_path


def main():
    parser = argparse.ArgumentParser(description='Attach ruler to part image without scaling.')
    parser.add_argument('part', help='part image path (e.g., finger_L_3_xxx.png)')
    parser.add_argument('ruler', help='ruler image path (ruler_finger_xxx.png or ruler_palm_xxx.png)')
    parser.add_argument('-o', '--out', help='output path', required=True)
    parser.add_argument('-p', '--position', choices=['left', 'right', 'top', 'bottom'], default='right',
                        help='where to place the ruler relative to the part')
    args = parser.parse_args()

    out = attach_ruler(args.part, args.ruler, args.out, position=args.position)
    print('Saved:', out)


if __name__ == '__main__':
    main()
