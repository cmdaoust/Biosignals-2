"""
01_create_ledalab_events_biopac.py
==================================
Reads BIOPAC .acq files and produces Ledalab-compatible event text files
by detecting trigger channel events directly from the physiology recording.

MUST RUN ON TRIMMED DATA
------------------------
Onsets are reported as seconds from the START OF THE FILE, so they are only
meaningful against the same recording Ledalab is fed. config.RAW_PHYSIOLOGY_DIR
therefore points at raw_physiology/experimental_protocol_duration/, where each
recording has been cut to the experimental protocol, and this script reads only
the {pid}_physiology_trimmed.acq files from it.

Pointing it at entire_session_duration/ instead does NOT fail loudly on its own:
the blocks come out shifted by the trim offset, and neg_induction collapses to
0.0000 s because an N-stim trigger channel is already HIGH at sample 0. The
validate_trimmed() check below exists to catch exactly that.

The {pid}_eda_trimmed.acq files in the same folder carry no trigger channels
(EDA, Y and PPGED-R only) and are deliberately not read here.

NOTE ON CHANNEL MAPPING
-----------------------
Channel names correctly reflect condition polarity (P = positive, N = negative).
There is no P/N inversion.

Verified two ways: against PsychoPy timing for pilot subject 002, and against
the full pilot sample — every participant ran neg_first in PsychoPy, and this
mapping puts neg_induction (~201 s) before pos_induction (~602 s), which an
inverted mapping would reverse.

  baseline_trig   → baseline
  Nstim2_trig     → neg_induction   (first neg video — earlier onset, used as block start)
  Nstim1_trig     → neg_induction   (second neg video — merged, onset not used)
  Nrecovery_trig  → neg_recovery
  Pstim2_trig     → pos_induction   (first pos video — earlier onset, used as block start)
  Pstim1_trig     → pos_induction   (second pos video — merged, onset not used)
  Precovery       → pos_recovery

Input
-----
  {RAW_PHYSIOLOGY_DIR}/{pid}_physiology_trimmed.acq

Output
------
  {BLOCK_ONSETS_DIR}/{pid}_events_blocks_biopac_ledalab.txt
      Tab-separated, two columns: time  nid
      One row per block epoch, sorted by onset time.

  {BLOCK_ONSETS_DIR}/nid_map_biopac_ledalab.txt
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
  python 01_create_ledalab_events_biopac.py

  Paths are read from config.py at the repo root.
  Exits non-zero if any participant fails validation.
"""

import os
import glob
import sys
import numpy as np
import bioread
import sys as _sys, os as _os
# config.py lives at the repo root (two folders up from this script)
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..')))
from config import RAW_PHYSIOLOGY_DIR, BLOCK_ONSETS_DIR

# ── CONFIG ────────────────────────────────────────────────────────────────────

RAW_PHYSIOLOGY_DIR = str(RAW_PHYSIOLOGY_DIR)
BLOCK_ONSETS_DIR   = str(BLOCK_ONSETS_DIR)

THRESHOLD = 0.5   # Volts — threshold to detect a trigger HIGH
MIN_DUR_S = 1.0   # seconds — rejects noise spikes

# Only the physiology recording carries the trigger channels.
ACQ_SUFFIX = '_physiology_trimmed.acq'

# A trimmed recording starts at the baseline block, so its baseline onset sits a
# second or two into the file. On an untrimmed session it is several minutes in.
MAX_BASELINE_ONSET_S = 30.0

# Maps BIOPAC channel name → block-level condition label.
# See "NOTE ON CHANNEL MAPPING" above: the names are accurate, P = positive and
# N = negative. The two induction channels per valence are merged so that the
# earlier of the two video onsets becomes the block start.
TRIGGER_MAP = {
    'baseline_trig':  'baseline',
    'Nstim2_trig':    'neg_induction',   # first neg video  (240s)
    'Nstim1_trig':    'neg_induction',   # second neg video (355s) — merged; min gives block onset
    'Nrecovery_trig': 'neg_recovery',    # neg recovery     (441s)
    'Pstim2_trig':    'pos_induction',   # first pos video  (649s)
    'Pstim1_trig':    'pos_induction',   # second pos video (753s) — merged; min gives block onset
    'Precovery':      'pos_recovery',    # pos recovery     (855s)
}

EXPECTED_CONDITIONS = sorted(set(TRIGGER_MAP.values()))

# Optional: override ACQ filename → participant ID mapping.
# Leave empty to take the participant ID from the filename, which is everything
# before ACQ_SUFFIX (e.g. "e5510_physiology_trimmed.acq" → "e5510").
ACQ_TO_PID = {
    # 'carmen_pilot_physiology_trimmed.acq': '001',
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def pid_from_filename(acq_name):
    """Participant ID = the filename with ACQ_SUFFIX stripped."""
    if acq_name in ACQ_TO_PID:
        return ACQ_TO_PID[acq_name]
    if acq_name.endswith(ACQ_SUFFIX):
        return acq_name[:-len(ACQ_SUFFIX)]
    return os.path.splitext(acq_name)[0]


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


def validate_trimmed(rows):
    """Return a list of reasons these onsets do not look like trimmed data.

    Catches the untrimmed-input failure mode: on a full session recording the
    baseline lands minutes into the file and neg_induction collapses to 0.0000 s
    because an N-stim channel is HIGH at sample 0, so baseline stops being the
    earliest event.
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
            'baseline starts at %.1fs (expected < %.0fs) — this looks like an '
            'untrimmed recording' % (baseline, MAX_BASELINE_ONSET_S))

    early = {c: t for c, t in by_condition.items() if c != 'baseline' and t < baseline}
    if early:
        problems.append(
            'condition(s) before baseline: %s — a trigger channel is probably '
            'HIGH at sample 0' % ', '.join('%s=%.4fs' % kv for kv in sorted(early.items())))

    return problems


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
    acq_files = sorted(glob.glob(os.path.join(RAW_PHYSIOLOGY_DIR, '*' + ACQ_SUFFIX)))
    if not acq_files:
        raise FileNotFoundError(
            f'No *{ACQ_SUFFIX} files found in {RAW_PHYSIOLOGY_DIR}. '
            'This script reads the trimmed physiology recordings — check that '
            'RAW_PHYSIOLOGY_DIR in config.py points at '
            'raw_physiology/experimental_protocol_duration.')

    all_rows = {}
    skipped  = {}

    for acq_path in acq_files:
        acq_name = os.path.basename(acq_path)
        pid      = pid_from_filename(acq_name)

        print(f'\n{"─"*50}')
        print(f'ACQ : {acq_name}  →  PID : {pid}')

        acq        = bioread.read(acq_path)
        ch_by_name = {ch.name: ch for ch in acq.channels}
        sr         = acq.channels[0].samples_per_second
        total_s    = len(acq.channels[0].data) / sr
        print(f'Duration: {total_s:.1f} s  @ {sr:.0f} Hz')

        # Collect raw onsets per condition
        condition_onsets = {}   # condition → list of onset_s
        for trig_name, condition in TRIGGER_MAP.items():
            if trig_name not in ch_by_name:
                print(f'  ⚠  "{trig_name}" not in .acq — skipped')
                continue
            evs = find_events(ch_by_name[trig_name], THRESHOLD, MIN_DUR_S)
            for onset, _ in evs:
                condition_onsets.setdefault(condition, []).append(onset)
                print(f'  {trig_name:20s} → {condition:15s}  onset={onset:.2f}s')

        # Build Ledalab rows: one row per block epoch.
        # Induction conditions have two trigger onsets (two videos);
        # use the earliest onset as the block start.
        rows = []
        for condition, onsets in condition_onsets.items():
            rows.append((condition, min(onsets)))

        problems = validate_trimmed(rows)
        if problems:
            print(f'  ✗ REJECTED — {pid} does not look like trimmed data:')
            for p in problems:
                print(f'      - {p}')
            print('    No event file written for this participant.')
            skipped[pid] = problems
            continue

        all_rows[pid] = rows

    if not all_rows:
        print('\nNo participant passed validation — nothing written.')
        return 1

    # ── Build global NID map and write output ────────────────────────────────
    nid_map = build_nid_map(all_rows.values())

    print('\nNID map (consistent across participants):')
    for name, nid in sorted(nid_map.items(), key=lambda x: x[1]):
        print(f'  {nid}  {name}')

    save_nid_map(nid_map, os.path.join(BLOCK_ONSETS_DIR, 'nid_map_biopac_ledalab.txt'))

    print()
    for pid, rows in all_rows.items():
        print(f'PID : {pid}')
        out_path = os.path.join(BLOCK_ONSETS_DIR, f'{pid}_events_blocks_biopac_ledalab.txt')
        save_ledalab_txt(rows, nid_map, out_path)

    print(f'\nOutput dir: {BLOCK_ONSETS_DIR}')
    print(f'Written: {len(all_rows)}   Rejected: {len(skipped)}')
    if skipped:
        print('Rejected participants: ' + ', '.join(sorted(skipped)))
        return 1
    print('Done.')
    return 0


sys.exit(main())
