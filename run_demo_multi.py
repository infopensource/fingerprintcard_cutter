import random
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image, ImageEnhance

from src.build_card_templates import save_template_assets
from src.generate_cards_pdf import generate_cards
from src import preprocess_card


def _simulate_scan(img: Image.Image, dpi: int) -> Image.Image:
    angle = random.uniform(-6.0, 6.0)
    shift = int(0.02 * dpi)
    dx = random.randint(-shift, shift)
    dy = random.randint(-shift, shift)

    rotated = img.rotate(angle, expand=True, fillcolor='white')
    # apply simple translate using affine
    translated = rotated.transform(rotated.size, Image.AFFINE, (1, 0, dx, 0, 1, dy), fillcolor='white')

    # mild contrast tweak
    enhancer = ImageEnhance.Contrast(translated)
    translated = enhancer.enhance(random.uniform(0.95, 1.05))
    return translated


def run_demo(count: int = 2, dpi_choices=None):
    if dpi_choices is None:
        dpi_choices = [150, 200, 300]

    out_root = Path('demo_output_multi')
    pdf_dir = out_root / 'pdf'
    scan_dir = out_root / 'scans'
    crop_dir = out_root / 'crops'
    out_root.mkdir(exist_ok=True)
    pdf_dir.mkdir(exist_ok=True)
    scan_dir.mkdir(exist_ok=True)
    crop_dir.mkdir(exist_ok=True)

    # 1) build templates
    save_template_assets(output_dir=str(out_root))
    tpl_paths = {
        'finger': out_root / 'template_finger.json',
        'palm': out_root / 'template_palm.json',
    }

    # 2) generate PDF cards
    pdf_path = pdf_dir / 'cards.pdf'
    cards = generate_cards(count, str(pdf_path))

    # 3) render pages to images at varying DPI
    base_dpi = max(dpi_choices)
    pages = convert_from_path(str(pdf_path), dpi=base_dpi)

    for idx, page in enumerate(pages):
        card_idx = idx // 2
        is_finger = idx % 2 == 0
        role = 'finger' if is_finger else 'palm'
        uid = cards[card_idx]['uuid']

        target_dpi = random.choice(dpi_choices)
        if target_dpi != base_dpi:
            scale = target_dpi / float(base_dpi)
            new_size = (int(page.width * scale), int(page.height * scale))
            page_resized = page.resize(new_size, Image.BICUBIC)
        else:
            page_resized = page

        sim = _simulate_scan(page_resized, target_dpi)

        uid_dir = scan_dir / uid
        uid_dir.mkdir(exist_ok=True)
        img_path = uid_dir / f'{role}.png'
        sim.save(img_path)

        crops_out = crop_dir / uid
        crops_out.mkdir(exist_ok=True)
        preprocess_card.preprocess_image(
            str(img_path),
            str(tpl_paths[role]),
            output_dir=str(crops_out),
            name_suffix=uid,
            allow_contour_fallback=False,
        )

    print('Demo finished.')
    print('PDF:', pdf_path)
    print('Scans in:', scan_dir)
    print('Crops in:', crop_dir)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--count', type=int, default=2, help='number of cards (each has 2 pages)')
    args = parser.parse_args()

    run_demo(count=args.count)
