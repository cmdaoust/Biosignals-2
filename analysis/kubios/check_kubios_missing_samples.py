"""
check_kubios_missing_samples.py - flag participants with missing Kubios samples (blocks) in a
Kubios batch export (KubiosHRVresults.csv).

Default input: FACEREADER_RESULTS_DIR/KubiosHRVresults.csv (Box 3_Data/facereader).
The file is read the same way as 08_combine_timeseries.R (read_kubios_batch_blocks): header = the
line starting with FileName, lines split on commas by hand (Kubios doesn't quote; rows end in a
varying number of empty fields), participant = FileName basename up to the first _ or .,
S1..S5 = BLOCK_ORDER, last row wins for duplicates.

A participant is flagged when:
  NOT IN FILE  - in the reference file (ECG batch export, 3_Data/kubios/KubiosHRVresults.csv)
                 but has no row in this file
  MISSING      - a block (S1..S5) has no values at all (every measure empty / NaN)
  PARTIAL      - a block has some measures empty that are filled for other participants
                 (columns empty for EVERYONE, e.g. ECG morphology in the FaceReader file, are ignored)
  NO COLUMNS   - the file has no S<i>_ columns for a block (affects everyone)
Duplicate rows for a participant are reported as a note (the last row is the one checked, as in 08).

BEAT COVERAGE (when the input's folder has a Kubios_Samples.csv, i.e. the FaceReader/webcam folder):
for each participant, <pid>_facereader_beats_kubios.txt (written by 002_create_kubios_samples_video.py)
is compared with that file's row in Kubios_Samples.csv: first beat, last beat, and where each sample
ends. A sample that ends after the last beat is flagged "ENDS AFTER LAST BEAT" - Kubios returns an empty
sample when its window runs past the data. Also printed: the first beat time, because if Kubios starts
its time axis at the first beat (see the !! note in 002), every window is shifted later by that amount.
Written to <input name>_beat_coverage.csv. Turn off with --no-beats.

Usage (from the repo):
  python analysis/kubios/check_kubios_missing_samples.py                  # FaceReader file
  python analysis/kubios/check_kubios_missing_samples.py path/to/KubiosHRVresults.csv
  options: --reference FILE    compare against another batch file for "NOT IN FILE"
           --no-reference      skip the "NOT IN FILE" check
           --pilots            also check pilots (test/excluded sessions are always left out)

Output: console summary + <input name>_missing_samples.csv next to the input (all flags and notes;
real IDs, so it stays on Box with the input). Writes nothing else. Standard library only.
"""
import argparse
import csv
import os
import re
import sys

BLOCK_ORDER = ["baseline", "negative_induction", "negative_recovery", "positive_induction", "positive_recovery"]
EMPTY_VALUES = {"", "na", "nan", "n/a", "-", "inf", "-inf"}
# Measures Kubios often leaves empty for a 3-min sample even when the data are fine (multiscale
# entropy at coarse scales, HRV triangular index). Not used for PARTIAL unless --all-measures.
NOISY_MEASURES = re.compile(r"^(MSE_\d+|HRV triangular index)$", re.I)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)
import config as C  # noqa: E402

FACEREADER_RESULTS_DIR = getattr(C, "FACEREADER_RESULTS_DIR", os.path.join(C.SERVER_ROOT, "facereader"))
KUBIOS_RESULTS_DIR = getattr(C, "KUBIOS_RESULTS_DIR", os.path.join(C.SERVER_ROOT, "kubios"))
ECG_FILE = os.path.join(KUBIOS_RESULTS_DIR, "KubiosHRVresults.csv")


def same_file(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def other_stream_rx(path):
    # rows from the other stream are left out, as in 08
    return r"facereader|heart beat log|webcam" if same_file(path, ECG_FILE) else r"physiology|webcam"


def is_empty(v):
    return v.strip().lower() in EMPTY_VALUES


def split_line(line):
    return [re.sub(r'^"|"$', "", x.strip()).strip() for x in line.rstrip("\r\n").split(",")]


def read_batch(path):
    """Returns (header, rows, filenames, pids) with other-stream rows left out."""
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        lines = f.readlines()
    h = next((i for i, l in enumerate(lines) if l.lstrip('"').startswith("FileName")), None)
    if h is None:
        sys.exit(f"{path}: no header line starting with FileName")
    hdr = split_line(lines[h])
    while hdr and not hdr[-1]:
        hdr.pop()
    rows = []
    for l in lines[h + 1:]:
        x = split_line(l)
        if len(x) > len(hdr) and any(x[len(hdr):]):
            print(f"  WARNING: row '{x[0]}' has values beyond the last header column - check for a column shift")
        x = (x + [""] * len(hdr))[:len(hdr)]
        if x[0]:
            rows.append(x)
    fnames = [os.path.basename(r[0].replace("\\", "/")) for r in rows]
    rx = re.compile(other_stream_rx(path), re.I)
    other = [f for f in fnames if rx.search(f)]
    if other:
        print(f"  {len(other)} row(s) from the other stream left out: {', '.join(other)}")
    keep = [i for i, f in enumerate(fnames) if not rx.search(f)]
    rows = [rows[i] for i in keep]
    fnames = [fnames[i] for i in keep]
    pids = [re.sub(r"[_.].*$", "", f).lower() for f in fnames]
    return hdr, rows, fnames, pids


def find_ci(folder, name):
    """File called `name` (any case) in folder, or None."""
    try:
        for f in os.listdir(folder):
            if f.lower() == name.lower():
                return os.path.join(folder, f)
    except OSError:
        pass
    return None


def read_samples_csv(path):
    """{file name lower: [(start, end) or None] * n_samples} from a Kubios_Samples.csv."""
    out = {}
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        lines = [l.rstrip("\r\n") for l in f if l.strip()]
    for l in lines[1:]:
        x = [v.strip() for v in l.split(",")]
        wins = []
        for i in range(len(BLOCK_ORDER)):
            try:
                a, b = float(x[3 + 3 * i]), float(x[4 + 3 * i])
                wins.append(None if a != a or b != b else (a, b))
            except (IndexError, ValueError):
                wins.append(None)
        out[x[0].lower()] = wins
    return out


def read_beats(path):
    t = []
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for l in f:
            try:
                t.append(float(l.split()[0].replace(",", ".")))
            except (IndexError, ValueError):
                pass
    return t


def beat_coverage(folder, pids, suffix):
    """Rows comparing each participant's beat file with its Kubios_Samples.csv row."""
    samples_path = find_ci(folder, "Kubios_Samples.csv")
    if not samples_path:
        print(f"\nBeat coverage: no Kubios_Samples.csv in {folder} - skipped")
        return []
    samples = read_samples_csv(samples_path)
    rows = []
    for p in pids:
        name = f"{p}{suffix}"
        r = dict(participant_id=p, beat_file=name, n_beats="", first_beat_s="", last_beat_s="", status="", detail="")
        for i in range(1, len(BLOCK_ORDER) + 1):
            r[f"S{i}_end_s"] = ""
            r[f"S{i}_end_minus_last_beat_s"] = ""
        path = find_ci(folder, name)
        wins = samples.get(name.lower())
        if not path:
            r["status"] = "NO BEAT FILE"
        elif wins is None:
            r["status"] = "NO SAMPLES ROW"
            r["detail"] = f"{name} not in {os.path.basename(samples_path)} (rerun 002)"
        if path:
            t = read_beats(path)
            r["n_beats"] = len(t)
            if t:
                r["first_beat_s"], r["last_beat_s"] = round(t[0], 3), round(t[-1], 3)
            elif not r["status"]:
                r["status"] = "EMPTY BEAT FILE"
        if wins is not None and r["last_beat_s"] != "":
            late = []
            for i, w in enumerate(wins, 1):
                if w is None:
                    continue
                gap = round(w[1] - r["last_beat_s"], 3)
                r[f"S{i}_end_s"] = round(w[1], 3)
                r[f"S{i}_end_minus_last_beat_s"] = gap
                if gap > 0:
                    late.append(f"S{i} by {gap:.1f} s")
            if late:
                r["status"] = "ENDS AFTER LAST BEAT"
                r["detail"] = "; ".join(late)
            elif not r["status"]:
                r["status"] = "ok"
        rows.append(r)
    return rows


def load_status():
    """Returns (keep(pid, include_pilots), status_of) from participant_status.csv.
    Stops if the file can't be read: no silent "keep everyone" fallback (pilots must stay out)."""
    try:
        sys.path.insert(0, os.path.join(REPO_ROOT, "analysis"))
        import participant_status as ps
    except Exception as e:  # noqa: BLE001
        sys.exit(f"participant_status.csv could not be read ({e}). It is needed to leave out pilots, "
                 f"test sessions and excluded participants - fix it (PARTICIPANT_STATUS_PATH in config.py) and rerun.")
    keep = lambda pid, pilots: ps.status_of(pid) == "main" or (pilots and ps.status_of(pid) == "pilot")
    return keep, ps.status_of


def main():
    ap = argparse.ArgumentParser(description="Flag participants with missing Kubios samples.")
    ap.add_argument("input", nargs="?", default=os.path.join(FACEREADER_RESULTS_DIR, "KubiosHRVresults.csv"))
    ap.add_argument("--reference", help="batch file used for the NOT IN FILE check (default: ECG batch export)")
    ap.add_argument("--no-reference", action="store_true", help="skip the NOT IN FILE check")
    ap.add_argument("--pilots", action="store_true", help="also check pilot participants")
    ap.add_argument("--no-beats", action="store_true", help="skip the beat-coverage check")
    ap.add_argument("--beats-suffix", default="_facereader_beats_kubios.txt",
                    help="beat file name after the participant ID (default: _facereader_beats_kubios.txt)")
    ap.add_argument("--all-measures", action="store_true",
                    help="also count MSE_* and HRV triangular index for PARTIAL (noisy for 3-min samples)")
    a = ap.parse_args()

    if not os.path.isfile(a.input):
        sys.exit(f"Input not found: {a.input}")
    if a.no_reference:
        ref_file = None
    elif a.reference:
        ref_file = a.reference
    else:
        ref_file = None if same_file(a.input, ECG_FILE) else ECG_FILE
    keep, status_of = load_status()

    print(f"Checking {a.input}")
    hdr, rows, fnames, pids = read_batch(a.input)
    left = sorted({p for p in pids if not keep(p, a.pilots)})
    if left:
        print(f"  left out (participant_status.csv{'' if a.pilots else '; --pilots to include pilots'}): "
              + ", ".join(f"{p} ({status_of(p)})" for p in left))
    else:
        print("  participant_status.csv: nobody in this file is a pilot, test or excluded session")
    checked = list(dict.fromkeys(p for p in pids if keep(p, a.pilots)))
    last_row = {p: rows[max(i for i, q in enumerate(pids) if q == p)] for p in checked}

    # columns per block; measures empty for everyone are ignored for PARTIAL
    cols = [[j for j, h in enumerate(hdr) if h.startswith(f"S{i}_")] for i in range(1, len(BLOCK_ORDER) + 1)]
    used = [[j for j in k if any(not is_empty(x[j]) for x in last_row.values())
             and (a.all_measures or not NOISY_MEASURES.match(re.sub(r"^S\d+_", "", hdr[j])))] for k in cols]

    flags = []

    def add(pid, block="", sample="", status="", n_empty="", n_measures="", detail=""):
        flags.append(dict(participant_id=pid, block=block, sample=sample, status=status,
                          n_empty=n_empty, n_measures=n_measures, detail=detail))

    for i, k in enumerate(cols, 1):
        if not k:
            add("(all)", BLOCK_ORDER[i - 1], f"S{i}", "NO COLUMNS", detail=f"no S{i}_ columns in the header")

    for p in checked:
        r = [i for i, q in enumerate(pids) if q == p]
        if len(r) > 1:
            differ = len({fnames[i] for i in r}) > 1
            add(p, status="DUPLICATE (different files)" if differ else "note: duplicate rows",
                detail=f"{len(r)} rows ({'; '.join(fnames[i] for i in r)}); the last one was checked")
        x = last_row[p]
        for i, k in enumerate(used, 1):
            if not k:
                continue
            empty = [j for j in k if is_empty(x[j])]
            if len(empty) == len(k):
                add(p, BLOCK_ORDER[i - 1], f"S{i}", "MISSING", len(empty), len(k))
            elif empty:
                add(p, BLOCK_ORDER[i - 1], f"S{i}", "PARTIAL", len(empty), len(k),
                    "; ".join(re.sub(r"^S\d+_", "", hdr[j]) for j in empty))

    if ref_file:
        if not os.path.isfile(ref_file):
            print(f"  reference {ref_file} not found - NOT IN FILE check skipped")
        else:
            _, _, _, ref_pids = read_batch(ref_file)
            for p in sorted({q for q in ref_pids if keep(q, a.pilots)} - set(checked)):
                add(p, status="NOT IN FILE",
                    detail=f"in {os.path.basename(os.path.dirname(os.path.abspath(ref_file)))} but no row here")

    # ── Report ──
    flagged = {f["participant_id"] for f in flags
               if not f["status"].startswith("note") and f["participant_id"] != "(all)"}
    not_in = {f["participant_id"] for f in flags if f["status"] == "NOT IN FILE"}
    print(f"\n{len(checked)} participant(s) in the file, {len(flagged - not_in)} of them flagged; "
          f"{len(not_in)} more in the reference but not in the file")
    for i, b in enumerate(BLOCK_ORDER, 1):
        n = sum(f["status"] == "MISSING" and f["sample"] == f"S{i}" for f in flags)
        if n:
            print(f"  S{i} ({b}) missing for {n}/{len(checked)}")
    odd = sorted(p for p in checked if not re.fullmatch(r"[a-z]\d{4}", p))
    if odd:
        print(f"  IDs not in the usual letter+4-digit form (file naming?): {', '.join(odd)}")
    order = (["(all)"] if any(f["participant_id"] == "(all)" for f in flags) else []) + \
        sorted({f["participant_id"] for f in flags} - {"(all)"})
    for p in order:
        print(f"  {p}")
        for f in (f for f in flags if f["participant_id"] == p):
            where = f"{f['sample']} ({f['block']})" if f["block"] else ""
            if f["status"] in ("MISSING", "PARTIAL"):
                info = f"{f['n_empty']}/{f['n_measures']} empty" + (f": {f['detail']}" if f["detail"] else "")
            else:
                info = f["detail"]
            print(f"    {f['status']:<21}{where:<26}{info}")
    if not flags:
        print("  nothing missing")

    stem = os.path.join(os.path.dirname(os.path.abspath(a.input)),
                        re.sub(r"\.csv$", "", os.path.basename(a.input), flags=re.I))
    out = stem + "_missing_samples.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["participant_id", "block", "sample", "status", "n_empty", "n_measures", "detail"])
        w.writeheader()
        w.writerows(flags)
    print(f"\nWritten: {out}")

    if a.no_beats:
        return
    folder = os.path.dirname(os.path.abspath(a.input))
    pids_all = sorted(set(checked) | not_in)
    cov = beat_coverage(folder, pids_all, a.beats_suffix)
    if not cov:
        return
    missing = {(f["participant_id"], f["sample"]) for f in flags if f["status"] == "MISSING"}
    n = len(BLOCK_ORDER)
    print(f"\nBeat coverage ({a.beats_suffix} vs Kubios_Samples.csv; seconds; "
          f"+ = sample ends after the last beat; * = sample empty in Kubios)")
    print(f"  {'participant':<12}{'beats':>7}{'first':>9}{'last':>9}" +
          "".join(f"{'S' + str(i) + ' end-last':>14}" for i in range(1, n + 1)) + "  status")
    for r in cov:
        cells = []
        for i in range(1, n + 1):
            g = r[f"S{i}_end_minus_last_beat_s"]
            star = "*" if (r["participant_id"], f"S{i}") in missing else " "
            cells.append(f"{(f'{g:+.1f}' if g != '' else '-') + star:>14}")
        print(f"  {r['participant_id']:<12}{str(r['n_beats']):>7}{str(r['first_beat_s']):>9}{str(r['last_beat_s']):>9}"
              + "".join(cells) + f"  {r['status']}{(': ' + r['detail']) if r['detail'] and r['status'] != 'ENDS AFTER LAST BEAT' else ''}")

    # does "ends after the last beat" explain the empty samples?
    explained = unexplained = 0
    other = []
    for (p, smp) in sorted(missing):
        r = next((c for c in cov if c["participant_id"] == p), None)
        g = r[f"{smp}_end_minus_last_beat_s"] if r else ""
        if g != "" and g > 0:
            explained += 1
        else:
            unexplained += 1
            other.append(f"{p} {smp}")
    late_ok = [f"{c['participant_id']} S{i}" for c in cov for i in range(1, n + 1)
               if c[f"S{i}_end_minus_last_beat_s"] != "" and c[f"S{i}_end_minus_last_beat_s"] > 0
               and (c["participant_id"], f"S{i}") not in missing]
    print(f"\n  Empty samples that end after the last beat: {explained} of {explained + unexplained}")
    if other:
        print(f"  Empty although the beats cover the window: {', '.join(other)}")
    if late_ok:
        print(f"  End after the last beat but NOT empty in Kubios: {', '.join(late_ok)}")
    # second explanation: Kubios starts its axis at the first beat -> window end + first beat > last beat
    shifted = []
    for (p, smp) in sorted(missing):
        r = next((c for c in cov if c["participant_id"] == p), None)
        g = r[f"{smp}_end_minus_last_beat_s"] if r else ""
        if g != "" and r["first_beat_s"] != "" and g <= 0 < g + r["first_beat_s"]:
            shifted.append(f"{p} {smp}")
    if missing:
        print(f"  ...of the rest, would end after the last beat if Kubios starts at the first beat: "
              f"{len(shifted)}{(' (' + ', '.join(shifted) + ')') if shifted else ''}")
    firsts = [c["first_beat_s"] for c in cov if c["first_beat_s"] != ""]
    if firsts:
        print(f"  First beat: median {sorted(firsts)[len(firsts) // 2]:.1f} s (range {min(firsts):.1f}-{max(firsts):.1f}). "
              "If Kubios starts its time axis at the first beat, windows shift later by this much (see 002's !! note).")

    cov_out = stem + "_beat_coverage.csv"
    with open(cov_out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cov[0].keys()))
        w.writeheader()
        w.writerows(cov)
    print(f"\nWritten: {cov_out}")


if __name__ == "__main__":
    main()
