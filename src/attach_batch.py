"""
Batch attach ruler to parts during export with optional multiprocessing and progress.

Ruler selection rules:
  - finger rulers: parts starting with finger_*, or left_flat/right_flat
  - palm rulers  : parts starting with palm_*, or side_left/side_right
  - skip: qr, info, ruler_*, label_*
"""
from pathlib import Path
from typing import List, Optional, Tuple
import shutil
import multiprocessing

from src.ruler_attach import attach_ruler
from src import export_redirect


def _classify_ruler_kind(part_name: Optional[str], filename: str) -> Optional[str]:
    """Return 'finger' | 'palm' | None for given part."""
    stem = Path(filename).stem
    if stem.startswith('ruler_') or stem.startswith('label'):
        return None
    if part_name in ('info', 'qr'):
        return None
    if part_name is None:
        return None
    if part_name.startswith('finger_') or part_name in ('left_flat', 'right_flat'):
        return 'finger'
    if part_name.startswith('palm_') or part_name in ('side_left', 'side_right'):
        return 'palm'
    return None


def _find_ruler(workdir: Path, uuid_name: str, ruler_kind: str) -> Optional[Path]:
    uuid_dir = workdir / uuid_name
    pattern = 'ruler_finger_*.png' if ruler_kind == 'finger' else 'ruler_palm_*.png'
    rulers = sorted(uuid_dir.glob(pattern))
    return rulers[0] if rulers else None


def _build_out_path(output_path: Path, mode: str, uuid_name: str, filename: str, part_name: Optional[str]) -> Path:
    if mode == 'uuid':
        return output_path / uuid_name / filename
    if mode == 'flat':
        return output_path / filename
    # mode == 'part'
    part_dir = part_name if part_name else 'other'
    return output_path / part_dir / filename


def _attach_worker(args: Tuple[str, str, str, str, str, str, Optional[str]]) -> dict:
    file_path_str, out_file_str, position, ruler_kind, workdir_str, uuid_name, part_name = args
    file_path = Path(file_path_str)
    out_file = Path(out_file_str)
    workdir = Path(workdir_str)

    result = {
        'file': file_path.name,
        'status': 'copied',
        'detail': None,
    }

    ruler_path = _find_ruler(workdir, uuid_name, ruler_kind)

    try:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        if ruler_path and ruler_path.is_file():
            attach_ruler(str(file_path), str(ruler_path), str(out_file), position=position)
            result['status'] = 'attached'
        else:
            shutil.copy2(file_path, out_file)
            result['status'] = 'no_ruler'
    except Exception as e:
        result['status'] = 'failed'
        result['detail'] = str(e)[:120]
    return result


def attach_batch(
    workdir: str,
    output_dir: str,
    select: Optional[List[str]] = None,
    mode: str = 'uuid',
    position: str = 'left',
    threads: int = 1,
) -> dict:
    """
    Export parts from workdir and attach rulers.
    """
    workdir_path = Path(workdir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not workdir_path.is_dir():
        raise FileNotFoundError(f"workdir not found: {workdir}")
    if mode not in ('uuid', 'flat', 'part'):
        raise ValueError(f"mode must be 'uuid', 'flat' or 'part', got '{mode}'")
    if position not in ('left', 'right', 'top', 'bottom'):
        raise ValueError("position must be one of: left, right, top, bottom")

    select_set = set(select) if select else None

    tasks: List[Tuple[str, str, str, str, str, str, Optional[str]]] = []

    for uuid_dir in sorted(workdir_path.iterdir()):
        if not uuid_dir.is_dir():
            continue
        uuid_name = uuid_dir.name
        for file_path in sorted(uuid_dir.glob('*')):
            if not file_path.is_file():
                continue
            filename = file_path.name
            part_name = export_redirect._parse_part_name(filename)

            ruler_kind = _classify_ruler_kind(part_name, filename)
            if not ruler_kind:
                continue
            if select_set and part_name not in select_set:
                continue

            out_file = _build_out_path(output_path, mode, uuid_name, filename, part_name)
            tasks.append((
                str(file_path),
                str(out_file),
                position,
                ruler_kind,
                str(workdir_path),
                uuid_name,
                part_name,
            ))

    stats = {'total': len(tasks), 'attached': 0, 'exported_no_ruler': 0, 'failed': 0}

    if not tasks:
        print('[attach] No attachable parts found')
        return stats

    num_threads = min(max(1, threads), len(tasks))
    print(f"[attach] Tasks: {len(tasks)}, threads: {num_threads}")

    def _consume_results(iterator):
        processed = 0
        for res in iterator:
            processed += 1
            status = res['status']
            if status == 'attached':
                stats['attached'] += 1
            elif status == 'no_ruler':
                stats['exported_no_ruler'] += 1
            else:
                stats['failed'] += 1
            detail = f" ({res['detail']})" if res.get('detail') else ''
            print(f"[attach] [{processed}/{len(tasks)}] {res['file']}... {status}{detail}")

    if num_threads == 1:
        _consume_results(_attach_worker(task) for task in tasks)
    else:
        with multiprocessing.Pool(processes=num_threads) as pool:
            _consume_results(pool.imap_unordered(_attach_worker, tasks))

    return stats


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Export parts from workdir and attach rulers.')
    parser.add_argument('-w', '--workdir', required=True, help='Work directory')
    parser.add_argument('-o', '--output', required=True, help='Output directory')
    parser.add_argument('-s', '--select', nargs='*', default=[], help='Part names to process (space-separated)')
    parser.add_argument('-m', '--mode', choices=['uuid', 'flat', 'part'], default='uuid', help='Output directory structure')
    parser.add_argument('-p', '--position', choices=['left', 'right', 'top', 'bottom'], default='left', help='Ruler position')
    args = parser.parse_args()
    
    select_list = args.select if args.select else None
    stats = attach_batch(args.workdir, args.output, select=select_list, mode=args.mode, position=args.position)
    print(f"Attach complete: total={stats['total']} attached={stats['attached']} exported_no_ruler={stats['exported_no_ruler']} failed={stats['failed']}")
