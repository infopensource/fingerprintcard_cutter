"""
捺印卡PDF批量生成器
Fingerprint/Palmprint Card PDF Batch Generator

生成包含多个UUID的捺印卡PDF文件
每个UUID对应两页: 第一页指纹卡，第二页掌纹卡
"""

import uuid
import os
import argparse
from PIL import Image
from io import BytesIO

# 尝试导入reportlab (PDF生成)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("警告: reportlab未安装，将使用Pillow生成PDF (功能受限)")

from src.generate_fingerprint_template import build_fingerprint_template
from src.generate_palmprint_template import build_palmprint_template


def generate_cards_pdf(num_cards: int, output_pdf: str = 'collection_cards.pdf',
                       output_dir: str = 'generated_cards'):
    """
    生成捺印卡PDF
    
    Args:
        num_cards: 需要生成的捺印卡数量 (每个人一套，包含指纹+掌纹两页)
        output_pdf: 输出PDF文件名
        output_dir: 临时图片输出目录
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成UUID列表
    uuids = [str(uuid.uuid4()) for _ in range(num_cards)]
    
    print(f"正在生成 {num_cards} 套捺印卡...")
    print(f"UUID列表: ")
    for i, u in enumerate(uuids):
        print(f"  {i+1}. {u}")
    
    # 生成所有图片
    images = []
    for i, uid in enumerate(uuids):
        print(f"\n生成第 {i+1}/{num_cards} 套...")
        
        # 生成指纹卡
        fp_img, _ = build_fingerprint_template(
            output_png=os.path.join(output_dir, f'fingerprint_{i+1}.png'),
            output_json=None,
            uuid_str=uid,
            save_image=True
        )
        images.append(fp_img)
        
        # 生成掌纹卡
        pp_img, _ = build_palmprint_template(
            output_png=os.path.join(output_dir, f'palmprint_{i+1}.png'),
            output_json=None,
            uuid_str=uid,
            save_image=True
        )
        images.append(pp_img)
    
    # 生成PDF
    print(f"\n正在合并为PDF: {output_pdf}")
    
    if HAS_REPORTLAB:
        _generate_pdf_reportlab(images, output_pdf)
    else:
        _generate_pdf_pillow(images, output_pdf)
    
    print(f"\n✓ PDF生成完成: {output_pdf}")
    print(f"✓ 共 {len(images)} 页 ({num_cards} 套捺印卡)")
    
    # 保存UUID映射
    uuid_file = os.path.join(output_dir, 'uuid_mapping.txt')
    with open(uuid_file, 'w', encoding='utf-8') as f:
        f.write("# 捺印卡UUID映射表\n")
        f.write("# 序号, UUID, 指纹卡页码, 掌纹卡页码\n")
        for i, uid in enumerate(uuids):
            f.write(f"{i+1}, {uid}, {i*2+1}, {i*2+2}\n")
    print(f"✓ UUID映射表已保存: {uuid_file}")
    
    return output_pdf, uuids


def _generate_pdf_reportlab(images: list, output_pdf: str):
    """使用reportlab生成PDF (高质量)"""
    # A4尺寸 (点): 595.27 x 841.89
    c = canvas.Canvas(output_pdf, pagesize=A4)
    page_width, page_height = A4
    
    for i, img in enumerate(images):
        # 转换为RGB (如果是RGBA)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # 将PIL Image转换为reportlab可用的格式
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG', dpi=(300, 300))
        img_buffer.seek(0)
        
        # 计算缩放以适应A4
        img_width, img_height = img.size
        scale_w = page_width / img_width
        scale_h = page_height / img_height
        scale = min(scale_w, scale_h)
        
        new_width = img_width * scale
        new_height = img_height * scale
        
        # 居中
        x = (page_width - new_width) / 2
        y = (page_height - new_height) / 2
        
        # 绘制图片
        img_reader = ImageReader(img_buffer)
        c.drawImage(img_reader, x, y, new_width, new_height)
        
        # 添加新页面 (除了最后一页)
        if i < len(images) - 1:
            c.showPage()
    
    c.save()


def _generate_pdf_pillow(images: list, output_pdf: str):
    """使用Pillow生成PDF (备用方案)"""
    # 转换为RGB
    rgb_images = []
    for img in images:
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        rgb_images.append(img)
    
    # 保存为PDF
    if rgb_images:
        rgb_images[0].save(
            output_pdf, 
            'PDF', 
            resolution=300,
            save_all=True, 
            append_images=rgb_images[1:]
        )


def main():
    parser = argparse.ArgumentParser(
        description='批量生成指纹掌纹采集卡PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python generate_cards_pdf.py 10              # 生成10套捺印卡
  python generate_cards_pdf.py 5 -o cards.pdf  # 生成5套，输出为cards.pdf
  python generate_cards_pdf.py 3 -d output     # 生成3套，图片保存到output目录
        '''
    )
    parser.add_argument('num_cards', type=int, help='需要生成的捺印卡数量')
    parser.add_argument('-o', '--output', type=str, default='collection_cards.pdf',
                        help='输出PDF文件名 (默认: collection_cards.pdf)')
    parser.add_argument('-d', '--dir', type=str, default='generated_cards',
                        help='临时图片输出目录 (默认: generated_cards)')
    
    args = parser.parse_args()
    
    if args.num_cards <= 0:
        print("错误: 捺印卡数量必须大于0")
        return
    
    generate_cards_pdf(args.num_cards, args.output, args.dir)


if __name__ == '__main__':
    main()
