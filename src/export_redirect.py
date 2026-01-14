"""
Export utility to redirect cropped parts from workdir to output directory in multiple modes.

Modes:
  - uuid: output/<uuid>/<part>_<uuid>.png
  - flat: output/<part>_<uuid>.png
  - part: output/<part>/<part>_<uuid>.png
"""
import shutil
from pathlib import Path
from typing import List, Optional


def _parse_part_name(filename: str) -> Optional[str]:
    """Extract part name from filename like 'finger_L_1_uuid.png' or 'palm_left_uuid.png'."""
    stem = Path(filename).stem
    parts = stem.split('_')
    
    # Common patterns:
    # finger_L_1_<uuid>
    # finger_R_1_<uuid>
    # palm_left_<uuid>
    # palm_right_<uuid>
    # qr_<uuid>
    # info_<uuid>
    
    # For info and qr files
    if len(parts) >= 2 and parts[0] in ('info', 'qr'):
        return parts[0]
    
    # For finger files (finger_L/R_1_uuid or similar)
    if len(parts) >= 3 and parts[0] == 'finger':
        return f"{parts[0]}_{parts[1]}_{parts[2]}"
    
    # For palm files (palm_left/right_uuid)
    if len(parts) >= 2 and parts[0] == 'palm':
        return f"{parts[0]}_{parts[1]}"
    
    # If pattern doesn't match, use everything before last underscore (which is uuid)
    if '_' in stem:
        last_underscore = stem.rfind('_')
        return stem[:last_underscore]
    
    return None


def export_workdir(
    workdir: str,
    output_dir: str,
    select: Optional[List[str]] = None,
    mode: str = 'uuid'
) -> dict:
    """
    Export parts from workdir to output_dir.
    
    Args:
        workdir: Work directory containing <uuid>/ subdirectories with cropped parts
        output_dir: Destination directory
        select: List of part names to export (e.g., ['finger_L_1', 'palm_left', 'qr']).
                None means export all parts.
        mode: 'uuid' | 'flat' | 'part'
    
    Returns:
        dict with statistics {total: int, copied: int, skipped: int}
    """
    workdir_path = Path(workdir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if not workdir_path.is_dir():
        raise FileNotFoundError(f"workdir not found: {workdir}")
    
    if mode not in ('uuid', 'flat', 'part'):
        raise ValueError(f"mode must be 'uuid', 'flat' or 'part', got '{mode}'")
    
    # Parse select list
    select_set = set(select) if select else None
    
    stats = {'total': 0, 'copied': 0, 'skipped': 0}
    
    # Iterate over all uuid subdirectories
    for uuid_dir in sorted(workdir_path.iterdir()):
        if not uuid_dir.is_dir():
            continue
        
        uuid_name = uuid_dir.name
        
        # Iterate over all files in the uuid directory
        for file_path in sorted(uuid_dir.glob('*')):
            if not file_path.is_file():
                continue
            
            filename = file_path.name
            part_name = _parse_part_name(filename)
            
            # Check if this part should be exported
            stats['total'] += 1
            if select_set and part_name not in select_set:
                stats['skipped'] += 1
                continue
            
            # Determine output path based on mode
            if mode == 'uuid':
                # output/<uuid>/<filename>
                out_file = output_path / uuid_name / filename
            elif mode == 'flat':
                # output/<filename>
                out_file = output_path / filename
            else:  # mode == 'part'
                # output/<part>/<filename>
                if part_name is None:
                    part_name = 'other'
                out_file = output_path / part_name / filename
            
            # Create parent directory if needed
            out_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            try:
                shutil.copy2(file_path, out_file)
                stats['copied'] += 1
            except Exception as e:
                print(f"Error copying {file_path} -> {out_file}: {e}")
                stats['skipped'] += 1
    
    return stats


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Export parts from workdir to output directory.')
    parser.add_argument('-w', '--workdir', required=True, help='Work directory')
    parser.add_argument('-o', '--output', required=True, help='Output directory')
    parser.add_argument('-s', '--select', nargs='*', default=[], help='Part names to export (space-separated)')
    parser.add_argument('-m', '--mode', choices=['uuid', 'flat', 'part'], default='uuid', help='Output directory structure')
    args = parser.parse_args()
    
    select_list = args.select if args.select else None
    stats = export_workdir(args.workdir, args.output, select=select_list, mode=args.mode)
    print(f"Export complete: total={stats['total']} copied={stats['copied']} skipped={stats['skipped']}")
