"""
fix_participant_id.py - change a participant ID everywhere outside Qualtrics.

The Qualtrics questionnaire ID is treated as correct. This script renames every
file and folder whose name contains the wrong ID, and corrects the ID inside
text files (.csv .txt .log .json .tsv .md) and PsychoPy .psydat files whose
name contains it. Case is kept:
"s9689" becomes "s9686" and "S9689" becomes "S9686".

DRY RUN BY DEFAULT: it only prints what it would do. Add --apply to do it.

    python fix_participant_id.py --old S9689 --new S9686            # preview
    python fix_participant_id.py --old S9689 --new S9686 --apply    # do it

Searched by default (paths from config.py, skipped if missing):
    SERVER_ROOT (Box 3_Data, all subfolders) except raw_questionnaire and
    clean_combined_data, plus WEBCAM_DIR and VIDEO_DIR on D:.
Use --roots to search other folders instead (e.g. the lab PC's Experiment\\data).

Not changed:
  * raw_questionnaire  - Qualtrics is the correct source.
  * clean_combined_data - regenerate it: re-knit 01_data_cleaning.Rmd and
    04_questionnaire_analysis.Rmd afterwards.
  * Files whose NAME does not contain the ID (e.g. Kubios batch summaries,
    nid_map_psychopy_ledalab.txt). Add --scan-contents to also fix the ID inside
    every text file under 50 MB. On Box Drive this downloads those files, so it
    is slow.
  * The inside of other binary files (.acq .zip .avi .mkv .xlsx .odx .mat ...).
    They are renamed only; the script lists them so you know their contents
    still mention the old ID (e.g. the folder name inside <id>_frames.zip).

On --apply, every change is appended to id_changes_log.csv in SERVER_ROOT
(or the first searched folder if SERVER_ROOT isn't there).
The script stops before changing anything if files for the new ID already exist.
"""
import argparse
import csv
import datetime as dt
import pickletools
import os
import re
import sys
import tempfile

TEXT_EXT = {".csv", ".txt", ".log", ".json", ".tsv", ".md"}
# Pickle files (PsychoPy .psydat): the ID is swapped byte for byte. Only safe when the old
# and new IDs have the same length (pickle stores string lengths), and the file is checked
# to still be a valid pickle before it replaces the original.
PICKLE_EXT = {".psydat"}
SCAN_MAX_BYTES = 50 * 1024**2
SKIP_DIRS = {"raw_questionnaire", "clean_combined_data"}


def id_pattern(pid):
    # whole ID only: not preceded by a letter/digit, not followed by a digit
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(pid) + r"(?![0-9])", re.IGNORECASE)


def make_replacer(new):
    def repl(m):
        s = m.group(0)
        if s.isupper():
            return new.upper()
        if s.islower():
            return new.lower()
        return new
    return repl


def default_roots():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import config  # analysis/config.py
    return [config.SERVER_ROOT, config.WEBCAM_DIR, config.VIDEO_DIR], config.SERVER_ROOT


def walk(roots):
    """Yield (dirpath, dirnames, filenames) bottom-up (contents before their folder), skipping SKIP_DIRS."""
    for root in roots:
        if not os.path.isdir(root):
            print(f"  (skipping, not found: {root})")
            continue
        for dirpath, dirnames, filenames in os.walk(root, topdown=False):
            rel_parts = os.path.relpath(dirpath, root).split(os.sep)
            if any(p in SKIP_DIRS for p in rel_parts):
                continue
            yield dirpath, [d for d in dirnames if d not in SKIP_DIRS], filenames


def fix_contents(path, pat, repl, apply):
    """Replace the ID inside a text file. Returns the number of replacements."""
    n = 0
    tmp = None
    with open(path, "r", encoding="utf-8", errors="surrogateescape", newline="") as src:
        if apply:
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".idfix.tmp")
            dst = os.fdopen(fd, "w", encoding="utf-8", errors="surrogateescape", newline="")
        for line in src:
            new_line, k = pat.subn(repl, line)
            n += k
            if apply:
                dst.write(new_line)
        if apply:
            dst.close()
    if apply:
        if n > 0:
            os.replace(tmp, path)
        else:
            os.remove(tmp)
    return n


def pickle_ok(path):
    """True if the file parses as a pickle (opcodes only; no PsychoPy needed)."""
    try:
        with open(path, "rb") as f:
            for _ in pickletools.genops(f):
                pass
        return True
    except Exception:
        return False


def fix_pickle(path, old, new, apply):
    """Swap the ID inside a pickle (.psydat). Returns the number of replacements."""
    if len(old) != len(new):
        raise ValueError("old and new IDs differ in length; a pickle can't be edited byte for byte")
    pat = re.compile(rb"(?<![A-Za-z0-9])" + re.escape(old.encode()) + rb"(?![0-9])", re.IGNORECASE)

    def repl(m):
        s = m.group(0)
        return new.upper().encode() if s.isupper() else new.lower().encode() if s.islower() else new.encode()

    with open(path, "rb") as f:
        data = f.read()
    if not pickle_ok(path):
        raise ValueError("not a readable pickle; left unchanged")
    new_data, n = pat.subn(repl, data)
    if apply and n:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".idfix.tmp")
        with os.fdopen(fd, "wb") as f:
            f.write(new_data)
        if not pickle_ok(tmp):
            os.remove(tmp)
            raise ValueError("edited copy failed the pickle check; original left unchanged")
        os.replace(tmp, path)
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old", required=True, help="wrong ID, e.g. S9689")
    ap.add_argument("--new", required=True, help="correct ID from Qualtrics, e.g. S9686")
    ap.add_argument("--apply", action="store_true", help="make the changes (default: preview only)")
    ap.add_argument("--roots", nargs="+", help="folders to search instead of the config.py defaults")
    ap.add_argument("--scan-contents", action="store_true",
                    help="also fix the ID inside text files whose name does not contain it")
    args = ap.parse_args()

    old, new = args.old.strip(), args.new.strip()
    if not re.fullmatch(r"[A-Za-z0-9]+", old) or not re.fullmatch(r"[A-Za-z0-9]+", new):
        sys.exit("IDs must be letters and digits only.")
    if old.lower() == new.lower():
        sys.exit("Old and new ID are the same.")

    roots, server_root = default_roots()
    if args.roots:
        roots = args.roots
    pat_old, pat_new = id_pattern(old), id_pattern(new)
    repl = make_replacer(new)
    mode = "APPLYING" if args.apply else "DRY RUN (nothing will change; add --apply)"
    print(f"{mode}: {old} -> {new}\nSearching:\n  " + "\n  ".join(roots))

    # ── Safety: stop if the new ID already has files ──
    clashes = []
    for dirpath, dirnames, filenames in walk(roots):
        clashes += [os.path.join(dirpath, n) for n in filenames + dirnames if pat_new.search(n)]
    if clashes:
        print(f"\nSTOPPED: files for {new} already exist, so renaming could mix two people's data:")
        for c in clashes:
            print("  " + c)
        sys.exit(1)

    changes = []      # (action, old_path, new_path, detail)
    binary_renamed = []

    for dirpath, dirnames, filenames in walk(roots):
        for name in filenames:
            path = os.path.join(dirpath, name)
            if name.endswith(".idfix.tmp"):
                continue
            ext = os.path.splitext(name)[1].lower()
            name_hit = bool(pat_old.search(name))
            is_text = ext in TEXT_EXT

            if is_text and (name_hit or (args.scan_contents and os.path.getsize(path) <= SCAN_MAX_BYTES)):
                try:
                    n = fix_contents(path, pat_old, repl, args.apply)
                except OSError as e:
                    print(f"  ! could not read {path}: {e}")
                    n = 0
                if n:
                    changes.append(("edit contents", path, path, f"{n} replacement(s)"))
                    print(f"  edit  {path}  ({n} replacement(s))")

            is_pickle = ext in PICKLE_EXT
            if is_pickle and name_hit:
                try:
                    n = fix_pickle(path, old, new, args.apply)
                    if n:
                        changes.append(("edit contents", path, path, f"{n} replacement(s) (pickle)"))
                        print(f"  edit  {path}  ({n} replacement(s), pickle checked)")
                except (OSError, ValueError) as e:
                    print(f"  ! {path}: {e}")
                    is_pickle = False   # list it under "renamed only"

            if name_hit:
                new_path = os.path.join(dirpath, pat_old.sub(repl, name))
                if os.path.exists(new_path):
                    sys.exit(f"STOPPED: target already exists: {new_path}")
                print(f"  rename {path}\n      -> {os.path.basename(new_path)}")
                if args.apply:
                    os.rename(path, new_path)
                changes.append(("rename file", path, new_path, ""))
                if not is_text and not is_pickle:
                    binary_renamed.append(new_path)

        for name in dirnames:
            if pat_old.search(name):
                path = os.path.join(dirpath, name)
                new_path = os.path.join(dirpath, pat_old.sub(repl, name))
                if os.path.exists(new_path):
                    sys.exit(f"STOPPED: target already exists: {new_path}")
                print(f"  rename folder {path}\n      -> {os.path.basename(new_path)}")
                if args.apply:
                    os.rename(path, new_path)
                changes.append(("rename folder", path, new_path, ""))

    print(f"\n{len(changes)} change(s) {'made' if args.apply else 'would be made'}.")
    if binary_renamed:
        print("\nRenamed only - their contents may still mention the old ID:")
        for p in binary_renamed:
            print("  " + p)
    print("\nNext: re-knit 01_data_cleaning.Rmd and 04_questionnaire_analysis.Rmd, then re-run "
          "generate_qc_report.R. Also rename the files on the lab PC / anywhere not searched here.")

    if args.apply and changes:
        # SERVER_ROOT if it exists, else the first searched folder that exists, else here
        log_dir = next((d for d in [server_root] + list(roots) if os.path.isdir(d)), os.getcwd())
        log_path = os.path.join(log_dir, "id_changes_log.csv")
        new_log = not os.path.exists(log_path)
        with open(log_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_log:
                w.writerow(["timestamp", "old_id", "new_id", "action", "old_path", "new_path", "detail"])
            now = dt.datetime.now().isoformat(timespec="seconds")
            for a, op, np_, d in changes:
                w.writerow([now, old, new, a, op, np_, d])
        print(f"Logged to {log_path}")


if __name__ == "__main__":
    main()
