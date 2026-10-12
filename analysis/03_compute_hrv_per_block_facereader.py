"""
03_compute_hrv_per_block_facereader.py
=======================================
Computes per-block HRV (RMSSD, SDNN) from FaceReader heart beat log files,
using PsychoPy block timings to define epochs.

Clock alignment
---------------
Two clocks need aligning:

  PsychoPy clock  : t=0 at experiment launch
  FaceReader clock: t=0 at first video frame (video-relative timestamps)

The PsychoPy CSV contains both clocks at one shared moment:
  - trigger_setup.started       : when the webcam trigger fired (PsychoPy time)
  - time_since_recording_start  : how long the video had been running at that moment

  offset_pp_to_fr = time_since_recording_start − trigger_setup.started
  fr_time(event)  = psychopy_time(event) + offset_pp_to_fr

No BIOPAC file is required for this script.

Input
-----
  {PSYCHOPY_DATA_DIR}/*.csv              (PsychoPy trial files)
  {FACEREADER_DIR}/*_heart beat log.txt  (FaceReader IBI exports)

Output
------
  {HRV_OUTPUT_DIR}/{pid}_hrv_per_block.csv
      Columns: pid, block, onset_fr_s, offset_fr_s, n_ibis,
               rmssd_ms, sdnn_ms, mean_ibi_ms, mean_hr_bpm,
               offset_pp_to_fr_s

  {HRV_OUTPUT_DIR}/all_participants_hrv_per_block.csv
      Same columns, all participants concatenated.

Usage
-----
  python 03_compute_hrv_per_block_facereader.py

  Paths are read from config.py in the same directory.
"""

import os
import sys
import glob
import numpy as np
import pandas as pd

# ── CONFIG ────────────────────────────────────────────────────────────────────
# config.py lives one directory up. This works both as a script and in a
# notebook cell (__file__ is not defined in notebooks, so we fall back to cwd).

_script_dir = os.path.dirname(__file__) if '__file__' in dir() else os.getcwd()
sys.path.insert(0, os.path.join(_script_dir, '..'))
from config import PSYCHOPY_DATA_DIR, COMBINED_DATA_DIR, SERVER_ROOT

PSYCHOPY_DATA_DIR = str(PSYCHOPY_DATA_DIR)
FACEREADER_DIR    = os.path.join(str(SERVER_ROOT), 'facereader')  # FaceReader heart beat logs
HRV_OUTPUT_DIR    = str(COMBINED_DATA_DIR)

# Block duration cap: used only for the final block, where there is no
# subsequent block onset to mark the end. Adjust to your longest block.
DEFAULT_BLOCK_DURATION_S = 180.0

# Minimum IBIs required to compute HRV for a block.
# Blocks below this threshold receive NaN metrics rather than noisy estimates.
MIN_IBIS = 10

# PsychoPy CSVs to exclude (biometrics, frame timestamps, etc.)
EXCLUDE_SUFFIXES = ('_biometrics.csv', '_frame_timestamps.csv')


# ── HELPERS ───────────────────────────────────────────────────────────────────

def extract_facereader_offset(csv_path):
    """
    Derive the PsychoPy → FaceReader video clock offset from a PsychoPy CSV.

    The webcam code component logs two values in the trigger_setup row:
      trigger_setup.started       — PsychoPy time when the trigger fired
      time_since_recording_start  — FaceReader video time at that same moment

    Returns
    -------
    offset_pp_to_fr : float
        Add this to any PsychoPy timestamp to get the equivalent FaceReader
        video-clock time.
        fr_time = psychopy_time + offset_pp_to_fr
    """
    df = pd.read_csv(csv_path, low_memory=False)

    trigger_rows = df[df['trigger_setup.started'].notna()]
    if trigger_rows.empty:
        raise ValueError(f'No trigger_setup row found in {csv_path}')

    row = trigger_rows.iloc[0]

    if 'time_since_recording_start' not in df.columns or pd.isna(row['time_since_recording_start']):
        raise ValueError(
            f'time_since_recording_start column missing or empty in {csv_path}. '
            f'This column is logged by the webcam code component — older pilot files '
            f'may not have it.'
        )

    trigger_pp  = float(row['trigger_setup.started'])
    fr_at_trigger = float(row['time_since_recording_start'])
    offset = fr_at_trigger - trigger_pp

    return offset


def extract_psychopy_blocks(csv_path):
    """
    Parse a PsychoPy CSV and return block-level onset and offset times on
    PsychoPy's clock.

    Returns list of (condition, onset_s, offset_s) tuples:
      baseline      — fixation_baseline.started / .stopped
      pos_induction — first / last video.started / .stopped for positive videos
      neg_induction — first / last video.started / .stopped for negative videos
      pos_recovery  — fixation_stim_recovery.started / .stopped for positive block
      neg_recovery  — fixation_stim_recovery.started / .stopped for negative block

    Block offsets are taken directly from PsychoPy rather than inferred from
    the next block's onset, so inter-block rating screens are excluded.
    """
    df = pd.read_csv(csv_path, low_memory=False)
    rows = []

    # Baseline
    bl = df[df['fixation_baseline.started'].notna()]
    if bl.empty:
        raise ValueError(f'No baseline fixation row in {csv_path}')
    onset  = float(bl.iloc[0]['fixation_baseline.started'])
    offset = float(bl.iloc[0]['fixation_baseline.stopped'])
    rows.append(('baseline', onset, offset))

    # Induction blocks — first onset and last offset per polarity
    vid = df[df['video.started'].notna() & df['stim_path'].notna()].copy()
    for _, row in vid.iterrows():
        vid_id = os.path.splitext(os.path.basename(str(row['stim_path'])))[0]
        cond   = 'positive' if str(vid_id).startswith('P') else 'negative'
        label  = 'pos_induction' if cond == 'positive' else 'neg_induction'
        onset  = float(row['video.started'])
        offset = float(row['video.stopped'])
        existing = [r for r in rows if r[0] == label]
        if not existing:
            rows.append((label, onset, offset))
        else:
            rows = [(n, min(on, onset), max(off, offset)) if n == label
                    else (n, on, off)
                    for n, on, off in rows]

    # Recovery periods
    rec = df[df['fixation_stim_recovery.started'].notna()].copy()
    for _, row in rec.iterrows():
        cond   = str(row['condition'])
        label  = 'pos_recovery' if cond == 'positive' else 'neg_recovery'
        onset  = float(row['fixation_stim_recovery.started'])
        offset = float(row['fixation_stim_recovery.stopped'])
        rows.append((label, onset, offset))

    return rows


def parse_heartbeat_log(log_path):
    """
    Parse a FaceReader heart beat log and return beat timestamps and IBIs.

    FaceReader format (tab-separated, after a ~10-line header):
        Time                    Interbeat Interval (s)
        00:00:05.566            1.000000000
        ...

    Returns
    -------
    beat_times_s : np.ndarray
        Timestamp of each detected beat in FaceReader video time (seconds).
    ibis_ms : np.ndarray
        IBI preceding each beat, converted to milliseconds.
        Note: quantised to ~33.33 ms increments (one video frame at 30 fps).
    """
    beat_times = []
    ibis       = []

    with open(log_path, 'r') as f:
        lines = f.readlines()

    data_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith('Time') and 'Interbeat' in line:
            data_start = i + 1
            break

    if data_start is None:
        raise ValueError(f'Could not find data header in {log_path}')

    for line in lines[data_start:]:
        parts = line.strip().split('\t')
        if len(parts) < 2:
            continue
        time_str, ibi_str = parts[0].strip(), parts[1].strip()
        try:
            h, m, s = time_str.split(':')
            t_s = int(h) * 3600 + int(m) * 60 + float(s)
            ibi = float(ibi_str) * 1000.0  # s → ms
            beat_times.append(t_s)
            ibis.append(ibi)
        except (ValueError, AttributeError):
            continue

    return np.array(beat_times), np.array(ibis)


def compute_block_hrv(beat_times_s, ibis_ms, block_onset_s, block_offset_s):
    """
    Extract beats within [block_onset_s, block_offset_s] and compute HRV.

    Parameters
    ----------
    beat_times_s   : np.ndarray — FaceReader video-clock timestamps of each beat
    ibis_ms        : np.ndarray — IBI (ms) preceding each beat
    block_onset_s  : float      — block start in FaceReader video time
    block_offset_s : float      — block end in FaceReader video time

    Returns
    -------
    dict with keys: n_ibis, rmssd_ms, sdnn_ms, mean_ibi_ms, mean_hr_bpm.
    HRV metrics are NaN if fewer than MIN_IBIS beats fall in the window.
    """
    mask       = (beat_times_s >= block_onset_s) & (beat_times_s < block_offset_s)
    block_ibis = ibis_ms[mask]
    n          = int(mask.sum())

    nan_result = dict(n_ibis=n, rmssd_ms=np.nan, sdnn_ms=np.nan,
                      mean_ibi_ms=np.nan, mean_hr_bpm=np.nan)

    if n < MIN_IBIS:
        return nan_result

    successive_diffs = np.diff(block_ibis)
    rmssd    = np.sqrt(np.mean(successive_diffs ** 2))
    sdnn     = np.std(block_ibis, ddof=1)
    mean_ibi = np.mean(block_ibis)
    mean_hr  = 60000.0 / mean_ibi  # ms IBI → bpm

    return dict(n_ibis=n,
                rmssd_ms=round(rmssd, 2),
                sdnn_ms=round(sdnn, 2),
                mean_ibi_ms=round(mean_ibi, 2),
                mean_hr_bpm=round(mean_hr, 2))


def match_by_pid(pid, file_list):
    """Return the first file in file_list whose basename starts with pid (case-insensitive), or None."""
    for f in file_list:
        if os.path.basename(f)[:len(pid)].lower() == pid.lower():
            return f
    return None


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(HRV_OUTPUT_DIR, exist_ok=True)

    csv_files = sorted(
        f for f in glob.glob(os.path.join(PSYCHOPY_DATA_DIR, '*.csv'))
        if not any(os.path.basename(f).endswith(s) for s in EXCLUDE_SUFFIXES)
    )
    log_files = sorted(glob.glob(os.path.join(FACEREADER_DIR, '*heart beat log.txt')))

    if not csv_files:
        raise FileNotFoundError(f'No PsychoPy trial CSVs in {PSYCHOPY_DATA_DIR}')
    if not log_files:
        raise FileNotFoundError(f'No FaceReader heart beat logs in {FACEREADER_DIR}')

    all_results = []

    for csv_path in csv_files:
        csv_name = os.path.basename(csv_path)
        pid      = csv_name.split('_')[0]  # e.g. '001' or 'S0943'

        print(f'\n{"─"*50}')
        print(f'CSV : {csv_name}  →  PID : {pid}')

        # ── PsychoPy → FaceReader clock offset ───────────────────────────────
        try:
            offset_pp_to_fr = extract_facereader_offset(csv_path)
        except ValueError as e:
            print(f'  ⚠  {e} — skipping')
            continue

        print(f'  PsychoPy→FaceReader offset : {offset_pp_to_fr:+.4f} s '
              f'(video started {-offset_pp_to_fr:.4f} s before PsychoPy t=0)'
              if offset_pp_to_fr < 0 else
              f'  PsychoPy→FaceReader offset : {offset_pp_to_fr:+.4f} s '
              f'(video started {offset_pp_to_fr:.4f} s after PsychoPy t=0)')

        # ── PsychoPy block onsets ─────────────────────────────────────────────
        try:
            psychopy_rows = extract_psychopy_blocks(csv_path)
        except Exception as e:
            print(f'  ERROR reading PsychoPy CSV: {e}')
            continue

        # Convert to FaceReader video clock
        fr_rows = [(name, on + offset_pp_to_fr, off + offset_pp_to_fr)
                   for name, on, off in psychopy_rows]

        print(f'  Block windows (FaceReader video clock):')
        for name, on, off in sorted(fr_rows, key=lambda x: x[1]):
            print(f'    {name:20s}  {on:.3f} – {off:.3f} s  ({off-on:.1f}s)')

        # ── FaceReader heart beat log ─────────────────────────────────────────
        log_path = match_by_pid(pid, log_files)
        if log_path is None:
            print(f'  ⚠  No heart beat log matching PID {pid} — skipping')
            continue

        try:
            beat_times, ibis_ms = parse_heartbeat_log(log_path)
        except Exception as e:
            print(f'  ERROR reading heart beat log: {e}')
            continue

        print(f'  Heart beat log : {len(beat_times)} beats, '
              f'{beat_times[0]:.1f}–{beat_times[-1]:.1f} s (video clock)')

        # Drop the first IBI: it has no valid preceding beat
        beat_times = beat_times[1:]
        ibis_ms    = ibis_ms[1:]

        # ── Compute HRV per block ─────────────────────────────────────────────
        sorted_blocks = sorted(fr_rows, key=lambda x: x[1])

        for block_name, onset_s, offset_s in sorted_blocks:
            metrics = compute_block_hrv(beat_times, ibis_ms, onset_s, offset_s)

            row = dict(pid=pid, block=block_name,
                       onset_fr_s=round(onset_s, 3),
                       offset_fr_s=round(offset_s, 3),
                       duration_s=round(offset_s - onset_s, 3),
                       offset_pp_to_fr_s=round(offset_pp_to_fr, 4),
                       **metrics)
            all_results.append(row)

            status = ('OK' if not np.isnan(metrics['rmssd_ms'])
                      else f'INSUFFICIENT IBIs (n={metrics["n_ibis"]})')
            print(f'    {block_name:20s}  [{onset_s:.1f}–{offset_s:.1f}s]  '
                  f'n={metrics["n_ibis"]:3d}  '
                  f'RMSSD={metrics["rmssd_ms"]}  SDNN={metrics["sdnn_ms"]}  '
                  f'[{status}]')

        # ── Save per-participant CSV ───────────────────────────────────────────
        pid_results = [r for r in all_results if r['pid'] == pid]
        pid_df      = pd.DataFrame(pid_results)
        pid_path    = os.path.join(FACEREADER_DIR, f'{pid}_hrv_per_block.csv')
        pid_df.to_csv(pid_path, index=False)
        print(f'  Saved → {pid_path}')

    # ── Combined output ───────────────────────────────────────────────────────
    if all_results:
        combined_df   = pd.DataFrame(all_results)
        combined_path = os.path.join(HRV_OUTPUT_DIR, 'biosignals2_facereader_hrv.csv')
        combined_df.to_csv(combined_path, index=False)
        print(f'\nCombined output → {combined_path}')
    else:
        print('\nNo results to save.')

    print('\nDone.')


main()
