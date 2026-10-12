r"""
000_convert_png_to_avi.py
=========================
Turns the PNG webcam frames recorded by the PsychoPy experiment into ONE of three kinds of video.
You must choose which with --method; the method is written into the output file name, so the two
can never be mixed up.

  --method realtime   ->  <id>_realtime_30fps.avi  (+ <id>_realtime_30fps_frame_map.csv)
      FOR FACEREADER. Uncompressed AVI (rawvideo bgr24, FaceReader's BI_RGB format) at a constant
      frame rate. AVI frame k shows the PNG captured closest to k/fps, so PNGs are REPEATED where
      the camera paused and SKIPPED where it ran fast. Result: video time == time since recording
      start, so FaceReader output lines up with experiment events directly by time.
      NOT FOR rPPG: repeated/skipped frames distort the pulse signal, and frame k is not PNG k.

  --method 1to1       ->  <id>_1to1_ffv1.avi  (+ a copy of <id>_frame_timestamps.csv next to it)
      THE ONE VIDEO FOR BOTH HEART-RATE ANALYSES: WebcamBiometrics (003) AND FaceReader read this
      same file, so they analyse exactly the same frames. Every PNG exactly once, in order,
      nothing repeated or dropped, so video frame i == PNG frame i == row i of the timestamps CSV.
      Stored LOSSLESSLY as FFV1 (pixels bit-identical to the PNGs, RGB, no chroma subsampling)
      at a constant nominal frame rate = the measured average fps (~5.5 GB for ~19 min).
      WebcamBiometrics extracts it WITH --timestamps <id>_frame_timestamps.csv, so the real
      capture time of every frame is used; FaceReader reports times as frame / nominal fps and
      the HRV scripts (005/006) map them back through the same timestamps CSV.
      Why .avi and not .mkv (what this method made until 7 Oct 2026): FaceReader can't read a bit
      rate from an .mkv, warns "frame rate / bit rate / resolution is too low" on every frame and
      processes it worse (r2433: 24-43% of ECG R-peaks found vs 85-99% for the same frames as
      .avi). WebcamBiometrics gets identical pixels from either. Existing <id>_1to1.mkv files can
      be turned into this .avi with 004_convert_mkv_to_avi.py (no re-encoding).

  --method 1to1-facereader  ->  <id>_1to1_facereader.avi  (+ copy of <id>_frame_timestamps.csv)
      FALLBACK ONLY: the same 1:1 frames uncompressed (rawvideo bgr24, ~30 GB for ~19 min), in
      case a FaceReader installation can't decode FFV1. Not needed while the 1to1 .avi works.

Output folder: VIDEO_DIR from the nearest config.py above this script (the external drive,
D:\Biosignals2_video), else D:\Biosignals2_video, or --output-dir. Videos are working copies (the PNGs are archived on Box).
Existing outputs are never overwritten: a participant that already has the output is skipped,
so an interrupted batch can simply be rerun.

Input (written by the experiment's WebcamRecorder):
  <id>_frames/frame_000000.png, frame_000001.png, ...
  <id>_frame_timestamps.csv   columns include frame_index, time_since_recording_start
The participant ID is everything before the first "_" in the folder/CSV name.

Usage
-----
  Batch (every <id>_frames folder + <id>_frame_timestamps.csv in a folder):
    python 000_convert_png_to_avi.py <data_dir> --method realtime|1to1|1to1-facereader [--output-dir DIR] [--fps 30]
  One participant:
    python 000_convert_png_to_avi.py <frames_dir> <timestamps_csv> --method realtime|1to1|1to1-facereader [--output-dir DIR]

Examples:
  python 000_convert_png_to_avi.py D:\Biosignals2 --method realtime   # FaceReader videos
  python 000_convert_png_to_avi.py D:\Biosignals2 --method 1to1       # rPPG video (ours + FaceReader)
  python 000_convert_png_to_avi.py D:\Biosignals2\i4155_frames D:\Biosignals2\i4155_frame_timestamps.csv --method 1to1

LINING UP FACEREADER RESULTS (realtime videos)
----------------------------------------------
A time in the realtime video equals time_since_recording_start, the same clock as
stim_onset_since_rec_start in the PsychoPy data file (see 001_generate_event_onsets.py), e.g.
onset 125.400 s -> AVI frame round(125.400 * 30) = 3762. To go from a PNG frame number to an AVI
frame, look it up in <output>_frame_map.csv (source_frame_index -> avi_frame). Each AVI frame is
within abs_time_error of its true capture time (pilot: ~9 ms mean, ~90 ms in camera gaps).

To check a 1to1 video is bit-identical to its PNGs: 05_verify_roundtrip.py <frames_dir> <video>.

Requires ffmpeg on PATH (ffmpeg -version; install: winget install ffmpeg).
"""

import argparse
import bisect
import csv
import filecmp
import importlib.util
import os
import shutil
import subprocess
import sys

import cv2

DEFAULT_OUTPUT_DIR = r"D:\Biosignals2_video"   # external hard drive
METHODS = ("realtime", "1to1", "1to1-facereader")


def output_name(pid, method, fps):
    """The file name says which method made it — the whole point of this script's naming."""
    if method == "realtime":
        return f"{pid}_realtime_{fps:g}fps.avi"
    if method == "1to1-facereader":
        return f"{pid}_1to1_facereader.avi"
    return f"{pid}_1to1_ffv1.avi"


def default_output_dir():
    """VIDEO_DIR from the nearest config.py above this script, else DEFAULT_OUTPUT_DIR."""
    folder = os.path.dirname(os.path.abspath(__file__))
    while True:
        path = os.path.join(folder, "config.py")
        if os.path.isfile(path):
            spec = importlib.util.spec_from_file_location("convert_config", path)
            cfg = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(cfg)
                if hasattr(cfg, "VIDEO_DIR"):
                    return str(cfg.VIDEO_DIR)
            except Exception as e:  # a broken config shouldn't stop a conversion
                print(f"[WARNING] couldn't read {path} ({e}); using {DEFAULT_OUTPUT_DIR}")
            break
        parent = os.path.dirname(folder)
        if parent == folder:
            break
        folder = parent
    return DEFAULT_OUTPUT_DIR


REQUIRED_COLUMNS = ("frame_index", "time_since_recording_start")


def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install it first:\n"
            "  Windows: winget install ffmpeg\n"
            "  or download from https://ffmpeg.org/download.html and add to PATH.\n"
            "Verify with: ffmpeg -version"
        )


def load_timestamps(csv_path):
    """Return a list of (frame_index, time_since_recording_start), sorted by frame index.

    The experiment appends to this CSV at the end of every routine, so after a
    crash it can be shorter than the PNG folder. Frames without a timestamp
    row are left out (a warning is printed in convert())."""
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(
                f"{csv_path} is missing column(s) {missing}; found {reader.fieldnames}. "
                f"Is this a timestamps file from the current experiment version?"
            )
        rows = [(int(r["frame_index"]), float(r["time_since_recording_start"])) for r in reader]

    if len(rows) < 2:
        raise ValueError(f"Not enough rows in {csv_path} to build a video")

    rows.sort()
    indices = [i for i, _ in rows]
    if len(set(indices)) != len(indices):
        raise ValueError(f"Duplicate frame_index values in {csv_path} — timestamps were saved twice?")
    gaps = [(a, b) for a, b in zip(indices, indices[1:]) if b != a + 1]
    if gaps or indices[0] != 0:
        print(f"[WARNING] frame_index is not contiguous from 0 (first={indices[0]}, "
              f"{len(gaps)} gap(s), e.g. {gaps[:3]}). Timing stays correct, but check the recording.")
    times = [t for _, t in rows]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError(f"time_since_recording_start is not strictly increasing in {csv_path}")
    return rows


def build_frame_map(rows, fps):
    """For each output frame k (time k/fps), pick the source frame nearest in time."""
    times = [t for _, t in rows]
    n_out = int(times[-1] * fps) + 1
    frame_map = []
    for k in range(n_out):
        t = k / fps
        j = bisect.bisect_left(times, t)
        if j == len(times) or (j > 0 and t - times[j - 1] <= times[j] - t):
            j -= 1
        frame_map.append((k, t, rows[j][0], times[j]))
    return frame_map


def encode(frames_dir, frame_sequence, fps, width, height, output_path, method):
    """Pipe raw BGR frames (one PNG index per output frame) into ffmpeg."""
    if method in ("realtime", "1to1-facereader"):
        codec = ["-c:v", "rawvideo", "-pix_fmt", "bgr24"]           # uncompressed, FaceReader's BI_RGB
    else:
        # FFV1 is lossless; bgr0 keeps the PNGs' BGR pixels exactly (no YUV conversion, no subsampling)
        codec = ["-c:v", "ffv1", "-level", "3", "-g", "1", "-slicecrc", "1", "-pix_fmt", "bgr0"]
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}",
        "-framerate", f"{fps:.6f}", "-i", "-",
        *codec, output_path,
    ]
    print("Running:", " ".join(cmd))
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    last_idx, last_bytes = None, None
    n_total = len(frame_sequence)
    try:
        for n, src_idx in enumerate(frame_sequence):
            if src_idx != last_idx:
                path = os.path.join(frames_dir, f"frame_{src_idx:06d}.png")
                img = cv2.imread(path, cv2.IMREAD_COLOR)
                if img is None:
                    raise RuntimeError(f"Could not read {path}")
                if img.shape != (height, width, 3):
                    raise RuntimeError(f"{path} has shape {img.shape}, expected {(height, width, 3)}")
                last_idx, last_bytes = src_idx, img.tobytes()
            proc.stdin.write(last_bytes)
            if n % 3000 == 0:
                print(f"  {n}/{n_total} frames written")
        proc.stdin.close()
    except BrokenPipeError:
        pass
    except BaseException:
        proc.kill()
        proc.wait()
        if os.path.exists(output_path):
            os.remove(output_path)  # don't leave a truncated video that looks usable
        raise

    stderr = proc.stderr.read().decode(errors="replace")
    if proc.wait() != 0:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise RuntimeError(f"ffmpeg failed:\n{stderr[-3000:]}")


def convert(frames_dir, csv_path, output_dir, method, fps=30.0):
    """Convert one participant. Returns the output path."""
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}, got {method!r}")
    check_ffmpeg()
    pid = participant_id(os.path.basename(os.path.normpath(frames_dir)))
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_name(pid, method, fps))
    if os.path.exists(output_path):
        raise FileExistsError(f"'{output_path}' already exists - delete it first to redo it.")

    print(f"METHOD: {method.upper()}  ->  {output_path}")
    print("  " + {
        "realtime": "for FaceReader expressions: constant fps, frames repeated/skipped to follow real time",
        "1to1": "for rPPG (WebcamBiometrics AND FaceReader): every PNG exactly once, lossless FFV1 in .avi; "
                "use WITH the timestamps CSV",
        "1to1-facereader": "fallback: the same 1:1 frames uncompressed, only if FaceReader can't read FFV1",
    }[method])

    rows = load_timestamps(csv_path)
    times = [t for _, t in rows]
    duration = times[-1] - times[0]
    avg_fps = (len(rows) - 1) / duration
    intervals = [b - a for a, b in zip(times, times[1:])]
    print(f"Timestamp rows        : {len(rows)} (last frame at {times[-1]:.3f} s)")
    print(f"Measured average fps  : {avg_fps:.3f}")
    print(f"Frame interval        : min {min(intervals)*1000:.1f} ms, max {max(intervals)*1000:.1f} ms")

    png_indices = {int(f[6:12]) for f in os.listdir(frames_dir)
                   if f.startswith("frame_") and f.lower().endswith(".png") and f[6:12].isdigit()}
    csv_indices = {i for i, _ in rows}
    print(f"PNG files found       : {len(png_indices)}")
    missing_png = sorted(csv_indices - png_indices)
    if missing_png:
        raise FileNotFoundError(f"{len(missing_png)} frame(s) in the CSV have no PNG, e.g. {missing_png[:5]}")
    untimed = sorted(png_indices - csv_indices)
    if untimed:
        print(f"[WARNING] {len(untimed)} PNG(s) have no timestamp row (frames {untimed[0]}-{untimed[-1]}) "
              f"and will be left out. This is expected if the experiment stopped before "
              f"saving timestamps at the end of the routine.")

    first = cv2.imread(os.path.join(frames_dir, f"frame_{rows[0][0]:06d}.png"), cv2.IMREAD_COLOR)
    if first is None:
        raise RuntimeError("Could not read the first PNG frame")
    height, width = first.shape[:2]

    if method == "realtime":
        frame_map = build_frame_map(rows, fps)
        errors = [abs(t - src_t) for _, t, _, src_t in frame_map]
        used = len({src for _, _, src, _ in frame_map})
        print(f"\nResampling to {fps:g} fps on the recording timeline:")
        print(f"  AVI frames          : {len(frame_map)} ({len(frame_map)/fps:.3f} s)")
        print(f"  Source frames used  : {used}/{len(rows)} "
              f"({len(rows) - used} dropped where the camera ran faster than {fps:g} fps)")
        print(f"  Timing error        : mean {sum(errors)/len(errors)*1000:.1f} ms, "
              f"max {max(errors)*1000:.1f} ms")
        sequence = [src for _, _, src, _ in frame_map]
        out_fps = fps
        est = len(sequence) * width * height * 3 / 1024**3
        print(f"  Estimated size      : {est:.1f} GB uncompressed ({width}x{height})\n")
    else:
        print(f"\n1:1 - {len(rows)} frames, each PNG once. Nominal rate {avg_fps:.3f} fps is only a "
              f"label: real frame times are in the timestamps CSV.")
        sequence = [idx for idx, _ in rows]
        out_fps = avg_fps
        est = len(sequence) * width * height * 3 / 1024**3
        if method == "1to1":
            print(f"  Uncompressed would be {est:.1f} GB; FFV1 size depends on image noise (printed at the end).\n")
        else:
            print(f"  Estimated size      : {est:.1f} GB uncompressed ({width}x{height})\n")

    encode(frames_dir, sequence, out_fps, width, height, output_path, method)

    if method == "realtime":
        map_path = os.path.splitext(output_path)[0] + "_frame_map.csv"
        with open(map_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["avi_frame", "avi_time", "source_frame_index",
                             "source_time_since_recording_start", "abs_time_error"])
            for k, t, src, src_t in frame_map:
                writer.writerow([k, round(t, 6), src, round(src_t, 6), round(abs(t - src_t), 6)])
        print(f"Frame map : {map_path}")
    else:
        # Keep the clock next to the video, so the pair travels together (the eval needs both).
        ts_copy = os.path.join(output_dir, f"{pid}_frame_timestamps.csv")
        if not os.path.exists(ts_copy):
            shutil.copy2(csv_path, ts_copy)
            print(f"Timestamps copied to : {ts_copy}")
        elif not filecmp.cmp(csv_path, ts_copy, shallow=False):
            print(f"[WARNING] {ts_copy} already exists and DIFFERS from {csv_path} - not overwritten. "
                  f"The eval would use the wrong clock: check which one belongs to this recording.")

    size_gb = os.path.getsize(output_path) / 1024**3
    print(f"\nDone. Wrote: {output_path} ({size_gb:.2f} GB, {len(sequence)} frames)")
    if method == "realtime":
        print("Before trusting it, confirm FaceReader opens it and reports the expected frame count/duration.")
    return output_path


def participant_id(name):
    """Participant ID = everything before the first '_' in a file/folder name."""
    return name.split("_", 1)[0]


def find_sessions(data_dir):
    """Pair <id>_..._frames folders with <id>_..._frame_timestamps.csv files by participant ID.

    Returns (sessions, problems): sessions maps id -> (frames_dir, csv_path);
    problems is a list of human-readable reasons an ID was skipped."""
    folders, csvs = {}, {}
    for entry in os.scandir(data_dir):
        if "_" not in entry.name:
            continue
        pid = participant_id(entry.name)
        if entry.is_dir() and entry.name.endswith("_frames"):
            folders.setdefault(pid, []).append(entry.path)
        elif entry.is_file() and entry.name.lower().endswith("frame_timestamps.csv"):
            csvs.setdefault(pid, []).append(entry.path)

    sessions, problems = {}, []
    for pid in sorted(set(folders) | set(csvs)):
        f, c = folders.get(pid, []), csvs.get(pid, [])
        if not f:
            problems.append(f"{pid}: timestamps CSV but no frames folder ({', '.join(map(os.path.basename, c))})")
        elif not c:
            problems.append(f"{pid}: frames folder but no timestamps CSV ({', '.join(map(os.path.basename, f))})")
        elif len(f) > 1 or len(c) > 1:
            problems.append(f"{pid}: more than one match, can't tell which belong together "
                            f"({', '.join(os.path.basename(p) for p in f + c)})")
        else:
            sessions[pid] = (f[0], c[0])
    return sessions, problems


def convert_all(data_dir, output_dir, method, fps):
    check_ffmpeg()
    sessions, problems = find_sessions(data_dir)
    print(f"METHOD: {method.upper()}  |  output folder: {output_dir}")
    print(f"Found {len(sessions)} participant(s) with a frames folder and timestamps CSV in {data_dir}")
    for p in problems:
        print(f"[SKIPPED] {p}")

    done, skipped, failed = [], [], []
    for pid, (frames_dir, csv_path) in sessions.items():
        output_path = os.path.join(output_dir, output_name(pid, method, fps))
        print(f"\n{'=' * 70}\nParticipant {pid}\n  frames : {frames_dir}\n  csv    : {csv_path}\n"
              f"  output : {output_path}\n{'=' * 70}")
        if os.path.exists(output_path):
            print("Already converted - skipping (delete the output to redo it).")
            skipped.append(pid)
            continue
        try:
            convert(frames_dir, csv_path, output_dir, method, fps)
            done.append(pid)
        except Exception as e:
            print(f"[ERROR] {pid} failed: {e}")
            failed.append(pid)

    print(f"\n{'=' * 70}\nBatch summary ({method})")
    print(f"  Converted              : {len(done)} {done}")
    print(f"  Already done (skipped) : {len(skipped)} {skipped}")
    print(f"  Failed                 : {len(failed)} {failed}")
    print(f"  Unmatched (skipped)    : {len(problems)}")
    return not failed


def parse_args():
    p = argparse.ArgumentParser(
        description="Convert the experiment's PNG webcam frames into a realtime AVI (FaceReader "
                    "expressions), a lossless 1:1 video (rPPG) or a 1:1 uncompressed AVI (FaceReader rPPG).",
        usage="%(prog)s <data_dir> --method realtime|1to1|1to1-facereader [--output-dir DIR] [--fps 30]\n"
              "       %(prog)s <frames_dir> <timestamps_csv> --method ... [--output-dir DIR]",
    )
    p.add_argument("paths", nargs="+",
                   help="Either one folder containing all <id>_frames folders and <id>_frame_timestamps.csv "
                        "files (batch), or <frames_dir> <timestamps_csv> (one participant)")
    p.add_argument("--method", required=True, choices=METHODS,
                   help="realtime = FaceReader expressions AVI (frames repeated/skipped onto a constant-fps "
                        "real-time grid); 1to1 = THE rPPG video for WebcamBiometrics AND FaceReader (every PNG once, "
                        "lossless FFV1 in .avi); 1to1-facereader = fallback, same frames uncompressed")
    p.add_argument("--output-dir", help="Where to write (default: VIDEO_DIR in config.py, i.e. D:\\Biosignals2_video)")
    p.add_argument("--fps", type=float, default=30.0,
                   help="realtime only: constant output frame rate (default: 30)")
    p.add_argument("--no-resample", action="store_true", help=argparse.SUPPRESS)
    args = p.parse_args()
    if args.no_resample:
        p.error("--no-resample was replaced by --method 1to1 (the output name now says which method made it)")
    if len(args.paths) == 1 and not os.path.isdir(args.paths[0]):
        p.error(f"'{args.paths[0]}' is not a folder")
    if len(args.paths) not in (1, 2):
        p.error("give either one data folder, or <frames_dir> <timestamps_csv>")
    if args.method != "realtime" and args.fps != 30.0:
        p.error("--fps only applies to --method realtime (1to1 methods keep every frame with its real time)")
    return args


if __name__ == "__main__":
    args = parse_args()
    out_dir = args.output_dir or default_output_dir()
    if len(args.paths) == 1:
        ok = convert_all(args.paths[0], out_dir, args.method, args.fps)
        sys.exit(0 if ok else 1)
    else:
        convert(args.paths[0], args.paths[1], out_dir, args.method, args.fps)
