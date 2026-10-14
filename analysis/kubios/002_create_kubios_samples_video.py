"""
002_create_kubios_samples_video.py
==================================
Kubios samples for the two VIDEO heart-beat sources, so their raw beats can be run through
Kubios with the same five blocks as the ECG (001_create_kubios_samples.py):

  3_Data\\facereader\\Kubios_Samples.csv         FaceReader heart beat logs
  3_Data\\webcam_biometrics\\Kubios_Samples.csv  WebcamBiometrics beats (every labelled variant)

Kubios matches a samples row to the file it opens by FILE NAME, so each folder gets its own CSV
with times on that file's own clock ("video time"):

  FaceReader   FaceReader's Time column = frame number / the log's "Frame rate" row.
               For the 1:1 video (<id>_1to1_ffv1.avi) and older <id>_recording.avi this is NOT real
               time (the camera's real frame times vary); it drifts from real time by up to ~1.4 s
               over a session. So block times are converted to FaceReader time through the real
               frame timestamps: real onset -> frame number -> frame / Frame rate (exactly the
               inverse of what 005_compare_hrv.R does with FaceReader's beats).
               Real-time AVIs (*_realtime*, *_facereader.avi): FaceReader time = real time.
  Webcam       time_video_s in <id>_webcam_beats_<variant>.csv = real seconds since the webcam
               recording started = onset_s / offset_s in <id>_video_events.csv (001), unchanged.

Block windows come from 001_generate_event_onsets.py (<id>_video_events.csv in
FACEREADER_ONSETS_DIR): PsychoPy's own onset/offset of each block on the webcam clock.
Samples (same labels and order as the ECG Kubios_Samples.csv):
  S1 baseline  S2 neg_induction  S3 neg_recovery  S4 pos_induction  S5 pos_recovery

KUBIOS-READY BEAT FILES (written next to the originals)
-------------------------------------------------------
Kubios can't read either original directly (FaceReader: metadata rows + hh:mm:ss times, often
.xlsx; webcam: a text 'block' column first). So for each source this script also writes a plain
one-column text file of BEAT TIMES in seconds, on the same clock as the samples:
  3_Data\\facereader\\<id>_facereader_beats_kubios.txt
  3_Data\\webcam_biometrics\\<id>_webcam_beats_<variant>_kubios.txt
Import them in Kubios as RR data, column 1 = R-wave time instants (s), no header lines. Beat
times (not RR intervals) keep face-loss gaps in place; an RR-only import would shift every block
after the first gap. Rows for the original file names are written too, with the same times.

!! CHECK ONCE IN KUBIOS (not documented for beat-time imports): does Kubios put a beat at the
time in the file (time 0 = video start), or does it start its time axis at the first beat? Open
one *_kubios.txt, read the first beat's time on Kubios' axis and compare with line 1 of the
file. If Kubios starts at the first beat, rerun with --origin first-beat (subtracts each file's
first beat time from its windows). The script prints the first beat time of every file.

Usage (paths from config.py at the repo root)
-----
  python 002_create_kubios_samples_video.py               # every main-study participant
  python 002_create_kubios_samples_video.py --pilots      # ... plus pilots
  python 002_create_kubios_samples_video.py r2433 s9686   # these only (rows for others are kept)
  python 002_create_kubios_samples_video.py --origin first-beat
  python 002_create_kubios_samples_video.py --source facereader   # or webcam (default: both)

Test sessions and excluded participants (analysis/participant_status.csv) are left out unless
named. Each existing Kubios_Samples.csv is kept as Kubios_Samples_previous.csv. Needs pandas
(+ openpyxl for .xlsx heart beat logs).

Checks (warnings, listed again at the end):
  - block missing from <id>_video_events.csv
  - FaceReader time from the timestamps differs > 1 frame from 001's frame columns
  - block starts before the first beat / ends after the last beat, or has < 30 beats
  - frame timestamps not found for a 1:1 / recording video (FaceReader rows skipped)
"""

import argparse
import csv
import glob
import os
import re
import shutil
import sys

import numpy as np
import pandas as pd


# ── CONFIG ────────────────────────────────────────────────────────────────────

def _find_repo_root():
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isfile(os.path.join(current, "config.py")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    raise FileNotFoundError("Could not find config.py above this script (copy config_template.py).")


REPO_ROOT = _find_repo_root()
sys.path.insert(0, REPO_ROOT)
import config as C  # noqa: E402

SERVER_ROOT = str(C.SERVER_ROOT)
EVENTS_DIR = str(getattr(C, "FACEREADER_ONSETS_DIR", os.path.join(SERVER_ROOT, "event_onsets", "facereader_video")))
FACEREADER_DIR = str(getattr(C, "FACEREADER_RESULTS_DIR", os.path.join(SERVER_ROOT, "facereader")))
WEBCAM_DIR = str(getattr(C, "WEBCAM_HR_DIR", os.path.join(SERVER_ROOT, "webcam_biometrics")))
TIMESTAMP_DIRS = [str(d) for d in (getattr(C, "VIDEO_EXTERNAL_DIR", None),
                                   getattr(C, "WEBCAM_PNG_EXTERNAL_DIR", None),
                                   getattr(C, "VIDEO_BOX_DIR", os.path.join(SERVER_ROOT, "video")))
                  if d]

# 001's event names -> Kubios sample labels (same labels/order as the ECG Kubios_Samples.csv)
SAMPLES = {
    "baseline": "Baseline",
    "neg_induction": "Negative Induction",
    "neg_recovery": "Negative Recovery",
    "pos_induction": "Positive Induction",
    "pos_recovery": "Positive Recovery",
}
MIN_BEATS = 30            # warn if a block has fewer beats than this
WEBCAM_VARIANT_RE = re.compile(r"^(?P<pid>[^_]+)_webcam_beats_(?P<variant>(?!optimize\b)[A-Za-z0-9_]+?)\.csv$",
                               re.IGNORECASE)


# ── HELPERS ───────────────────────────────────────────────────────────────────

def pid_of(name):
    return os.path.basename(name).split("_", 1)[0].lower()


def find_ci(folders, name):
    """First file called `name` (any case) in any of `folders`."""
    for d in folders:
        if not d or not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.lower() == name.lower():
                return os.path.join(d, f)
    return None


def load_windows(pid):
    """{sample: (onset_s, offset_s)} on the webcam clock, plus the events table (for checks)."""
    path = find_ci([EVENTS_DIR], f"{pid}_video_events.csv")
    if path is None:
        return None, None, f"no {pid}_video_events.csv in {EVENTS_DIR} (run video/001_generate_event_onsets.py)"
    ev = pd.read_csv(path)
    wins = {}
    for sample, event in SAMPLES.items():
        r = ev[ev["event"] == event]
        if len(r) == 1 and pd.notna(r["onset_s"].iloc[0]) and pd.notna(r["offset_s"].iloc[0]):
            wins[sample] = (float(r["onset_s"].iloc[0]), float(r["offset_s"].iloc[0]))
    return wins, ev, None


def read_frame_clock(pid):
    """Real time (s since recording start) of every frame of the 1:1 video, as 005 reads it."""
    path = find_ci(TIMESTAMP_DIRS, f"{pid}_frame_timestamps.csv")
    if path is None:
        return None, None
    d = pd.read_csv(path)
    col = d["time_since_recording_start"] if "time_since_recording_start" in d.columns else d.iloc[:, 2]
    return col.to_numpy(dtype=float), path


def hms_to_s(x):
    """FaceReader time: 'hh:mm:ss.fff', a number of seconds, or an Excel day fraction / datetime."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    if hasattr(x, "hour") and hasattr(x, "minute"):              # datetime.time / Timestamp from Excel
        return x.hour * 3600 + x.minute * 60 + x.second + getattr(x, "microsecond", 0) / 1e6
    s = str(x).strip().replace(",", ".")
    if ":" in s:
        parts = [float(p) for p in s.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0.0)
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    try:
        v = float(s)
    except ValueError:
        return np.nan
    return v * 86400 if v < 1 else v                            # Excel day fraction vs seconds


def read_grid(path):
    if path.lower().endswith((".xlsx", ".xls")):
        g = pd.read_excel(path, sheet_name=0, header=None, dtype=object)
    else:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            rows = [l.rstrip("\r\n").split("\t") for l in f]
        n = max(len(r) for r in rows)
        g = pd.DataFrame([r + [None] * (n - len(r)) for r in rows], dtype=object)
    return g


def read_facereader_log(path):
    """(beat times in FaceReader seconds, metadata dict) from a FaceReader heart beat log."""
    g = read_grid(path)
    first = g.iloc[:, 0].astype(str).str.strip()
    hdr = first[first == "Time"].index
    if not len(hdr):
        raise ValueError("no 'Time' header row - not a FaceReader heart beat log?")
    h = hdr[0]
    meta = {}
    for i in range(h):
        k, v = str(g.iat[i, 0]).strip().lower(), g.iat[i, 1] if g.shape[1] > 1 else None
        if re.match(r"^file ?name", k):
            meta["video"] = str(v).replace("\\", "/") if v is not None else ""
        elif k.startswith("frame rate"):
            try:
                meta["fps"] = float(str(v).replace(",", "."))
            except (TypeError, ValueError):
                pass
    t = np.array([hms_to_s(x) for x in g.iloc[h + 1:, 0]], dtype=float)
    ibi = pd.to_numeric(g.iloc[h + 1:, 1].astype(str).str.replace(",", "."), errors="coerce").to_numpy()
    ok = ~np.isnan(t) & ~np.isnan(ibi)
    return np.sort(t[ok]), meta


def facereader_mode(video):
    v = (video or "").lower()
    if "1to1" in v or "recording" in v:
        return "frames"
    if "realtime" in v or "_facereader" in v:
        return "real"
    return None


def real_to_facereader(t_real, clock, fps):
    """Real time -> FaceReader time: frame number (interpolated on the real frame clock) / fps."""
    frame = np.interp(t_real, clock, np.arange(len(clock)))
    return frame / fps


def check_beats(times, wins, label, warnings):
    if len(times) == 0:
        warnings.append(f"{label}: no beats")
        return
    for sample, (a, b) in wins.items():
        n = int(np.sum((times >= a) & (times <= b)))
        if a < times[0]:
            warnings.append(f"{label}: {sample} starts {times[0] - a:.1f} s before the first beat")
        if b > times[-1]:
            warnings.append(f"{label}: {sample} ends {b - times[-1]:.1f} s after the last beat")
        if n < MIN_BEATS:
            warnings.append(f"{label}: only {n} beats in {sample}")


def write_beats_txt(times, path):
    with open(path, "w", newline="") as f:
        f.write("\n".join(f"{t:.4f}" for t in times) + "\n")


def csv_header():
    parts = ["File name", "0=Absolute time/1=Relative to beginning of measurement"]
    for i in range(1, len(SAMPLES) + 1):
        parts += [f"Label (Sample {i})", f"START (Sample {i})", f"END (Sample {i})"]
    return ",".join(parts)


def samples_line(fname, wins, shift=0.0):
    parts = [fname, "1"]
    for sample in SAMPLES:
        if sample in wins:
            a, b = wins[sample]
            parts += [sample, f"{a - shift:.3f}", f"{b - shift:.3f}"]
        else:
            parts += [sample, "NaN", "NaN"]
    return ",".join(parts)


def write_samples(folder, new_lines, pids_done):
    """Write folder/Kubios_Samples.csv: new rows + kept rows of participants not processed now."""
    out = os.path.join(folder, "Kubios_Samples.csv")
    kept = {}
    if os.path.exists(out):
        with open(out, encoding="utf-8-sig") as f:
            lines = [l.rstrip("\r\n") for l in f if l.strip()]
        if lines and lines[0] == csv_header():
            kept = {l.split(",", 1)[0]: l for l in lines[1:] if pid_of(l.split(",", 1)[0]) not in pids_done}
        shutil.copy2(out, os.path.join(folder, "Kubios_Samples_previous.csv"))
    rows = {**kept, **new_lines}
    with open(out, "w", newline="") as f:
        f.write("\n".join([csv_header()] + [rows[k] for k in sorted(rows, key=str.lower)]) + "\n")
    return out, len(rows), len(kept)


def fmt_wins(wins):
    return "  ".join(f"{s} {a:7.2f}-{b:7.2f}" for s, (a, b) in wins.items())


# ── SOURCES ───────────────────────────────────────────────────────────────────

def do_facereader(pid, wins, ev, origin, warnings):
    """{file name: samples line} for pid's FaceReader heart beat log (+ its Kubios .txt)."""
    logs = [f for f in glob.glob(os.path.join(FACEREADER_DIR, "*heart beat log.*"))
            if pid_of(f) == pid and f.lower().endswith((".txt", ".xlsx")) and not os.path.basename(f).startswith("~$")]
    if not logs:
        return {}
    if len(logs) > 1:   # .txt and .xlsx of the same export -> prefer .txt; else must contain 1to1
        txt = [f for f in logs if f.lower().endswith(".txt")]
        one = [f for f in logs if "1to1" in os.path.basename(f).lower()]
        logs = one if len(one) == 1 else txt if len(txt) == 1 else logs
        if len(logs) > 1:
            warnings.append(f"FaceReader: several heart beat logs, can't choose: {[os.path.basename(f) for f in logs]}")
            return {}
    log = logs[0]
    try:
        beats, meta = read_facereader_log(log)
    except Exception as e:
        warnings.append(f"FaceReader: {os.path.basename(log)} unreadable ({e})")
        return {}
    mode = facereader_mode(meta.get("video"))
    if mode is None:
        warnings.append(f"FaceReader: can't tell which video it analysed ('{meta.get('video')}') - skipped")
        return {}
    if mode == "real":
        fr_wins, how = dict(wins), "real-time video: FaceReader time = real time"
    else:
        clock, ts_path = read_frame_clock(pid)
        if clock is None:
            warnings.append(f"FaceReader: no {pid}_frame_timestamps.csv in {TIMESTAMP_DIRS} - skipped")
            return {}
        fps = meta.get("fps") or (len(clock) - 1) / (clock[-1] - clock[0])
        fr_wins = {s: (real_to_facereader(a, clock, fps), real_to_facereader(b, clock, fps)) for s, (a, b) in wins.items()}
        how = f"frame / {fps:.4f} fps ({'log Frame rate row' if meta.get('fps') else 'average real fps - no Frame rate row'})"
        # cross-check against 001's own frame numbers (1:1 video: PNG frame = video frame)
        col = "onset_webcam_frame" if "1to1" in meta.get("video", "").lower() else "onset_avi_frame"
        if ev is not None and col in ev.columns:
            for s, event in SAMPLES.items():
                r = ev[ev["event"] == event]
                if s in fr_wins and len(r) == 1 and pd.notna(r[col].iloc[0]):
                    d = fr_wins[s][0] - float(r[col].iloc[0]) / fps
                    if abs(d) > 1.0 / fps + 1e-6:
                        warnings.append(f"FaceReader: {s} onset differs from 001's {col} by {d * 1000:+.0f} ms")
    shift = beats[0] if (origin == "first-beat" and len(beats)) else 0.0
    check_beats(beats, fr_wins, "FaceReader", warnings)
    txt = os.path.join(FACEREADER_DIR, f"{pid}_facereader_beats_kubios.txt")
    write_beats_txt(beats - shift, txt)
    print(f"  FaceReader  {os.path.basename(log)}  ({len(beats)} beats, first at {beats[0] if len(beats) else float('nan'):.2f} s; "
          f"video {os.path.basename(meta.get('video', ''))}; {how})")
    print(f"              {fmt_wins({s: (a - shift, b - shift) for s, (a, b) in fr_wins.items()})}")
    return {os.path.basename(txt): samples_line(os.path.basename(txt), fr_wins, shift),
            os.path.basename(log): samples_line(os.path.basename(log), fr_wins, 0.0)}


def do_webcam(pid, wins, origin, warnings):
    """{file name: samples line} for every labelled <id>_webcam_beats_<variant>.csv (+ Kubios .txt)."""
    out = {}
    for f in sorted(glob.glob(os.path.join(WEBCAM_DIR, "*_webcam_beats_*.csv"))):
        m = WEBCAM_VARIANT_RE.match(os.path.basename(f))
        if not m or m["pid"].lower() != pid or m["variant"].lower().startswith("test30"):
            continue
        variant = m["variant"]
        d = pd.read_csv(f)
        beats = np.sort(d["time_video_s"].dropna().to_numpy(dtype=float))
        shift = beats[0] if (origin == "first-beat" and len(beats)) else 0.0
        check_beats(beats, wins, f"webcam {variant}", warnings)
        txt = os.path.join(WEBCAM_DIR, f"{pid}_webcam_beats_{variant}_kubios.txt")
        write_beats_txt(beats - shift, txt)
        print(f"  webcam      {os.path.basename(f)}  ({len(beats)} beats, first at "
              f"{beats[0] if len(beats) else float('nan'):.2f} s)")
        out[os.path.basename(txt)] = samples_line(os.path.basename(txt), wins, shift)
        out[os.path.basename(f)] = samples_line(os.path.basename(f), wins, 0.0)
    return out


# ── MAIN ──────────────────────────────────────────────────────────────────────

def participants(named, include_pilots):
    if named:
        return sorted({p.lower() for p in named})
    found = {pid_of(f) for f in glob.glob(os.path.join(FACEREADER_DIR, "*heart beat log.*"))}
    found |= {pid_of(f) for f in glob.glob(os.path.join(WEBCAM_DIR, "*_webcam_beats_*.csv"))}
    try:
        sys.path.insert(0, os.path.join(REPO_ROOT, "analysis"))
        import participant_status as ps
        status_of = ps.status_of
    except Exception as e:
        print(f"WARNING: participant_status.csv not used ({e}) - everyone found is included")
        status_of = lambda pid: "main"  # noqa: E731
    keep = [p for p in sorted(found) if status_of(p) == "main" or (include_pilots and status_of(p) == "pilot")]
    left = sorted(set(found) - set(keep))
    if left:
        print(f"Left out (participant_status.csv{'' if include_pilots else '; add --pilots for pilots'}): {', '.join(left)}\n")
    return keep


def main():
    ap = argparse.ArgumentParser(description="Kubios_Samples.csv for FaceReader and webcam beats (video time).")
    ap.add_argument("pids", nargs="*", help="participant IDs (default: everyone with beats)")
    ap.add_argument("--pilots", action="store_true", help="include pilot participants")
    ap.add_argument("--source", choices=["both", "facereader", "webcam"], default="both")
    ap.add_argument("--origin", choices=["video", "first-beat"], default="video",
                    help="time 0 of the samples: video start (default) or each file's first beat (see CHECK in the docstring)")
    args = ap.parse_args()

    pids = participants(args.pids, args.pilots)
    fr_lines, wc_lines, flagged, done = {}, {}, {}, set()
    for pid in pids:
        print(pid)
        warnings = []
        wins, ev, err = load_windows(pid)
        if err:
            print(f"  SKIPPED: {err}\n")
            flagged[pid] = [err]
            continue
        missing = [s for s in SAMPLES if s not in wins]
        if missing:
            warnings.append(f"blocks missing from {pid}_video_events.csv: {', '.join(missing)}")
        print(f"  blocks (real s since recording start): {fmt_wins(wins)}")
        if args.source in ("both", "facereader"):
            fr_lines.update(do_facereader(pid, wins, ev, args.origin, warnings))
        if args.source in ("both", "webcam"):
            wc_lines.update(do_webcam(pid, wins, args.origin, warnings))
        for w in warnings:
            print(f"  WARNING: {w}")
        if warnings:
            flagged[pid] = warnings
        done.add(pid)
        print()

    for name, folder, lines in (("FaceReader", FACEREADER_DIR, fr_lines), ("webcam", WEBCAM_DIR, wc_lines)):
        if args.source not in ("both", name.lower()):
            continue
        if not lines:
            print(f"{name}: no beat files found for these participants - {folder}\\Kubios_Samples.csv not changed.")
            continue
        out, n, n_kept = write_samples(folder, lines, done)
        print(f"{name}: {out}  ({n} rows: {len(lines)} new, {n_kept} kept from before)")
    print(f"Time origin: {'video start' if args.origin == 'video' else 'first beat of each file'}")
    if flagged:
        print("\nCheck these:")
        for pid, ws in flagged.items():
            for w in ws:
                print(f"  {pid}: {w}")


if __name__ == "__main__":
    main()
