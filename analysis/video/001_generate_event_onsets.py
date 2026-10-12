
# %%
"""
001_generate_event_onsets.py

Extracts experiment event onsets/offsets from PsychoPy data files and gives
them as frame numbers and times in each participant's webcam video, for
lining up with FaceReader output.

Events written (one row each, in chronological order):
  Baseline
  <Valence> Induction   first video onset -> last video offset of the block
  <Valence> Video <n>   each video in the block (stimulus name in `stimulus`)
  <Valence> Recovery

TWO RECORDING FORMATS
---------------------
The format of each PsychoPy data file is detected from its columns.

1. Current sessions ("png2avi", e.g. i4155, r4755)
   The webcam saved PNG frames, turned into <id>_realtime_30fps.avi (older runs:
   <id>_facereader.avi) by 000_convert_png_to_avi.py --method realtime, which rebuilds the
   video on the real timeline.
   PsychoPy logs stim_onset_since_rec_start (and ..._offset_...): seconds
   since recording start, on the same clock as the webcam frames.
     onset       stim_onset_since_rec_start, logged at routine start
     offset      <routine>.stopped + clock_gap, where
                 clock_gap = stim_onset_since_rec_start - <routine>.started
                 (both logged at routine start, so this is the offset between
                 the webcam clock and globalClock for that row).
                 NOT stim_offset_since_rec_start: for videos it is logged in
                 End Routine code, which runs after video.stop() has unloaded
                 the movie (~3 s), so it is ~3 s after the video really ended.
                 <routine>.stopped is stamped as soon as the routine ends.
                 (Do not use video.stopped either - it is stamped on the next
                 screen flip, i.e. when the NEXT routine starts.)
   Because that AVI is built so that AVI time == time since recording start:
       AVI frame  = round(onset_s * FPS)
       video time = AVI frame / FPS

2. Older sessions ("legacy_avi", e.g. e5510, g2313, n2026, p7259, s0943)
   The recorder wrote frames straight into <id>_recording.avi, one AVI frame
   per row of <id>_frame_timestamps.csv. The frame rate stored in the AVI
   (e.g. 30.002) is NOT the rate the camera really ran at (e.g. 30.05), so
   time in the video drifts away from real time (about 1.4 s by the last
   recovery period for g2313). So for these sessions:
     onset       time_since_recording_start, logged at routine start (same
                 clock as the frame timestamps)
     offset      onset + (<routine>.stopped - <routine>.started). Offsets were
                 not logged; the duration comes from PsychoPy's globalClock,
                 which runs at the same rate, so this is accurate to a few ms.
     AVI frame   the row of the timestamps file captured closest to the event
     video time  AVI frame / the frame rate stored in the AVI (read with ffprobe)
                 - this is the time FaceReader reports for that frame

FOR FACEREADER, ALWAYS USE THE VIDEO COLUMNS
--------------------------------------------
  onset_avi_frame / offset_avi_frame          frame number in the video
  onset_video_time_s / offset_video_time_s    time in the video, as FaceReader reports it
  onset_video_hhmmss / offset_video_hhmmss    the same, as hh:mm:ss.sss
onset_s / offset_s are real seconds since the recording started. For current
sessions they match the video time; for older sessions they do not.

FOR rPPG (WebcamBiometrics eval), USE onset_s / offset_s - THE OPPOSITE RULE
-----------------------------------------------------------------------------
The rPPG eval extracts from a 1:1 video (000_convert_png_to_avi.py --method 1to1, or an older
<id>_recording.avi) WITH the per-frame timestamps, so its time axis is real seconds since recording
start = onset_s / offset_s. The *_video_time_s and *_avi_frame columns are positions in the
FaceReader AVI and are wrong for rPPG (up to ~1.4 s off for older sessions). The eval reads this
file directly (eval/py/datasets/sussex.py) and estimate_offsets.py matches its events by name to
002_create_webcam_events_biopac.py's BIOPAC events.

Other columns:
  onset_webcam_frame / offset_webcam_frame      PNG frame number (current sessions)
                                                or timestamps frame_index (older sessions)
  onset_frame_diff_ms / offset_frame_diff_ms    how far from the event that frame was captured
      (current sessions: the offset frame is looked up in <id>_frame_timestamps.csv;
       it is left blank if that file is not available, because PsychoPy's logged
       stim_offset_frame_idx belongs to the late logged offset)
  recording_format, video_file

Do NOT use <routine>.started / .stopped directly as times in the video: they
are on PsychoPy's globalClock, not the webcam clock. They are only used via
durations (older sessions) or the per-row clock_gap (current sessions), and
to check that the two clocks stay in step.

Each block's valence comes from conditionOrder (neg_first / pos_first) and is
cross-checked against the video file names (N... = negative, P... = positive).

HOW TO RUN
----------
Paths are read from config.py, the nearest one in this folder or above it
(normally analysis/config.py, which is not tracked by git). It needs:
  PSYCHOPY_DATA_DIR      PsychoPy data files     <id>_<expName>_<date>.csv
  WEBCAM_DIR             current sessions        <id>_frame_timestamps.csv (optional, for checks)
  VIDEO_DIR (optional)   <id>_realtime_30fps.avi   (optional, file name only; also looked for in
                                                 WEBCAM_DIR and OLD_WEBCAM_DIR)
  OLD_WEBCAM_DIR         older sessions          <id>_frame_timestamps.csv and <id>_recording.avi
                                                 (both required)
  FACEREADER_ONSETS_DIR  where results are written
<id> is everything before the first "_" in the file name, ignoring upper/lower
case (participant IDs are written in lower case). Then run the last cell. It
writes, into FACEREADER_ONSETS_DIR:
  <id>_video_events.csv                 one file per participant
  all_participants_video_events.csv     everyone, with a `participant` column

Data files with neither set of timing columns (e.g. sessions without a
camera) and empty files from aborted runs are ignored. A participant with more
than one usable data file (e.g. a restarted session) is skipped and reported,
so you can move the wrong file out and rerun. One participant failing does not
stop the rest. A summary at the end lists who is OK, who has warnings, and who
failed or was skipped.

Older sessions need ffprobe (installed with ffmpeg) to read the AVI frame rate.
"""

import glob
import importlib.util
import json
import os
import shutil
import subprocess

import numpy as np
import pandas as pd

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


def find_participants(data_dir, webcam_dir, old_webcam_dir, video_dir=None):
    """Return (sessions, problems).

    sessions: participant ID -> dict(format, exp, frames, video, note)
    problems: 'id: reason' strings for participants that were skipped."""
    for label, folder in (('PSYCHOPY_DATA_DIR', data_dir), ('WEBCAM_DIR', webcam_dir),
                          ('OLD_WEBCAM_DIR', old_webcam_dir)):
        if not os.path.isdir(folder):
            raise FileNotFoundError(f"{label} '{folder}' does not exist (drive not connected?)")

    data_files = {pid: [p for p in paths if not p.endswith('_biometrics.csv')]
                  for pid, paths in index_by_participant(data_dir, '*_*Psychopy*.csv').items()}
    data_files = {pid: paths for pid, paths in data_files.items() if paths}
    new_frames = index_by_participant(webcam_dir, '*_*frame_timestamps.csv')
    # realtime AVIs from 000_convert_png_to_avi.py --method realtime (older runs: *_facereader.avi)
    new_videos = {}
    for folder, pattern in ((video_dir or webcam_dir, '*_realtime_*fps.avi'), (webcam_dir, '*_realtime_*fps.avi'),
                            (old_webcam_dir, '*_realtime_*fps.avi'), (webcam_dir, '*_facereader.avi')):
        if not os.path.isdir(folder):
            continue
        for pid, paths in index_by_participant(folder, pattern).items():
            new_videos.setdefault(pid, paths)
    old_frames = index_by_participant(old_webcam_dir, '*_*frame_timestamps.csv')
    old_videos = index_by_participant(old_webcam_dir, '*_recording.avi')

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
                note = f"no {pid}_frame_timestamps.csv in {webcam_dir} - skipping the recording-coverage check"
            elif len(frames) > 1:
                note = f"several timestamps files ({names(frames)}) - skipping the recording-coverage check"
            sessions[pid] = {'format': fmt, 'exp': exp_path, 'note': note,
                             'frames': frames[0] if len(frames) == 1 else None,
                             'video': videos[0] if len(videos) == 1 else None}
        else:
            frames, videos = old_frames.get(pid, []), old_videos.get(pid, [])
            if len(frames) != 1 or len(videos) != 1:
                problems.append(f"{pid}: older session needs exactly one <id>_frame_timestamps.csv and one "
                                f"<id>_recording.avi in {old_webcam_dir} (found {len(frames)} and {len(videos)})")
                continue
            sessions[pid] = {'format': fmt, 'exp': exp_path, 'note': None,
                             'frames': frames[0], 'video': videos[0]}
    return dict(sorted(sessions.items())), problems


def run_all(data_dir, webcam_dir, old_webcam_dir, out_dir, fps=30.0, video_dir=None):
    sessions, problems = find_participants(data_dir, webcam_dir, old_webcam_dir, video_dir)
    os.makedirs(out_dir, exist_ok=True)
    print(f"Found {len(sessions)} participant(s) to process in {data_dir}")
    for p in problems:
        print(f"[SKIPPED] {p}")

    all_events, summary = [], []
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
        n_warnings = len(warnings) + (s['note'] is not None)
        status = 'OK' if not n_warnings else f'{n_warnings} warning(s) - see log above'
        summary.append((pid, f"{status} [{s['format']}]"))

    if all_events:
        combined_path = os.path.join(out_dir, 'all_participants_video_events.csv')
        pd.concat(all_events, ignore_index=True).to_csv(combined_path, index=False)
        print(f"\nCombined events for {len(all_events)} participant(s) saved to {combined_path}")

    print(f"\n{'=' * 70}\nSummary")
    for pid, status in summary:
        print(f"  {pid:>10} : {status}")
    for p in problems:
        pid, reason = p.split(': ', 1)
        print(f"  {pid:>10} : SKIPPED - {reason}")
    return summary, problems


CONFIG_VARIABLES = ('PSYCHOPY_DATA_DIR', 'WEBCAM_DIR', 'OLD_WEBCAM_DIR', 'FACEREADER_ONSETS_DIR')


def load_config():
    """Load the nearest config.py in this script's folder or any folder above it."""
    start = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    folder = start
    while not os.path.isfile(os.path.join(folder, 'config.py')):
        parent = os.path.dirname(folder)
        if parent == folder:
            raise FileNotFoundError(f"No config.py found in {start} or any folder above it")
        folder = parent
    path = os.path.join(folder, 'config.py')
    # Load by path, so a different `config` module imported earlier in this session can't be used by mistake
    spec = importlib.util.spec_from_file_location('video_config', path)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    missing = [v for v in CONFIG_VARIABLES if not hasattr(config, v)]
    if missing:
        raise AttributeError(f"{path} is missing {missing}. Add e.g.\n"
                             f'  WEBCAM_DIR            = r"D:\\Biosignals2"\n'
                             f'  OLD_WEBCAM_DIR        = os.path.join(SERVER_ROOT, "video")\n'
                             f'  FACEREADER_ONSETS_DIR = os.path.join(SERVER_ROOT, "event_onsets", "facereader_video")')
    print(f"Paths from {path}:")
    for v in CONFIG_VARIABLES:
        print(f"  {v:22} = {getattr(config, v)}")
    return config


# %%
FPS = 30.0   # current sessions: must match --fps of 000_convert_png_to_avi.py --method realtime (default 30)

if __name__ == '__main__':
    cfg = load_config()
    run_all(str(cfg.PSYCHOPY_DATA_DIR), str(cfg.WEBCAM_DIR), str(cfg.OLD_WEBCAM_DIR),
            str(cfg.FACEREADER_ONSETS_DIR), FPS, video_dir=getattr(cfg, 'VIDEO_DIR', None))
