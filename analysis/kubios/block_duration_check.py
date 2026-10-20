"""
block_duration_check.py
=======================
Shared check, used by three scripts: whichever of them runs last catches a mismatch.
  analysis/video/001_generate_event_onsets.py      (step 4)
  analysis/kubios/001_create_kubios_samples.py     (end of run)
  analysis/kubios/002_create_kubios_samples_video.py (end of run)

WHY: ECG, FaceReader and WebcamBiometrics HRV are only comparable if Kubios analyses blocks of
the SAME length in all three. So for each participant it compares the duration of the five
Kubios blocks (baseline, neg_induction, neg_recovery, pos_induction, pos_recovery) across:

  source               file                                              written by
  ECG Kubios samples   RAW_PHYSIOLOGY_DIR/Kubios_Samples.csv             kubios/001_create_kubios_samples.py
  video events         FACEREADER_ONSETS_DIR/<id>_video_events.csv       video/001_generate_event_onsets.py (step 1)
  BIOPAC events        WEBCAM_EVENTS_DIR/<id>_events_biopac.csv          video/001_generate_event_onsets.py (step 2)
  FaceReader samples   FACEREADER_RESULTS_DIR/Kubios_Samples.csv         kubios/002_create_kubios_samples_video.py
  webcam samples       WEBCAM_HR_DIR/Kubios_Samples.csv                  kubios/002_create_kubios_samples_video.py

The reference is the ECG Kubios samples (what the ECG HRV uses); if a participant has no ECG
row, the BIOPAC events are used instead. Every other source must agree within TOLERANCE_S.

FACEREADER: its windows are deliberately on FaceReader's OWN clock (frame number / the frame rate
in its log), because we report FaceReader as sold - on the video as fed in. For 1:1 and
*_recording.avi videos that clock runs fast or slow wherever the camera's real frame rate varied,
so a block that covers exactly the right frames can measure e.g. 0.6 s longer in FaceReader
seconds. That is NOT a mismatch. So each FaceReader window is first converted back to real time
(frame -> real capture time in <id>_frame_timestamps.csv, the exact inverse of what
002_create_kubios_samples_video.py does) and the REAL span is compared with the other sources.
The clock difference itself is printed as a note, never as a warning. Real-time videos
(*realtime*, *_facereader*) need no conversion. If the conversion isn't possible (log or
timestamps not found), FaceReader is left out of the comparison with a warning saying why.

A file that doesn't exist yet, or has no row for a participant, is reported with the script to
run - the check then covers the sources that do exist. Nothing is written; it only warns.
"""

import os

import numpy as np
import pandas as pd

SAMPLES = ['baseline', 'neg_induction', 'neg_recovery', 'pos_induction', 'pos_recovery']
EVENT_OF_SAMPLE = {'baseline': 'Baseline', 'neg_induction': 'Negative Induction',
                   'neg_recovery': 'Negative Recovery', 'pos_induction': 'Positive Induction',
                   'pos_recovery': 'Positive Recovery'}
TOLERANCE_S = 0.25

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.dirname(HERE)
SCRIPT_ECG = os.path.join(ANALYSIS, 'kubios', '001_create_kubios_samples.py')
SCRIPT_VIDEO_SAMPLES = os.path.join(ANALYSIS, 'kubios', '002_create_kubios_samples_video.py')
SCRIPT_EVENTS = os.path.join(ANALYSIS, 'video', '001_generate_event_onsets.py')


def pid_of(name):
    return os.path.basename(str(name)).split('_', 1)[0].lower()


def source_paths(cfg):
    """[(source, kind, path, script)] - kind 'samples' (one CSV, rows per file) or 'events' (folder of <id> CSVs)."""
    server = str(getattr(cfg, 'SERVER_ROOT', '') or '')
    def opt(name, *default):
        v = getattr(cfg, name, None)
        return str(v) if v else (os.path.join(server, *default) if server else None)
    raw = str(cfg.RAW_PHYSIOLOGY_DIR) if getattr(cfg, 'RAW_PHYSIOLOGY_DIR', None) else None
    fr, wc = opt('FACEREADER_RESULTS_DIR', 'facereader'), opt('WEBCAM_HR_DIR', 'webcam_biometrics')
    return [
        ('ECG Kubios samples', 'samples', raw and os.path.join(raw, 'Kubios_Samples.csv'), SCRIPT_ECG),
        ('video events', 'events', (opt('FACEREADER_ONSETS_DIR', 'event_onsets', 'facereader_video'), '_video_events.csv'), SCRIPT_EVENTS),
        ('BIOPAC events', 'events', (opt('WEBCAM_EVENTS_DIR', 'event_onsets', 'webcam_biometrics'), '_events_biopac.csv'), SCRIPT_EVENTS),
        ('FaceReader samples', 'samples', fr and os.path.join(fr, 'Kubios_Samples.csv'), SCRIPT_VIDEO_SAMPLES),
        ('webcam samples', 'samples', wc and os.path.join(wc, 'Kubios_Samples.csv'), SCRIPT_VIDEO_SAMPLES),
    ]


def read_samples_csv(path):
    """{pid: [(file name, {sample: (start_s, end_s), nan if missing})]} from a Kubios_Samples.csv."""
    out = {}
    with open(path, encoding='utf-8-sig') as f:
        lines = [l.rstrip('\r\n') for l in f if l.strip()]
    for line in lines[1:]:
        parts = line.split(',')
        name, durs = parts[0], {}
        if name.lower().endswith('_eda_trimmed.acq'):
            continue
        for i in range(2, len(parts) - 2, 3):
            label = parts[i].strip()
            try:
                durs[label] = (float(parts[i + 1]), float(parts[i + 2]))
            except ValueError:
                durs[label] = (np.nan, np.nan)
        out.setdefault(pid_of(name), []).append((name, durs))
    return out


def read_events_durations(folder, suffix):
    """{pid: {sample: (onset_s, offset_s)}} from every <id><suffix> in folder."""
    out = {}
    if not folder or not os.path.isdir(folder):
        return None
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith(suffix) or f.lower().startswith('all_participants'):
            continue
        try:
            ev = pd.read_csv(os.path.join(folder, f))
        except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
            continue
        if not {'event', 'onset_s', 'offset_s'} <= set(ev.columns):
            continue
        durs = {}
        for sample, event in EVENT_OF_SAMPLE.items():
            r = ev[ev['event'] == event]
            durs[sample] = ((float(r['onset_s'].iloc[0]), float(r['offset_s'].iloc[0])) if len(r) == 1
                            else (np.nan, np.nan))
        out[f[: -len(suffix)].lower()] = durs
    return out


def durations(windows):
    """{sample: (start, end)} -> {sample: duration_s (nan if missing)}."""
    return {s: (b - a) for s, (a, b) in windows.items()}


def pick_row(pid, source, rows, notes):
    """One windows dict out of several samples rows for a participant (their durations should agree)."""
    if source == 'ECG Kubios samples':
        trimmed = [r for r in rows if r[0].lower().endswith('_physiology_trimmed.acq')]
        if len(rows) > 1:
            notes.append(f"{source}: {len(rows)} rows ({', '.join(r[0] for r in rows)}) - "
                         + (f"using {trimmed[0][0]}" if len(trimmed) == 1 else f"using {rows[0][0]}"))
        return (trimmed[0] if len(trimmed) == 1 else rows[0])[1]
    first = durations(rows[0][1])
    for name, wins in rows[1:]:   # FaceReader: log + .txt; webcam: every variant - same lengths
        d = durations(wins)
        bad = [s for s in SAMPLES if abs(d.get(s, np.nan) - first.get(s, np.nan)) > 1e-3]
        if bad:
            notes.append(f"{source}: rows for {rows[0][0]} and {name} differ in {bad} - "
                         f"rerun {os.path.basename(SCRIPT_VIDEO_SAMPLES)} for {pid}")
    return rows[0][1]


_video_samples_module = None


def video_samples_module():
    """002_create_kubios_samples_video.py, loaded once, so the FaceReader clock conversion uses exactly
    its readers, folders and rules."""
    global _video_samples_module
    if _video_samples_module is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location('kubios_samples_video', SCRIPT_VIDEO_SAMPLES)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _video_samples_module = module
    return _video_samples_module


def facereader_to_real(pid, rows):
    """FaceReader-clock windows -> real time (s since webcam recording start).
    Returns (windows, how, problem): windows=None and problem=reason if it can't be done."""
    m = video_samples_module()
    # the row named after the heart beat log itself (never shifted by --origin first-beat)
    logs = [name for name, _ in rows if not name.lower().endswith('_kubios.txt')]
    if not logs:
        return None, None, "no row for the heart beat log itself in the FaceReader Kubios_Samples.csv"
    name = logs[0]
    wins = dict(rows)[name]
    path = os.path.join(m.FACEREADER_DIR, name)
    if not os.path.isfile(path):
        return None, None, f"heart beat log {name} not found in {m.FACEREADER_DIR}"
    try:
        _, meta = m.read_facereader_log(path)
    except Exception as e:
        return None, None, f"{name} unreadable ({e})"
    mode = m.facereader_mode(meta.get('video'))
    if mode == 'real':
        return wins, 'real-time video - FaceReader time is real time', None
    if mode is None:
        return None, None, f"can't tell which video {name} analysed ('{meta.get('video')}')"
    clock, _ = m.read_frame_clock(pid)
    if clock is None:
        return None, None, f"no {pid}_frame_timestamps.csv in {m.TIMESTAMP_DIRS}"
    fps = meta.get('fps') or (len(clock) - 1) / (clock[-1] - clock[0])   # as 002 does
    frames = np.arange(len(clock))
    real = {s: (float(np.interp(a * fps, frames, clock)), float(np.interp(b * fps, frames, clock)))
            for s, (a, b) in wins.items() if not (np.isnan(a) or np.isnan(b))}
    real.update({s: (np.nan, np.nan) for s, (a, b) in wins.items() if np.isnan(a) or np.isnan(b)})
    return real, f'converted from FaceReader time (frame / {fps:.4f} fps) via the frame timestamps', None


def check_block_durations(cfg, pids=None, verbose=True):
    """Compare Kubios block durations across all sources. Returns ({pid: [warnings]}, [global notes]).
    pids: participants to report on (default: everyone in any source)."""
    data, global_notes = {}, []
    for source, kind, where, script in source_paths(cfg):
        if kind == 'samples':
            if not where or not os.path.isfile(where):
                global_notes.append(f"{source}: {where or '(folder not set in config.py)'} not found - "
                                    f"run {os.path.basename(script)} first; this source is not checked")
                continue
            data[source] = read_samples_csv(where)
        else:
            folder, suffix = where
            found = read_events_durations(folder, suffix)
            if found is None:
                global_notes.append(f"{source}: folder {folder} not found - run {os.path.basename(script)} first")
                continue
            if not found:
                global_notes.append(f"{source}: no *{suffix} in {folder} - run {os.path.basename(script)} first")
            data[source] = found
    script_of = {s: sc for s, _, _, sc in source_paths(cfg)}

    everyone = sorted({p for d in data.values() for p in d})
    pids = sorted({p.lower() for p in pids}) if pids is not None else everyone
    warnings = {}
    if verbose:
        print(f"\nBlock duration check (Kubios blocks must last the same in ECG, FaceReader and webcam; "
              f"tolerance {TOLERANCE_S} s; FaceReader compared in real time - see block_duration_check.py)")
        for n in global_notes:
            print(f"  [WARNING] {n}")
    for pid in pids:
        notes, infos, durs = [], [], {}
        for source in data:
            rows = data[source].get(pid)
            if rows is None:
                notes.append(f"no {source} for {pid} yet - run {os.path.basename(script_of[source])}")
                continue
            wins = pick_row(pid, source, rows, notes) if isinstance(rows, list) else rows
            if source == 'FaceReader samples':
                real, how, problem = facereader_to_real(pid, rows)
                if problem:
                    notes.append(f"FaceReader samples not compared: {problem} - can't convert its clock to real time")
                    continue
                own = durations(wins)
                diffs = {s: own[s] - (b - a) for s, (a, b) in real.items()
                         if not np.isnan(own.get(s, np.nan)) and not np.isnan(b - a)}
                if diffs and max(abs(v) for v in diffs.values()) > 0.01:
                    worst = max(diffs, key=lambda s: abs(diffs[s]))
                    infos.append(f"FaceReader's own clock makes blocks up to {diffs[worst]:+.2f} s longer/shorter "
                                 f"({worst}) - expected (camera frame rate varies), not a mismatch")
                wins = real
            durs[source] = durations(wins)
        ref = next((s for s in ('ECG Kubios samples', 'BIOPAC events') if s in durs), None)
        if ref is None:
            notes.append("no ECG Kubios samples or BIOPAC events - nothing to compare against")
        elif len(durs) < 2:
            notes.append(f"only {ref} available - nothing to compare it with")
        else:
            for sample in SAMPLES:
                r = durs[ref].get(sample, np.nan)
                if np.isnan(r):
                    notes.append(f"{sample} missing in {ref}")
                    continue
                for source, d in durs.items():
                    if source == ref:
                        continue
                    v = d.get(sample, np.nan)
                    tol = TOLERANCE_S
                    if np.isnan(v):
                        notes.append(f"{sample} missing in {source}")
                    elif abs(v - r) > tol:
                        notes.append(f"{sample} lasts {v:.2f} s in {source} but {r:.2f} s in {ref} "
                                     f"({v - r:+.2f} s) - HRV for this block is not comparable")
        if verbose:
            if notes:
                for n in notes:
                    print(f"  [WARNING] {pid}: {n}")
            else:
                print(f"  {pid}: all {len(durs)} sources agree ({', '.join(durs)})")
            for n in infos:
                print(f"  note: {pid}: {n}")
        if notes:
            warnings[pid] = notes
    return warnings, global_notes
