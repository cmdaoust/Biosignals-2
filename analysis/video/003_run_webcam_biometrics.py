r"""
003_run_webcam_biometrics.py
============================
One script to get WebcamBiometrics heart rate (rPPG) for each participant, as CSVs you can load in R.
No ECG or FaceReader comparison here - that is the separate eval (eval/run_sussex_all.py).

For each participant it runs, skipping any step whose output already exists:
  1. VIDEO    PNG frames -> VIDEO_EXTERNAL_DIR (D:\Biosignals2_video)\<id>_1to1_ffv1.avi (+ <id>_frame_timestamps.csv)
              via 000_convert_png_to_avi.py --method 1to1 (every PNG once, lossless). This is the
              same file FaceReader analyses. An older <id>_1to1.mkv is still used if there is no .avi
              (identical pixels); turn it into the .avi with 004_convert_mkv_to_avi.py --delete-mkv.
              Older sessions without PNGs use VIDEO_BOX_DIR (3_Data\video)\<id>_recording.avi.
  2. EXTRACT  video -> skin-colour (RGB) series, WITH the real frame timestamps
              (WebcamBiometrics eval/ts/extract/extractRGB.ts - slow, runs MediaPipe in Chromium;
              needs ~5 GB free temp space for a 19-min session, deleted afterwards)
  3. ANALYSE  RGB series -> heart rate per frame (eval/ts/replay/analyseSeries.ts - fast)
  4. EXPORT   -> 3_Data\webcam_biometrics\<id>_webcam_hr_frames_<variant>.csv   (one row per frame)
               -> 3_Data\webcam_biometrics\<id>_webcam_hr_events_<variant>.csv  (one row per event)
               -> 3_Data\webcam_biometrics\<id>_webcam_beats_<variant>.csv      (one row per detected beat)

<id>_webcam_beats_<variant>.csv  - beat-by-beat, laid out like Kubios' <id>_kubios_rr.csv (block, time_s, rr_s)
  block           Baseline / <Valence> Induction / <Valence> Recovery the beat falls in (blank =
                  between blocks; Kubios has no beats there). Needs <id>_video_events.csv.
  time_s          beat time on the ECG / Kubios clock (trimmed .acq) = time_video_s + offset. The
                  offset is read from 3_Data\ecg_video_offsets.csv, or - if the participant isn't in
                  it yet - estimated here automatically (WebcamBiometrics eval/py/estimate_offsets.py:
                  needs <id>_video_events.csv from 001 and <id>_events_biopac.csv from 002) and saved
                  there. Blank if it can't be estimated or the events disagree (the reason is printed).
  rr_s            interval since the previous detected beat (s) - compare with Kubios rr_s. Blank for
                  the first beat after a face-loss gap (> 0.5 s without a face): never measured
                  across a gap.
  segment         continuous stretch the beat belongs to (a new one starts after each such gap)
  s_to_gap        seconds from this beat to the start of the next face-loss gap (blank if none follows)
  s_since_gap     seconds since the end of the previous face-loss gap (blank if none before)
  near_gap        1 if the beat is within NEAR_GAP_BEFORE_S (1 s) before or NEAR_GAP_AFTER_S (3 s)
                  after a face-loss gap, else 0. A FLAG ONLY - nothing is removed. Around face loss the
                  skin signal is disturbed (head turning, hand to face), so these beats are less
                  trustworthy; decide in your analysis whether to drop them (e.g. filter near_gap == 0).
                  On r2433 (checked against ECG) beats 0-5 s after a gap matched an R-peak 70% of the
                  time vs 89% elsewhere; the few beats just before a gap were fine (n=8) - see
                  WebcamBiometrics docs/face-loss-gaps.md. Use s_to_gap / s_since_gap for other margins.
  time_video_s    beat time on the webcam clock (seconds since recording start)
  bpm             60 / rr_s
  These are the RAW detected beats: no artefact correction. A missed beat gives one ~2x interval,
  an extra beat two short ones (on the pilot ~30% of intervals were wrong), and every beat sits
  ~150-250 ms AFTER its R-peak (pulse transit time) and is frame-quantised (~33 ms). So compare
  intervals / matched beats, not raw times one-to-one, and clean IBIs before any HRV.

CODE VERSIONS (--variant) - every output file is labelled with the code that made it
  baseline   Max Lovell's ORIGINAL WebcamBiometrics rPPG code (upstream main 1efc19b, a frozen copy in
             WebcamBiometrics eval/baseline_src/; eval/ts/replay/analyseSeries_baseline.ts)
  faceloss   original + the face-loss gap fix (reset at gaps > 0.5 s, 1 s warm-up; WebcamBiometrics
             src/rppg on branch optimize/beat-detection; eval/ts/replay/analyseSeries.ts)
  optimized  face-loss fix + linear-phase FIR filter + heart-rate-guided beat picking
             (WebcamBiometrics *_optimize files; eval/ts/replay/analyseSeries_optimize.ts;
             docs/beat-optimization-log.md)
  Default: all three. Each gets its own files - <id>_webcam_beats_<variant>.csv,
  <id>_webcam_hr_frames_<variant>.csv, <id>_webcam_hr_events_<variant>.csv - and its own cached
  predictions (eval/cache/<id>/full.predictions_<variant>.json), so nothing overwrites another
  version. Re-running a variant overwrites only that variant's files (same code -> same result).
  Files from earlier runs without a variant label (<id>_webcam_beats.csv, *_optimize.csv) are left
  untouched; they are not read by 005 any more (their code version is not recorded reliably).
  All three are exported the same way (e.g. no interval is ever measured across a face-loss gap),
  so differences between them come from the WebcamBiometrics code only.
  The beats CSV has a 'variant' column too.

  optimized only: the FIR filter + beat confirmation add ~1.6 s live delay (--live-delay-ms changes
  the filter part, default 1000; a non-default value gets its own label, optimized_d733 etc.). Saved
  beat times are TRUE times (delay removed), so beats, intervals and HRV are not shifted; only the
  frames CSV 'pulse' column (the filtered waveform) runs behind its time_s.

Step 4 is always redone (cheap). --reanalyse redoes step 3 only (seconds per participant), which is
all a change to the heart-rate code in WebcamBiometrics/src needs. --redo redoes steps 2-3; step 2
re-reads every frame with MediaPipe (slow) and is only needed if extractRGB.ts or the video changed.

OUTPUT COLUMNS
--------------
<id>_webcam_hr_frames_<variant>.csv
  time_s          seconds since webcam recording start = the clock of PsychoPy's
                  stim_onset_since_rec_start and of onset_s in <id>_video_events.csv
  hr_fft_bpm      heart rate from the dominant pulse frequency over a sliding window (smooth;
                  use this for block averages). Blank while the window is filling.
  hr_beats_bpm    heart rate from the interval between detected beats (noisier)
  pulse           band-pass filtered pulse waveform (arbitrary units)
  beat            1 if a beat was detected on this frame
  segment         continuous stretch (0, 1, 2 ...); a new segment starts after > 0.5 s without a face
  warming_up      1 = just after a gap, while the heart-rate code restarts (no beats reported);
                  blank for results made before WebcamBiometrics' face-loss-gap fix
  Frames where no face was found are absent (see coverage below).

<id>_webcam_hr_events_<variant>.csv  (needs <id>_video_events.csv from 001_generate_event_onsets.py)
  event, onset_s, offset_s, duration_s
  hr_fft_median, hr_fft_mean, hr_beats_median   over frames inside the event
  n_beats, beats_per_min      detected beats in the event and their rate (a cross-check)
  coverage        share of captured frames in the event that have a heart-rate value
                  (low = face lost, or the start of the recording while the window fills)

Usage (from anywhere; paths come from config.py at the repo root)
-----
  python 003_run_webcam_biometrics.py i4155                 # one participant
  python 003_run_webcam_biometrics.py i4155 r4755           # several
  python 003_run_webcam_biometrics.py --all                 # every main-study participant with a video
  python 003_run_webcam_biometrics.py --all --pilots        # ... plus pilots (participant_status.csv)
  python 003_run_webcam_biometrics.py i4155 --test          # first 30 s only: quick check, frames CSV only
  python 003_run_webcam_biometrics.py i4155 --redo          # re-run extract + analyse (slow)
  python 003_run_webcam_biometrics.py --all --reanalyse     # re-run analyse only (fast), e.g. after a src/ change
  python 003_run_webcam_biometrics.py --all --variant optimized          # one code version only
  python 003_run_webcam_biometrics.py r2433 --variant optimized --live-delay-ms 733   # shorter live delay

config.py variables used: SERVER_ROOT, WEBCAM_PNG_EXTERNAL_DIR, VIDEO_EXTERNAL_DIR, VIDEO_BOX_DIR, FACEREADER_ONSETS_DIR, and optionally
WEBCAM_BIOMETRICS_REPO (default C:\Users\carme\OneDrive\Documents\GitHub\WebcamBiometrics)
and WEBCAM_HR_DIR (default SERVER_ROOT\webcam_biometrics).

Needs: ffmpeg/ffprobe on PATH, Node.js (npx), and in the WebcamBiometrics repo once:
  npm install ; npx playwright install chromium
"""

import argparse
import bisect
import csv
import glob
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from statistics import mean, median

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPO = r"C:\Users\carme\OneDrive\Documents\GitHub\WebcamBiometrics"
TEST_SECONDS = 30


# ── setup ─────────────────────────────────────────────────────────────────────

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_config():
    folder = HERE
    while not os.path.isfile(os.path.join(folder, "config.py")):
        parent = os.path.dirname(folder)
        if parent == folder:
            raise SystemExit(f"No config.py found in {HERE} or above")
        folder = parent
    cfg = load_module("webcam_hr_config", os.path.join(folder, "config.py"))
    root = str(cfg.SERVER_ROOT)
    paths = {
        "repo": str(getattr(cfg, "WEBCAM_BIOMETRICS_REPO", DEFAULT_REPO)),
        "webcam_png_external_dir": str(cfg.WEBCAM_PNG_EXTERNAL_DIR),
        "video_external_dir": str(getattr(cfg, "VIDEO_EXTERNAL_DIR", r"D:\Biosignals2_video")),
        "video_box_dir": str(getattr(cfg, "VIDEO_BOX_DIR", os.path.join(root, "video"))),
        "events_dir": str(getattr(cfg, "FACEREADER_ONSETS_DIR",
                                  os.path.join(root, "event_onsets", "facereader_video"))),
        "out_dir": str(getattr(cfg, "WEBCAM_HR_DIR", os.path.join(root, "webcam_biometrics"))),
        "offsets": os.path.join(root, "ecg_video_offsets.csv"),
        "dataset": root,
    }
    return paths


def check_tools(repo, variants=()):
    missing = [t for t in ("ffmpeg", "ffprobe", "npx") if shutil.which(t) is None]
    if missing:
        raise SystemExit(f"Not found on PATH: {missing}. Install ffmpeg (winget install ffmpeg) and Node.js.")
    for p in ("eval/ts/extract/extractRGB.ts", "eval/ts/replay/analyseSeries.ts", "node_modules"):
        if not os.path.exists(os.path.join(repo, p)):
            raise SystemExit(f"{os.path.join(repo, p)} not found. Is WEBCAM_BIOMETRICS_REPO right, and have "
                             f"you run 'npm install' and 'npx playwright install chromium' there?")
    for v in variants:
        if not os.path.exists(os.path.join(repo, VARIANT_SCRIPTS[v])):
            raise SystemExit(f"{os.path.join(repo, VARIANT_SCRIPTS[v])} not found: --variant {v} needs the "
                             f"WebcamBiometrics branch optimize/beat-detection (in {repo}: git switch optimize/beat-detection).")


# Which WebcamBiometrics replay script makes each labelled code version (see CODE VERSIONS above).
VARIANT_SCRIPTS = {
    "baseline": "eval/ts/replay/analyseSeries_baseline.ts",
    "faceloss": "eval/ts/replay/analyseSeries.ts",
    "optimized": "eval/ts/replay/analyseSeries_optimize.ts",
}
# Source files each version depends on: if any is newer than its cached predictions, they are rebuilt.
VARIANT_SOURCES = {
    "baseline": ["eval/baseline_src", "eval/ts/replay/analyseSeries_baseline.ts"],
    "faceloss": ["src/rppg", "eval/ts/replay/analyseSeries.ts"],
    "optimized": ["src/rppg", "eval/ts/replay/analyseSeries_optimize.ts"],
}
DEFAULT_LIVE_DELAY_MS = 1000   # = WebcamBiometrics LiveRoute_optimize default (liveFilterDelayMs)


def variant_label(variant, live_delay_ms=None):
    """'baseline' | 'faceloss' | 'optimized' | 'optimized_d733' (non-default live delay)."""
    if variant == "optimized" and live_delay_ms not in (None, DEFAULT_LIVE_DELAY_MS):
        return f"optimized_d{int(live_delay_ms)}"
    return variant


def newest_mtime(repo, paths):
    newest = 0.0
    for p in paths:
        full = os.path.join(repo, p)
        if os.path.isfile(full):
            newest = max(newest, os.path.getmtime(full))
        for root, _, files in os.walk(full):
            for f in files:
                if f.endswith(".ts"):
                    newest = max(newest, os.path.getmtime(os.path.join(root, f)))
    return newest


def run(cmd, cwd):
    print("  $ " + " ".join(f'"{c}"' if " " in c else c for c in cmd), flush=True)
    t0 = time.time()
    rc = subprocess.run(cmd, cwd=cwd).returncode
    print(f"  ({(time.time() - t0) / 60:.1f} min)")
    if rc != 0:
        raise RuntimeError(f"{os.path.basename(cmd[2]) if len(cmd) > 2 else cmd[0]} failed (exit code {rc})")


# ── steps ─────────────────────────────────────────────────────────────────────

def find_ci(folder, name):
    """Case-insensitive file lookup in folder -> path or None."""
    if not os.path.isdir(folder):
        return None
    for entry in os.listdir(folder):
        if entry.lower() == name.lower():
            return os.path.join(folder, entry)
    return None


def find_all_participants(P, converter, include_pilots=False):
    """--all: every participant with a video anywhere 003 can read one, filtered by
    analysis/participant_status.csv (test sessions and excluded participants left out; pilots only
    with --pilots). Prints who was found where and who was left out, so nothing is dropped silently.

    NOTE (GitHub / other datasets): this discovery is specific to the Biosignals2 storage layout - PNG
    folders named <id>_..._frames, <id>_1to1_ffv1.avi / <id>_1to1.mkv in VIDEO_EXTERNAL_DIR,
    <id>_recording.avi in VIDEO_BOX_DIR, IDs = text before the first "_". To be replaced by a participant
    manifest before sharing - see WebcamBiometrics docs/before-sharing.md."""
    found = {}

    def add(pid, where):
        found.setdefault(pid.lower(), []).append(where)

    if os.path.isdir(P["webcam_png_external_dir"]):
        sessions, problems = converter.find_sessions(P["webcam_png_external_dir"])
        for pid in sessions:
            add(pid, "PNG frames")
        for p in problems:
            print(f"[PNG folder problem] {p}")
    for folder, suffixes, where in ((P["video_external_dir"], ("_1to1_ffv1.avi", "_1to1.mkv"), "1:1 video"),
                                    (P["video_box_dir"], ("_recording.avi",), "older recording")):
        if not os.path.isdir(folder):
            print(f"[--all] {where} folder not found: {folder}")
            continue
        for name in os.listdir(folder):
            low = name.lower()
            for suf in suffixes:
                if low.endswith(suf) and "_" in name:
                    add(name.split("_", 1)[0], where)
    try:
        sys.path.insert(0, os.path.dirname(HERE))          # analysis/participant_status.py
        import participant_status as ps
        status_of = ps.status_of
    except Exception as e:                                  # missing/broken file: keep everyone, say so
        print(f"[--all] WARNING: participant_status.csv not used ({e}) - every participant found is run")
        status_of = lambda pid: "main"
    keep, left_out = [], []
    for pid in sorted(found):
        st = status_of(pid)
        if st == "main" or (st == "pilot" and include_pilots):
            keep.append(pid)
        else:
            left_out.append(f"{pid} ({st})")
    print(f"--all: {len(keep)} participant(s){' incl. pilots' if include_pilots else ' (main study; --pilots adds pilots)'}:")
    for pid in keep:
        print(f"    {pid:8s} {status_of(pid):6s} video: {', '.join(dict.fromkeys(found[pid]))}")
    if left_out:
        print(f"  left out (participant_status.csv): {', '.join(left_out)}")
    return keep


def step_video(pid, P, converter):
    """-> (video_path, timestamps_path), making the 1:1 video if needed."""
    ts = find_ci(P["video_external_dir"], f"{pid}_frame_timestamps.csv")
    for name in (f"{pid}_1to1_ffv1.avi", f"{pid}_1to1.mkv"):     # .avi = shared with FaceReader; .mkv = older
        video = find_ci(P["video_external_dir"], name)
        if video and ts:
            print(f"  video: {video} (exists)")
            if video.lower().endswith(".mkv"):
                print("         (older .mkv - same pixels as the .avi; for FaceReader run 004_convert_mkv_to_avi.py "
                      f"{pid} --delete-mkv to replace it with {pid}_1to1_ffv1.avi)")
            return video, ts
    sessions, _ = converter.find_sessions(P["webcam_png_external_dir"]) if os.path.isdir(P["webcam_png_external_dir"]) else ({}, [])
    match = {k.lower(): v for k, v in sessions.items()}.get(pid)
    if match:
        frames_dir, csv_path = match
        print(f"  video: converting {frames_dir} -> 1:1 FFV1 .avi")
        out = converter.convert(frames_dir, csv_path, P["video_external_dir"], "1to1")
        return out, find_ci(P["video_external_dir"], f"{pid}_frame_timestamps.csv")
    legacy = find_ci(P["video_box_dir"], f"{pid}_recording.avi")
    ts = find_ci(P["video_box_dir"], f"{pid}_frame_timestamps.csv")
    if legacy and ts:
        print(f"  video: {legacy} (older session, already 1:1)")
        return legacy, ts
    raise RuntimeError(f"no {pid}_1to1_ffv1.avi / {pid}_1to1.mkv (+ timestamps) in {P['video_external_dir']}, no {pid}_recording.avi "
                       f"(+ timestamps) in {P['video_box_dir']}, "
                       f"and no {pid}_frames folder + timestamps CSV in {P['webcam_png_external_dir']}")


def step_extract(pid, video, ts, P, test, redo):
    """-> the cached RGB series (eval/cache/<id>/<full|test30>.json), extracting it if needed (slow)."""
    cache = os.path.join(P["repo"], "eval", "cache", pid)
    os.makedirs(cache, exist_ok=True)
    stem = "test30" if test else "full"
    series = os.path.join(cache, f"{stem}.json")
    npx = shutil.which("npx")
    if redo or not os.path.exists(series):
        cmd = [npx, "tsx", "eval/ts/extract/extractRGB.ts", video, series, "--timestamps", ts]
        if test:
            cmd += ["--max", str(TEST_SECONDS)]
        print(f"  extract: {'first %d s' % TEST_SECONDS if test else 'whole video (slow)'}")
        run(cmd, P["repo"])
    else:
        print(f"  extract: {series} (exists; --redo to re-run)")
    return series


def step_analyse(pid, series, P, variant, label, redo, reanalyse, live_delay_ms=None):
    """Run one labelled code version on the cached series -> its own predictions file."""
    preds = series[:-len(".json")] + f".predictions_{label}.json"
    stale = (not os.path.exists(preds) or os.path.getmtime(preds) < os.path.getmtime(series)
             or os.path.getmtime(preds) < newest_mtime(P["repo"], VARIANT_SOURCES[variant]))
    if redo or reanalyse or stale:
        print(f"  analyse [{label}]:")
        cmd = [shutil.which("npx"), "tsx", VARIANT_SCRIPTS[variant], series, preds, "--label", f"{pid} {label}"]
        if variant == "optimized":
            live = {"quiet": True}
            if live_delay_ms is not None:
                live["liveFilterDelayMs"] = live_delay_ms
            cmd += ["--config", json.dumps({"live": live})]
        run(cmd, P["repo"])
    else:
        print(f"  analyse [{label}]: {preds} (up to date)")
    return preds


# ── export ────────────────────────────────────────────────────────────────────

def load_predictions(path):
    """-> (rows: one per frame, beats: [(true beat time s, segment)], meta).
    Optimised predictions carry each beat's TRUE time (beat_times_ms; the FIR filter's delay removed):
    those are the beat times, and the frames' 'beat' flag is moved to the frame at that time. Older
    predictions only flag the frame a beat was detected on: that frame time is the beat time."""
    with open(path) as f:
        d = json.load(f)
    frames = d["frames"]
    rows = [{"time_s": fr["t_ms"] / 1000.0, "hr_fft_bpm": fr.get("heart_rate_bpm"),
             "hr_beats_bpm": fr.get("live_bpm"), "pulse": fr.get("filtered"),
             "beat": 1 if fr.get("peak_detected") else 0,
             "segment": fr.get("segment"), "warming_up": fr.get("warming_up")} for fr in frames]
    # Older predictions (before the face-loss-gap fix in WebcamBiometrics) carry no segment: infer it
    # from the frame times, so an interval is never measured across a stretch without a face.
    if rows and rows[0]["segment"] is None:
        seg, prev = 0, None
        for r in rows:
            if prev is not None and r["time_s"] - prev > MAX_GAP_S:
                seg += 1
            r["segment"], prev = seg, r["time_s"]
    if any("beat_times_ms" in fr for fr in frames):
        times = [r["time_s"] for r in rows]
        for r in rows:
            r["beat"] = 0
        beats = []
        for t in sorted(t / 1000.0 for fr in frames for t in fr.get("beat_times_ms") or []):
            # The frame at the beat's TRUE time gives its segment and gets the 'beat' flag. (A beat is
            # reported later than it happened - e.g. one held when the face is lost comes with the first
            # frame after the gap - so the frame that reported it can be in the next segment.)
            i = bisect.bisect_left(times, t)
            i = min((j for j in (i - 1, i) if 0 <= j < len(rows)), key=lambda j: abs(times[j] - t))
            rows[i]["beat"] = 1
            beats.append((t, rows[i]["segment"]))
    else:
        beats = [(r["time_s"], r["segment"]) for r in rows if r["beat"]]
    return rows, beats, d.get("meta", {})


MAX_GAP_S = 0.5   # = WebcamBiometrics pulse.maxGapMs: a longer gap between frames (face lost) starts a new segment


def load_frame_times(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [float(r["time_since_recording_start"]) for r in csv.DictReader(f)]


def _fmt(x, nd=3):
    return "" if x is None else f"{x:.{nd}f}"


def write_frames(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_s", "hr_fft_bpm", "hr_beats_bpm", "pulse", "beat", "segment", "warming_up"])
        for r in rows:
            wu = "" if r["warming_up"] is None else int(bool(r["warming_up"]))
            w.writerow([f"{r['time_s']:.6f}", _fmt(r["hr_fft_bpm"], 2), _fmt(r["hr_beats_bpm"], 2),
                        _fmt(r["pulse"], 6), r["beat"], r["segment"], wu])


def summarise_events(rows, beats, frame_times, events_path, out_path):
    with open(events_path, newline="", encoding="utf-8-sig") as f:
        events = [(r["event"], float(r["onset_s"]), float(r["offset_s"])) for r in csv.DictReader(f)]
    out = []
    for name, on, off in events:
        inside = [r for r in rows if on <= r["time_s"] <= off]
        fft = [r["hr_fft_bpm"] for r in inside if r["hr_fft_bpm"] is not None]
        beats_hr = [r["hr_beats_bpm"] for r in inside if r["hr_beats_bpm"] is not None]
        n_beats = sum(1 for t, _ in beats if on <= t <= off)
        captured = sum(1 for t in frame_times if on <= t <= off)
        dur = off - on
        out.append([name, f"{on:.3f}", f"{off:.3f}", f"{dur:.3f}",
                    _fmt(median(fft) if fft else None, 2), _fmt(mean(fft) if fft else None, 2),
                    _fmt(median(beats_hr) if beats_hr else None, 2),
                    n_beats, _fmt(n_beats / dur * 60 if dur > 0 else None, 2),
                    _fmt(len(fft) / captured if captured else None, 3)])
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event", "onset_s", "offset_s", "duration_s", "hr_fft_median", "hr_fft_mean",
                    "hr_beats_median", "n_beats", "beats_per_min", "coverage"])
        w.writerows(out)
    return out


def ensure_offset(pid, P):
    """The participant's ECG->video offset: from ecg_video_offsets.csv if already there, otherwise
    estimated now with WebcamBiometrics' eval/py/estimate_offsets.py (same checks: events matched by
    name, refused if they disagree by > 50 ms or drift) and saved to that file. None if it can't be."""
    offset = load_offset(P["offsets"], pid)
    if offset is not None:
        return offset
    py_dir = os.path.join(P["repo"], "eval", "py")
    if py_dir not in sys.path:
        sys.path.insert(0, py_dir)
    try:
        eo = load_module("estimate_offsets", os.path.join(py_dir, "estimate_offsets.py"))
        off, lines = eo.estimate(P["dataset"], pid, 0.050)
    except Exception as e:  # unreadable events files etc. - report, don't stop the export
        print(f"  offset : could not estimate ({e})")
        return None
    print("  offset : estimating ECG->video offset")
    print("\n".join("  " + l for l in lines))
    if off is None:
        print("  offset : NOT saved (see above) - beats keep video-clock times only")
        return None
    eo.write_offsets(P["dataset"], {pid: off})
    print(f"  offset : {off:.3f} s saved to {P['offsets']}")
    return off


def load_offset(path, pid):
    """ECG->video offset (s) for pid from ecg_video_offsets.csv, or None."""
    if not os.path.exists(path):
        return None
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if (r.get("pid") or "").strip().lower() == pid:
                try:
                    return float(r["offset_s"])
                except (TypeError, ValueError):
                    return None
    return None


BLOCKS = ("Baseline", "Negative Induction", "Negative Recovery", "Positive Induction", "Positive Recovery")


NEAR_GAP_BEFORE_S = 1.0   # near_gap flag: beats this close before a face-loss gap ...
NEAR_GAP_AFTER_S = 3.0    # ... or this soon after it (see the docstring)


def face_loss_gaps(rows):
    """[(start_s, end_s)] of stretches with no frames longer than MAX_GAP_S (face not detected)."""
    t = [r["time_s"] for r in rows]
    return [(a, b) for a, b in zip(t, t[1:]) if b - a > MAX_GAP_S]


def write_beats(rows, beats, pid, events_path, offset, out_path, label=""):
    blocks = []
    if events_path:
        with open(events_path, newline="", encoding="utf-8-sig") as f:
            blocks = [(r["event"], float(r["onset_s"]), float(r["offset_s"]))
                      for r in csv.DictReader(f) if r["event"] in BLOCKS]
    gaps = face_loss_gaps(rows)
    n_near = 0
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block", "time_s", "rr_s", "time_video_s", "bpm", "segment",
                    "s_to_gap", "s_since_gap", "near_gap", "variant"])
        prev = None
        for t, seg in beats:
            block = next((n for n, on, off in blocks if on <= t <= off), "")
            # No interval across a face-loss gap: the first beat of each segment has no rr_s.
            rr = t - prev[0] if prev is not None and prev[1] == seg else None
            to_gap = min((a - t for a, _ in gaps if a >= t), default=None)
            since_gap = min((t - b for _, b in gaps if b <= t), default=None)
            near = int((to_gap is not None and to_gap <= NEAR_GAP_BEFORE_S)
                       or (since_gap is not None and since_gap <= NEAR_GAP_AFTER_S))
            n_near += near
            w.writerow([block, _fmt(t + offset if offset is not None else None, 4), _fmt(rr, 4),
                        f"{t:.4f}", _fmt(60 / rr if rr else None, 2), seg,
                        _fmt(to_gap, 3), _fmt(since_gap, 3), near, label])
            prev = (t, seg)
    return len(beats), len(gaps), n_near


def step_export(pid, preds, ts, P, test, label):
    os.makedirs(P["out_dir"], exist_ok=True)
    rows, beats, meta = load_predictions(preds)
    if meta.get("live_delay_message"):
        print("  NOTE   : " + meta["live_delay_message"].replace("[rPPG live route] ", ""))
    tag = f"_{label}"
    suffix = ("_test30" if test else "") + tag
    frames_csv = os.path.join(P["out_dir"], f"{pid}_webcam_hr_frames{suffix}.csv")
    write_frames(rows, frames_csv)
    fft = [r["hr_fft_bpm"] for r in rows if r["hr_fft_bpm"] is not None]
    print(f"  frames : {frames_csv}  ({len(rows)} frames, median HR "
          f"{median(fft):.1f} BPM)" if fft else f"  frames : {frames_csv}  (NO heart-rate values!)")
    if test:
        return
    events = find_ci(P["events_dir"], f"{pid}_video_events.csv")
    offset = ensure_offset(pid, P)
    beats_csv = os.path.join(P["out_dir"], f"{pid}_webcam_beats{tag}.csv")
    n, n_gaps, n_near = write_beats(rows, beats, pid, events, offset, beats_csv, label)
    print(f"  beats  : {beats_csv}  ({n} beats; {n_gaps} face-loss gap(s) > {MAX_GAP_S} s, "
          f"{n_near} beats flagged near_gap; "
          + (f"ECG clock via offset {offset:.3f} s)" if offset is not None else
             f"no ECG-clock times: needs {pid}_video_events.csv (001) and {pid}_events_biopac.csv (002) - "
             f"run those, then this script again)"))
    if not events:
        print(f"  events : skipped - no {pid}_video_events.csv in {P['events_dir']} "
              f"(run 001_generate_event_onsets.py, then this script again)")
        return
    events_csv = os.path.join(P["out_dir"], f"{pid}_webcam_hr_events{tag}.csv")
    summary = summarise_events(rows, beats, load_frame_times(ts), events, events_csv)
    print(f"  events : {events_csv}")
    for name, on, off, dur, fmed, _, bmed, nb, bpm, cov in summary:
        flag = "   <- low coverage" if cov and float(cov) < 0.8 else ""
        print(f"    {name:20s} HR {fmed or '-':>6}  beats/min {bpm or '-':>6}  coverage {cov or '-'}{flag}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="WebcamBiometrics heart rate per participant -> CSV.")
    ap.add_argument("pids", nargs="*", help="participant IDs (e.g. i4155)")
    ap.add_argument("--all", action="store_true",
                    help="every participant with a video (PNG frames, 1:1 video or older recording), minus test "
                         "sessions and excluded participants in analysis/participant_status.csv")
    ap.add_argument("--pilots", action="store_true", help="with --all: include pilot participants too")
    ap.add_argument("--test", action="store_true", help=f"first {TEST_SECONDS} s only (quick check)")
    ap.add_argument("--redo", action="store_true", help="re-run extract + analyse even if cached (slow: re-reads every frame)")
    ap.add_argument("--reanalyse", action="store_true",
                    help="re-run only the analyse step on the cached RGB series (fast) - use after a change to the "
                         "heart-rate code in WebcamBiometrics/src, e.g. the face-loss gap fix")
    ap.add_argument("--variant", nargs="+", choices=list(VARIANT_SCRIPTS) + ["all"], default=["all"],
                    help="which WebcamBiometrics code version(s) to run: baseline (original), faceloss (original + "
                         "face-loss gap fix), optimized (gap fix + FIR + heart-rate-guided beats), or all (default). "
                         "Each writes its own *_<variant>.csv files.")
    ap.add_argument("--optimize", action="store_true", help="old name for --variant optimized")
    ap.add_argument("--live-delay-ms", type=float, default=None,
                    help=f"optimized only: the FIR filter's live delay (default {DEFAULT_LIVE_DELAY_MS}). Shorter = "
                         "beats shown sooner live, somewhat less accurate. Saved beat times are true times either way. "
                         "A non-default value gets its own files (*_optimized_d<ms>.csv).")
    a = ap.parse_args()
    variants = ["optimized"] if a.optimize else (list(VARIANT_SCRIPTS) if "all" in a.variant else list(dict.fromkeys(a.variant)))
    if a.live_delay_ms is not None and "optimized" not in variants:
        raise SystemExit("--live-delay-ms only applies to --variant optimized.")

    P = load_config()
    converter = load_module("convert_png", os.path.join(HERE, "000_convert_png_to_avi.py"))
    if a.all:
        pids = find_all_participants(P, converter, a.pilots)
    else:
        pids = [p.lower() for p in a.pids]
        try:                                                # named IDs always run; just say if they're flagged
            sys.path.insert(0, os.path.dirname(HERE))
            import participant_status as ps
            for pid in pids:
                if ps.status_of(pid) != "main":
                    print(f"[note] {pid} is '{ps.status_of(pid)}' in participant_status.csv - running it because you named it")
        except Exception:
            pass
    if not pids:
        raise SystemExit("Give participant IDs, or --all.")
    check_tools(P["repo"], variants)
    print(f"code versions: {', '.join(variant_label(v, a.live_delay_ms) for v in variants)}")
    for k, v in P.items():
        print(f"{k:11s}: {v}")

    status = {}
    for pid in pids:
        print(f"\n{'=' * 70}\n{pid}{' (TEST: first %d s)' % TEST_SECONDS if a.test else ''}\n{'=' * 70}")
        try:
            video, ts = step_video(pid, P, converter)
            series = step_extract(pid, video, ts, P, a.test, a.redo)
            for v in variants:
                label = variant_label(v, a.live_delay_ms)
                preds = step_analyse(pid, series, P, v, label, a.redo, a.reanalyse, a.live_delay_ms)
                step_export(pid, preds, ts, P, a.test, label)
            status[pid] = "OK"
        except Exception as e:
            print(f"  [ERROR] {e}")
            status[pid] = f"FAILED: {e}"

    print(f"\n{'=' * 70}\nSummary")
    for pid, s in status.items():
        print(f"  {pid:>10} : {s}")
    sys.exit(0 if all(s == "OK" for s in status.values()) else 1)


if __name__ == "__main__":
    main()
