"""
001_create_kubios_samples.py
============================
Reads the BIOPAC .acq files in RAW_PHYSIOLOGY_DIR, finds the experiment's
trigger events in them, and writes Kubios_Samples.csv into the same folder.
Kubios picks the CSV up automatically when it is next to the .acq files,
matching rows by file name.

One row per .acq file, five samples each:
  S1  baseline       baseline_trig
  S2  neg_induction  Nstim1_trig + Nstim2_trig   first video start -> last video end
  S3  neg_recovery   Nrecovery_trig
  S4  pos_induction  Pstim1_trig + Pstim2_trig   first video start -> last video end
  S5  pos_recovery   Precovery

How the triggers work
---------------------
PsychoPy sets a trigger line HIGH (5 V) when the fixation cross / video starts
and back to 0 V ('00') when it ends, so each event is one HIGH pulse:
  START = rising edge, END = falling edge
Times are seconds relative to the start of each .acq file.

Channel names match the stimuli (checked against PsychoPy timing for g2313,
e5510 and i4155): Nstim1_trig = N007, Nstim2_trig = N01, Pstim1_trig = P0141,
Pstim2_trig = P02. Which video of a pair is shown first is counterbalanced, so
each induction sample runs from the earliest start to the latest end of its
two channels.

Files without trigger channels (e.g. *_eda_trimmed.acq, which only hold EDA)
are skipped.

Checks (printed as warnings, listed again in the summary):
  - trigger channel missing, with no pulse, or with more than one pulse
  - trigger still HIGH at the end of the recording (sample END cut short)
  - baseline / recovery not about 180 s long
  - samples overlapping or out of order

Usage
-----
  python 001_create_kubios_samples.py                # only recordings not in the CSV yet
  python 001_create_kubios_samples.py --all          # redo every recording
  python 001_create_kubios_samples.py --redo r2433   # redo these participants / files only

  By default, recordings that already have a row in Kubios_Samples.csv are
  skipped and their rows are copied over unchanged, so the CSV still lists
  everyone. Only new .acq files are read. Use --redo (by participant ID or file
  name) after fixing a recording, or --all after changing this script (e.g. the
  thresholds or SAMPLES). If the existing CSV has different columns from what
  this script writes, everything is redone automatically.

  RAW_PHYSIOLOGY_DIR is read from config.py (the nearest one above this
  script). The previous Kubios_Samples.csv is kept as Kubios_Samples_previous.csv.
"""

import argparse

import os
import glob
import shutil
import sys
import numpy as np
import bioread

# ── CONFIG ────────────────────────────────────────────────────────────────────

def _find_repo_root():
    try:
        start = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        start = os.path.abspath('.')
    current = start
    for _ in range(6):
        if os.path.isfile(os.path.join(current, 'config.py')):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    raise FileNotFoundError(
        f"Could not find config.py searching upward from: {start}\n"
        "Make sure config.py exists at the repo root (copy config_template.py)."
    )

sys.path.insert(0, _find_repo_root())
from config import RAW_PHYSIOLOGY_DIR

RAW_PHYSIOLOGY_DIR = str(RAW_PHYSIOLOGY_DIR)

THRESHOLD   = 1.0   # Volts — triggers are 0 V / 5 V
MIN_PULSE_S = 1.0   # seconds — shorter HIGH periods are treated as noise

# Expected sample lengths, used only for warnings
EXPECTED_DURATION_S  = {'baseline': 180.0, 'neg_recovery': 180.0, 'pos_recovery': 180.0}
DURATION_TOLERANCE_S = 2.0

# Sample order in the Kubios CSV (S1..S5) → trigger channel(s) that define each sample
SAMPLES = {
    'baseline':      ['baseline_trig'],
    'neg_induction': ['Nstim1_trig', 'Nstim2_trig'],
    'neg_recovery':  ['Nrecovery_trig'],
    'pos_induction': ['Pstim1_trig', 'Pstim2_trig'],
    'pos_recovery':  ['Precovery'],
}
TRIGGER_CHANNELS = {ch for channels in SAMPLES.values() for ch in channels}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_pulses(channel, threshold=THRESHOLD, min_pulse_s=MIN_PULSE_S):
    """Return (start_s, end_s, still_high_at_end) for every HIGH pulse of at least min_pulse_s."""
    signal = np.asarray(channel.data, dtype=float)
    sr     = channel.samples_per_second
    high   = (signal > threshold).astype(np.int8)
    edges  = np.diff(np.concatenate([[0], high, [0]]))
    starts = np.where(edges == 1)[0]
    ends   = np.where(edges == -1)[0]
    return [(s / sr, e / sr, e == len(signal)) for s, e in zip(starts, ends)
            if (e - s) / sr >= min_pulse_s]


def sec_to_hms(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def find_sample_windows(acq):
    """Return ({sample: (start_s, end_s)}, warnings) for one recording."""
    ch_by_name = {ch.name: ch for ch in acq.channels}
    windows, warnings = {}, []

    for sample, channel_names in SAMPLES.items():
        pulses = []
        for name in channel_names:
            if name not in ch_by_name:
                warnings.append(f'channel "{name}" not found')
                continue
            found = get_pulses(ch_by_name[name])
            if not found:
                warnings.append(f'no pulse on "{name}"')
            elif len(found) > 1:
                warnings.append(f'{len(found)} pulses on "{name}" (expected 1): '
                                f'{[(round(s, 1), round(e, 1)) for s, e, _ in found]} - sample spans all of them')
            if any(cut for _, _, cut in found):
                warnings.append(f'"{name}" is still HIGH at the end of the recording - {sample} END is cut short')
            pulses += found
        if not pulses:
            continue

        start_s = min(s for s, _, _ in pulses)
        end_s   = max(e for _, e, _ in pulses)
        windows[sample] = (start_s, end_s)
        expected = EXPECTED_DURATION_S.get(sample)
        if expected is not None and abs((end_s - start_s) - expected) > DURATION_TOLERANCE_S:
            warnings.append(f'{sample} lasts {end_s - start_s:.1f} s (expected about {expected:.0f} s)')

    ordered = [windows[s] for s in SAMPLES if s in windows]
    if any(b[0] < a[1] for a, b in zip(ordered, ordered[1:])):
        warnings.append('samples overlap or are out of order')
    return windows, warnings


# ── MAIN ──────────────────────────────────────────────────────────────────────

def csv_header():
    parts = ['File name', '0=Absolute time/1=Relative to beginning of measurement']
    for i in range(1, len(SAMPLES) + 1):
        parts += [f'Label (Sample {i})', f'START (Sample {i})', f'END (Sample {i})']
    return ','.join(parts)


def read_existing_rows(output_path):
    """{file name: original CSV line} from an existing Kubios_Samples.csv ({} if none/incompatible)."""
    if not os.path.exists(output_path):
        return {}
    with open(output_path, encoding='utf-8-sig') as f:
        lines = [l.rstrip('\r\n') for l in f if l.strip()]
    if not lines or lines[0] != csv_header():
        print('Existing Kubios_Samples.csv has different columns from this script - redoing every recording.\n')
        return {}
    return {l.split(',', 1)[0]: l for l in lines[1:]}


def wants_redo(acq_name, redo):
    """True if acq_name matches a --redo entry (participant ID before the first '_', or the file name)."""
    name = acq_name.lower()
    pid = name.split('_', 1)[0]
    return any(r.lower() in (pid, name, os.path.splitext(name)[0]) for r in redo)


def main(acq_dir=RAW_PHYSIOLOGY_DIR, output_path=None, redo_all=False, redo=()):
    output_path = output_path or os.path.join(acq_dir, 'Kubios_Samples.csv')
    acq_files = sorted(glob.glob(os.path.join(acq_dir, '*.acq')))
    if not acq_files:
        raise FileNotFoundError(f'No .acq files found in: {acq_dir}')
    print(f'Found {len(acq_files)} .acq file(s) in: {acq_dir}\n')

    existing = {} if redo_all else read_existing_rows(output_path)
    unmatched = [r for r in redo if not any(wants_redo(os.path.basename(a), [r]) for a in acq_files)]
    if unmatched:
        print(f'WARNING: --redo matched no .acq file: {", ".join(unmatched)}\n')

    rows, skipped, flagged, kept = [], [], {}, []

    for acq_path in acq_files:
        acq_name = os.path.basename(acq_path)
        if acq_name in existing and not wants_redo(acq_name, redo):
            kept.append(acq_name)
            continue
        channel_names = {ch.name for ch in bioread.read_headers(acq_path).channels}
        if not channel_names & TRIGGER_CHANNELS:
            print(f'Skipping {acq_name}: no trigger channels ({sorted(channel_names)})\n')
            skipped.append(acq_name)
            continue

        print(f'Processing: {acq_name}')
        windows, warnings = find_sample_windows(bioread.read(acq_path))
        for sample in SAMPLES:
            if sample in windows:
                start_s, end_s = windows[sample]
                print(f'  {sample:14s} [{sec_to_hms(start_s)} → {sec_to_hms(end_s)}]  {end_s - start_s:6.1f} s')
            else:
                print(f'  {sample:14s} not found')
        for w in warnings:
            print(f'  WARNING: {w}')
        if warnings:
            flagged[acq_name] = warnings
        rows.append({'filename': acq_name, 'windows': windows})
        print()

    if kept:
        print(f'Already done, row kept unchanged ({len(kept)}): {", ".join(kept)}\n')
    if not rows and set(kept) == set(existing):
        print('No new recordings - Kubios_Samples.csv left as it is.')
        print('  (use --all to redo everyone, or --redo <id> for one participant)')
        return rows

    # ── Write Kubios_Samples.csv ─────────────────────────────────────────────
    # Kept rows are copied verbatim; rows for .acq files that no longer exist are kept too.
    new_lines = {}
    for row in rows:
        parts = [row['filename'], '1']   # 1 = relative to beginning of measurement
        for sample in SAMPLES:
            if sample in row['windows']:
                start_s, end_s = row['windows'][sample]
                parts += [sample, f'{start_s:.3f}', f'{end_s:.3f}']
            else:
                parts += [sample, 'NaN', 'NaN']
        new_lines[row['filename']] = ','.join(parts)

    # a --redo'd file that now has no trigger channels loses its old row
    all_lines = {**{k: v for k, v in existing.items() if k not in skipped}, **new_lines}
    gone = sorted(k for k in existing if not os.path.exists(os.path.join(acq_dir, k)))
    lines = [csv_header()] + [all_lines[k] for k in sorted(all_lines, key=str.lower)]

    if os.path.exists(output_path):
        previous = os.path.join(os.path.dirname(output_path), 'Kubios_Samples_previous.csv')
        shutil.copy2(output_path, previous)
        print(f'Existing file kept as: {previous}')
    with open(output_path, 'w', newline='') as f:
        f.write('\n'.join(lines) + '\n')

    print(f'Kubios_Samples.csv written to:\n  {output_path}')
    print(f'  {len(lines) - 1} recording(s) in the file: {len(rows)} processed now, {len(kept)} kept from before.')
    if gone:
        print(f'  Kept rows for .acq files no longer in the folder: {", ".join(gone)}')
    if skipped:
        print(f'  Skipped (no trigger channels): {", ".join(skipped)}')
    if flagged:
        print('  Check these recordings:')
        for name, warnings in flagged.items():
            print(f'    {name}: {"; ".join(warnings)}')
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Write Kubios_Samples.csv (samples S1-S5) for the BIOPAC .acq files.')
    ap.add_argument('--all', action='store_true', help='redo every recording, not just new ones')
    ap.add_argument('--redo', nargs='+', default=[], metavar='ID_OR_FILE',
                    help='redo these recordings (participant ID, e.g. r2433, or file name)')
    args = ap.parse_args()
    main(redo_all=args.all, redo=args.redo)
