from pathlib import Path
import multiprocessing
import os
from time import perf_counter
from src import preprocess_auto
from src.build_card_templates import save_template_assets

# Helper function must be at module level for multiprocessing
def _worker_process_file(args):
    img_path_str, tpl_finger, tpl_palm, output_root_str = args
    img_path = Path(img_path_str)
    output_root = Path(output_root_str)
    
    stem = img_path.stem
    out_dir = output_root / stem
    out_dir.mkdir(exist_ok=True, parents=True)
    log_path = output_root / 'errors.log'
    t0 = perf_counter()
    
    try:
        preprocess_auto.preprocess_auto(
            str(img_path),
            finger_template=tpl_finger,
            palm_template=tpl_palm,
            output_dir=str(out_dir),
            allow_contour_fallback=True,
        )
        return f"[OK] {stem} -> {out_dir} ({perf_counter() - t0:.2f}s)"
    except Exception as e:
        import traceback
        traceback.print_exc()
        msg = f"[FAIL] {stem}: {e} ({perf_counter() - t0:.2f}s)"
        try:
            with log_path.open('a', encoding='utf-8') as f:
                f.write(msg + "\n")
        except Exception:
            pass
        return msg

def process_samples():
    # 1. Generate templates
    template_dir = Path('templates_generated')
    template_dir.mkdir(exist_ok=True)
    save_template_assets(output_dir=str(template_dir))
    
    tpl_finger = str(template_dir / 'template_finger.json')
    tpl_palm = str(template_dir / 'template_palm.json')

    # 2. Input/Output setup
    input_dir = Path('sample_scan/AB面scan')
    output_root = Path('sample_output')
    output_root.mkdir(exist_ok=True)

    if not input_dir.exists():
        print(f"Error: input directory {input_dir} not found.")
        return

    # 3. Process files
    extensions = ['*.jpg', '*.png', '*.jpeg']
    files = []
    for ext in extensions:
        files.extend(input_dir.glob(ext))
    
    files = sorted(files)
    total_files = len(files)
    print(f"Found {total_files} files in {input_dir}")

    # Prepare arguments for workers
    # We pass strings to avoid pickling issues with some Path objects if any
    tasks = [
        (str(p), tpl_finger, tpl_palm, str(output_root)) 
        for p in files
    ]

    # Limit processes to avoid OOM. 
    # Use min(cpu_count, 4) or even 2 if memory is very tight.
    # Assuming 600dpi scans, 2-4 is probably safe on 16GB+ RAM. 
    # Let's be conservative with 4 by default, override via MAX_PROCS env.
    max_procs = int(os.environ.get('MAX_PROCS', '4'))
    num_procs = min(os.cpu_count() or 1, max_procs)
    print(f"Starting processing with {num_procs} processes... (MAX_PROCS={max_procs})")

    start_total = perf_counter()
    ok = 0
    fail = 0
    with multiprocessing.Pool(processes=num_procs) as pool:
        # Use imap_unordered for responsiveness
        for res in pool.imap_unordered(_worker_process_file, tasks):
            print(res)
            if res.startswith('[OK]'):
                ok += 1
            else:
                fail += 1
    elapsed = perf_counter() - start_total
    print(f"[summary] total={total_files} ok={ok} fail={fail} elapsed={elapsed:.2f}s")

if __name__ == '__main__':
    # Ensure support for spawn on some platforms, though Linux usually uses fork
    multiprocessing.freeze_support() 
    process_samples()
