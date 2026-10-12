"""
002_create_webcam_events_biopac.py
==================================
Writes every experiment event as seen by the BIOPAC trigger channels, in the SAME event names as
001_generate_event_onsets.py writes for the webcam video, so the two can be matched one-to-one
by WebcamBiometrics/eval/py/estimate_offsets.py to find each participant's ECG->video clock offset.

Why a separate file (the Ledalab / Kubios files already exist)
-------------------------------------------------------------
  {pid}_events_blocks_biopac_ledalab.txt   5 block ONSETS, numeric codes, induction merged
  Kubios_Samples.csv                       5 block windows, one row per file
For the clock offset we want more points and names: all 7 trigger pulses (baseline, each video,
each recovery), with START and END, labelled like 001's events. 7 onsets give a firmer offset
and a drift check, and the second video of each block is where a late-logged onset would show.

Times are seconds from the start of the TRIMMED recording — the same .acq files Kubios is run on,
so Kubios beat times and these events share one clock.

Events written (one row each, sorted by onset):
  Baseline                      baseline_trig
  <Valence> Video 1, Video 2    Nstim1_trig/Nstim2_trig (or Pstim*), numbered by ONSET ORDER —
                                which video comes first is counterbalanced, so numbering by
                                time is what lines up with 001 (which also numbers by time)
  <Valence> Induction           first video start -> last video end
  <Valence> Recovery            Nrecovery_trig / Precovery
Columns: event, channel, onset_s, offset_s, duration_s

A participant is skipped (nothing written, listed at the end) if any trigger channel is missing,
has no pulse or more than one pulse, is still HIGH at the end of the file, or if baseline is not
the first event (= probably an untrimmed recording; see 01_create_ledalab_events_biopac.py).

Input   {RAW_PHYSIOLOGY_DIR}/{pid}_physiology_trimmed.acq      (config.py: trimmed folder)
Output  {WEBCAM_EVENTS_DIR}/{pid}_events_biopac.csv
        WEBCAM_EVENTS_DIR from config.py if set, else SERVER_ROOT/event_onsets/webcam_biometrics

Usage   python 002_create_webcam_events_biopac.py
"""

import csv
import glob
import importlib.util
import os
import sys

import bioread
import numpy as np

THRESHOLD = 1.0      # V — triggers are 0 V / 5 V (as 001_create_kubios_samples.py)
MIN_PULSE_S = 1.0    # s — shorter HIGH periods are noise
ACQ_SUFFIX = "_physiology_trimmed.acq"

# channel -> (kind, valence)
CHANNELS = {
    "baseline_trig":  ("baseline", None),
    "Nstim1_trig":    ("video", "Negative"),
    "Nstim2_trig":    ("video", "Negative"),
    "Nrecovery_trig": ("recovery", "Negative"),
    "Pstim1_trig":    ("video", "Positive"),
    "Pstim2_trig":    ("video", "Positive"),
    "Precovery":      ("recovery", "Positive"),
}


def load_config():
    """Nearest config.py in this folder or above (normally analysis/config.py)."""
    folder = os.path.dirname(os.path.abspath(__file__))
    while not os.path.isfile(os.path.join(folder, "config.py")):
        parent = os.path.dirname(folder)
        if parent == folder:
            raise FileNotFoundError("No config.py found above " + os.path.dirname(os.path.abspath(__file__)))
        folder = parent
    spec = importlib.util.spec_from_file_location("webcam_events_config", os.path.join(folder, "config.py"))
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    return cfg


def get_pulses(channel):
    """[(start_s, end_s, still_high_at_end)] for every HIGH pulse >= MIN_PULSE_S."""
    signal = np.asarray(channel.data, dtype=float)
    sr = channel.samples_per_second
    edges = np.diff(np.concatenate([[0], (signal > THRESHOLD).astype(np.int8), [0]]))
    starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0]
    return [(float(s / sr), float(e / sr), bool(e == len(signal)))
            for s, e in zip(starts, ends) if (e - s) / sr >= MIN_PULSE_S]


def events_for(acq):
    """-> (events, problems). events = [(event, channel, onset_s, offset_s)] sorted by onset."""
    by_name = {ch.name: ch for ch in acq.channels}
    pulses, problems = {}, []
    for name in CHANNELS:
        if name not in by_name:
            problems.append(f'channel "{name}" not found')
            continue
        found = get_pulses(by_name[name])
        if len(found) != 1:
            problems.append(f'"{name}": {len(found)} pulses (expected 1) '
                            f'{[(round(s, 1), round(e, 1)) for s, e, _ in found]}')
            continue
        start, end, cut = found[0]
        if cut:
            problems.append(f'"{name}" still HIGH at the end of the recording (end cut short)')
            continue
        pulses[name] = (start, end)
    if problems:
        return [], problems

    events = []
    for valence in ("Negative", "Positive"):
        vids = sorted((pulses[c], c) for c, (k, v) in CHANNELS.items() if k == "video" and v == valence)
        for n, ((start, end), ch) in enumerate(vids, 1):
            events.append((f"{valence} Video {n}", ch, start, end))
        events.append((f"{valence} Induction", "+".join(c for _, c in vids), vids[0][0][0], vids[-1][0][1]))
    for ch, (kind, valence) in CHANNELS.items():
        if kind == "baseline":
            events.append(("Baseline", ch, *pulses[ch]))
        elif kind == "recovery":
            events.append((f"{valence} Recovery", ch, *pulses[ch]))
    events.sort(key=lambda e: (e[2], "Induction" not in e[0]))   # Induction before its Video 1

    singles = [e for e in events if "Induction" not in e[0]]
    if singles[0][0] != "Baseline":
        problems.append(f"{singles[0][0]} ({singles[0][2]:.2f} s) comes before Baseline — untrimmed recording?")
    if any(b[2] < a[3] for a, b in zip(singles, singles[1:])):
        problems.append("events overlap or are out of order")
    return (events if not problems else []), problems


def main():
    cfg = load_config()
    acq_dir = str(cfg.RAW_PHYSIOLOGY_DIR)
    out_dir = str(getattr(cfg, "WEBCAM_EVENTS_DIR",
                          os.path.join(str(cfg.SERVER_ROOT), "event_onsets", "webcam_biometrics")))
    if os.path.basename(os.path.normpath(acq_dir)) != "experimental_protocol_duration":
        print(f"[WARNING] RAW_PHYSIOLOGY_DIR = {acq_dir} — expected the trimmed "
              f"'experimental_protocol_duration' folder (the one Kubios is run on).")
    files = sorted(glob.glob(os.path.join(acq_dir, "*" + ACQ_SUFFIX)))
    if not files:
        raise SystemExit(f"No *{ACQ_SUFFIX} in {acq_dir}")
    os.makedirs(out_dir, exist_ok=True)

    written, skipped = [], {}
    for path in files:
        pid = os.path.basename(path)[: -len(ACQ_SUFFIX)].lower()
        print(f"\n{pid}  ({os.path.basename(path)})")
        events, problems = events_for(bioread.read(path))
        if problems:
            for p in problems:
                print(f"  [SKIPPED] {p}")
            skipped[pid] = problems
            continue
        out = os.path.join(out_dir, f"{pid}_events_biopac.csv")
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["event", "channel", "onset_s", "offset_s", "duration_s"])
            for name, ch, on, off in events:
                w.writerow([name, ch, f"{on:.4f}", f"{off:.4f}", f"{off - on:.3f}"])
                print(f"  {name:20s} {ch:26s} {on:9.3f} -> {off:9.3f}  ({off - on:6.1f} s)")
        written.append(pid)

    print(f"\nWritten {len(written)} to {out_dir}; skipped {len(skipped)}"
          + (f": {', '.join(sorted(skipped))}" if skipped else ""))
    return 1 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
