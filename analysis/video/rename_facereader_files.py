"""Rename FaceReader exports using the participant ID from the source video.

FaceReader names exports after its own participant slot, e.g.
    Participant 1_Participant 1_Analysis 1_video_20261020_130114_detailed.xlsx
but the header block inside each file records the real video, e.g.
    Filename    D:\\Biosignals2_video\\M9351_1to1_ffv1.avi
This script reads that header, takes the PID (the part of the video name
before the first "_"), and renames the export to PID + the log type that follows the timestamp:
    M9351_detailed.xlsx, M9351_state.xlsx, M9351_heart beat log.txt, ...
The .odx project file has no Filename row, so it gets the PID of the exports
with the same "Participant N" in their name (renamed in the same run): M9351.odx

Folder: FACEREADER_RESULTS_DIR from the nearest config.py above this script
(the repo-root config.py). Pass --folder to use a different one.

Dry run by default; add --apply to rename.

    python analysis\\video\\rename_facereader_files.py
    python analysis\\video\\rename_facereader_files.py --apply
"""
import argparse
import importlib.util
import re
import sys
from pathlib import Path, PureWindowsPath

import openpyxl

HEADER_ROWS = 30  # the "Filename" row is in the header block at the top
FR_PREFIX = re.compile(r"^Participant \d+_Participant \d+_")
SLOT_RE = re.compile(r"Participant (\d+)")  # FaceReader's participant slot
TIMESTAMP_RE =re.compile(r"_\d{8}_\d{6}(?=_)")  # e.g. _20261020_130114
PID_RE = re.compile(r"^[A-Za-z]\d+$")  # e.g. M9351; adjust if your IDs differ


def source_video(path: Path) -> str | None:
    """Return the value next to 'Filename' in the export's header block."""
    if path.suffix.lower() == ".xlsx":
        wb = openpyxl.load_workbook(path, read_only=True)
        try:
            rows = wb.worksheets[0].iter_rows(max_row=HEADER_ROWS, values_only=True)
            for row in rows:
                if row and str(row[0]).strip() == "Filename" and len(row) > 1:
                    return str(row[1]).strip()
        finally:
            wb.close()
    else:  # tab-separated .txt export
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            for _, line in zip(range(HEADER_ROWS), f):
                parts = line.rstrip("\r\n").split("\t")
                if parts[0].strip() == "Filename" and len(parts) > 1:
                    return parts[1].strip()
    return None


def config_folder() -> Path:
    """FACEREADER_RESULTS_DIR from the nearest config.py in this folder or above."""
    folder = Path(__file__).resolve().parent
    while not (folder / "config.py").is_file():
        if folder.parent == folder:
            sys.exit(f"No config.py found above {Path(__file__).resolve().parent}")
        folder = folder.parent
    # Load by path, so a different `config` module can't be picked up by mistake
    spec = importlib.util.spec_from_file_location("rename_fr_config", folder / "config.py")
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    if not hasattr(cfg, "FACEREADER_RESULTS_DIR"):
        sys.exit(f"{folder / 'config.py'} does not define FACEREADER_RESULTS_DIR")
    return Path(cfg.FACEREADER_RESULTS_DIR)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder", type=Path,
                    help="override FACEREADER_RESULTS_DIR from config.py")
    ap.add_argument("--apply", action="store_true", help="rename (default: dry run)")
    args = ap.parse_args()
    args.folder = args.folder or config_folder()
    if not args.folder.is_dir():
        sys.exit(f"Folder not found: {args.folder}")
    print(f"FaceReader folder: {args.folder}\n")

    files = sorted(p for p in args.folder.iterdir()
                   if p.suffix.lower() in (".xlsx", ".txt")
                   and FR_PREFIX.match(p.name))  # skip files already renamed
    odx_files = sorted(p for p in args.folder.iterdir()
                       if p.suffix.lower() == ".odx" and SLOT_RE.search(p.stem))
    if not files and not odx_files:
        print("No 'Participant N_...' exports or .odx files found.")
        return 0

    problems = 0
    slot_pids: dict[str, set[str]] = {}  # FaceReader "Participant N" -> PIDs seen
    for p in files:
        video = source_video(p)
        if not video:
            print(f"SKIP  {p.name}: no 'Filename' row in header")
            problems += 1
            continue
        pid = PureWindowsPath(video).stem.split("_")[0]
        if not PID_RE.match(pid):
            print(f"SKIP  {p.name}: unexpected PID '{pid}' from {video}")
            problems += 1
            continue
        slot_pids.setdefault(SLOT_RE.search(p.name).group(1), set()).add(pid)
        m = TIMESTAMP_RE.search(p.name)
        if not m:
            print(f"SKIP  {p.name}: no _YYYYMMDD_HHMMSS timestamp to split on")
            problems += 1
            continue
        new = p.with_name(pid + p.name[m.end():])  # e.g. M9351_detailed.xlsx
        if new.exists():
            print(f"SKIP  {p.name}: {new.name} already exists")
            problems += 1
            continue
        print(f"{'RENAME' if args.apply else 'WOULD'}  {p.name}  ->  {new.name}")
        if args.apply:
            p.rename(new)

    # .odx has no Filename row: take the PID from the exports with the same
    # "Participant N" in their name (found above, in this run).
    for p in odx_files:
        slot = SLOT_RE.search(p.stem).group(1)
        pids = slot_pids.get(slot, set())
        if len(pids) != 1:
            why = ("no export for Participant " + slot + " in this run" if not pids
                   else "Participant " + slot + " matches several PIDs: " + ", ".join(sorted(pids)))
            print(f"SKIP  {p.name}: {why}")
            problems += 1
            continue
        new = p.with_name(f"{pids.pop()}.odx")
        if new.exists():
            print(f"SKIP  {p.name}: {new.name} already exists")
            problems += 1
            continue
        print(f"{'RENAME' if args.apply else 'WOULD'}  {p.name}  ->  {new.name}")
        if args.apply:
            p.rename(new)

    if not args.apply:
        print("\nDry run only. Re-run with --apply to rename.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
