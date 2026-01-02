from src.generate_template import build_template
from src import preprocess_card
from PIL import Image
import os


def make_simulated_photo(template_png='template.png', out='simulated_capture.png'):
    # open template and rotate + paste on larger white background to simulate a photo
    img = Image.open(template_png)
    # rotate a bit
    img_rot = img.rotate(240, expand=True, fillcolor='white')
    bg_w = img_rot.width + 400
    bg_h = img_rot.height + 300
    bg = Image.new('RGB', (bg_w, bg_h), 'white')
    # paste with offset
    bg.paste(img_rot, (180, 120))
    bg.save(out)
    return out


if __name__ == '__main__':
    build_template('template.png', 'template.json')
    print('Template generated.')
    # sim = make_simulated_photo('template.png', 'simulated_capture.png')
    # sim = 'image.png'
    sim = 'template.png'
    print('Simulated photo:', sim)
    os.makedirs('demo_output', exist_ok=True)
    crops = preprocess_card.preprocess_image(sim, 'template.json', output_dir='demo_output')
    print('Crops saved to demo_output')
