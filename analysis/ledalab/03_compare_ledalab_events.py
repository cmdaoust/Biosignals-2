"""
03_compare_ledalab_events.py
============================
Compares the Ledalab event files produced by the two extraction methods:

  01_create_ledalab_events_biopac.py   → {pid}_events_blocks_biopac_ledalab.txt
  02_create_ledalab_events_psychopy.py → {pid}_events_blocks_psychopy_ledalab.txt

For each participant and each condition, prints the onset times from both
sources and flags any difference exceeding ONSET_TOL.

This is the primary check for whether the BIOPAC channel-to-condition mapping
is correct: if BIOPAC and PsychoPy agree on onset times (within ~1s), the
mapping is right.

Usage
-----
  python 03_compare_ledalab_events.py

  Run both event creation scripts first, then run this.
  Paths are read from config.py in the same directory.
"""

import os
import glob
import pandas as pd
from config import BLOCK_ONSETS_DIR

# ── CONFIG ────────────────────────────────────────────────────────────────────

BLOCK_ONSETS_DIR = str(BLOCK_ONSETS_DIR)

ONSET_TOL = 2.0   # seconds — flag if onsets differ by more than this


# ── HELPERS ───────────────────────────────────────────────────────────────────

def load_events(filepath, nid_map):
    """
    Load a Ledalab event file and return a dict: condition_name → onset_s.
    Uses nid_map (nid → condition name) to convert numeric IDs to labels.
    """
    df = pd.read_csv(filepath, sep='\t')
    return {nid_map[int(row['nid'])]: row['time'] for _, row in df.iterrows()}


def load_nid_map(filepath):
    """Load nid_map file → dict: nid (int) → condition name (str)."""
    df = pd.read_csv(filepath, sep='\t')
    return dict(zip(df['nid'].astype(int), df['condition']))


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    # Find all participant IDs that have at least one event file
    biopac_files   = glob.glob(os.path.join(BLOCK_ONSETS_DIR, '*_events_blocks_biopac_ledalab.txt'))
    psychopy_files = glob.glob(os.path.join(BLOCK_ONSETS_DIR, '*_events_blocks_psychopy_ledalab.txt'))

    if not biopac_files and not psychopy_files:
        print('No event files found. Run both extraction scripts first.')
        print(f'  Looking in: {BLOCK_ONSETS_DIR}')
        return

    def pid_from(path):
        return os.path.basename(path).split('_')[0]

    pids = sorted(set(pid_from(f) for f in biopac_files + psychopy_files))

    # Load NID maps
    nid_map_b_path = os.path.join(BLOCK_ONSETS_DIR, 'nid_map_biopac_ledalab.txt')
    nid_map_p_path = os.path.join(BLOCK_ONSETS_DIR, 'nid_map_psychopy_ledalab.txt')

    nid_map_b = load_nid_map(nid_map_b_path) if os.path.exists(nid_map_b_path) else {}
    nid_map_p = load_nid_map(nid_map_p_path) if os.path.exists(nid_map_p_path) else {}

    any_flag = False

    for pid in pids:
        print(f'\n{"═"*55}')
        print(f'Participant: {pid}')

        b_path = os.path.join(BLOCK_ONSETS_DIR, f'{pid}_events_blocks_biopac_ledalab.txt')
        p_path = os.path.join(BLOCK_ONSETS_DIR, f'{pid}_events_blocks_psychopy_ledalab.txt')

        b_exists = os.path.exists(b_path)
        p_exists = os.path.exists(p_path)

        if not b_exists:
            print(f'  ⚠  BIOPAC file missing — run 01_create_ledalab_events_biopac.py')
        if not p_exists:
            print(f'  ⚠  PsychoPy file missing — run 02_create_ledalab_events_psychopy.py')
        if not b_exists or not p_exists:
            continue

        b_events = load_events(b_path, nid_map_b)
        p_events = load_events(p_path, nid_map_p)

        all_conditions = sorted(set(b_events) | set(p_events))

        print(f'\n  {"Condition":<20s}  {"BIOPAC (s)":>10}  {"PsychoPy (s)":>12}  {"Δ (s)":>8}  Flag')
        print('  ' + '─' * 58)

        for cond in all_conditions:
            if cond not in b_events:
                print(f'  {cond:<20s}  {"—":>10}  {p_events[cond]:>12.3f}  {"":>8}  ⚠ missing from BIOPAC')
                any_flag = True
                continue
            if cond not in p_events:
                print(f'  {cond:<20s}  {b_events[cond]:>10.3f}  {"—":>12}  {"":>8}  ⚠ missing from PsychoPy')
                any_flag = True
                continue

            t_b   = b_events[cond]
            t_p   = p_events[cond]
            delta = t_b - t_p
            flag  = '  ⚠ LARGE DIFF' if abs(delta) > ONSET_TOL else ''
            if flag:
                any_flag = True
            print(f'  {cond:<20s}  {t_b:>10.3f}  {t_p:>12.3f}  {delta:>+8.3f}{flag}')

    print(f'\n{"═"*55}')
    if any_flag:
        print(f'⚠  Some differences exceed {ONSET_TOL}s — review flagged rows above.')
        print('   If BIOPAC and PsychoPy agree within ~1s, the BIOPAC channel')
        print('   mapping is correct. Larger differences suggest a mapping error.')
    else:
        print(f'✓  All onsets agree within {ONSET_TOL}s.')
        print('   BIOPAC channel mapping appears correct.')


main()
