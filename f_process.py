#!/usr/bin/env python3
"""
f_process: Main CLI entry point for fingerprint/palm print card processing.

Usage:
  f_process gen    [options]   # 生成多页 PDF + 模板
  f_process pre    [options]   # 预处理扫描图并分割到"工作目录"(按 uuid 分组)
  f_process export [options]   # 从工作目录批量 redirect 导出（3 种目录结构）
  f_process attach [options]   # 从工作目录批量拼接标尺并导出（自动选指印/掌印标尺）
"""

import argparse
import sys
import traceback
from pathlib import Path
from time import perf_counter
import re
import shutil
import tempfile
import multiprocessing
import io
from contextlib import redirect_stdout

from src import preprocess_auto, preprocess_card
from src import export_redirect, attach_batch


# ===== Worker function for multiprocessing (must be at module level) =====
def _preprocess_worker(args):
    """Worker function for multi-threaded preprocessing.
    
    Returns a dict with processing result to maintain ordered output in main process.
    """
    (file_path_str, tpl_finger, tpl_palm, workdir_str,
     allow_contour_fallback, temp_dir_str, group_mode, force_template, quiet) = args
    
    file_path = Path(file_path_str)
    workdir = Path(workdir_str)
    temp_dir = Path(temp_dir_str)
    
    uuid_pattern = re.compile(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})')
    
    result = {
        'filename': file_path.name,
        'status': 'ok',
        'crops': 0,
        'error': None,
    }
    
    try:
        # Force a specific template: skip auto classification / QR-template selection.
        if force_template:
            if quiet:
                with redirect_stdout(io.StringIO()):
                    crops = preprocess_card.preprocess_image(
                        str(file_path),
                        template_json=str(force_template),
                        output_dir=str(temp_dir),
                        name_suffix=file_path.stem,
                        allow_contour_fallback=allow_contour_fallback
                    )
            else:
                crops = preprocess_card.preprocess_image(
                    str(file_path),
                    template_json=str(force_template),
                    output_dir=str(temp_dir),
                    name_suffix=file_path.stem,
                    allow_contour_fallback=allow_contour_fallback
                )
        else:
            # Auto preprocessing
            try:
                if quiet:
                    with redirect_stdout(io.StringIO()):
                        crops = preprocess_auto.preprocess_auto(
                            str(file_path),
                            str(tpl_finger),
                            str(tpl_palm),
                            output_dir=str(temp_dir),
                            allow_contour_fallback=allow_contour_fallback
                        )
                else:
                    crops = preprocess_auto.preprocess_auto(
                        str(file_path),
                        str(tpl_finger),
                        str(tpl_palm),
                        output_dir=str(temp_dir),
                        allow_contour_fallback=allow_contour_fallback
                    )
            except Exception:
                # Fallback to single template
                if quiet:
                    with redirect_stdout(io.StringIO()):
                        crops = preprocess_card.preprocess_image(
                            str(file_path),
                            template_json=str(tpl_finger),
                            output_dir=str(temp_dir),
                            allow_contour_fallback=allow_contour_fallback
                        )
                else:
                    crops = preprocess_card.preprocess_image(
                        str(file_path),
                        template_json=str(tpl_finger),
                        output_dir=str(temp_dir),
                        allow_contour_fallback=allow_contour_fallback
                    )
        
        # Organize files by UUID or by input filename
        if group_mode == 'name':
            group_dir = workdir / file_path.stem
            group_dir.mkdir(exist_ok=True, parents=True)
            for crop_file in temp_dir.glob('*'):
                if crop_file.is_file():
                    dest = group_dir / crop_file.name
                    shutil.copy2(str(crop_file), str(dest))
                    crop_file.unlink()
        else:
            for crop_file in temp_dir.glob('*'):
                if crop_file.is_file():
                    match = uuid_pattern.search(crop_file.name)
                    if match:
                        uuid = match.group(1)
                        uuid_dir = workdir / uuid
                        uuid_dir.mkdir(exist_ok=True, parents=True)
                        dest = uuid_dir / crop_file.name
                        shutil.copy2(str(crop_file), str(dest))
                    else:
                        fallback_dir = workdir / file_path.stem
                        fallback_dir.mkdir(exist_ok=True, parents=True)
                        dest = fallback_dir / crop_file.name
                        shutil.copy2(str(crop_file), str(dest))
                    crop_file.unlink()  # Clean up temp file either way
        
        result['crops'] = len(crops)
        
    except Exception as e:
        result['status'] = 'fail'
        result['error'] = str(e)[:100]
    
    return result


def setup_subparsers(parser, lang='en'):
    """Set up all subcommands. lang: 'en' or 'zh'"""
    
    # Help text templates
    help_text = {
        'en': {
            'gen_help': 'Generate multi-page PDF cards and template resources',
            'gen_count': 'Number of cards to generate (default: 1)',
            'gen_pdf': 'Output PDF path (default: cards.pdf)',
            'gen_template': 'Template output directory (default: templates)',
            'gen_dpi': 'Rendering DPI for PDF and template images (default: 600). Note: higher DPI improves PDF quality but does not affect segmentation quality from scans',
            
            'pre_help': 'Preprocess scan images and segment into work directory',
            'pre_input': 'Input directory or single image file',
            'pre_workdir': 'Work directory (outputs organized by UUID subdirectories)',
            'pre_template': 'Template directory (containing template_finger.json, template_palm.json, etc.)',
            'pre_template_note': 'Required when --force-template is not set',
            'pre_group': 'Grouping mode for output directories: uuid=<uuid>/<file>, name=<input_filename>/<file> (default: uuid)',
            'pre_fallback': 'Allow contour fallback when corner blocks are missing',
            'pre_threads': 'Use N processes for parallel processing (default: 1=single-threaded). Multi-threading accelerates processing but output is slightly delayed',
            'pre_force_template': 'Force a specific template JSON for segmentation; skips auto template classification and QR-based template decision',
            'pre_quiet': 'Quiet mode: suppress per-file and inner algorithm logs, keep summary only',
            
            'export_help': 'Export cropped parts from work directory in different directory structures',
            'export_workdir': 'Work directory',
            'export_output': 'Output directory',
            'export_select': 'Parts to export (space-separated). Empty means export all. Examples: finger_L_1 finger_L_2 palm_left',
            'export_mode': 'Output directory structure: uuid=<uuid>/<part>, flat=<part>, part=<part>/<part> (default: uuid)',
            
            'attach_help': 'Export and attach rulers to parts automatically',
            'attach_workdir': 'Work directory',
            'attach_output': 'Output directory',
            'attach_select': 'Parts to process (space-separated). Empty means all attachable parts. (default: empty)',
            'attach_mode': 'Output directory structure (default: uuid)',
            'attach_position': 'Ruler position relative to part (default: left)',
            'attach_threads': 'Use N processes for parallel attaching (default: 1)',
        },
        'zh': {
            'gen_help': '生成多页 PDF 卡片和模板资源',
            'gen_count': '生成卡片数量（默认: 1）',
            'gen_pdf': '输出 PDF 路径（默认: cards.pdf）',
            'gen_template': '模板输出目录（默认: templates）',
            'gen_dpi': 'PDF 和模板图像的渲染 DPI（默认: 600）。注：更高的 DPI 改进 PDF 质量，但不影响扫描分割结果的清晰度',
            
            'pre_help': '预处理扫描图并分割到工作目录',
            'pre_input': '输入目录或单个图像文件',
            'pre_workdir': '工作目录（输出按 UUID 子目录组织）',
            'pre_template': '模板目录（包含 template_finger.json、template_palm.json 等）',
            'pre_template_note': '未设置 --force-template 时必填',
            'pre_group': '输出分组方式：uuid=<uuid>/<文件>，name=<源图文件名>/<文件>（默认: uuid）',
            'pre_fallback': '当角块缺失时允许使用外轮廓兜底',
            'pre_threads': '使用 N 个进程并行处理（默认: 1=单线程）。多线程可加速处理但输出会稍有延迟',
            'pre_force_template': '强制使用指定模板 JSON 进行分割；跳过自动模板判断与二维码模板判定',
            'pre_quiet': '安静模式：抑制逐文件和内部算法日志，仅保留汇总输出',
            
            'export_help': '从工作目录批量导出部位（支持 3 种目录结构）',
            'export_workdir': '工作目录',
            'export_output': '输出目录',
            'export_select': '要导出的部位（空格分隔）。空=导出全部。示例: finger_L_1 finger_L_2 palm_left',
            'export_mode': '输出目录结构: uuid=<uuid>/<part>, flat=<part>, part=<part>/<part>（默认: uuid）',
            
            'attach_help': '导出并自动为部位拼接标尺',
            'attach_workdir': '工作目录',
            'attach_output': '输出目录',
            'attach_select': '要处理的部位（空格分隔）。空=处理全部可拼接部位。（默认: 空）',
            'attach_mode': '输出目录结构（默认: uuid）',
            'attach_position': '标尺相对于部位的位置（默认: left）',
            'attach_threads': '使用 N 个进程并行拼接（默认: 1）',
        }
    }
    
    h = help_text[lang]
    
    subparsers = parser.add_subparsers(
        title='subcommands' if lang == 'en' else '子命令',
        dest='command',
        help='Available commands' if lang == 'en' else '可用的子命令'
    )
    
    # ===== gen =====
    gen_parser = subparsers.add_parser('gen', help=h['gen_help'])
    gen_parser.add_argument('-n', '--count', type=int, default=1, help=h['gen_count'])
    gen_parser.add_argument('--out-pdf', default='cards.pdf', help=h['gen_pdf'])
    gen_parser.add_argument('-t', '--template', default='templates', help=h['gen_template'])
    gen_parser.add_argument('--dpi', type=int, default=600, help=h['gen_dpi'])
    
    # ===== pre =====
    pre_parser = subparsers.add_parser('pre', help=h['pre_help'])
    pre_parser.add_argument('-i', '--input', required=True, help=h['pre_input'])
    pre_parser.add_argument('-o', '--workdir', required=True, help=h['pre_workdir'])
    pre_parser.add_argument(
        '-t',
        '--template',
        default=None,
        help=f"{h['pre_template']} ({h['pre_template_note']})"
    )
    pre_parser.add_argument('--group', choices=['uuid', 'name'], default='uuid', help=h['pre_group'])
    pre_parser.add_argument('--allow-contour-fallback', action='store_true', help=h['pre_fallback'])
    pre_parser.add_argument('--threads', type=int, default=1, help=h['pre_threads'])
    pre_parser.add_argument('--force-template', default=None, help=h['pre_force_template'])
    pre_parser.add_argument('--quiet', action='store_true', help=h['pre_quiet'])
    
    # ===== export =====
    export_parser = subparsers.add_parser('export', help=h['export_help'])
    export_parser.add_argument('-w', '--workdir', required=True, help=h['export_workdir'])
    export_parser.add_argument('-o', '--output', required=True, help=h['export_output'])
    export_parser.add_argument('-s', '--select', nargs='*', default=[], help=h['export_select'])
    export_parser.add_argument('-m', '--mode', choices=['uuid', 'flat', 'part'], default='uuid', 
                              help=h['export_mode'])
    
    # ===== attach =====
    attach_parser = subparsers.add_parser('attach', help=h['attach_help'])
    attach_parser.add_argument('-w', '--workdir', required=True, help=h['attach_workdir'])
    attach_parser.add_argument('-o', '--output', required=True, help=h['attach_output'])
    attach_parser.add_argument('-s', '--select', nargs='*', default=[], help=h['attach_select'])
    attach_parser.add_argument('-m', '--mode', choices=['uuid', 'flat', 'part'], default='uuid',
                              help=h['attach_mode'])
    attach_parser.add_argument('-p', '--position', choices=['left', 'right', 'top', 'bottom'], 
                              default='left', help=h['attach_position'])
    attach_parser.add_argument('--threads', type=int, default=1, help=h['attach_threads'])


def cmd_gen(args):
    """生成多页 PDF + 模板."""
    from src.build_card_templates import save_template_assets
    from src.generate_cards_pdf import generate_cards

    print(f"[gen] Generating {args.count} cards...")
    t0 = perf_counter()
    
    # Generate templates
    template_dir = Path(args.template)
    template_dir.mkdir(parents=True, exist_ok=True)
    print(f"[gen] Saving templates to {template_dir}...")
    save_template_assets(output_dir=str(template_dir), dpi=args.dpi)
    
    # Generate PDF
    pdf_path = Path(args.out_pdf)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[gen] Generating PDF to {pdf_path}...")
    cards = generate_cards(args.count, str(pdf_path))
    
    elapsed = perf_counter() - t0
    print(f"[gen] Complete: {len(cards)} cards, {len(cards) * 2} pages in {elapsed:.2f}s")
    print(f"  PDF: {pdf_path}")
    print(f"  Templates: {template_dir}")
    for card in cards[:5]:  # Show first 5 UUIDs
        print(f"    UUID: {card['uuid']}")
    if len(cards) > 5:
        print(f"    ... and {len(cards) - 5} more")
    
    return 0


def cmd_pre(args):
    """预处理扫描图并分割到工作目录."""
    print(f"[pre] Preprocessing from {args.input}...")

    if not args.template and not args.force_template:
        print("ERROR: one of -t/--template or --force-template must be provided", file=sys.stderr)
        return 1
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input path not found: {args.input}", file=sys.stderr)
        return 1
    
    force_template_path = None
    if args.force_template:
        force_template_path = Path(args.force_template)
        if not force_template_path.is_file():
            print(f"ERROR: force template not found: {args.force_template}", file=sys.stderr)
            return 1
        tpl_finger = force_template_path
        tpl_palm = force_template_path
        print(f"[pre] Force template mode enabled: {force_template_path}")
    else:
        template_dir = Path(args.template)
        if not template_dir.is_dir():
            print(f"ERROR: Template directory not found: {args.template}", file=sys.stderr)
            return 1

        # Find template files
        tpl_finger = template_dir / 'template_finger.json'
        tpl_palm = template_dir / 'template_palm.json'

        if not tpl_finger.is_file():
            print(f"ERROR: {tpl_finger} not found", file=sys.stderr)
            return 1
        if not tpl_palm.is_file():
            print(f"ERROR: {tpl_palm} not found", file=sys.stderr)
            return 1
    
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    
    # Collect input files
    files = []
    if input_path.is_file():
        files = [input_path]
    else:
        for ext in ('*.jpg', '*.png', '*.jpeg', '*.JPG', '*.PNG', '*.JPEG'):
            files.extend(input_path.glob(ext))
        for ext in ('*.jpg', '*.png', '*.jpeg'):
            files.extend(input_path.glob(f'**/{ext}'))
    
    files = sorted(set(files))
    print(f"[pre] Found {len(files)} image(s)")
    
    if not files:
        print(f"ERROR: No image files found in {args.input}", file=sys.stderr)
        return 1
    
    # Dispatch to single or multi-threaded processing
    if args.threads and args.threads > 1:
        return _cmd_pre_multithread(args, files, str(tpl_finger), str(tpl_palm))
    else:
        return _cmd_pre_single(args, files, str(tpl_finger), str(tpl_palm))


def _cmd_pre_single(args, files, tpl_finger, tpl_palm):
    """Single-threaded preprocessing."""
    workdir = Path(args.workdir)
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix='preprocess_'))
    
    processed = 0
    failed = 0
    t0 = perf_counter()
    
    uuid_pattern = re.compile(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})')
    
    for idx, img_path in enumerate(files, 1):
        try:
            if not args.quiet:
                print(f"[pre] [{idx}/{len(files)}] Processing {img_path.name}...", end=' ')
            
            # Clean temp dir for this image
            for f in temp_dir.glob('*'):
                if f.is_file():
                    f.unlink()
            
            # Try auto preprocessing first
            if args.force_template:
                if args.quiet:
                    with redirect_stdout(io.StringIO()):
                        crops = preprocess_card.preprocess_image(
                            str(img_path),
                            template_json=str(args.force_template),
                            output_dir=str(temp_dir),
                            name_suffix=img_path.stem,
                            allow_contour_fallback=args.allow_contour_fallback
                        )
                else:
                    crops = preprocess_card.preprocess_image(
                        str(img_path),
                        template_json=str(args.force_template),
                        output_dir=str(temp_dir),
                        name_suffix=img_path.stem,
                        allow_contour_fallback=args.allow_contour_fallback
                    )
            else:
                try:
                    if args.quiet:
                        with redirect_stdout(io.StringIO()):
                            crops = preprocess_auto.preprocess_auto(
                                str(img_path),
                                str(tpl_finger),
                                str(tpl_palm),
                                output_dir=str(temp_dir),
                                allow_contour_fallback=args.allow_contour_fallback
                            )
                    else:
                        crops = preprocess_auto.preprocess_auto(
                            str(img_path),
                            str(tpl_finger),
                            str(tpl_palm),
                            output_dir=str(temp_dir),
                            allow_contour_fallback=args.allow_contour_fallback
                        )
                except Exception:
                    # Fallback: try single template preprocessing
                    if not args.quiet:
                        print("fallback", end=' ')
                    if args.quiet:
                        with redirect_stdout(io.StringIO()):
                            crops = preprocess_card.preprocess_image(
                                str(img_path),
                                template_json=str(tpl_finger),
                                output_dir=str(temp_dir),
                                allow_contour_fallback=args.allow_contour_fallback
                            )
                    else:
                        crops = preprocess_card.preprocess_image(
                            str(img_path),
                            template_json=str(tpl_finger),
                            output_dir=str(temp_dir),
                            allow_contour_fallback=args.allow_contour_fallback
                        )
            
            # Organize outputs
            if args.group == 'name':
                group_dir = workdir / img_path.stem
                group_dir.mkdir(exist_ok=True)
                for crop_file in temp_dir.glob('*'):
                    if crop_file.is_file():
                        dest = group_dir / crop_file.name
                        shutil.copy2(str(crop_file), str(dest))
            else:
                for crop_file in temp_dir.glob('*'):
                    if crop_file.is_file():
                        match = uuid_pattern.search(crop_file.name)
                        if match:
                            uuid = match.group(1)
                            uuid_dir = workdir / uuid
                            uuid_dir.mkdir(exist_ok=True)
                            dest = uuid_dir / crop_file.name
                            shutil.copy2(str(crop_file), str(dest))
                        else:
                            fallback_dir = workdir / img_path.stem
                            fallback_dir.mkdir(exist_ok=True)
                            dest = fallback_dir / crop_file.name
                            shutil.copy2(str(crop_file), str(dest))
            
            if not args.quiet:
                print(f"OK ({len(crops)} crops)")
            processed += 1
        except Exception as e:
            print(f"[pre] [{idx}/{len(files)}] {img_path.name}... FAIL: {str(e)[:50]}")
            failed += 1
    
    # Clean up temp directory
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass
    
    elapsed = perf_counter() - t0
    print(f"[pre] Complete: {processed} ok, {failed} failed in {elapsed:.2f}s")
    print(f"  Workdir: {workdir}")
    
    return 0 if failed == 0 else 1


def _cmd_pre_multithread(args, files, tpl_finger, tpl_palm):
    """Multi-threaded preprocessing using multiprocessing.Pool."""
    workdir = Path(args.workdir)
    num_threads = min(args.threads, len(files))  # Don't create more threads than files
    
    # Create base temp directory for all workers
    temp_base = Path(tempfile.mkdtemp(prefix='preprocess_pool_'))
    
    print(f"[pre] Using {num_threads} processes for {len(files)} files")
    
    # Prepare tasks - each worker gets its own temp directory
    tasks = []
    for idx, file_path in enumerate(files):
        temp_dir = temp_base / f'worker_{idx}'
        temp_dir.mkdir(parents=True, exist_ok=True)
        tasks.append((
            str(file_path),
            tpl_finger,
            tpl_palm,
            str(workdir),
            args.allow_contour_fallback,
            str(temp_dir),
            args.group,
            args.force_template,
            args.quiet,
        ))
    
    processed = 0
    failed = 0
    t0 = perf_counter()
    
    # Use Pool.map to maintain order
    with multiprocessing.Pool(processes=num_threads) as pool:
        for idx, result in enumerate(pool.map(_preprocess_worker, tasks), 1):
            if result['status'] == 'ok':
                crops = result['crops']
                if not args.quiet:
                    print(f"[pre] [{idx}/{len(files)}] {result['filename']}... OK ({crops} crops)")
                processed += 1
            else:
                error = result['error']
                print(f"[pre] [{idx}/{len(files)}] {result['filename']}... FAIL: {error}")
                failed += 1
    
    # Clean up temp directory
    try:
        shutil.rmtree(temp_base)
    except Exception:
        pass
    
    elapsed = perf_counter() - t0
    print(f"[pre] Complete: {processed} ok, {failed} failed in {elapsed:.2f}s")
    print(f"  Workdir: {workdir}")
    
    return 0 if failed == 0 else 1


def cmd_export(args):
    """从工作目录批量 redirect 导出."""
    print(f"[export] Exporting from {args.workdir} (mode={args.mode})...")
    t0 = perf_counter()
    
    select_list = args.select if args.select else None
    
    try:
        stats = export_redirect.export_workdir(
            args.workdir,
            args.output,
            select=select_list,
            mode=args.mode
        )
        
        elapsed = perf_counter() - t0
        print(f"[export] Complete in {elapsed:.2f}s")
        print(f"  Total: {stats['total']}, Copied: {stats['copied']}, Skipped: {stats['skipped']}")
        print(f"  Output: {args.output}")
        
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        return 1


def cmd_attach(args):
    """从工作目录批量拼接标尺并导出."""
    print(f"[attach] Attaching rulers from {args.workdir} (mode={args.mode}, position={args.position}, threads={args.threads})...")
    t0 = perf_counter()
    
    select_list = args.select if args.select else None
    
    try:
        stats = attach_batch.attach_batch(
            args.workdir,
            args.output,
            select=select_list,
            mode=args.mode,
            position=args.position,
            threads=args.threads,
        )
        
        elapsed = perf_counter() - t0
        print(f"[attach] Complete in {elapsed:.2f}s")
        print(f"  Total: {stats['total']}, Attached: {stats['attached']}, "
              f"Exported (no ruler): {stats['exported_no_ruler']}, Failed: {stats['failed']}")
        print(f"  Output: {args.output}")
        
        return 0 if stats['failed'] == 0 else 1
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        return 1


def main():
    """Bootstrap language parsing, then build the full parser so --lang appears in help."""
    # Step 1: bootstrap parser to capture --lang while still showing it in final help
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument('--lang', choices=['en', 'zh'], default='en',
                          help='Language for help text: en (English, default) or zh (中文)')
    args_bootstrap, remaining = bootstrap.parse_known_args()
    lang = args_bootstrap.lang

    # Step 2: build the main parser with the selected language
    parser = argparse.ArgumentParser(
        prog='f_process',
        description='Fingerprint/Palmprint card processing utility | 指纹/掌纹卡片处理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples (English):
  # Generate 5 cards
  f_process gen -n 5 --out-pdf cards.pdf -t templates

  # Preprocess scans
  f_process pre -i ./scans -o ./workdir -t ./templates

  # Export specific parts
  f_process export -w ./workdir -o ./output -m part -s finger_L_1 palm_left

  # Export with rulers
  f_process attach -w ./workdir -o ./output -m part -s finger_L_1 palm_left -p left

示例 (中文):
  # 生成 5 份卡片
  f_process gen -n 5 --out-pdf cards.pdf -t templates --lang zh

  # 预处理扫描图
  f_process pre -i ./scans -o ./workdir -t ./templates --lang zh

  # 导出指定部位
  f_process export -w ./workdir -o ./output -m part -s finger_L_1 palm_left --lang zh

  # 导出并拼接标尺
  f_process attach -w ./workdir -o ./output -m part -s finger_L_1 palm_left -p left --lang zh
        """
    )

    # Re-add lang so it shows in help/usage
    parser.add_argument('--lang', choices=['en', 'zh'], default='en',
                       help='Language for help text: en (English, default) or zh (中文)')

    setup_subparsers(parser, lang=lang)

    # Parse the full args (using remaining so --lang is already known, but still displayed in help)
    args = parser.parse_args(remaining)

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to subcommand
    try:
        if args.command == 'gen':
            return cmd_gen(args)
        elif args.command == 'pre':
            return cmd_pre(args)
        elif args.command == 'export':
            return cmd_export(args)
        elif args.command == 'attach':
            return cmd_attach(args)
        else:
            print(f"ERROR: Unknown command: {args.command}")
            return 1
    except KeyboardInterrupt:
        print("\n[interrupted]")
        return 130
    except Exception as e:
        print(f"\nERROR: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
