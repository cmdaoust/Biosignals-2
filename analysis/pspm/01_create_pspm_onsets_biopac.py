"""
create_pspm_onsets_biopac.py
============================
Reads BIOPAC .acq files and produces PSPM-compatible event onset .mat files
by detecting trigger channel events directly from the physio recording.

NOTE ON CHANNEL MAPPING
-----------------------
PsychoPy sends hex-encoded ASCII trigger codes via serial STP.
BIOPAC decodes each byte and routes individual bits to digital output channels
in sequential order D0–D6.  The trigger codes assign:
  low bits  (02, 04, 08) → negative condition events
  high bits (10, 20, 40) → positive condition events
But the BIOPAC channels were *named* with positive events first (lower D numbers),
so the names and the actual bit-routed content are swapped.

Actual bit → channel → content:
  bit 0 / '01' → D0 = baseline_trig   → baseline
  bit 1 / '02' → D1 = Pstim1_trig     → neg_stim1   (not pos!)
  bit 2 / '04' → D2 = Pstim2_trig     → neg_stim2
  bit 3 / '08' → D3 = Nstim1_trig     → neg_recovery
  bit 4 / '10' → D4 = Nstim2_trig     → pos_stim1   (not neg!)
  bit 5 / '20' → D5 = Precovery       → pos_stim2
  bit 6 / '40' → D6 = Nrecovery_trig  → pos_recovery

For future recordings, fix the experiment trigger codes OR re-label the BIOPAC
channels so they match.

Output files:
  stimulus_videos/{pid}_events_stimuli_biopac_pspm.mat   — individual video epochs
  blocks/{pid}_events_blocks_biopac_pspm.mat             — block-level epochs

Usage
-----
  python create_pspm_onsets_biopac.py

  Paths are read from config.py in the same directory.
  Copy config_template.R → config.R (or edit config.py directly) and set SERVER_ROOT.
"""

import os
import glob
import numpy as np
import scipy.io as sio
import pandas as pd
import bioread
from config import RAW_PHYSIOLOGY_DIR, PSYCHOPY_DATA_DIR, BLOCK_ONSETS_DIR, VIDEO_ONSETS_DIR

# ── CONFIG ────────────────────────────────────────────────────────────────────

RAW_PHYSIOLOGY_DIR = str(RAW_PHYSIOLOGY_DIR)
PSYCHOPY_DATA_DIR  = str(PSYCHOPY_DATA_DIR)
BLOCK_ONSETS_DIR         = str(BLOCK_ONSETS_DIR)
VIDEO_ONSETS_DIR         = str(VIDEO_ONSETS_DIR)

THRESHOLD = 0.5   # Volts — threshold to detect a trigger HIGH
MIN_DUR_S = 1.0   # seconds — rejects noise spikes

# .acq channel name → (video_label, block_label)
# video_label : used in the individual-videos timing file (None = skip)
# block_label : used in the conditions timing file
TRIGGER_MAP = {
    'baseline_trig':  (None,      'baseline'),
    'Pstim1_trig':    ('Nstim1',  'neg_induction'),  # bit 1 → neg_stim1
    'Pstim2_trig':    ('Nstim2',  'neg_induction'),  # bit 2 → neg_stim2
    'Nstim1_trig':    (None,      'neg_recovery'),   # bit 3 → neg_recovery
    'Nstim2_trig':    ('Pstim1',  'pos_induction'),  # bit 4 → pos_stim1
    'Precovery':      ('Pstim2',  'pos_induction'),  # bit 5 → pos_stim2
    'Nrecovery_trig': (None,      'pos_recovery'),   # bit 6 → pos_recovery
}

ACQ_TO_PID = {
    # 'carmen_pilot.acq': '001',
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def find_events(channel, threshold=0.5, min_dur_s=1.0):
    """Detect rising-edge onsets in a trigger channel."""
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
    """Write a PSPM / SPM timing .mat file (GLM format)."""
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

    Produces:
      {filepath}            — 'epochs' N×2 matrix [onset, offset] for pspm_sf
      {filepath}_labels.csv — epoch_num, condition, onset, offset for R analysis
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

    csv_path = os.path.splitext(filepath)[0] + '_labels.csv'
    with open(csv_path, 'w') as f:
        f.write('epoch_num,condition,onset,offset\n')
        for i, r in enumerate(rows, start=1):
            f.write(f"{i},{r['condition']},{r['onset']:.6f},{r['offset']:.6f}\n")
    print(f'    Saved → {csv_path}')


def match_csv(pid, csv_files):
    """Return the CSV whose filename starts with pid, or None."""
    for f in csv_files:
        if os.path.basename(f)[:3] == pid:
            return f
    return None


def video_id_from_trigger(trigger_name, csv_path):
    """Look up actual video ID from the PsychoPy CSV; falls back to trigger name."""
    if csv_path is None:
        return trigger_name
    try:
        df = pd.read_csv(csv_path, nrows=50)
        row = df[df['trigger_name'] == trigger_name]
        if not row.empty:
            return str(row.iloc[0]['video_id'])
    except Exception:
        pass
    return trigger_name


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(VIDEO_ONSETS_DIR, exist_ok=True)
    os.makedirs(BLOCK_ONSETS_DIR, exist_ok=True)

    acq_files = sorted(glob.glob(os.path.join(RAW_PHYSIOLOGY_DIR, '*.acq')))
    csv_files = sorted(glob.glob(os.path.join(PSYCHOPY_DATA_DIR,  '*.csv')))

    if not acq_files:
        raise FileNotFoundError(f'No .acq files found in {RAW_PHYSIOLOGY_DIR}')

    for acq_path in acq_files:
        acq_name = os.path.basename(acq_path)
        pid      = ACQ_TO_PID.get(acq_name, acq_name[:3])
        csv_path = match_csv(pid, csv_files)

        print(f'\n{"─"*60}')
        print(f'ACQ  : {acq_name}')
        print(f'PID  : {pid}')
        print(f'CSV  : {os.path.basename(csv_path) if csv_path else "not found"}')

        acq        = bioread.read(acq_path)
        ch_by_name = {ch.name: ch for ch in acq.channels}
        sr         = acq.channels[0].samples_per_second
        total_s    = len(acq.channels[0].data) / sr
        print(f'Channels ({len(ch_by_name)}): {list(ch_by_name.keys())}')
        print(f'Duration : {total_s:.1f} s  ({total_s/60:.1f} min)  @ {sr:.0f} Hz')

        raw_events = {}
        print('\nTrigger events found:')
        for trig_name in TRIGGER_MAP:
            if trig_name not in ch_by_name:
                print(f'  ⚠  "{trig_name}" not in .acq — skipped')
                continue
            evs = find_events(ch_by_name[trig_name],
                              threshold=THRESHOLD,
                              min_dur_s=MIN_DUR_S)
            if evs:
                raw_events[trig_name] = evs
                for onset, dur in evs:
                    print(f'  {trig_name:20s}  onset={onset:7.2f}s  dur={dur:6.2f}s')
            else:
                print(f'  ⚠  "{trig_name}" — no events above threshold')

        if not raw_events:
            print('  ERROR: no trigger events found — check THRESHOLD setting')
            continue

        # ── Individual-video timing → videos/ ────────────────────────────────
        video_conditions = {}
        for trig_name, evs in raw_events.items():
            video_label = TRIGGER_MAP[trig_name][0]
            if video_label is None:
                continue
            vid_id = video_id_from_trigger(trig_name, csv_path)
            video_conditions.setdefault(vid_id, []).extend(evs)

        # ── Block-level timing → blocks/ ─────────────────────────────────────
        block_raw = {}
        for trig_name, evs in raw_events.items():
            block_label = TRIGGER_MAP[trig_name][1]
            block_raw.setdefault(block_label, []).extend(evs)

        cond_conditions = {}
        for label, evs in block_raw.items():
            evs_sorted = sorted(evs, key=lambda x: x[0])
            if label in ('pos_induction', 'neg_induction'):
                first_onset = evs_sorted[0][0]
                last_end    = max(e[0] + e[1] for e in evs_sorted)
                cond_conditions[label] = [(first_onset, last_end - first_onset)]
            else:
                cond_conditions[label] = evs_sorted

        # ── Save ──────────────────────────────────────────────────────────────
        print()
        if video_conditions:
            save_timing_mat(
                video_conditions,
                os.path.join(VIDEO_ONSETS_DIR, f'{pid}_events_stimuli_biopac_pspm.mat')
            )
        else:
            print('  ⚠  No video-level events — events_stimuli_biopac_pspm.mat not written')

        save_timing_mat(
            cond_conditions,
            os.path.join(BLOCK_ONSETS_DIR, f'{pid}_events_blocks_biopac_pspm.mat')
        )
        save_epochs_mat(
            cond_conditions,
            os.path.join(BLOCK_ONSETS_DIR, f'{pid}_epochs_conditions_biopac.mat')
        )

    print(f'\n{"─"*60}')
    print('Stimuli output :', VIDEO_ONSETS_DIR)
    print('Blocks output  :', BLOCK_ONSETS_DIR)
    print('Done.')


if __name__ == '__main__':
    main()
