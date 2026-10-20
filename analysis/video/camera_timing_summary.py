"""
camera_timing_summary.py
========================
How regular was the webcam's frame timing? One row per participant (and per Kubios block), for
the methods section and to judge how much FaceReader's own clock is off.

WHY: FaceReader assumes the frames of a video are evenly spaced (its time = frame / frame rate).
A consumer webcam is not perfectly even - it jitters, drops frames, and slows down in dim light -
so FaceReader's clock runs fast or slow in places. We evaluate FaceReader as sold, on the video as
fed in, so this is part of its measurement error; this script measures how big it was, so readers
can judge how typical our camera was. (See analysis/kubios/block_duration_check.py.)

Input   <id>_frame_timestamps.csv (columns frame_index, time_since_recording_start) - the first
        found in VIDEO_EXTERNAL_DIR, WEBCAM_PNG_EXTERNAL_DIR, VIDEO_BOX_DIR (config.py)
        <id>_video_events.csv in FACEREADER_ONSETS_DIR (optional: per-block rows, and for older
        sessions the frame rate stored in the AVI)
Output  CAMERA_TIMING_DIR (config.py, else SERVER_ROOT/camera_timing):
          camera_timing_participants.csv   one row per participant
          camera_timing_blocks.csv         one row per participant x Kubios block
        and a short summary per participant group (main / pilot) printed at the end.

Columns (intervals = time between consecutive frames)
  mean_fps                 frames / duration
  interval_median_ms, interval_p5_ms, interval_p95_ms, interval_max_ms
  jitter_ms                SD of the intervals that are NOT gaps (frame-to-frame irregularity)
  pct_within_2ms           % of intervals within 2 ms of the median. High (> ~90%) = very regular
                           capture; spread out = either real jitter or delayed logging (see below)
  n_gaps, gap_total_s, longest_gap_s   gaps = intervals > GAP_FACTOR x the median. A gap is EITHER
                           a late-logged frame OR a real drop - split into:
  n_late_frames            gaps followed by a catch-up: one or more very short intervals (< half the
                           median) that bring the timing back on schedule (long + shorts together
                           ~ the normal time for that many frames). The camera captured on time; the
                           frame was only TIME-STAMPED late (delivery/logging delay).
  late_max_delay_s         the largest such delay
  n_true_drops, frames_lost   gaps with no catch-up: frames really missing (frames_lost estimated
                           from gap length / median interval)
  n_short_intervals        intervals < half the median (should all be catch-ups after late frames)
  fps_10s_min / fps_10s_max            lowest / highest frame rate in any 10-s window
  nominal_fps              the frame rate FaceReader's clock uses: 1:1 videos = mean_fps; older
                           sessions (<id>_recording.avi) = the AVI's stored rate, from 001's events
  fr_clock_max_error_s     largest |FaceReader time - real time| anywhere in the recording
  per block: fr_clock_length_diff_s = block length in FaceReader seconds minus its real length
             (what block_duration_check.py prints as a note)
  bad_intervals            zero/negative intervals (timestamps not increasing) - should be 0
  time_column              the timestamps column used (time_since_recording_start, else the 3rd
                           column with a warning - check the file if that happens)

READING late frames vs drops: if most gaps are late frames, the timestamps are mostly DELIVERY
times with occasional delays, not capture times. Anything that uses them as the time of each frame
(WebcamBiometrics with --timestamps, the FaceReader conversion in block_duration_check.py) then
places those frames up to late_max_delay_s too late.

READING jitter: a hardware-timed capture gives intervals bunched tightly at ~33.3 ms with clean
gaps at multiples of it. Intervals spread evenly over a few ms either side usually means the
timestamp was taken when the frame ARRIVED (USB/driver delay), not when it was captured.

Usage   python camera_timing_summary.py              everyone found
        python camera_timing_summary.py r2433 s9686  these only
Test sessions (participant_status.csv) are left out of the group summary, but still get a row.
"""

import argparse
import glob
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

GAP_FACTOR = 1.5          # an interval longer than this x the median counts as a gap (dropped frame)
WINDOW_S = 10.0           # window for the local frame rate
BLOCKS = {'baseline': 'Baseline', 'neg_induction': 'Negative Induction', 'neg_recovery': 'Negative Recovery',
          'pos_induction': 'Positive Induction', 'pos_recovery': 'Positive Recovery'}
HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()


def load_config():
    folder = HERE
    while not os.path.isfile(os.path.join(folder, 'config.py')):
        parent = os.path.dirname(folder)
        if parent == folder:
            raise FileNotFoundError(f"No config.py found in {HERE} or any folder above it")
        folder = parent
    spec = importlib.util.spec_from_file_location('camera_timing_config', os.path.join(folder, 'config.py'))
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    return cfg


def status_lookup():
    """participant -> main / pilot / test / excluded (participant_status.csv); 'main' if unavailable."""
    path = os.path.join(os.path.dirname(HERE), 'participant_status.py')
    try:
        spec = importlib.util.spec_from_file_location('participant_status', path)
        ps = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ps)
        return ps.status_of
    except Exception as e:
        print(f"[WARNING] participant_status.csv not used ({e}) - everyone counted as main study")
        return lambda pid: 'main'


def find_timestamps(dirs):
    """participant -> first <id>_frame_timestamps.csv found (dirs searched in order)."""
    found = {}
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        for path in sorted(glob.glob(os.path.join(d, '*frame_timestamps.csv'))):
            pid = os.path.basename(path).split('_', 1)[0].lower()
            found.setdefault(pid, path)
    return found


def stored_fps_from_events(events):
    """Older sessions: the AVI's stored frame rate = avi frame / video time in 001's events."""
    if events is None or 'recording_format' not in events or 'onset_avi_frame' not in events:
        return None
    if not (events['recording_format'] == 'legacy_avi').any():
        return None
    e = events[(events['onset_video_time_s'] > 0) & events['onset_avi_frame'].notna()]
    return float((e['onset_avi_frame'] / e['onset_video_time_s']).median()) if len(e) else None


def classify_gaps(d, med, gaps):
    """Split gaps into late-logged frames (a catch-up of short intervals follows) and true drops."""
    short = d < 0.5 * med
    n_late = n_drop = lost = 0
    late_delays = []
    for i in np.where(gaps)[0]:
        j = i + 1
        while j < len(d) and short[j] and j - i <= 10:      # the catch-up burst
            j += 1
        m = j - i - 1                                       # number of short intervals after the gap
        span = d[i:j].sum()                                 # gap + catch-up
        if m >= 1 and abs(span - (m + 1) * med) <= 0.5 * med:
            n_late += 1
            late_delays.append(d[i] - med)
        else:
            n_drop += 1
            lost += max(int(round(span / med)) - (m + 1), 1)
    return {'n_late_frames': n_late, 'late_max_delay_s': float(max(late_delays)) if late_delays else 0.0,
            'n_true_drops': n_drop, 'frames_lost': lost, 'n_short_intervals': int(short.sum())}


def interval_stats(t):
    d = np.diff(t)
    med = float(np.median(d))
    gaps = d > GAP_FACTOR * med
    regular = d[~gaps & (d > 0)]
    return {**classify_gaps(d, med, gaps),
        'interval_median_ms': 1000 * med,
        'interval_p5_ms': 1000 * float(np.percentile(d, 5)),
        'interval_p95_ms': 1000 * float(np.percentile(d, 95)),
        'interval_max_ms': 1000 * float(d.max()),
        'jitter_ms': 1000 * float(regular.std()) if len(regular) > 1 else np.nan,
        'pct_within_2ms': 100 * float(np.mean(np.abs(d - med) <= 0.002)),
        'n_gaps': int(gaps.sum()),
        'gap_total_s': float((d[gaps] - med).sum()),
        'longest_gap_s': float(d.max()) if gaps.any() else 0.0,
        'bad_intervals': int((d <= 0).sum()),
    }


def local_fps(t):
    edges = np.arange(t[0], t[-1], WINDOW_S)
    if len(edges) < 2:
        return np.nan, np.nan
    counts = np.histogram(t, bins=np.append(edges, edges[-1] + WINDOW_S))[0][:-1]   # full windows only
    rates = counts / WINDOW_S
    return float(rates.min()), float(rates.max())


def summarise(pid, ts_path, events, status):
    ts = pd.read_csv(ts_path)
    col = 'time_since_recording_start' if 'time_since_recording_start' in ts.columns else ts.columns[2]
    if col != 'time_since_recording_start':
        print(f"[WARNING] {pid}: no time_since_recording_start column in {os.path.basename(ts_path)} - used "
              f"'{col}' (columns: {list(ts.columns)}). Check this file before trusting its row.")
    t = ts[col].to_numpy(dtype=float)
    t = t[~np.isnan(t)]
    n = len(t)
    duration = t[-1] - t[0]
    mean_fps = (n - 1) / duration
    stored = stored_fps_from_events(events)
    nominal = stored or mean_fps
    fr_time = np.arange(n) / nominal + t[0]          # FaceReader's clock for frame k (same origin)
    fps_min, fps_max = local_fps(t)
    row = {'participant': pid, 'status': status, 'timestamps_file': ts_path, 'time_column': col, 'n_frames': n,
           'duration_s': duration, 'mean_fps': mean_fps, 'nominal_fps': nominal,
           'nominal_from': 'AVI stored rate (older session)' if stored else 'mean fps (1:1 video)',
           **interval_stats(t), 'fps_10s_min': fps_min, 'fps_10s_max': fps_max,
           'fr_clock_max_error_s': float(np.max(np.abs(fr_time - t)))}
    blocks = []
    if events is not None:
        frames = np.arange(n)
        for block, event in BLOCKS.items():
            r = events[events['event'] == event]
            if len(r) != 1:
                continue
            on, off = float(r['onset_s'].iloc[0]), float(r['offset_s'].iloc[0])
            inside = t[(t >= on) & (t <= off)]
            if len(inside) < 2:
                continue
            k_on, k_off = np.interp([on, off], t, frames)     # real time -> (fractional) frame
            stats = interval_stats(inside)
            blocks.append({'participant': pid, 'status': status, 'block': block, 'real_length_s': off - on,
                           'mean_fps': (len(inside) - 1) / (inside[-1] - inside[0]),
                           'jitter_ms': stats['jitter_ms'], 'n_gaps': stats['n_gaps'],
                           'n_late_frames': stats['n_late_frames'], 'n_true_drops': stats['n_true_drops'],
                           'frames_lost': stats['frames_lost'], 'longest_gap_s': stats['longest_gap_s'],
                           'fr_clock_length_s': (k_off - k_on) / nominal,
                           'fr_clock_length_diff_s': (k_off - k_on) / nominal - (off - on)})
    return row, blocks


def group_summary(df, blocks):
    print(f"\n{'=' * 78}\nGROUP SUMMARY  median [min - max] across participants (test sessions left out)\n{'=' * 78}")
    for status, g in df[df['status'] != 'test'].groupby('status'):
        def mm(col, fmt='{:.1f}'):
            v = g[col].dropna()
            return f"{fmt.format(v.median())} [{fmt.format(v.min())} - {fmt.format(v.max())}]" if len(v) else '-'
        print(f"\n{status} (n = {len(g)})")
        print(f"  mean frame rate            {mm('mean_fps', '{:.2f}')} fps")
        print(f"  frame-to-frame jitter (SD) {mm('jitter_ms')} ms")
        print(f"  intervals within 2 ms      {mm('pct_within_2ms', '{:.0f}')} %")
        print(f"  gaps (> {GAP_FACTOR}x median)       {mm('n_gaps', '{:.0f}')} per session, longest {mm('longest_gap_s', '{:.2f}')} s")
        print(f"    of which late-logged     {mm('n_late_frames', '{:.0f}')} (largest delay {mm('late_max_delay_s', '{:.2f}')} s)")
        print(f"    of which true drops      {mm('n_true_drops', '{:.0f}')} ({mm('frames_lost', '{:.0f}')} frames lost)")
        print(f"  lowest 10-s frame rate     {mm('fps_10s_min')} fps")
        print(f"  FaceReader clock max error {mm('fr_clock_max_error_s', '{:.2f}')} s")
        b = blocks[blocks['participant'].isin(g['participant'])] if len(blocks) else blocks
        if len(b):
            v = b['fr_clock_length_diff_s'].abs()
            print(f"  FaceReader block length vs real: median |diff| {v.median():.2f} s, "
                  f"largest {v.max():.2f} s ({len(b)} blocks)")


def main(named=()):
    cfg = load_config()
    server = str(getattr(cfg, 'SERVER_ROOT', ''))
    dirs = [str(d) for d in (getattr(cfg, 'VIDEO_EXTERNAL_DIR', None), getattr(cfg, 'WEBCAM_PNG_EXTERNAL_DIR', None),
                             getattr(cfg, 'VIDEO_BOX_DIR', None)) if d]
    events_dir = str(getattr(cfg, 'FACEREADER_ONSETS_DIR', os.path.join(server, 'event_onsets', 'facereader_video')))
    out_dir = str(getattr(cfg, 'CAMERA_TIMING_DIR', None) or os.path.join(server, 'camera_timing'))
    print("Timestamps searched in: " + "; ".join(dirs))
    found = find_timestamps(dirs)
    if named:
        named = [p.lower() for p in named]
        for p in named:
            if p not in found:
                print(f"[WARNING] no {p}_frame_timestamps.csv found")
        found = {p: v for p, v in found.items() if p in named}
    if not found:
        raise SystemExit("No frame timestamps files found.")
    status_of = status_lookup()

    rows, blocks = [], []
    for pid, path in sorted(found.items()):
        ev_path = os.path.join(events_dir, f'{pid}_video_events.csv')
        events = pd.read_csv(ev_path) if os.path.isfile(ev_path) else None
        try:
            row, b = summarise(pid, path, events, status_of(pid))
        except Exception as e:
            print(f"[ERROR] {pid}: {e}")
            continue
        if events is None:
            print(f"[WARNING] {pid}: no {pid}_video_events.csv - no per-block rows "
                  f"(run 001_generate_event_onsets.py)")
        if row['bad_intervals']:
            print(f"[WARNING] {pid}: {row['bad_intervals']} frame interval(s) <= 0 - timestamps not increasing")
        rows.append(row)
        blocks += b
        print(f"  {pid:>8} {row['status']:<8} {row['mean_fps']:6.2f} fps  jitter {row['jitter_ms']:5.1f} ms  "
              f"{row['pct_within_2ms']:4.0f}% within 2 ms  {row['n_gaps']:4d} gaps = {row['n_late_frames']:4d} late "
              f"(max {row['late_max_delay_s']:.2f} s) + {row['n_true_drops']:3d} drops ({row['frames_lost']} frames)  "
              f"10-s fps {row['fps_10s_min']:.1f}-{row['fps_10s_max']:.1f}  FaceReader clock off by up to "
              f"{row['fr_clock_max_error_s']:.2f} s")

    df, bdf = pd.DataFrame(rows), pd.DataFrame(blocks)
    os.makedirs(out_dir, exist_ok=True)
    df.round(4).to_csv(os.path.join(out_dir, 'camera_timing_participants.csv'), index=False)
    bdf.round(4).to_csv(os.path.join(out_dir, 'camera_timing_blocks.csv'), index=False)
    group_summary(df, bdf)
    print(f"\nSaved camera_timing_participants.csv and camera_timing_blocks.csv to {out_dir}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description="Webcam frame-timing regularity per participant and block.")
    ap.add_argument('pids', nargs='*', help="participant IDs (default: everyone with frame timestamps)")
    args, _ = ap.parse_known_args()
    main(args.pids)
