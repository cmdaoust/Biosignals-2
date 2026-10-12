"""
create_pspm_onsets_psychopy.py
==============================
Reads BIOPAC .acq files and cleaned PsychoPy CSV files to produce
PSPM-compatible event onset .mat files.

Strategy
--------
PsychoPy records precise onset/offset times for every routine on its own
internal clock.  The BIOPAC recording has its own clock (t=0 at recording
start).  We align the two clocks using a single anchor event: the baseline
fixation cross, which is visible in both datasets.

  BIOPAC anchor  : onset of the 'baseline_trig' channel (bit 0, code '01')
                   — the one trigger channel that is correctly wired.
  PsychoPy anchor: fixation_baseline.started (seconds since experiment launch)

  offset = biopac_baseline_onset - psychopy_baseline_started
  biopac_time(event) = psychopy_time(event) + offset

All event onsets and durations then come from PsychoPy's timestamps,
converted to BIOPAC-recording time via this offset.

Two sets of files are written per participant:

  stimulus_videos/{pid}_events_stimuli_psychopy_pspm.mat
      One condition per individual video, named by video ID (e.g. P02, N007).

  blocks/{pid}_events_blocks_psychopy_pspm.mat
      One condition per experimental block:
        baseline       – fixation period before emotion induction
        pos_induction  – merged epoch spanning both positive videos
        neg_induction  – merged epoch spanning both negative videos
        pos_recovery   – recovery fixation after positive block
        neg_recovery   – recovery fixation after negative block

.mat structure (SPM / PSPM convention):
  names     – 1×N cell array of condition name strings
  onsets    – 1×N cell array; each cell is a column vector of onset
              times in seconds from the start of the physio recording
  durations – 1×N cell array; each cell is a column vector of event
              durations in seconds

Usage
-----
  python create_pspm_onsets_psychopy.py

  By default the script finds all .acq files in the configured data_dir and
  matches each one to a PsychoPy CSV by the first 3 characters of the
  filename.  Edit ACQ_TO_PID below if naming differs.

  Paths are read from config.py at the repo root.
  Copy config_template.py → config.py at the repo root and set SERVER_ROOT.
"""

import os
import glob
import numpy as np
import scipy.io as sio
import pandas as pd
import bioread
import sys as _sys, os as _os
# config.py lives at the repo root (two folders up from this script)
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..')))
from config import RAW_PHYSIOLOGY_DIR, PSYCHOPY_DATA_DIR, BLOCK_ONSETS_DIR, VIDEO_ONSETS_DIR

# ── CONFIG ────────────────────────────────────────────────────────────────────

RAW_PHYSIOLOGY_DIR = str(RAW_PHYSIOLOGY_DIR)
PSYCHOPY_DATA_DIR  = str(PSYCHOPY_DATA_DIR)
BLOCK_ONSETS_DIR         = str(BLOCK_ONSETS_DIR)
VIDEO_ONSETS_DIR         = str(VIDEO_ONSETS_DIR)

# Voltage threshold to detect a trigger HIGH on the baseline_trig channel.
# BIOPAC STP digital outputs are typically 0 V or 5 V.
THRESHOLD = 0.5   # Volts

# Minimum duration to accept as a real event (rejects noise spikes).
MIN_DUR_S = 1.0   # seconds

# Optional: override ACQ filename → participant ID mapping.
# Leave empty to use automatic first-3-character matching.
ACQ_TO_PID = {
    # 'carmen_pilot.acq': '001',
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def find_events(channel, threshold=0.5, min_dur_s=1.0):
    """
    Detect rising-edge onsets in a trigger channel.

    Returns a list of (onset_s, duration_s) tuples where onset_s is
    measured from the start of the BIOPAC recording.
    """
    data = np.asarray(channel.data, dtype=float)
    sr   = channel.samples_per_second
    high = (data > threshold).astype(int)
    diff = np.diff(np.concatenate([[0], high, [0]]))
    onsets_idx  = np.where(diff ==  1)[0]
    offsets_idx = np.where(diff == -1)[0]

    events = []
    for on, off in zip(onsets_idx, offsets_idx):
        dur = (off - on) / sr
        if dur >= min_dur_s:
            events.append((on / sr, dur))
    return events


def save_timing_mat(conditions, filepath):
    """
    Write a PSPM / SPM timing .mat file (GLM format).

    conditions : dict  { name_str : [(onset_s, duration_s), ...] }
    """
    names = sorted(conditions.keys())
    n     = len(names)

    names_arr     = np.empty((1, n), dtype=object)
    onsets_arr    = np.empty((1, n), dtype=object)
    durations_arr = np.empty((1, n), dtype=object)

    for i, name in enumerate(names):
        evs = sorted(conditions[name], key=lambda x: x[0])
        names_arr[0, i]     = name
        onsets_arr[0, i]    = np.array([e[0] for e in evs], dtype=float).reshape(-1, 1)
        durations_arr[0, i] = np.array([e[1] for e in evs], dtype=float).reshape(-1, 1)

    sio.savemat(filepath, {
        'names':     names_arr,
        'onsets':    onsets_arr,
        'durations': durations_arr,
    })
    print(f'    Saved → {filepath}')


def save_epochs_mat(conditions, filepath):
    """
    Write a PsPM SF epochs .mat file and a companion CSV with condition labels.

    conditions : dict  { name_str : [(onset_s, duration_s), ...] }

    Produces:
      {filepath}        — 'epochs' N×2 matrix [onset, offset] for pspm_sf
      {filepath}.csv    — epoch_num, condition, onset, offset for R analysis
    Rows in both files are sorted by onset time.
    """
    rows = []
    for name, evs in conditions.items():
        for onset, dur in evs:
            rows.append({'condition': name, 'onset': onset, 'offset': onset + dur})
    rows.sort(key=lambda x: x['onset'])

    epochs = np.array([[r['onset'], r['offset']] for r in rows], dtype=float)
    sio.savemat(filepath, {'epochs': epochs})
    print(f'    Saved → {filepath}')

    # Companion CSV: epoch_num, condition, onset, offset
    csv_path = os.path.splitext(filepath)[0] + '_labels.csv'
    with open(csv_path, 'w') as f:
        f.write('epoch_num,condition,onset,offset\n')
        for i, r in enumerate(rows, start=1):
            f.write(f"{i},{r['condition']},{r['onset']:.6f},{r['offset']:.6f}\n")
    print(f'    Saved → {csv_path}')


def match_csv(pid, csv_files):
    """Return the CSV whose filename starts with pid (first 3 chars), or None."""
    for f in csv_files:
        if os.path.basename(f)[:3] == pid:
            return f
    return None


def extract_psychopy_events(csv_path):
    """
    Parse a PsychoPy CSV and return a dict of event timing on PsychoPy's clock.

    Returns
    -------
    dict with keys:
      'baseline'   : dict  { onset_psychopy, duration }
      'videos'     : list of dicts { video_id, trigger_name, condition,
                                     onset_psychopy, duration }
      'recoveries' : list of dicts { condition, onset_psychopy, duration }
    """
    df = pd.read_csv(csv_path, low_memory=False)

    # ── Baseline ──────────────────────────────────────────────────────────────
    bl_rows = df[df['fixation_baseline.started'].notna()]
    if bl_rows.empty:
        raise ValueError(f'No baseline fixation row found in {csv_path}')
    bl_row = bl_rows.iloc[0]
    bl_onset = float(bl_row['fixation_baseline.started'])
    bl_stop  = float(bl_row['fixation_baseline.stopped'])
    baseline = {'onset_psychopy': bl_onset, 'duration': bl_stop - bl_onset}

    # ── Individual videos ─────────────────────────────────────────────────────
    vid_rows = df[df['video.started'].notna() & df['stim_path'].notna()].copy()
    videos = []
    for _, row in vid_rows.iterrows():
        vid_onset = float(row['video.started'])
        vid_stop  = float(row['video.stopped'])
        # Extract bare video ID from file path (e.g. 'stimuli/P02.mp4' → 'P02')
        vid_id = os.path.splitext(os.path.basename(str(row['stim_path'])))[0]
        # Infer condition from video ID prefix
        cond = 'positive' if str(vid_id).startswith('P') else 'negative'
        videos.append({
            'video_id':       vid_id,
            'trigger_name':   str(row.get('trigger_name', '')),
            'condition':      cond,
            'onset_psychopy': vid_onset,
            'duration':       vid_stop - vid_onset,
        })

    # ── Recovery periods ──────────────────────────────────────────────────────
    rec_rows = df[df['fixation_stim_recovery.started'].notna()].copy()
    recoveries = []
    for _, row in rec_rows.iterrows():
        rec_onset = float(row['fixation_stim_recovery.started'])
        rec_stop  = float(row['fixation_stim_recovery.stopped'])
        recoveries.append({
            'condition':      str(row['condition']),   # 'positive' or 'negative'
            'onset_psychopy': rec_onset,
            'duration':       rec_stop - rec_onset,
        })

    return {
        'baseline':   baseline,
        'videos':     videos,
        'recoveries': recoveries,
    }


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(VIDEO_ONSETS_DIR, exist_ok=True)
    os.makedirs(BLOCK_ONSETS_DIR, exist_ok=True)

    acq_files = sorted(glob.glob(os.path.join(RAW_PHYSIOLOGY_DIR, '*.acq')))
    EXCLUDE_SUFFIXES = ('_biometrics.csv', '_frame_timestamps.csv')
    csv_files = sorted(
        f for f in glob.glob(os.path.join(PSYCHOPY_DATA_DIR, '*.csv'))
        if not any(os.path.basename(f).endswith(s) for s in EXCLUDE_SUFFIXES)
    )

    if not acq_files:
        raise FileNotFoundError(f'No .acq files found in {RAW_PHYSIOLOGY_DIR}')

    for acq_path in acq_files:
        acq_name = os.path.basename(acq_path)
        pid      = ACQ_TO_PID.get(acq_name, acq_name[:3])
        csv_path = match_csv(pid, csv_files)

        print(f'\n{"─"*60}')
        print(f'ACQ  : {acq_name}')
        print(f'PID  : {pid}')

        if csv_path is None:
            print('  ERROR: no matching PsychoPy CSV found — skipping')
            continue
        print(f'CSV  : {os.path.basename(csv_path)}')

        # ── Read BIOPAC .acq ──────────────────────────────────────────────────
        acq        = bioread.read(acq_path)
        ch_by_name = {ch.name: ch for ch in acq.channels}
        sr         = acq.channels[0].samples_per_second
        total_s    = len(acq.channels[0].data) / sr
        print(f'Channels ({len(ch_by_name)}): {list(ch_by_name.keys())}')
        print(f'Duration : {total_s:.1f} s  ({total_s/60:.1f} min)  @ {sr:.0f} Hz')

        # ── Find BIOPAC baseline anchor ───────────────────────────────────────
        if 'baseline_trig' not in ch_by_name:
            print('  ERROR: "baseline_trig" channel not in .acq — cannot align clocks')
            continue

        bl_events = find_events(ch_by_name['baseline_trig'],
                                threshold=THRESHOLD,
                                min_dur_s=MIN_DUR_S)
        if not bl_events:
            print('  ERROR: no baseline trigger detected in BIOPAC — check threshold')
            continue
        if len(bl_events) > 1:
            print(f'  WARNING: {len(bl_events)} events on baseline_trig — using first')

        biopac_baseline_onset = bl_events[0][0]
        print(f'\nBIOPAC baseline trigger onset : {biopac_baseline_onset:.3f} s into recording')

        # ── Parse PsychoPy CSV ────────────────────────────────────────────────
        try:
            events = extract_psychopy_events(csv_path)
        except Exception as e:
            print(f'  ERROR reading PsychoPy CSV: {e}')
            continue

        psychopy_baseline_onset = events['baseline']['onset_psychopy']
        offset = biopac_baseline_onset - psychopy_baseline_onset

        print(f'PsychoPy baseline fixation    : {psychopy_baseline_onset:.3f} s (PsychoPy clock)')
        print(f'Clock offset applied          : {offset:+.3f} s')
        print(f'  (biopac_time = psychopy_time + {offset:.3f})')

        # ── Print extracted events ────────────────────────────────────────────
        print('\nEvents extracted from PsychoPy (BIOPAC-referenced times):')

        bl = events['baseline']
        biopac_bl_onset = bl['onset_psychopy'] + offset
        print(f'  baseline          onset={biopac_bl_onset:7.2f}s  dur={bl["duration"]:6.2f}s')

        for v in events['videos']:
            bo = v['onset_psychopy'] + offset
            print(f'  {v["video_id"]:12s}  onset={bo:7.2f}s  dur={v["duration"]:6.2f}s  '
                  f'({v["condition"]})')

        for r in events['recoveries']:
            bo = r['onset_psychopy'] + offset
            label = 'pos_recovery' if r['condition'] == 'positive' else 'neg_recovery'
            print(f'  {label:15s}  onset={bo:7.2f}s  dur={r["duration"]:6.2f}s')

        # ── Build individual-video timing → videos/ ───────────────────────────
        video_conditions = {}
        for v in events['videos']:
            onset_biopac = v['onset_psychopy'] + offset
            video_conditions[v['video_id']] = [(onset_biopac, v['duration'])]

        # ── Build block-level timing → blocks/ ───────────────────────────────
        cond_conditions = {}

        # Baseline
        cond_conditions['baseline'] = [(bl['onset_psychopy'] + offset, bl['duration'])]

        # Induction blocks — merge both videos into one epoch
        for polarity in ('positive', 'negative'):
            label = 'pos_induction' if polarity == 'positive' else 'neg_induction'
            block_vids = [v for v in events['videos'] if v['condition'] == polarity]
            if not block_vids:
                print(f'  WARNING: no {polarity} video rows found')
                continue
            first_onset = min(v['onset_psychopy'] for v in block_vids) + offset
            last_end    = max(v['onset_psychopy'] + v['duration'] for v in block_vids) + offset
            cond_conditions[label] = [(first_onset, last_end - first_onset)]

        # Recovery periods
        for r in events['recoveries']:
            label = 'pos_recovery' if r['condition'] == 'positive' else 'neg_recovery'
            cond_conditions[label] = [(r['onset_psychopy'] + offset, r['duration'])]

        # ── Save ──────────────────────────────────────────────────────────────
        print()
        if video_conditions:
            save_timing_mat(
                video_conditions,
                os.path.join(VIDEO_ONSETS_DIR, f'{pid}_events_stimuli_psychopy_pspm.mat')
            )
        else:
            print('  WARNING: no video events — events_stimuli_psychopy_pspm.mat not written')

        save_timing_mat(
            cond_conditions,
            os.path.join(BLOCK_ONSETS_DIR, f'{pid}_events_blocks_psychopy_pspm.mat')
        )
        save_epochs_mat(
            cond_conditions,
            os.path.join(BLOCK_ONSETS_DIR, f'{pid}_epochs_conditions_psychopy.mat')
        )

    print(f'\n{"─"*60}')
    print('Stimuli output :', VIDEO_ONSETS_DIR)
    print('Blocks output  :', BLOCK_ONSETS_DIR)
    print('Done.')


if __name__ == '__main__':
    main()
