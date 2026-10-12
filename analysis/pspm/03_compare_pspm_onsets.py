"""
compare_pspm_onsets.py
======================
Compares the PSPM event onset .mat files produced by the two extraction methods:

  create_pspm_onsets_biopac.py   → {pid}_timing_*_biopac.mat
  create_pspm_onsets_psychopy.py → {pid}_timing_*_psychopy.mat

For each participant and each timing file type (videos / conditions), the script
prints a table showing onset and duration differences for every matched condition.
A summary flags any condition where the onset difference exceeds ONSET_TOL or
the duration difference exceeds DUR_TOL.

File locations searched:
  videos/  — individual-video timing files
  blocks/  — block-level (condition) timing files

Run BOTH extraction scripts first, then run this script.

Usage
-----
  python compare_pspm_onsets.py

  Paths are read from config.py at the repo root.
  Copy config.yaml.example → config.yaml and set your paths.
"""

import os
import glob
import numpy as np
import scipy.io as sio
import sys as _sys, os as _os
# config.py lives at the repo root (two folders up from this script)
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..')))
from config import BLOCK_ONSETS_DIR, VIDEO_ONSETS_DIR

# ── CONFIG ────────────────────────────────────────────────────────────────────

BLOCK_ONSETS_DIR = str(BLOCK_ONSETS_DIR)
VIDEO_ONSETS_DIR = str(VIDEO_ONSETS_DIR)

ONSET_TOL = 1.0   # seconds — flag if onsets differ by more than this
DUR_TOL   = 2.0   # seconds — flag if durations differ by more than this

# Map timing file type → directory where it lives
TYPE_DIR = {
    'stimuli': VIDEO_ONSETS_DIR,
    'blocks':  BLOCK_ONSETS_DIR,
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def load_mat(filepath):
    """
    Load a PSPM timing .mat file.

    Returns dict: { condition_name: {'onsets': np.array, 'durations': np.array} }
    """
    mat = sio.loadmat(filepath, squeeze_me=False)

    names_raw     = mat['names']
    onsets_raw    = mat['onsets']
    durations_raw = mat['durations']

    result = {}
    n = names_raw.shape[1]
    for i in range(n):
        name = str(names_raw[0, i]).strip()
        onsets    = np.asarray(onsets_raw[0, i],    dtype=float).flatten()
        durations = np.asarray(durations_raw[0, i], dtype=float).flatten()
        result[name] = {'onsets': onsets, 'durations': durations}
    return result


def compare_mats(biopac_mat, psychopy_mat, label):
    """
    Compare two loaded timing dicts and print a difference table.

    Returns True if any difference exceeds tolerance.
    """
    all_names = sorted(set(biopac_mat) | set(psychopy_mat))
    has_flag  = False

    print(f'\n  ── {label} ──')
    header = f"  {'Condition':<20s}  {'#ev':>3}  {'Onset_B':>8}  {'Onset_P':>8}  "
    header += f"{'ΔOnset':>7}  {'Dur_B':>7}  {'Dur_P':>7}  {'ΔDur':>7}  Flag"
    print(header)
    print('  ' + '─' * (len(header) - 2))

    for name in all_names:
        if name not in biopac_mat:
            print(f"  {'[BIOPAC missing]':<20s}  —  condition '{name}' only in PsychoPy file")
            has_flag = True
            continue
        if name not in psychopy_mat:
            print(f"  {'[PSYCHOPY missing]':<20s}  —  condition '{name}' only in BIOPAC file")
            has_flag = True
            continue

        b = biopac_mat[name]
        p = psychopy_mat[name]

        n_b = len(b['onsets'])
        n_p = len(p['onsets'])

        if n_b != n_p:
            print(f"  {name:<20s}  ⚠  event count mismatch: BIOPAC={n_b}, PsychoPy={n_p}")
            has_flag = True
            continue

        for ev_i in range(n_b):
            o_b = b['onsets'][ev_i]
            o_p = p['onsets'][ev_i]
            d_b = b['durations'][ev_i]
            d_p = p['durations'][ev_i]
            d_onset = o_b - o_p
            d_dur   = d_b - d_p
            flag = ''
            if abs(d_onset) > ONSET_TOL:
                flag += ' ⚠onset'
                has_flag = True
            if abs(d_dur) > DUR_TOL:
                flag += ' ⚠dur'
                has_flag = True

            ev_label = name if ev_i == 0 else ''
            print(f"  {ev_label:<20s}  {ev_i+1:>3}  "
                  f"{o_b:>8.2f}  {o_p:>8.2f}  {d_onset:>+7.2f}  "
                  f"{d_b:>7.2f}  {d_p:>7.2f}  {d_dur:>+7.2f}  {flag}")

    return has_flag


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    # Collect all participant IDs from both output directories
    all_files = (
        glob.glob(os.path.join(VIDEO_ONSETS_DIR, '*_biopac_pspm.mat')) +
        glob.glob(os.path.join(VIDEO_ONSETS_DIR, '*_psychopy_pspm.mat')) +
        glob.glob(os.path.join(BLOCK_ONSETS_DIR, '*_biopac_pspm.mat')) +
        glob.glob(os.path.join(BLOCK_ONSETS_DIR, '*_psychopy_pspm.mat'))
    )

    if not all_files:
        print('No output .mat files found in stimulus_videos/ or blocks/.')
        print(f'  stimulus_videos/ : {VIDEO_ONSETS_DIR}')
        print(f'  blocks/          : {BLOCK_ONSETS_DIR}')
        print('Run both extraction scripts first.')
        return

    def pid_from_path(p):
        return os.path.basename(p)[:3]

    pids = sorted(set(pid_from_path(f) for f in all_files))

    any_flag = False
    for pid in pids:
        print(f'\n{"═"*60}')
        print(f'Participant: {pid}')

        for ftype, outdir in TYPE_DIR.items():
            b_path = os.path.join(outdir, f'{pid}_events_{ftype}_biopac_pspm.mat')
            p_path = os.path.join(outdir, f'{pid}_events_{ftype}_psychopy_pspm.mat')

            b_exists = os.path.exists(b_path)
            p_exists = os.path.exists(p_path)

            if not b_exists and not p_exists:
                print(f'\n  ── {ftype} ── (neither file exists in {outdir})')
                continue
            if not b_exists:
                print(f'\n  ── {ftype} ── (BIOPAC file missing: {os.path.basename(b_path)})')
                any_flag = True
                continue
            if not p_exists:
                print(f'\n  ── {ftype} ── (PsychoPy file missing: {os.path.basename(p_path)})')
                any_flag = True
                continue

            b_mat = load_mat(b_path)
            p_mat = load_mat(p_path)
            flag  = compare_mats(b_mat, p_mat, ftype)
            any_flag = any_flag or flag

    print(f'\n{"═"*60}')
    if any_flag:
        print('⚠  Differences exceed tolerances — review flagged rows above.')
        print(f'   Onset tolerance    : {ONSET_TOL} s')
        print(f'   Duration tolerance : {DUR_TOL} s')
    else:
        print('✓  All onsets and durations agree within tolerance.')
        print(f'   Onset tolerance    : {ONSET_TOL} s')
        print(f'   Duration tolerance : {DUR_TOL} s')


if __name__ == '__main__':
    main()
