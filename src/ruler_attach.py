import cv2
import numpy as np
from pathlib import Path
import argparse


def _load_image(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    return img


def _center_crop_pad_axis(img: np.ndarray, target_len: int, axis: int) -> np.ndarray:
    """Center-crop or pad along a single axis without scaling."""
    h, w = img.shape[:2]
    if axis == 0:  # vertical (height)
        excess = h - target_len
        if excess > 0:
            start = excess // 2
            img = img[start:start + target_len, :]
        elif excess < 0:
            pad_top = (-excess) // 2
            pad_bottom = -excess - pad_top
            img = cv2.copyMakeBorder(img, pad_top, pad_bottom, 0, 0, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    else:  # horizontal (width)
        excess = w - target_len
        if excess > 0:
            start = excess // 2
            img = img[:, start:start + target_len]
        elif excess < 0:
            pad_left = (-excess) // 2
            pad_right = -excess - pad_left
            img = cv2.copyMakeBorder(img, 0, 0, pad_left, pad_right, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    return img


def attach_ruler(part_path: str, ruler_path: str, out_path: str, position: str = 'right') -> str:
    """Attach ruler to a part image without any scaling.

    - Use ruler long edge aligned to the attach direction; rotate 90° if needed.
    - Center-crop along the long edge to match the part dimension; pad if shorter.
    - No resizing is performed (scale accuracy preserved).
    """
    pos = position.lower()
    if pos not in {'left', 'right', 'top', 'bottom'}:
        raise ValueError("position must be one of: left, right, top, bottom")

    part = _load_image(part_path)
    ruler = _load_image(ruler_path)

    ph, pw = part.shape[:2]
    rh, rw = ruler.shape[:2]

    desired_vertical = pos in ('left', 'right')
    ruler_vertical = rh >= rw  # long edge orientation

    # Rotate ruler so long edge aligns with desired orientation
    if desired_vertical and not ruler_vertical:
        ruler = np.rot90(ruler)
        rh, rw = ruler.shape[:2]
    elif not desired_vertical and ruler_vertical:
        ruler = np.rot90(ruler)
        rh, rw = ruler.shape[:2]

    if desired_vertical:
        ruler_adj = _center_crop_pad_axis(ruler, ph, axis=0)
    else:
        ruler_adj = _center_crop_pad_axis(ruler, pw, axis=1)

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
