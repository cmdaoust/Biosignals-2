"""
02_create_ledalab_events_psychopy.py
=====================================
Reads PsychoPy CSV files and produces Ledalab-compatible event text files.

Clock alignment
---------------
PsychoPy records onset times on its own internal clock (t=0 at experiment
launch).  The BIOPAC recording has its own clock (t=0 at recording start).
A single anchor event aligns them:

  BIOPAC anchor  : onset of the 'baseline_trig' channel
  PsychoPy anchor: fixation_baseline.started

  offset = biopac_baseline_onset − psychopy_baseline_started
  biopac_time(event) = psychopy_time(event) + offset

MUST RUN ON TRIMMED DATA
------------------------
The anchor is measured from the start of the .acq file, so the whole output is
expressed in that file's time base. config.RAW_PHYSIOLOGY_DIR therefore points
at raw_physiology/experimental_protocol_duration/, and this script reads only
the {pid}_physiology_trimmed.acq files from it — the same recordings Ledalab is
ultimately fed.

Anchoring against an untrimmed session instead shifts every event by the trim
offset (~414 s for e5510) without failing on its own, so validate_trimmed()
rejects any participant whose baseline anchor is implausibly late.

The {pid}_eda_trimmed.acq files in the same folder hold no trigger channels, so
they carry no 'baseline_trig' and are deliberately not read here.

Input
-----
  {RAW_PHYSIOLOGY_DIR}/{pid}_physiology_trimmed.acq   (for clock alignment only)
  {PSYCHOPY_DATA_DIR}/{pid}_*.csv

Output
------
  {BLOCK_ONSETS_DIR}/{pid}_events_blocks_psychopy_ledalab.txt
      Tab-separated, two columns: time  nid
      One row per block epoch, sorted by onset time.

  {BLOCK_ONSETS_DIR}/nid_map_psychopy_ledalab.txt
      nid → condition name legend, consistent across participants.

NID mapping
-----------
  Conditions are assigned integer IDs in alphabetical order and are
  consistent across participants.

  Typical mapping:
    1  baseline
    2  neg_induction
    3  neg_recovery
    4  pos_induction
    5  pos_recovery

Usage
-----
  python 02_create_ledalab_events_psychopy.py

  Paths are read from config.py at the repo root.
  Participants with no trimmed recording are reported and skipped without
  failing the run; exits non-zero if any participant fails validation.
"""

import os
import glob
import sys
import numpy as np
import pandas as pd
import bioread
import sys as _sys, os as _os
# config.py lives at the repo root (two folders up from this script)
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..')))
from config import RAW_PHYSIOLOGY_DIR, PSYCHOPY_DATA_DIR, BLOCK_ONSETS_DIR

# ── CONFIG ────────────────────────────────────────────────────────────────────

RAW_PHYSIOLOGY_DIR = str(RAW_PHYSIOLOGY_DIR)
PSYCHOPY_DATA_DIR  = str(PSYCHOPY_DATA_DIR)
BLOCK_ONSETS_DIR   = str(BLOCK_ONSETS_DIR)

THRESHOLD = 0.5   # Volts — to detect baseline trigger HIGH in BIOPAC
MIN_DUR_S = 1.0   # seconds — rejects noise spikes

# Only the physiology recording carries the trigger channels.
ACQ_SUFFIX = '_physiology_trimmed.acq'

# A trimmed recording starts at the baseline block, so its baseline onset sits a
# second or two into the file. On an untrimmed session it is several minutes in.
MAX_BASELINE_ONSET_S = 30.0

EXPECTED_CONDITIONS = ['baseline', 'neg_induction', 'neg_recovery',
                       'pos_induction', 'pos_recovery']

# Non-trial CSVs written alongside the PsychoPy trial file.
EXCLUDE_SUFFIXES = ('_biometrics.csv', '_frame_timestamps.csv')

# Optional: override ACQ filename → participant ID mapping.
ACQ_TO_PID = {
    # 'carmen_pilot_physiology_trimmed.acq': '001',
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def pid_from_acq(acq_name):
    """Participant ID = the .acq filename with ACQ_SUFFIX stripped."""
    if acq_name in ACQ_TO_PID:
        return ACQ_TO_PID[acq_name]
    if acq_name.endswith(ACQ_SUFFIX):
        return acq_name[:-len(ACQ_SUFFIX)]
    return os.path.splitext(acq_name)[0]


def pid_from_csv(csv_name):
    """Participant ID = everything before the first underscore.

    PsychoPy writes "{pid}_Biosignals2_Psychopy_...csv" (and "001_carmen_pilot_..."
    for the pilots), so the ID is the leading field, not a fixed slice.
    """
    return csv_name.split('_')[0]


def find_baseline_onset(acq_path, threshold=0.5, min_dur_s=1.0):
    """
    Read a BIOPAC .acq file and return the onset (s) of the first event on
    the 'baseline_trig' channel.  Used as the clock alignment anchor.
    """
    acq = bioread.read(acq_path)
    ch_by_name = {ch.name: ch for ch in acq.channels}

    if 'baseline_trig' not in ch_by_name:
        raise ValueError(f'"baseline_trig" channel not found in {acq_path}')

    ch   = ch_by_name['baseline_trig']
    data = np.asarray(ch.data, dtype=float)
    sr   = ch.samples_per_second
    high = (data > threshold).astype(int)
    diff = np.diff(np.concatenate([[0], high, [0]]))
    onsets_idx  = np.where(diff ==  1)[0]
    offsets_idx = np.where(diff == -1)[0]

    for on, off in zip(onsets_idx, offsets_idx):
        dur = (off - on) / sr
        if dur >= min_dur_s:
            return on / sr   # return first valid onset

    raise ValueError(f'No baseline trigger event found in {acq_path}')


def validate_trimmed(rows):
    """Return a list of reasons these BIOPAC-referenced onsets look wrong.

    Mirrors the check in 01_create_ledalab_events_biopac.py. The baseline row
    equals the BIOPAC anchor, so a late baseline means the .acq was an untrimmed
    session and every event is shifted by the trim offset.
    """
    problems = []
    by_condition = dict(rows)

    missing = [c for c in EXPECTED_CONDITIONS if c not in by_condition]
    if missing:
        problems.append('missing condition(s): %s' % ', '.join(missing))
    if 'baseline' not in by_condition:
        return problems

    baseline = by_condition['baseline']
    if baseline > MAX_BASELINE_ONSET_S:
        problems.append(
            'baseline anchor at %.1fs (expected < %.0fs) — the .acq looks like an '
            'untrimmed recording' % (baseline, MAX_BASELINE_ONSET_S))

    early = {c: t for c, t in by_condition.items() if c != 'baseline' and t < baseline}
    if early:
        problems.append(
            'condition(s) before baseline: %s'
            % ', '.join('%s=%.4fs' % kv for kv in sorted(early.items())))

    return problems


def extract_psychopy_blocks(csv_path):
    """
    Parse a PsychoPy CSV and return block-level onset times on PsychoPy's clock.

    Returns list of (condition, onset_psychopy_s) tuples:
      baseline      — fixation_baseline.started
      pos_induction — onset of first positive video
      neg_induction — onset of first negative video
      pos_recovery  — fixation_stim_recovery.started for positive block
      neg_recovery  — fixation_stim_recovery.started for negative block
    """
    df = pd.read_csv(csv_path, low_memory=False)
    rows = []

    # ── Baseline ──────────────────────────────────────────────────────────────
    bl = df[df['fixation_baseline.started'].notna()]
    if bl.empty:
        raise ValueError(f'No baseline fixation row in {csv_path}')
    rows.append(('baseline', float(bl.iloc[0]['fixation_baseline.started'])))

    # ── Induction blocks — first video onset per polarity ────────────────────
    vid = df[df['video.started'].notna() & df['stim_path'].notna()].copy()
    for _, row in vid.iterrows():
        vid_id = os.path.splitext(os.path.basename(str(row['stim_path'])))[0]
        cond   = 'positive' if str(vid_id).startswith('P') else 'negative'
        label  = 'pos_induction' if cond == 'positive' else 'neg_induction'
        onset  = float(row['video.started'])
        # Keep only the earliest onset per induction condition
        existing = [r for r in rows if r[0] == label]
        if not existing:
            rows.append((label, onset))
        else:
            rows = [(n, t) if n != label else (n, min(t, onset)) for n, t in rows]

    # ── Recovery periods ──────────────────────────────────────────────────────
    rec = df[df['fixation_stim_recovery.started'].notna()].copy()
    for _, row in rec.iterrows():
        cond  = str(row['condition'])
        label = 'pos_recovery' if cond == 'positive' else 'neg_recovery'
        rows.append((label, float(row['fixation_stim_recovery.started'])))

    return rows


def build_nid_map(all_rows):
    """Assign stable integer IDs (alphabetical) to condition names."""
    all_names = sorted({name for rows in all_rows for name, _ in rows})
    return {name: i + 1 for i, name in enumerate(all_names)}


def save_ledalab_txt(rows, nid_map, filepath):
    """Write a Ledalab event file: tab-separated time and nid, sorted by time."""
    rows_sorted = sorted(rows, key=lambda x: x[1])
    with open(filepath, 'w') as f:
        f.write('time\tnid\n')
        for name, t in rows_sorted:
            f.write(f'{t:.4f}\t{nid_map[name]}\n')
    print(f'    Saved → {filepath}')


def save_nid_map(nid_map, filepath):
    """Save the nid → condition name legend."""
    with open(filepath, 'w') as f:
        f.write('nid\tcondition\n')
        for name, nid in sorted(nid_map.items(), key=lambda x: x[1]):
            f.write(f'{nid}\t{name}\n')
    print(f'    NID map → {filepath}')


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    csv_files = sorted(
        f for f in glob.glob(os.path.join(PSYCHOPY_DATA_DIR, '*.csv'))
        if not any(os.path.basename(f).endswith(s) for s in EXCLUDE_SUFFIXES)
    )
    acq_files = sorted(glob.glob(os.path.join(RAW_PHYSIOLOGY_DIR, '*' + ACQ_SUFFIX)))

    if not csv_files:
        raise FileNotFoundError(f'No PsychoPy trial .csv files found in {PSYCHOPY_DATA_DIR}')
    if not acq_files:
        raise FileNotFoundError(
            f'No *{ACQ_SUFFIX} files found in {RAW_PHYSIOLOGY_DIR}. '
            'This script anchors against the trimmed physiology recordings — check '
            'that RAW_PHYSIOLOGY_DIR in config.py points at '
            'raw_physiology/experimental_protocol_duration.')

    # pid → .acq path, matched on the full participant ID rather than a prefix.
    acq_by_pid = {pid_from_acq(os.path.basename(f)): f for f in acq_files}

    all_rows = {}
    # A participant with no trimmed recording (e.g. an early pilot) is simply not
    # part of this analysis — reported, but not a failure. Anything that IS present
    # and does not validate is a failure, and fails the run.
    no_physiology = []
    rejected      = {}

    for csv_path in csv_files:
        csv_name = os.path.basename(csv_path)
        pid      = pid_from_csv(csv_name)

        print(f'\n{"─"*50}')
        print(f'CSV : {csv_name}  →  PID : {pid}')

        # ── Clock alignment via BIOPAC baseline trigger ───────────────────────
        acq_path = acq_by_pid.get(pid)
        if acq_path is None:
            print(f'  –  No {pid}{ACQ_SUFFIX} — not in the trimmed physiology set, skipping')
            no_physiology.append(pid)
            continue

        try:
            biopac_baseline_onset = find_baseline_onset(acq_path, THRESHOLD, MIN_DUR_S)
        except ValueError as e:
            print(f'  ✗ REJECTED — {e}')
            rejected[pid] = [str(e)]
            continue

        # ── Extract PsychoPy block events ────────────────────────────────────
        try:
            psychopy_rows = extract_psychopy_blocks(csv_path)
        except Exception as e:
            print(f'  ✗ REJECTED — unreadable PsychoPy CSV: {e}')
            rejected[pid] = ['unreadable PsychoPy CSV: %s' % e]
            continue

        psychopy_baseline_onset = next(t for name, t in psychopy_rows if name == 'baseline')
        offset = biopac_baseline_onset - psychopy_baseline_onset

        print(f'  ACQ : {os.path.basename(acq_path)}')
        print(f'  BIOPAC baseline onset   : {biopac_baseline_onset:.3f} s')
        print(f'  PsychoPy baseline onset : {psychopy_baseline_onset:.3f} s')
        print(f'  Clock offset applied    : {offset:+.3f} s')

        # Apply clock offset to all events
        rows = [(name, t + offset) for name, t in psychopy_rows]

        problems = validate_trimmed(rows)
        if problems:
            print(f'  ✗ REJECTED — {pid} does not look like trimmed data:')
            for p in problems:
                print(f'      - {p}')
            print('    No event file written for this participant.')
            rejected[pid] = problems
            continue

        print('  Events (BIOPAC-referenced):')
        for name, t in sorted(rows, key=lambda x: x[1]):
            print(f'    {name:20s}  onset={t:.3f}s')

        all_rows[pid] = rows

    if not all_rows:
        print('\nNo participants processed — nothing written.')
        return 1

    # ── Build global NID map and write output ────────────────────────────────
    nid_map = build_nid_map(all_rows.values())

    print('\nNID map (consistent across participants):')
    for name, nid in sorted(nid_map.items(), key=lambda x: x[1]):
        print(f'  {nid}  {name}')

    save_nid_map(nid_map, os.path.join(BLOCK_ONSETS_DIR, 'nid_map_psychopy_ledalab.txt'))

    print()
    for pid, rows in all_rows.items():
        out_path = os.path.join(BLOCK_ONSETS_DIR, f'{pid}_events_blocks_psychopy_ledalab.txt')
        save_ledalab_txt(rows, nid_map, out_path)

    print(f'\nOutput dir: {BLOCK_ONSETS_DIR}')
    print(f'Written: {len(all_rows)}   '
          f'No physiology: {len(no_physiology)}   Rejected: {len(rejected)}')
    if no_physiology:
        print('No trimmed recording (skipped): ' + ', '.join(sorted(no_physiology)))
    if rejected:
        print('REJECTED: ' + ', '.join(sorted(rejected)))
        return 1
    print('Done.')
    return 0


sys.exit(main())
