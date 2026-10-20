
# %%
"""
001_generate_event_onsets.py
============================
One script for every experiment-event table the video analysis needs. It replaces the old
001_generate_event_onsets.py and 002_create_webcam_events_biopac.py (now in archive/) and
writes exactly the same output files, so 002_run_webcam_biometrics.py and
WebcamBiometrics/eval (sussex.py, estimate_offsets.py) work unchanged.

It runs four steps, in this order:

  1. VIDEO   PsychoPy data -> event onsets/offsets on the WEBCAM clock
             -> FACEREADER_ONSETS_DIR/<id>_video_events.csv  (+ all_participants_video_events.csv)
  2. BIOPAC  trigger channels of the trimmed .acq -> the same events on the ECG (Kubios) clock
             -> WEBCAM_EVENTS_DIR/<id>_events_biopac.csv
  3. CHECK   pairs the two files by event name and checks they describe the same session
             -> WEBCAM_EVENTS_DIR/all_participants_event_crosscheck.csv
  4. DURATIONS checks each Kubios block (baseline, inductions, recoveries) lasts the same in the
             ECG Kubios_Samples.csv, these event files, and the FaceReader / webcam Kubios_Samples.csv
             (shared check in analysis/kubios/block_duration_check.py, also run by
             kubios/001_create_kubios_samples.py and kubios/002_create_kubios_samples_video.py, so
             whichever script runs last catches a mismatch). Warns if a file isn't made yet.

Both files use the same event names, in chronological order:
  Baseline
  <Valence> Induction   first video onset -> last video offset of the block
  <Valence> Video <n>   each video of the block, numbered by onset time (stimulus name in `stimulus`)
  <Valence> Recovery

STEP 1 - VIDEO (webcam clock)
-----------------------------
The recording format is detected from the PsychoPy data file's columns.

1. Current sessions ("png2avi", e.g. i4155, r4755)
   The webcam saved PNG frames, turned into <id>_realtime_30fps.avi (older runs:
   <id>_facereader.avi) by 000_convert_png_to_avi.py --method realtime, which rebuilds the
   video on the real timeline.
     onset       stim_onset_since_rec_start, logged at routine start
     offset      <routine>.stopped + clock_gap, where
                 clock_gap = stim_onset_since_rec_start - <routine>.started.
                 NOT stim_offset_since_rec_start: for videos it is logged in End Routine
                 code after video.stop() has unloaded the movie (~3 s late).
                 (Not video.stopped either - it is stamped on the next routine's first flip.)
     AVI frame = round(onset_s * FPS), video time = AVI frame / FPS

2. Older sessions ("legacy_avi", e.g. e5510, g2313, n2026, p7259, s0943)
   Frames were written straight into <id>_recording.avi, one AVI frame per row of
   <id>_frame_timestamps.csv. The AVI's stored frame rate is NOT the camera's real rate, so
   video time drifts from real time (~1.4 s by the last recovery for g2313).
     onset       time_since_recording_start, logged at routine start
     offset      onset + (<routine>.stopped - <routine>.started)
     AVI frame   the timestamps row captured closest to the event
     video time  AVI frame / the AVI's stored frame rate (read with ffprobe)

Which columns to use:
  FaceReader   onset_avi_frame / onset_video_time_s / onset_video_hhmmss (and offset_...)
  rPPG / ECG   onset_s / offset_s - real seconds since recording start (the eval extracts from a
               1:1 video WITH per-frame timestamps). The *_video_time_s / *_avi_frame columns
               are FaceReader-AVI positions and are up to ~1.4 s off for older sessions.
Other columns: onset/offset_webcam_frame, onset/offset_frame_diff_ms, recording_format, video_file.

Each block's valence comes from conditionOrder and is cross-checked against the video file
names (N... = negative, P... = positive).

STEP 2 - BIOPAC (ECG / Kubios clock)
------------------------------------
Times are seconds from the start of the TRIMMED recording (the .acq files Kubios is run on).
Each of the 7 trigger channels (baseline_trig, Nstim1_trig, Nstim2_trig, Nrecovery_trig,
Pstim1_trig, Pstim2_trig, Precovery) must hold exactly one HIGH pulse (> 1 V, >= 1 s):
pulse start = onset, pulse end = offset. Videos are numbered by onset order (which clip comes
first is counterbalanced), so they line up with step 1. Columns: event, channel, onset_s,
offset_s, duration_s.
In the PsychoPy script the trigger port is reset ('RR') when the routine ends, so a pulse's end
should match <routine>.stopped, i.e. step 1's offset_s - step 3 checks this.
A participant is skipped (nothing written) if a channel is missing, has 0 or >1 pulses, is still
HIGH at the end of the file, or if Baseline is not the first event.
RAW_PHYSIOLOGY_DIR must be the trimmed 'experimental_protocol_duration' folder; any other
folder stops the script (--allow-untrimmed to override), because untrimmed times are on the
wrong clock for Kubios.

STEP 3 - CHECK (both files)
---------------------------
For every participant with both files:
  * every event is present in both (a participant with only one file is reported)
  * clock offset: (BIOPAC onset - video onset) should be the same for every event, apart from a
    slow linear drift. Events more than ONSET_RESIDUAL_WARN_S from that line are flagged (late-
    logged onset on one side, or a mismatched event). The drift itself is reported and flagged
    above DRIFT_WARN_MS_PER_10MIN.
  * durations agree within DURATION_DIFF_WARN_S (catches late offsets and swapped videos)
  * Video 1 / Video 2 of a block are not swapped between the files
  * the valence order (negative first or positive first) is the same in both files
Output: one row per participant and event, with implied_offset_s, residual_ms, duration_diff_s
and a `flags` column. estimate_offsets.py does the real offset estimation; this step is the
early warning that it will be fed inconsistent events.

HOW TO RUN
----------
Paths come from the nearest config.py in this folder or above it (repo root, not in git):
  PSYCHOPY_DATA_DIR, WEBCAM_PNG_EXTERNAL_DIR, VIDEO_BOX_DIR, FACEREADER_ONSETS_DIR   (step 1)
  VIDEO_EXTERNAL_DIR                                                    (step 1, optional)
  RAW_PHYSIOLOGY_DIR                                                    (step 2)
  WEBCAM_EVENTS_DIR (else SERVER_ROOT/event_onsets/webcam_biometrics)   (steps 2, 3, 4)
  FACEREADER_RESULTS_DIR, WEBCAM_HR_DIR (else under SERVER_ROOT)        (step 4)

  python 001_generate_event_onsets.py                       new / changed participants only
  python 001_generate_event_onsets.py --rerun S9686 x1234   also redo these (any case)
  python 001_generate_event_onsets.py --rerun-all           redo everyone
  python 001_generate_event_onsets.py --steps video check   run only some steps (video biopac check durations)
  python 001_generate_event_onsets.py --allow-untrimmed     don't stop on a non-trimmed .acq folder
When running as cells, set STEPS / RERUN_ALL / RERUN_PARTICIPANTS in the last cell.

Participants whose output already exists are not re-run, unless one of their inputs (PsychoPy
file, timestamps file, older sessions' AVI, .acq) was modified after it. Changes to THIS SCRIPT
are not detected: after changing timing logic, use --rerun-all. Steps 3 and 4 always re-check
everyone. One participant failing never stops the rest. The script ends with one summary table
(video / biopac / check / durations per participant) and exits with code 1 if anything failed,
was skipped or was flagged.

Needs: pandas, numpy, bioread (step 2: pip install bioread), ffprobe (older sessions: ffmpeg).
"""

import argparse
import csv
import glob
import importlib.util
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 - VIDEO: PsychoPy data -> events on the webcam clock
# ══════════════════════════════════════════════════════════════════════════════

ROUTINES = ['baseline', 'stimuli', 'stim_recovery']
BASE_COLUMNS = ['conditionOrder', *[f'{r}.started' for r in ROUTINES]]
FORMAT_COLUMNS = {  # checked in this order
    'png2avi': BASE_COLUMNS + [
        'stim_onset_since_rec_start', 'stim_offset_since_rec_start',
        'stim_onset_frame_idx', 'stim_offset_frame_idx',
        'stim_onset_frame_diff', 'stim_offset_frame_diff',
    ],
    'legacy_avi': BASE_COLUMNS + [f'{r}.stopped' for r in ROUTINES] + ['time_since_recording_start'],
}
BLOCK_VALENCES = {'neg_first': ['negative', 'positive'], 'pos_first': ['positive', 'negative']}
VIDEO_PREFIX_VALENCE = {'N': 'negative', 'P': 'positive'}
MIN_USABLE_CAMERA_FPS = 20
MAX_FRAME_DIFF_MS = 100


def seconds_to_hhmmss(s):
    if s is None or pd.isna(s):
        return None
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    return f"{h:02d}:{m:02d}:{s % 60:06.3f}"


def to_frame(t, fps):
    """AVI frame shown at time t (AVI frame k is at k / fps)."""
    return int(np.floor(t * fps + 0.5))


def detect_format(columns):
    for fmt, required in FORMAT_COLUMNS.items():
        if all(c in columns for c in required):
            return fmt
    return None


# ── Events ────────────────────────────────────────────────────────────────────

def timing_rows(exp, fmt, warnings):
    """One dict per baseline/stimuli/stim_recovery row, with onset/offset in
    seconds since the webcam recording started."""
    rows = []
    for row_num, row in exp.iterrows():
        routines = [r for r in ROUTINES if pd.notna(row[f'{r}.started'])]
        if not routines:
            continue
        if len(routines) > 1:
            raise ValueError(f"Data row {row_num} has timings for several routines {routines}; can't tell them apart.")
        routine = routines[0]
        logged_offset = None
        if fmt == 'png2avi':
            onset = row['stim_onset_since_rec_start']
            logged_offset = row['stim_offset_since_rec_start']
            stopped = row.get(f'{routine}.stopped')
            if pd.notna(onset) and stopped is not None and pd.notna(stopped):
                # routine end on globalClock, moved onto the webcam clock with this row's clock gap
                offset = stopped + (onset - row[f'{routine}.started'])
            else:
                offset = logged_offset
                if pd.notna(logged_offset):
                    warnings.append(f"{routine} (data row {row_num}) has no {routine}.stopped - using the logged "
                                    f"stim_offset_since_rec_start, which is ~3 s late for videos")
        else:
            onset = row['time_since_recording_start']
            offset = onset + row[f'{routine}.stopped'] - row[f'{routine}.started']
        if pd.isna(onset) or pd.isna(offset):
            warnings.append(f"{routine} (data row {row_num}) has no onset/offset - skipped (routine did not finish?)")
            continue
        rows.append({'routine': routine, 'row': row, 'onset': float(onset), 'offset': float(offset),
                     'clock_gap': float(onset - row[f'{routine}.started']),
                     'logged_offset': float(logged_offset) if logged_offset is not None and pd.notna(logged_offset) else None,
                     'offset_corrected': logged_offset is not None and float(offset) != float(logged_offset)})
    return rows


def make_event(name, valence, block, first, last, stimulus=None):
    """Event from `first` timing row's onset to `last` timing row's offset."""
    return {'event': name, 'valence': valence, 'block': block, 'stimulus': stimulus,
            'onset_s': first['onset'], 'offset_s': last['offset'], '_first': first, '_last': last}


def stimulus_name(row):
    path = row.get('stim_path')
    return os.path.splitext(os.path.basename(path))[0] if isinstance(path, str) else None


def block_events(videos, valence, block, warnings):
    label = valence.capitalize()
    events = [make_event(f'{label} Induction', valence, block, videos[0], videos[-1])]
    for n, video in enumerate(videos, 1):
        name = stimulus_name(video['row'])
        looks_like = VIDEO_PREFIX_VALENCE.get(name[:1].upper()) if name else None
        if looks_like and looks_like != valence:
            warnings.append(f"Block {block} is {valence} according to conditionOrder, but video "
                            f"'{name}' looks {looks_like}. Check conditionOrder was set correctly.")
        events.append(make_event(f'{label} Video {n}', valence, block, video, video, stimulus=name))
    return events


def extract_events(exp, fmt):
    """Return (events, warnings, clock_gaps) from a PsychoPy data DataFrame."""
    orders = exp['conditionOrder'].dropna().unique()
    if len(orders) != 1 or orders[0] not in BLOCK_VALENCES:
        raise ValueError(f"Expected a single conditionOrder of {list(BLOCK_VALENCES)}, found {list(orders)}")
    valences = BLOCK_VALENCES[orders[0]]

    warnings = []
    timings = timing_rows(exp, fmt, warnings)
    events, videos = [], []   # videos: stimuli rows of the block in progress
    n_blocks = n_baseline = 0

    for timing in timings:
        if timing['routine'] == 'baseline':
            n_baseline += 1
            events.append(make_event('Baseline', None, None, timing, timing))
        elif timing['routine'] == 'stimuli':
            videos.append(timing)
        else:  # stim_recovery closes the block
            if n_blocks == len(valences):
                raise ValueError(f"Found more than {len(valences)} recovery periods")
            valence = valences[n_blocks]
            n_blocks += 1
            if videos:
                events.extend(block_events(videos, valence, n_blocks, warnings))
            else:
                warnings.append(f"Block {n_blocks} ({valence}) has a recovery period but no videos")
            events.append(make_event(f'{valence.capitalize()} Recovery', valence, n_blocks, timing, timing))
            videos = []

    if videos:
        if n_blocks == len(valences):
            raise ValueError("Found videos after the last recovery period")
        valence = valences[n_blocks]
        n_blocks += 1
        warnings.append(f"Block {n_blocks} ({valence}) has no recovery period (experiment stopped early?)")
        events.extend(block_events(videos, valence, n_blocks, warnings))

    if n_baseline != 1:
        warnings.append(f"Expected 1 baseline, found {n_baseline}")
    if n_blocks != len(valences):
        warnings.append(f"Expected {len(valences)} blocks, found {n_blocks}")
    return events, warnings, [t['clock_gap'] for t in timings]


# ── Video frames ──────────────────────────────────────────────────────────────

def nearest_frame(frames, target):
    """(frame_index, |time difference| in s) of the frame captured closest to `target`."""
    t = frames['time_since_recording_start'].to_numpy(dtype=float)
    j = int(np.searchsorted(t, target))
    if j == len(t) or (j > 0 and target - t[j - 1] <= t[j] - target):
        j -= 1
    return int(frames['frame_index'].iloc[j]), abs(t[j] - target)


def add_frames_png2avi(events, fps, frames=None):
    """Current sessions: the AVI timeline equals time since recording start.

    Onset PNG frames come from PsychoPy's logged stim_onset_frame_idx. The logged
    stim_offset_frame_idx belongs to the (late) logged offset, so when the offset was
    corrected the PNG frame is looked up in the timestamps file instead, or left blank."""
    for e in events:
        for which, key in (('onset', '_first'), ('offset', '_last')):
            timing = e[key]
            row = timing['row']
            k = to_frame(e[f'{which}_s'], fps)
            e[f'{which}_avi_frame'] = k
            e[f'{which}_video_time_s'] = k / fps
            if which == 'offset' and timing.get('offset_corrected'):
                if frames is not None:
                    idx, diff = nearest_frame(frames, e['offset_s'])
                    e['offset_webcam_frame'], e['offset_frame_diff_ms'] = idx, 1000 * diff
                else:
                    e['offset_webcam_frame'], e['offset_frame_diff_ms'] = None, None
            else:
                e[f'{which}_webcam_frame'] = int(row[f'stim_{which}_frame_idx'])
                e[f'{which}_frame_diff_ms'] = 1000 * row[f'stim_{which}_frame_diff']


def add_frames_legacy(events, frames, video_fps):
    """Older sessions: AVI frame k is row k of the timestamps file; video time uses the AVI's stored fps."""
    t = frames['time_since_recording_start'].to_numpy(dtype=float)
    frame_index = frames['frame_index'].to_numpy()
    for e in events:
        for which in ('onset', 'offset'):
            target = e[f'{which}_s']
            j = int(np.searchsorted(t, target))
            if j == len(t) or (j > 0 and target - t[j - 1] <= t[j] - target):
                j -= 1
            e[f'{which}_avi_frame'] = j
            e[f'{which}_video_time_s'] = j / video_fps
            e[f'{which}_webcam_frame'] = int(frame_index[j])
            e[f'{which}_frame_diff_ms'] = 1000 * abs(t[j] - target)


def read_video_info(path):
    """Return (stored frame rate, frame count or None) of a video, using ffprobe."""
    if shutil.which('ffprobe') is None:
        raise RuntimeError("ffprobe not found on PATH (it is installed with ffmpeg: winget install ffmpeg)")
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=avg_frame_rate,r_frame_rate,nb_frames', '-of', 'json', path],
        capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe could not read {path}: {result.stderr.strip()}")
    streams = json.loads(result.stdout).get('streams') or []
    if not streams:
        raise RuntimeError(f"No video stream found in {path}")
    stream = streams[0]
    rate = stream.get('avg_frame_rate')
    if not rate or rate == '0/0':
        rate = stream['r_frame_rate']
    num, den = (float(x) for x in rate.split('/'))
    n_frames = stream.get('nb_frames')
    return num / den, int(n_frames) if str(n_frames).isdigit() else None


def check_legacy_recording(frames, video_fps, n_video_frames):
    """Checks that an older recording's AVI lines up with its timestamps file."""
    warnings = []
    t = frames['time_since_recording_start'].to_numpy(dtype=float)
    if len(t) < 2 or not (np.diff(t) > 0).all():
        raise ValueError("time_since_recording_start in the timestamps file is not strictly increasing")
    frame_index = frames['frame_index'].to_numpy()
    if frame_index[0] != 0 or not (np.diff(frame_index) == 1).all():
        warnings.append("frame_index in the timestamps file is not contiguous from 0 - AVI frame numbers may not line up")
    if n_video_frames is not None and n_video_frames != len(t):
        warnings.append(f"AVI has {n_video_frames} frames but the timestamps file has {len(t)} rows - "
                        f"AVI frame numbers may not line up with the timestamps")
    camera_fps = (len(t) - 1) / (t[-1] - t[0])
    drift = np.abs(np.arange(len(t)) / video_fps - t).max()
    print(f"Older recording: AVI stored at {video_fps:.3f} fps, camera really ran at {camera_fps:.3f} fps; "
          f"video time is up to {drift:.2f} s away from real time (corrected via frame numbers)")
    if camera_fps < MIN_USABLE_CAMERA_FPS:
        warnings.append(f"camera only captured {camera_fps:.1f} frames per second - "
                        f"this recording is probably not usable for FaceReader")
    return warnings


# ── Checks and output ─────────────────────────────────────────────────────────

def check_events(events, clock_gaps, frames, fps):
    """Sanity checks. Returns a list of warning strings."""
    warnings = []
    for e in events:
        if e['onset_s'] < 0 or e['offset_s'] < e['onset_s']:
            warnings.append(f"{e['event']}: impossible times (onset {e['onset_s']:.3f}, offset {e['offset_s']:.3f})")
    def worst_diff(e):
        diffs = [d for d in (e['onset_frame_diff_ms'], e['offset_frame_diff_ms']) if d is not None and pd.notna(d)]
        return max(diffs) if diffs else 0.0
    far = [f"{e['event']} ({worst_diff(e):.0f} ms)" for e in events if worst_diff(e) > MAX_FRAME_DIFF_MS]
    if far:
        warnings.append(f"Nearest webcam frame more than {MAX_FRAME_DIFF_MS} ms from the event "
                        f"(camera gaps or dropped frames): {', '.join(far)}")
    singles = [e for e in events if 'Induction' not in e['event']]
    if any(b['onset_s'] < a['offset_s'] for a, b in zip(singles, singles[1:])):
        warnings.append("Events overlap or are out of order - check the data file")

    # Both clocks run at the same rate, so (webcam-clock time - globalClock time) should be the
    # same for every event, apart from a few ms between routine start and its code running.
    if clock_gaps:
        spread = max(clock_gaps) - min(clock_gaps)
        print(f"Clock check: webcam-clock minus globalClock varies by {spread * 1000:.1f} ms across events")
        if spread > 0.05:
            warnings.append(f"Webcam clock and PsychoPy globalClock drift by {spread * 1000:.0f} ms across "
                            f"events - timing columns may not come from the same session")

    # Current sessions: how far the logged stim_offset_since_rec_start was from the routine end.
    # ~3 s for videos is the known End Routine delay; baseline/recovery should agree within a few ms.
    lags = {}
    for e in events:
        if 'Induction' in e['event']:
            continue
        t = e['_last']
        if t.get('logged_offset') is not None:
            lags[e['event']] = t['logged_offset'] - e['offset_s']
    if lags:
        video_lags = [v for k, v in lags.items() if 'Video' in k]
        if video_lags:
            print(f"Offset correction: logged video offsets were {min(video_lags):.2f}-{max(video_lags):.2f} s "
                  f"after the video ended (now using <routine>.stopped)")
        odd = [f"{k} ({v:+.3f} s)" for k, v in lags.items() if 'Video' not in k and abs(v) > 0.05]
        if odd:
            warnings.append(f"Logged offset differs from <routine>.stopped by more than 50 ms for: {', '.join(odd)}")

    if frames is not None:
        last_t = frames['time_since_recording_start'].max()
        late = [e['event'] for e in events if e['offset_s'] > last_t + 1 / fps]
        if late:
            warnings.append(f"Recording timestamps end at {last_t:.3f} s, before these events end: {late} "
                            f"(timestamps not saved after a crash, or wrong frames file?)")
    return warnings


def to_dataframe(events, fmt, video_path):
    rows = []
    for e in events:
        rows.append({
            'event': e['event'],
            'valence': e['valence'],
            'block': e['block'],
            'stimulus': e['stimulus'],
            'onset_s': round(e['onset_s'], 4),
            'offset_s': round(e['offset_s'], 4),
            'duration_s': round(e['offset_s'] - e['onset_s'], 3),
            'onset_video_time_s': round(e['onset_video_time_s'], 4),
            'offset_video_time_s': round(e['offset_video_time_s'], 4),
            'onset_video_hhmmss': seconds_to_hhmmss(e['onset_video_time_s']),
            'offset_video_hhmmss': seconds_to_hhmmss(e['offset_video_time_s']),
            'onset_avi_frame': e['onset_avi_frame'],
            'offset_avi_frame': e['offset_avi_frame'],
            'onset_webcam_frame': e['onset_webcam_frame'],
            'offset_webcam_frame': e['offset_webcam_frame'],
            'onset_frame_diff_ms': None if e['onset_frame_diff_ms'] is None else round(e['onset_frame_diff_ms'], 1),
            'offset_frame_diff_ms': None if e['offset_frame_diff_ms'] is None else round(e['offset_frame_diff_ms'], 1),
            'recording_format': fmt,
            'video_file': os.path.basename(video_path) if video_path else None,
        })
    return pd.DataFrame(rows)


def main(exp_path, out_path, frames_path=None, fps=30.0, video_path=None):
    """Process one participant. `fps` is the AVI frame rate for current sessions;
    older sessions need `frames_path` and `video_path` and use the AVI's own frame rate."""
    print(f"Experiment data : {exp_path}")
    exp = pd.read_csv(exp_path)
    fmt = detect_format(exp.columns)
    if fmt is None:
        raise ValueError("Data file has neither the current timing columns (stim_onset_since_rec_start, ...) "
                         "nor the older ones (time_since_recording_start and <routine>.stopped)")
    print(f"Recording format: {fmt}")
    frames = pd.read_csv(frames_path) if frames_path else None

    events, warnings, clock_gaps = extract_events(exp, fmt)
    if fmt == 'png2avi':
        video_fps = fps
        add_frames_png2avi(events, fps, frames)
    else:
        if frames is None or video_path is None:
            raise ValueError("Older sessions need both <id>_frame_timestamps.csv and <id>_recording.avi")
        video_fps, n_video_frames = read_video_info(video_path)
        warnings += check_legacy_recording(frames, video_fps, n_video_frames)
        add_frames_legacy(events, frames, video_fps)
    warnings += check_events(events, clock_gaps, frames, video_fps)

    df = to_dataframe(events, fmt, video_path)
    print(f"\n=== Events in video time ({os.path.basename(video_path) if video_path else 'AVI'} "
          f"at {video_fps:.3f} fps) ===\n")
    print(df[['event', 'stimulus', 'onset_s', 'duration_s', 'onset_video_hhmmss',
              'onset_avi_frame', 'offset_avi_frame']].to_string(index=False))
    for w in warnings:
        print(f"[WARNING] {w}")

    df.to_csv(out_path, index=False)
    print(f"\nSaved to {out_path}")
    return df, warnings


# ── Batch ─────────────────────────────────────────────────────────────────────

def participant_id(name):
    """Participant ID = everything before the first '_' in a file name, in lower case."""
    return name.split('_', 1)[0].lower()


def index_by_participant(folder, pattern):
    found = {}
    for path in sorted(glob.glob(os.path.join(folder, pattern))):
        found.setdefault(participant_id(os.path.basename(path)), []).append(path)
    return found


def file_format(csv_path):
    """Recording format of a PsychoPy data file, or None (no timing columns, empty or unreadable)."""
    try:
        return detect_format(pd.read_csv(csv_path, nrows=0).columns)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        return None


def names(paths):
    return ', '.join(os.path.basename(p) for p in paths)


def find_participants(data_dir, webcam_png_external_dir, video_box_dir, video_external_dir=None):
    """Return (sessions, problems).

    sessions: participant ID -> dict(format, exp, frames, video, note)
    problems: 'id: reason' strings for participants that were skipped."""
    for label, folder in (('PSYCHOPY_DATA_DIR', data_dir), ('WEBCAM_PNG_EXTERNAL_DIR', webcam_png_external_dir),
                          ('VIDEO_BOX_DIR', video_box_dir)):
        if not os.path.isdir(folder):
            raise FileNotFoundError(f"{label} '{folder}' does not exist (drive not connected?)")

    data_files = {pid: [p for p in paths if not p.endswith('_biometrics.csv')]
                  for pid, paths in index_by_participant(data_dir, '*_*Psychopy*.csv').items()}
    data_files = {pid: paths for pid, paths in data_files.items() if paths}
    new_frames = index_by_participant(webcam_png_external_dir, '*_*frame_timestamps.csv')
    # realtime AVIs from 000_convert_png_to_avi.py --method realtime (older runs: *_facereader.avi)
    new_videos = {}
    for folder, pattern in ((video_external_dir or webcam_png_external_dir, '*_realtime_*fps.avi'), (webcam_png_external_dir, '*_realtime_*fps.avi'),
                            (video_box_dir, '*_realtime_*fps.avi'), (webcam_png_external_dir, '*_facereader.avi')):
        if not os.path.isdir(folder):
            continue
        for pid, paths in index_by_participant(folder, pattern).items():
            new_videos.setdefault(pid, paths)
    old_frames = index_by_participant(video_box_dir, '*_*frame_timestamps.csv')
    old_videos = index_by_participant(video_box_dir, '*_recording.avi')

    sessions, problems = {}, []
    for pid in sorted((set(new_frames) | set(old_frames)) - set(data_files)):
        problems.append(f"{pid}: webcam timestamps found but no PsychoPy data file (<id>_...Psychopy...csv) in {data_dir}")

    for pid, paths in data_files.items():
        usable = [(p, fmt) for p in paths if (fmt := file_format(p))]
        if not usable:
            problems.append(f"{pid}: no data file with event timing columns - session without webcam "
                            f"logging, or an empty file ({names(paths)})")
            continue
        if len(usable) > 1:
            problems.append(f"{pid}: {len(usable)} usable data files, can't tell which to use - "
                            f"move the wrong one out ({names(p for p, _ in usable)})")
            continue
        exp_path, fmt = usable[0]

        if fmt == 'png2avi':
            frames, videos = new_frames.get(pid, []), new_videos.get(pid, [])
            note = None
            if not frames:
                note = f"no {pid}_frame_timestamps.csv in {webcam_png_external_dir} - skipping the recording-coverage check"
            elif len(frames) > 1:
                note = f"several timestamps files ({names(frames)}) - skipping the recording-coverage check"
            sessions[pid] = {'format': fmt, 'exp': exp_path, 'note': note,
                             'frames': frames[0] if len(frames) == 1 else None,
                             'video': videos[0] if len(videos) == 1 else None}
        else:
            frames, videos = old_frames.get(pid, []), old_videos.get(pid, [])
            if len(frames) != 1 or len(videos) != 1:
                problems.append(f"{pid}: older session needs exactly one <id>_frame_timestamps.csv and one "
                                f"<id>_recording.avi in {video_box_dir} (found {len(frames)} and {len(videos)})")
                continue
            sessions[pid] = {'format': fmt, 'exp': exp_path, 'note': None,
                             'frames': frames[0], 'video': videos[0]}
    return dict(sorted(sessions.items())), problems


def read_existing_onsets(path):
    """An existing <id>_video_events.csv, or None if it is missing, empty or unreadable."""
    if not os.path.isfile(path):
        return None
    try:
        df = pd.read_csv(path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        return None
    return df if len(df) else None


def newer_inputs(session, out_path):
    """Input files of a session (data file, timestamps file, older sessions' AVI) modified after `out_path`."""
    inputs = [session['exp'], session['frames']]
    if session['format'] == 'legacy_avi':   # onsets depend on the AVI's stored frame rate
        inputs.append(session['video'])
    out_time = os.path.getmtime(out_path)
    return [p for p in inputs if p and os.path.isfile(p) and os.path.getmtime(p) > out_time]


def run_all(data_dir, webcam_png_external_dir, video_box_dir, out_dir, fps=30.0, video_external_dir=None, rerun_all=False,
            rerun=()):
    """Process every participant. Unless `rerun_all`, participants that already have a readable
    <id>_video_events.csv in `out_dir` are not re-run (except those listed in `rerun`, or whose
    inputs changed since); their existing file goes into the combined CSV."""
    sessions, problems = find_participants(data_dir, webcam_png_external_dir, video_box_dir, video_external_dir)
    os.makedirs(out_dir, exist_ok=True)
    rerun = {participant_id(p) for p in rerun}
    known = set(sessions) | {p.split(': ', 1)[0] for p in problems}
    for pid in sorted(rerun - known):
        print(f"[WARNING] --rerun / RERUN_PARTICIPANTS lists '{pid}', but no data for that participant was found")

    all_events, summary = [], []
    if not rerun_all:
        for pid in list(sessions):
            if pid in rerun:
                print(f"[RE-RUN] {pid}: listed in --rerun / RERUN_PARTICIPANTS")
                continue
            out_path = os.path.join(out_dir, f'{pid}_video_events.csv')
            existing = read_existing_onsets(out_path)
            if existing is None:
                continue
            newer = newer_inputs(sessions[pid], out_path)
            if newer:
                print(f"[RE-RUN] {pid}: {names(newer)} changed after {os.path.basename(out_path)} was written")
                continue
            del sessions[pid]
            existing.insert(0, 'participant', pid)
            all_events.append(existing)
            summary.append((pid, 'already done - kept existing file'))
    n_existing = len(all_events)

    print(f"Found {len(sessions)} participant(s) to process in {data_dir}"
          + (f" ({n_existing} already done, skipped - use --rerun-all to redo them)" if n_existing else ""))
    for p in problems:
        print(f"[SKIPPED] {p}")

    for pid, s in sessions.items():
        print(f"\n{'=' * 70}\nParticipant {pid} ({s['format']})\n{'=' * 70}")
        if s['note']:
            print(f"[WARNING] {s['note']}")
        try:
            df, warnings = main(s['exp'], os.path.join(out_dir, f'{pid}_video_events.csv'),
                                s['frames'], fps, s['video'])
        except Exception as e:
            print(f"[ERROR] {pid} failed: {e}")
            summary.append((pid, f'FAILED: {e}'))
            continue
        df.insert(0, 'participant', pid)
        all_events.append(df)
        all_warnings = ([s['note']] if s['note'] else []) + warnings
        status = 'OK' if not all_warnings else f"{len(all_warnings)} warning(s): {'; '.join(all_warnings)}"
        summary.append((pid, f"{status} [{s['format']}]"))

    if all_events:
        combined_path = os.path.join(out_dir, 'all_participants_video_events.csv')
        combined = pd.concat(all_events, ignore_index=True)
        # stable sort keeps each participant's events in their original order
        combined = combined.sort_values('participant', kind='stable').reset_index(drop=True)
        combined.to_csv(combined_path, index=False)
        print(f"\nCombined events for {len(all_events)} participant(s) "
              f"({n_existing} from existing files) saved to {combined_path}")

    print(f"\n{'=' * 70}\nSummary")
    for pid, status in sorted(summary):
        print(f"  {pid:>10} : {status}")
    for p in problems:
        pid, reason = p.split(': ', 1)
        print(f"  {pid:>10} : SKIPPED - {reason}")
    return summary, problems



# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 - BIOPAC: trigger channels of the trimmed .acq -> events on the ECG clock
# ══════════════════════════════════════════════════════════════════════════════

TRIMMED_FOLDER_NAME = "experimental_protocol_duration"

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
    """Nearest config.py in this folder or above (the repo-root config.py)."""
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


def up_to_date(out_path, acq_path):
    """True if out_path exists, has at least one event row, and is newer than the .acq file."""
    if not os.path.isfile(out_path) or os.path.getmtime(acq_path) > os.path.getmtime(out_path):
        return False
    with open(out_path, newline="") as f:
        return sum(1 for _ in f) > 1   # header + events


def count_short_pulses(channel, min_s=0.05):
    """HIGH periods between min_s and MIN_PULSE_S - ignored as noise, but worth knowing about."""
    signal = np.asarray(channel.data, dtype=float)
    sr = channel.samples_per_second
    edges = np.diff(np.concatenate([[0], (signal > THRESHOLD).astype(np.int8), [0]]))
    lengths = (np.where(edges == -1)[0] - np.where(edges == 1)[0]) / sr
    return int(((lengths >= min_s) & (lengths < MIN_PULSE_S)).sum())


def biopac_extra_checks(acq):
    """Non-fatal checks on the trigger channels. Returns warning strings."""
    warnings = []
    by_name = {ch.name: ch for ch in acq.channels}
    for name in CHANNELS:
        ch = by_name[name]
        if ch.samples_per_second < 100:
            warnings.append(f'"{name}" is sampled at only {ch.samples_per_second:g} Hz - event times '
                            f'are only accurate to {1000 / ch.samples_per_second:.0f} ms')
        n = count_short_pulses(ch)
        if n:
            warnings.append(f'"{name}" has {n} short HIGH blip(s) (< {MIN_PULSE_S:g} s) that were ignored - '
                            f'check the trigger cable/port if this is unusual')
    return warnings


def run_biopac(acq_dir, out_dir, rerun_all=False, rerun=(), allow_untrimmed=False):
    """Step 2 for every participant. Returns {pid: (level, message)}."""
    if os.path.basename(os.path.normpath(acq_dir)) != TRIMMED_FOLDER_NAME:
        msg = (f"RAW_PHYSIOLOGY_DIR = {acq_dir} is not the trimmed '{TRIMMED_FOLDER_NAME}' folder "
               f"(the one Kubios is run on), so event times would be on the wrong clock.")
        if not allow_untrimmed:
            raise RuntimeError(msg + " Fix config.py, or use --allow-untrimmed if you are sure.")
        print(f"[WARNING] {msg} Continuing because of --allow-untrimmed.")
    if not os.path.isdir(acq_dir):
        raise FileNotFoundError(f"RAW_PHYSIOLOGY_DIR '{acq_dir}' does not exist (drive not connected?)")
    try:
        import bioread
    except ImportError:
        raise RuntimeError("the 'bioread' package is not installed (pip install bioread)") from None
    files = sorted(glob.glob(os.path.join(acq_dir, "*" + ACQ_SUFFIX)))
    if not files:
        raise FileNotFoundError(f"No *{ACQ_SUFFIX} in {acq_dir}")
    os.makedirs(out_dir, exist_ok=True)

    rerun = {participant_id(p) for p in rerun}
    pids = [os.path.basename(p)[: -len(ACQ_SUFFIX)].lower() for p in files]
    for pid in sorted(rerun - set(pids)):
        print(f"[WARNING] --rerun lists '{pid}', but there is no {pid}{ACQ_SUFFIX} in {acq_dir}")

    status, done = {}, []
    for pid in sorted({p for p in pids if pids.count(p) > 1}):
        status[pid] = ('skip', f"several .acq files for this participant (differing only in upper/lower case): "
                               f"{names(p for p, q in zip(files, pids) if q == pid)}")
        print(f"[SKIPPED] {pid}: {status[pid][1]}")
    for path, pid in zip(files, pids):
        if pid in status:
            continue
        out = os.path.join(out_dir, f"{pid}_events_biopac.csv")
        if not rerun_all and pid not in rerun and up_to_date(out, path):
            done.append(pid)
            status[pid] = ('done', 'already done - kept existing file')
            continue
        print(f"\n{pid}  ({os.path.basename(path)})")
        if os.path.isfile(out):
            print("  [RE-RUN] " + ("listed in --rerun" if pid in rerun else
                                   "--rerun-all" if rerun_all else
                                   "existing file is empty or older than the .acq"))
        stale = (f" The old {os.path.basename(out)} is still there and is probably out of date - "
                 f"move it away so estimate_offsets.py does not use it." if os.path.isfile(out) else "")
        try:
            acq = bioread.read(path)
            events, problems = events_for(acq)
        except Exception as e:
            print(f"  [ERROR] could not read {os.path.basename(path)}: {e}.{stale}")
            status[pid] = ('fail', f"FAILED: {e}.{stale}")
            continue
        if problems:
            for p in problems:
                print(f"  [SKIPPED] {p}")
            if stale:
                print(f"  [WARNING]{stale}")
            status[pid] = ('skip', '; '.join(problems) + stale)
            continue
        warnings = biopac_extra_checks(acq)
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["event", "channel", "onset_s", "offset_s", "duration_s"])
            for name, ch, on, off in events:
                w.writerow([name, ch, f"{on:.4f}", f"{off:.4f}", f"{off - on:.3f}"])
                print(f"  {name:20s} {ch:26s} {on:9.3f} -> {off:9.3f}  ({off - on:6.1f} s)")
        for x in warnings:
            print(f"  [WARNING] {x}")
        status[pid] = ('warn', '; '.join(warnings)) if warnings else ('ok', 'OK')

    if done:
        print(f"\nAlready done, not re-run ({len(done)}; use --rerun ID or --rerun-all to redo): {', '.join(done)}")
    n_written = sum(level in ('ok', 'warn') for level, _ in status.values())
    print(f"\nWritten {n_written} to {out_dir}")
    return status


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 - CHECK: do the video and BIOPAC events describe the same session?
# ══════════════════════════════════════════════════════════════════════════════

EXPECTED_EVENTS = ['Baseline',
                   'Negative Induction', 'Negative Video 1', 'Negative Video 2', 'Negative Recovery',
                   'Positive Induction', 'Positive Video 1', 'Positive Video 2', 'Positive Recovery']
ONSET_RESIDUAL_WARN_S = 0.10     # an event's clock offset this far from the others -> flagged
DURATION_DIFF_WARN_S = 0.25      # video vs BIOPAC duration differing by more -> flagged
DRIFT_WARN_MS_PER_10MIN = 100    # ECG vs webcam clock running apart faster than this -> flagged
CROSSCHECK_FILE = 'all_participants_event_crosscheck.csv'


def read_events_csv(path):
    """An events CSV with event/onset_s/offset_s columns and at least one row, else None."""
    try:
        df = pd.read_csv(path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        return None
    if not {'event', 'onset_s', 'offset_s'} <= set(df.columns) or not len(df):
        return None
    return df


def event_files(folder, suffix):
    """participant ID -> [paths] for <id><suffix> in folder (combined all_participants files excluded)."""
    found = {}
    for path in sorted(glob.glob(os.path.join(folder, '*' + suffix))):
        base = os.path.basename(path)
        if base.lower().startswith('all_participants'):
            continue
        found.setdefault(base[: -len(suffix)].lower(), []).append(path)
    return found


def block_order(df):
    """Valences in the order their first event starts, e.g. ['Negative', 'Positive']."""
    first = {}
    for event, onset in zip(df['event'], df['onset_s']):
        for valence in ('Negative', 'Positive'):
            if str(event).startswith(valence):
                first[valence] = min(first.get(valence, np.inf), float(onset))
    return sorted(first, key=first.get)


def robust_line(x, y):
    """(slope, intercept) of a line through (x, y) that one bad point can't drag: median of pairwise
    slopes (Theil-Sen), intercept = median of y - slope * x."""
    slopes = [(y[j] - y[i]) / (x[j] - x[i]) for i in range(len(x)) for j in range(i + 1, len(x)) if x[j] != x[i]]
    slope = float(np.median(slopes)) if slopes else 0.0
    return slope, float(np.median(y - slope * x))


def crosscheck_participant(pid, video, biopac):
    """Compare one participant's video and BIOPAC events. Returns (rows, warnings)."""
    warnings, flags = [], {}

    def flag(event, text):
        flags.setdefault(event, []).append(text)

    for label, df in (('video', video), ('BIOPAC', biopac)):
        dup = sorted(df['event'][df['event'].duplicated()].unique())
        if dup:
            warnings.append(f"the {label} file lists {dup} more than once - can't pair events")
        odd = [e for e in df['event'] if e not in EXPECTED_EVENTS]
        if odd:
            warnings.append(f"the {label} file has unexpected event names {odd}")
    if any('more than once' in w for w in warnings):
        return [], warnings

    v, b = video.set_index('event'), biopac.set_index('event')
    only_v = [e for e in EXPECTED_EVENTS if e in v.index and e not in b.index]
    only_b = [e for e in EXPECTED_EVENTS if e in b.index and e not in v.index]
    neither = [e for e in EXPECTED_EVENTS if e not in v.index and e not in b.index]
    if only_v:
        warnings.append(f"only in the video file (not in BIOPAC): {only_v}")
    if only_b:
        warnings.append(f"only in the BIOPAC file (not in video): {only_b}")
    if neither:
        warnings.append(f"missing from both files: {neither}")
    order_v, order_b = block_order(video), block_order(biopac)
    if order_v and order_b and order_v != order_b:
        warnings.append(f"valence order differs: video file {order_v} (from conditionOrder), BIOPAC {order_b} "
                        f"(from trigger channels) - wrong conditionOrder, or wrong .acq file?")

    common = [e for e in EXPECTED_EVENTS if e in v.index and e in b.index]
    singles = [e for e in common if 'Induction' not in e]
    dur_v = {e: float(v.loc[e, 'offset_s'] - v.loc[e, 'onset_s']) for e in common}
    dur_b = {e: float(b.loc[e, 'offset_s'] - b.loc[e, 'onset_s']) for e in common}
    residual = {}

    if len(singles) >= 2:
        t_v = v.loc[singles, 'onset_s'].astype(float).to_numpy()
        gap = b.loc[singles, 'onset_s'].astype(float).to_numpy() - t_v
        slope, intercept = robust_line(t_v, gap) if len(singles) >= 3 else (0.0, float(np.median(gap)))
        residual = dict(zip(singles, gap - (intercept + slope * t_v)))
        drift = slope * 600 * 1000
        print(f"  {pid}: ECG minus webcam clock = {np.median(gap):.3f} s, drift {drift:+.0f} ms per 10 min, "
              f"onsets within {1000 * max(abs(r) for r in residual.values()):.0f} ms of that line "
              f"({len(singles)} events)")
        for e, r in residual.items():
            if abs(r) > ONSET_RESIDUAL_WARN_S:
                flag(e, f"onset is {1000 * r:+.0f} ms off the other events' clock offset")
        if abs(drift) > DRIFT_WARN_MS_PER_10MIN:
            warnings.append(f"the two clocks drift apart by {drift:+.0f} ms per 10 min (more than "
                            f"{DRIFT_WARN_MS_PER_10MIN}) - check the webcam timestamps / wrong session?")
    else:
        warnings.append("fewer than 2 events in both files - can't check the clock offset")

    for e in common:
        diff = dur_b[e] - dur_v[e]
        if abs(diff) > DURATION_DIFF_WARN_S:
            flag(e, f"duration {dur_b[e]:.2f} s in BIOPAC vs {dur_v[e]:.2f} s in video ({diff:+.2f} s)")
    for valence in ('Negative', 'Positive'):
        e1, e2 = f'{valence} Video 1', f'{valence} Video 2'
        if e1 in common and e2 in common:
            straight = abs(dur_v[e1] - dur_b[e1]) + abs(dur_v[e2] - dur_b[e2])
            crossed = abs(dur_v[e1] - dur_b[e2]) + abs(dur_v[e2] - dur_b[e1])
            if crossed + DURATION_DIFF_WARN_S < straight:
                for e in (e1, e2):
                    flag(e, "durations fit the OTHER video of the block better - videos swapped or mis-numbered?")
    for e, texts in flags.items():
        warnings.append(f"{e}: {'; '.join(texts)}")

    rows = []
    for e in common:
        rows.append({
            'participant': pid, 'event': e,
            'video_onset_s': round(float(v.loc[e, 'onset_s']), 4),
            'biopac_onset_s': round(float(b.loc[e, 'onset_s']), 4),
            'video_offset_s': round(float(v.loc[e, 'offset_s']), 4),
            'biopac_offset_s': round(float(b.loc[e, 'offset_s']), 4),
            'implied_offset_s': round(float(b.loc[e, 'onset_s'] - v.loc[e, 'onset_s']), 4),
            'residual_ms': round(1000 * residual[e], 1) if e in residual else None,
            'video_duration_s': round(dur_v[e], 3), 'biopac_duration_s': round(dur_b[e], 3),
            'duration_diff_s': round(dur_b[e] - dur_v[e], 3),
            'flags': '; '.join(flags.get(e, [])),
        })
    rows += [{'participant': pid, 'event': e, 'flags': 'only in the video file'} for e in only_v]
    rows += [{'participant': pid, 'event': e, 'flags': 'only in the BIOPAC file'} for e in only_b]
    return rows, warnings


def run_crosscheck(video_dir, biopac_dir):
    """Step 3 for every participant with an events file in either folder. Returns {pid: (level, message)}."""
    for label, folder in (('FACEREADER_ONSETS_DIR', video_dir), ('WEBCAM_EVENTS_DIR', biopac_dir)):
        if not os.path.isdir(folder):
            raise FileNotFoundError(f"{label} '{folder}' does not exist (drive not connected?)")
    vfiles = event_files(video_dir, '_video_events.csv')
    bfiles = event_files(biopac_dir, '_events_biopac.csv')
    status, rows = {}, []
    for pid in sorted(set(vfiles) | set(bfiles)):
        vp, bp = vfiles.get(pid, []), bfiles.get(pid, [])
        if len(vp) > 1 or len(bp) > 1:
            status[pid] = ('skip', f"several event files differing only in upper/lower case: {names(vp + bp)}")
        elif not vp:
            status[pid] = ('skip', f"no {pid}_video_events.csv in {video_dir} (only BIOPAC events)")
        elif not bp:
            status[pid] = ('skip', f"no {pid}_events_biopac.csv in {biopac_dir} (only video events)")
        else:
            video, biopac = read_events_csv(vp[0]), read_events_csv(bp[0])
            if video is None or biopac is None:
                status[pid] = ('fail', f"could not read {names(p for p, df in ((vp[0], video), (bp[0], biopac)) if df is None)} "
                                       f"(empty, or missing event/onset_s/offset_s columns)")
            else:
                r, w = crosscheck_participant(pid, video, biopac)
                rows += r
                for x in w:
                    print(f"  [WARNING] {pid}: {x}")
                status[pid] = ('warn', '; '.join(w)) if w else ('ok', 'OK')
        if status[pid][0] in ('skip', 'fail'):
            print(f"  [{'SKIPPED' if status[pid][0] == 'skip' else 'ERROR'}] {pid}: {status[pid][1]}")
    if rows:
        out = os.path.join(biopac_dir, CROSSCHECK_FILE)
        pd.DataFrame(rows).to_csv(out, index=False)
        print(f"\nCross-check for {len({r['participant'] for r in rows})} participant(s) saved to {out}")
    return status


# ══════════════════════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════════════════════

ALL_STEPS = ('video', 'biopac', 'check', 'durations')
STEP_CONFIG = {
    'video': ('PSYCHOPY_DATA_DIR', 'WEBCAM_PNG_EXTERNAL_DIR', 'VIDEO_BOX_DIR', 'FACEREADER_ONSETS_DIR'),
    'biopac': ('RAW_PHYSIOLOGY_DIR',),
    'check': ('FACEREADER_ONSETS_DIR',),
    'durations': ('FACEREADER_ONSETS_DIR', 'RAW_PHYSIOLOGY_DIR'),
}
DURATION_CHECK_MODULE = os.path.join(os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd(),
                                     '..', 'kubios', 'block_duration_check.py')


def run_duration_check(cfg):
    """Step 4: Kubios block durations, ECG vs video events vs FaceReader/webcam samples (shared with the
    kubios scripts, see analysis/kubios/block_duration_check.py). Returns {pid: (level, message)}."""
    path = os.path.normpath(DURATION_CHECK_MODULE)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{path} not found - it holds the duration check shared with the kubios scripts")
    spec = importlib.util.spec_from_file_location('block_duration_check', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    warnings, global_notes = module.check_block_durations(cfg)
    everyone = event_files(str(cfg.FACEREADER_ONSETS_DIR), '_video_events.csv')
    everyone.update(event_files(webcam_events_dir(cfg), '_events_biopac.csv'))
    # a source file that doesn't exist yet means the check is incomplete for everyone - don't call that OK
    partial = [n.split(':', 1)[0] for n in global_notes]
    status = {pid: ('warn', f"agree, but not checked against {', '.join(partial)} (not made yet - see above)")
                   if partial else ('ok', 'OK') for pid in everyone}
    status.update({pid: ('warn', '; '.join(w)) for pid, w in warnings.items()})
    return status


def load_config(steps):
    """Load the nearest config.py in this script's folder or any folder above it, and check it has
    every path the chosen steps need."""
    start = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    folder = start
    while not os.path.isfile(os.path.join(folder, 'config.py')):
        parent = os.path.dirname(folder)
        if parent == folder:
            raise FileNotFoundError(f"No config.py found in {start} or any folder above it")
        folder = parent
    path = os.path.join(folder, 'config.py')
    # Load by path, so a different `config` module imported earlier in this session can't be used by mistake
    spec = importlib.util.spec_from_file_location('event_onsets_config', path)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    needed = list(dict.fromkeys(v for s in steps for v in STEP_CONFIG[s]))
    missing = [v for v in needed if not hasattr(config, v)]
    if {'biopac', 'check'} & set(steps) and not (hasattr(config, 'WEBCAM_EVENTS_DIR') or hasattr(config, 'SERVER_ROOT')):
        missing.append('WEBCAM_EVENTS_DIR (or SERVER_ROOT)')
    if missing:
        raise AttributeError(f"{path} is missing {missing}, needed for step(s) {list(steps)}")
    print(f"Paths from {path}:")
    for v in needed + (['WEBCAM_EVENTS_DIR'] if {'biopac', 'check'} & set(steps) else []):
        value = webcam_events_dir(config) if v == 'WEBCAM_EVENTS_DIR' else getattr(config, v)
        print(f"  {v:24} = {value}")
    return config


def webcam_events_dir(cfg):
    return str(getattr(cfg, 'WEBCAM_EVENTS_DIR', None)
               or os.path.join(str(cfg.SERVER_ROOT), 'event_onsets', 'webcam_biometrics'))


def video_status(summary, problems, out_dir):
    """Turn step 1's (summary, problems) into {pid: (level, message)}."""
    status = {}
    for pid, text in summary:
        if text.startswith('already done'):
            status[pid] = ('done', text)
        elif text.startswith('OK'):
            status[pid] = ('ok', 'OK')
        elif text.startswith('FAILED'):
            old = os.path.join(out_dir, f'{pid}_video_events.csv')
            stale = (f" The old {os.path.basename(old)} is still there and is probably out of date - "
                     f"move it away so later scripts don't use it." if os.path.isfile(old) else "")
            status[pid] = ('fail', text + stale)
        else:
            status[pid] = ('warn', text)
    for p in problems:
        pid, reason = p.split(': ', 1)
        status[pid] = ('skip', reason)
    return status


LEVEL_LABEL = {'ok': 'OK', 'done': 'done', 'warn': 'WARN', 'skip': 'SKIP', 'fail': 'FAIL'}


def print_final_summary(steps, results, step_errors):
    print(f"\n{'#' * 78}\n# SUMMARY  (OK = written now, done = kept existing file, '-' = no input found)\n{'#' * 78}")
    pids = sorted({pid for r in results.values() for pid in r})
    print(f"  {'participant':>12}  " + "  ".join(f"{s:<9}" for s in steps))
    for pid in pids:
        cells = [LEVEL_LABEL[results[s][pid][0]] if s in results and pid in results[s]
                 else ('ERROR' if s in step_errors else '-') for s in steps]
        print(f"  {pid:>12}  " + "  ".join(f"{c:<9}" for c in cells))
    details = [(pid, s, results[s][pid]) for pid in pids for s in steps
               if s in results and pid in results[s] and results[s][pid][0] in ('warn', 'skip', 'fail')]
    if details:
        print("\nNeeds a look:")
        for pid, s, (level, msg) in details:
            print(f"  {pid:>12}  {s:<9} {LEVEL_LABEL[level]:<5} {msg}")
    for s, err in step_errors.items():
        print(f"\n[ERROR] step '{s}' did not run: {err}")


def run_pipeline(steps=ALL_STEPS, rerun_all=False, rerun=(), allow_untrimmed=False, fps=30.0):
    """Run the chosen steps in order. Returns 0 if everything is OK/done, else 1."""
    unknown = [s for s in steps if s not in ALL_STEPS]
    if unknown:
        raise ValueError(f"Unknown step(s) {unknown}; choose from {list(ALL_STEPS)}")
    steps = [s for s in ALL_STEPS if s in steps]
    cfg = load_config(steps)
    results, step_errors = {}, {}

    def banner(text):
        print(f"\n{'#' * 78}\n# {text}\n{'#' * 78}")

    if 'video' in steps:
        banner("STEP 1  VIDEO   PsychoPy -> events on the webcam clock")
        out_dir = str(cfg.FACEREADER_ONSETS_DIR)
        try:
            summary, problems = run_all(str(cfg.PSYCHOPY_DATA_DIR), str(cfg.WEBCAM_PNG_EXTERNAL_DIR),
                                        str(cfg.VIDEO_BOX_DIR), out_dir, fps,
                                        video_external_dir=getattr(cfg, 'VIDEO_EXTERNAL_DIR', None),
                                        rerun_all=rerun_all, rerun=rerun)
            results['video'] = video_status(summary, problems, out_dir)
        except Exception as e:
            step_errors['video'] = str(e)
            print(f"[ERROR] step 1 stopped: {e}")
    if 'biopac' in steps:
        banner("STEP 2  BIOPAC  trigger channels -> events on the ECG (Kubios) clock")
        try:
            results['biopac'] = run_biopac(str(cfg.RAW_PHYSIOLOGY_DIR), webcam_events_dir(cfg),
                                           rerun_all=rerun_all, rerun=rerun, allow_untrimmed=allow_untrimmed)
        except Exception as e:
            step_errors['biopac'] = str(e)
            print(f"[ERROR] step 2 stopped: {e}")
    if 'check' in steps:
        banner("STEP 3  CHECK   video events vs BIOPAC events, per participant")
        if step_errors:
            print(f"[WARNING] step(s) {list(step_errors)} failed - checking whatever event files already exist")
        try:
            results['check'] = run_crosscheck(str(cfg.FACEREADER_ONSETS_DIR), webcam_events_dir(cfg))
        except Exception as e:
            step_errors['check'] = str(e)
            print(f"[ERROR] step 3 stopped: {e}")
    if 'durations' in steps:
        banner("STEP 4  DURATIONS  Kubios blocks: same length for ECG, video events, FaceReader and webcam?")
        try:
            results['durations'] = run_duration_check(cfg)
        except Exception as e:
            step_errors['durations'] = str(e)
            print(f"[ERROR] step 4 stopped: {e}")

    print_final_summary(steps, results, step_errors)
    bad = step_errors or any(level in ('warn', 'skip', 'fail') for r in results.values() for level, _ in r.values())
    return 1 if bad else 0


# %%
FPS = 30.0   # current sessions: must match --fps of 000_convert_png_to_avi.py --method realtime (default 30)

STEPS = ['video', 'biopac', 'check', 'durations']   # when running as cells: which steps to run
RERUN_ALL = False                      # when running as cells: True = redo everyone
RERUN_PARTICIPANTS = []                # when running as cells: e.g. ['s9686'] to redo just them
ALLOW_UNTRIMMED = False                # when running as cells: True = accept a non-trimmed .acq folder

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Video (webcam-clock) and BIOPAC (ECG-clock) event onsets, "
                                                 "plus a cross-check of the two.")
    parser.add_argument('--steps', nargs='+', choices=ALL_STEPS, default=None,
                        help="steps to run (default: all four)")
    parser.add_argument('--rerun', nargs='+', default=[], metavar='ID',
                        help="participant ID(s) to redo even if they already have output (any case)")
    parser.add_argument('--rerun-all', action='store_true', help="redo every participant")
    parser.add_argument('--allow-untrimmed', action='store_true',
                        help="don't stop if RAW_PHYSIOLOGY_DIR is not the trimmed folder")
    args, _ = parser.parse_known_args()   # ignore extra arguments added when run as cells in an IDE
    exit_code = run_pipeline(args.steps or STEPS, rerun_all=RERUN_ALL or args.rerun_all,
                             rerun=[*RERUN_PARTICIPANTS, *args.rerun],
                             allow_untrimmed=ALLOW_UNTRIMMED or args.allow_untrimmed, fps=FPS)
    if not hasattr(sys, 'ps1') and 'ipykernel' not in sys.modules:   # don't kill an interactive session
        sys.exit(exit_code)
