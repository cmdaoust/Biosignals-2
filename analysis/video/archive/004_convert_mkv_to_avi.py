r"""
004_convert_mkv_to_avi.py
=========================
Makes the FaceReader videos from the lossless 1:1 video (<id>_1to1.mkv) instead of from the PNG
pictures. Use it once the PNGs are archived (e.g. zipped on Box) and only the .mkv + its timestamps
are on the drive.

This works because <id>_1to1.mkv holds EXACTLY the same pictures as the PNG folder (same pictures,
same order, same pixels), and <id>_frame_timestamps.csv next to it holds their real capture times.
So the result is identical to what 000_convert_png_to_avi.py makes from the PNGs.

  --method 1to1-facereader  ->  <id>_1to1_facereader.avi
      Every picture once, uncompressed, for FaceReader's HEART-RATE analysis (same pictures as
      our analysis). Speed label = the average pictures per second, as 000 writes it.
  --method realtime         ->  <id>_realtime_30fps.avi  (+ <id>_realtime_30fps_frame_map.csv)
      Constant 30 pictures per second on the real timeline (pictures repeated where the camera
      paused, skipped where it ran fast), for FaceReader's EXPRESSION analysis. Same rule as 000.

How it works
------------
1. Reads <id>_frame_timestamps.csv (the same checks as 000) and checks the .mkv contains exactly
   one picture per row - otherwise the two don't belong together, and it stops.
2. Works out which picture goes into each frame of the new video (1to1-facereader: every picture
   in order; realtime: for each 1/30 s slot, the picture taken closest to that moment).
3. Unpacks the .mkv picture by picture, IN ORDER, and writes the chosen pictures into the new
   uncompressed .avi. ffmpeg is told to pass every picture through as-is, so it can never
   silently repeat or drop pictures (it otherwise might, because the .mkv stores each
   picture's time rounded to the millisecond).
4. Counts the frames in the finished .avi and deletes it if the count is wrong.

Never overwrites: a participant whose output already exists is skipped.

Usage (paths from analysis\config.py: VIDEO_EXTERNAL_DIR, i.e. D:\)
-----
  python 004_convert_mkv_to_avi.py r2433 --method 1to1-facereader
  python 004_convert_mkv_to_avi.py r2433 i4155 --method realtime
  python 004_convert_mkv_to_avi.py --all --method 1to1-facereader      # every <id>_1to1.mkv in VIDEO_EXTERNAL_DIR
Options: --video-dir DIR (where the .mkv + timestamps are), --output-dir DIR (where to write;
default the same folder), --fps 30 (realtime only).

Needs ffmpeg + ffprobe on PATH (winget install ffmpeg). Uses 000_convert_png_to_avi.py from the
same folder for the shared rules (timestamp checks, realtime picture choice, file names).
"""

import argparse
import bisect
import csv
import glob
import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
METHODS = ("1to1-facereader", "realtime")


def load_converter():
    spec = importlib.util.spec_from_file_location("convert_png", os.path.join(HERE, "000_convert_png_to_avi.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C = load_converter()


def probe(path):
    """(width, height, number of pictures) of the first video stream, counting pictures exactly."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
         "-show_entries", "stream=width,height,nb_read_packets", "-of", "csv=p=0:s=,", path],
        capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe could not read {path}: {out.stderr.strip()}")
    w, h, n = out.stdout.strip().split(",")[:3]
    return int(w), int(h), int(n)


def passthrough_flag():
    """Option that stops ffmpeg repeating/dropping pictures (-fps_mode in new ffmpeg, -vsync in old)."""
    helptext = subprocess.run(["ffmpeg", "-hide_banner", "-h", "full"], capture_output=True, text=True).stdout
    return ["-fps_mode", "passthrough"] if "-fps_mode" in helptext else ["-vsync", "passthrough"]


def picture_plan(rows, method, fps):
    """-> (positions, out_fps, frame_map). positions[k] = which .mkv picture (0-based, in file order)
    goes into output frame k. frame_map rows match 000's *_frame_map.csv (realtime only)."""
    times = [t for _, t in rows]
    if method == "1to1-facereader":
        avg_fps = (len(rows) - 1) / (times[-1] - times[0])   # same label as 000 --method 1to1(-facereader)
        return list(range(len(rows))), avg_fps, None
    # realtime: identical rule to 000.build_frame_map, but keeping the picture's POSITION in the .mkv
    positions, frame_map = [], []
    for k in range(int(times[-1] * fps) + 1):
        t = k / fps
        j = bisect.bisect_left(times, t)
        if j == len(times) or (j > 0 and t - times[j - 1] <= times[j] - t):
            j -= 1
        positions.append(j)
        frame_map.append((k, t, rows[j][0], times[j]))
    return positions, fps, frame_map


def write_avi(mkv, positions, width, height, out_fps, output_path):
    """Decode the .mkv picture by picture and write positions[k] as output frame k (uncompressed)."""
    frame_bytes = width * height * 3
    dec = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", mkv, "-map", "0:v:0",
         *passthrough_flag(), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
        stdout=subprocess.PIPE)
    enc = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}",
         "-framerate", f"{out_fps:.6f}", "-i", "-",
         "-c:v", "rawvideo", "-pix_fmt", "bgr24", output_path],
        stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        cur_pos, cur = -1, None
        for k, want in enumerate(positions):
            while cur_pos < want:                       # read forward to the wanted picture
                cur = dec.stdout.read(frame_bytes)
                if len(cur) != frame_bytes:
                    raise RuntimeError(f"the .mkv ran out of pictures at {cur_pos + 1} (needed {want + 1})")
                cur_pos += 1
            enc.stdin.write(cur)
            if k % 3000 == 0:
                print(f"  {k}/{len(positions)} frames written", flush=True)
        enc.stdin.close()
        err = enc.stderr.read().decode(errors="replace")
        if enc.wait() != 0:
            raise RuntimeError(f"ffmpeg (writing) failed:\n{err[-3000:]}")
    except BaseException:
        enc.kill()
        enc.wait()
        if os.path.exists(output_path):
            os.remove(output_path)   # never leave a half-written video that looks usable
        raise
    finally:
        dec.kill()
        dec.wait()


def convert(pid, video_dir, output_dir, method, fps=30.0):
    mkv = os.path.join(video_dir, f"{pid}_1to1.mkv")
    ts = os.path.join(video_dir, f"{pid}_frame_timestamps.csv")
    for p in (mkv, ts):
        if not os.path.exists(p):
            raise FileNotFoundError(f"{p} not found")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, C.output_name(pid, method, fps))
    if os.path.exists(output_path):
        raise FileExistsError(f"'{output_path}' already exists - delete it first to redo it.")
    print(f"METHOD: {method.upper()} (from {os.path.basename(mkv)})  ->  {output_path}")

    rows = C.load_timestamps(ts)                         # same checks as when the .mkv was made
    width, height, n = probe(mkv)
    print(f"  .mkv: {n} pictures, {width}x{height};  timestamps: {len(rows)} rows")
    if n != len(rows):
        raise RuntimeError(f"{os.path.basename(mkv)} has {n} pictures but {os.path.basename(ts)} has "
                           f"{len(rows)} rows - they don't belong together (or one is incomplete).")

    positions, out_fps, frame_map = picture_plan(rows, method, fps)
    if method == "realtime":
        errors = [abs(t - st) for _, t, _, st in frame_map]
        print(f"  realtime: {len(positions)} frames at {fps:g} fps; {len(set(positions))}/{n} pictures used; "
              f"timing error mean {sum(errors) / len(errors) * 1000:.1f} ms, max {max(errors) * 1000:.1f} ms")
    else:
        print(f"  1:1: {n} frames, speed label {out_fps:.6f} fps (real times are in the timestamps CSV)")
    print(f"  size about {len(positions) * width * height * 3 / 1024**3:.1f} GB (uncompressed)")

    C.check_ffmpeg()
    write_avi(mkv, positions, width, height, out_fps, output_path)

    _, _, n_out = probe(output_path)                      # final check: right number of frames?
    if n_out != len(positions):
        os.remove(output_path)
        raise RuntimeError(f"output has {n_out} frames, expected {len(positions)} - deleted it.")
    if frame_map:
        map_path = os.path.splitext(output_path)[0] + "_frame_map.csv"
        with open(map_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["avi_frame", "avi_time", "source_frame_index",
                        "source_time_since_recording_start", "abs_time_error"])
            for k, t, src, st in frame_map:
                w.writerow([k, round(t, 6), src, round(st, 6), round(abs(t - st), 6)])
        print(f"  frame map: {map_path}")
    print(f"Done. Wrote: {output_path} ({os.path.getsize(output_path) / 1024**3:.2f} GB, {n_out} frames)")
    return output_path


def main():
    ap = argparse.ArgumentParser(description="Make FaceReader AVIs from <id>_1to1.mkv (instead of the PNGs).")
    ap.add_argument("pids", nargs="*", help="participant IDs, e.g. r2433")
    ap.add_argument("--all", action="store_true", help="every <id>_1to1.mkv in the video folder")
    ap.add_argument("--method", required=True, choices=METHODS)
    ap.add_argument("--video-dir", help="folder with <id>_1to1.mkv + <id>_frame_timestamps.csv "
                                        "(default VIDEO_EXTERNAL_DIR in config.py)")
    ap.add_argument("--output-dir", help="where to write (default: the same folder)")
    ap.add_argument("--fps", type=float, default=30.0, help="realtime only: output frame rate (default 30)")
    a = ap.parse_args()
    if a.method != "realtime" and a.fps != 30.0:
        ap.error("--fps only applies to --method realtime")

    video_dir = a.video_dir or C.default_output_dir()
    output_dir = a.output_dir or video_dir
    if a.all:
        pids = sorted(os.path.basename(p)[: -len("_1to1.mkv")]
                      for p in glob.glob(os.path.join(video_dir, "*_1to1.mkv")))
    else:
        pids = a.pids
    if not pids:
        ap.error(f"give participant IDs, or --all (no *_1to1.mkv found in {video_dir})" if a.all
                 else "give participant IDs, or --all")

    status = {}
    for pid in pids:
        print(f"\n{'=' * 70}\n{pid}\n{'=' * 70}")
        if os.path.exists(os.path.join(output_dir, C.output_name(pid, a.method, a.fps))):
            print("Already converted - skipping (delete the output to redo it).")
            status[pid] = "skipped (exists)"
            continue
        try:
            convert(pid, video_dir, output_dir, a.method, a.fps)
            status[pid] = "OK"
        except Exception as e:
            print(f"[ERROR] {e}")
            status[pid] = f"FAILED: {e}"
    print(f"\n{'=' * 70}\nSummary ({a.method})")
    for pid, s in status.items():
        print(f"  {pid:>10} : {s}")
    sys.exit(0 if all(not s.startswith("FAILED") for s in status.values()) else 1)


if __name__ == "__main__":
    main()
