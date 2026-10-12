r"""
004_convert_mkv_to_avi.py
=========================
ONE-OFF for participants converted before 7 Oct 2026, whose 1:1 video is an <id>_1to1.mkv.
Since then 000 (--method 1to1) writes <id>_1to1_ffv1.avi directly, and that single file is used by
BOTH WebcamBiometrics (003) and FaceReader. This script turns an old .mkv into that .avi, and with
--delete-mkv removes the .mkv afterwards so there is only one video per participant:

  python 004_convert_mkv_to_avi.py --all --delete-mkv

--delete-mkv only deletes after checking EVERY frame of the .avi is pixel-identical to the .mkv
(decodes both once; a few minutes per participant). If the .avi already exists it is checked the
same way. Nothing in 003's cached extraction needs redoing: the pixels are the same.

  --method 1to1-ffv1avi  ->  <id>_1to1_ffv1.avi      <- USE THIS FOR FACEREADER (default)
      The SAME compressed FFV1 pictures as the .mkv, just re-packed into an .avi with a constant
      frame rate (= the average real fps, as in the .mkv). Takes as long as copying the file
      (~5.5 GB per participant), is the same size, and is bit-for-bit the same pictures.
      Why: FaceReader can't read a bit rate from an .mkv, so it shows "the frame rate / bit rate /
      resolution is too low" on every frame AND processes the video differently. On r2433 (7 Oct
      2026) the .mkv run found 24-43% of ECG R-peaks within 150 ms with 51-75% false beats; the
      same frames as .avi: 85-99% found, ~1% false, no warning. Delete the .avi after FaceReader
      has run; this script remakes it from the .mkv.
      (A plain "ffmpeg -c copy" to .avi does NOT work: the .mkv stores times in milliseconds, so
      the .avi becomes 1000 fps padded with ~1 million empty frames.)

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

Usage (paths from config.py at the repo root: VIDEO_EXTERNAL_DIR, i.e. D:\)
-----
  python 004_convert_mkv_to_avi.py r2433                               # FFV1 .avi for FaceReader (default)
  python 004_convert_mkv_to_avi.py --all                               # every <id>_1to1.mkv in VIDEO_EXTERNAL_DIR
  python 004_convert_mkv_to_avi.py --all --output-dir C:\fr_temp       # faster if on a different drive
  python 004_convert_mkv_to_avi.py r2433 --method 1to1-facereader
  python 004_convert_mkv_to_avi.py r2433 i4155 --method realtime
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
METHODS = ("1to1-ffv1avi", "1to1-facereader", "realtime")


def out_name(pid, method, fps):
    return f"{pid}_1to1_ffv1.avi" if method == "1to1-ffv1avi" else C.output_name(pid, method, fps)


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


def stream_info(path):
    """(avg_frame_rate as float, packets counted exactly, bit_rate) of the first video stream."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
         "-show_entries", "stream=avg_frame_rate,nb_read_packets,bit_rate", "-of", "default=nw=1", path],
        capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe could not read {path}: {out.stderr.strip()}")
    d = dict(line.split("=", 1) for line in out.stdout.strip().splitlines() if "=" in line)
    num, den = (d.get("avg_frame_rate", "0/1") + "/1").split("/")[:2]
    rate = float(num) / float(den) if float(den) else 0.0
    br = d.get("bit_rate", "N/A")
    return rate, int(d.get("nb_read_packets", 0)), (int(br) if br.isdigit() else None)


def first_frames_md5(path, n=300):
    """Checksums of the first n decoded pictures - to prove the re-pack didn't change any pixel."""
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:v:0", *passthrough_flag(),
                          "-frames:v", str(n), "-f", "framemd5", "-"], capture_output=True, text=True)
    return [line.rsplit(",", 1)[-1].strip() for line in out.stdout.splitlines() if line and not line.startswith("#")]


def remux_ffv1(mkv, rows, n, width, height, output_path):
    """Copy the .mkv's FFV1 pictures unchanged into an .avi, one frame per picture, at the average fps."""
    times = [t for _, t in rows]
    avg_fps = (len(rows) - 1) / (times[-1] - times[0])          # same value as in the .mkv / FaceReader's log
    micro = int(round(avg_fps * 1_000_000))                      # rate as micro-frames per second
    print(f"  1:1 FFV1 re-pack: {n} frames at {micro / 1e6:.6f} fps (no re-encoding; ~{os.path.getsize(mkv) / 1024**3:.1f} GB)")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-i", mkv, "-map", "0:v:0", "-c", "copy",
           "-bsf:v", f"setts=ts=N:time_base=1000000/{micro}", "-r", f"{micro}/1000000", output_path]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise RuntimeError("ffmpeg re-pack failed (see messages above)")
    rate, packets, br = stream_info(output_path)
    problems = []
    if packets != n:
        problems.append(f"{packets} frames instead of {n}")
    if abs(rate - micro / 1e6) > 0.001:
        problems.append(f"frame rate {rate:.4f} instead of {micro / 1e6:.4f}")
    if first_frames_md5(mkv) != first_frames_md5(output_path):
        problems.append("the first 300 pictures are not identical to the .mkv")
    if problems:
        os.remove(output_path)
        raise RuntimeError("re-packed .avi failed its checks (" + "; ".join(problems) + ") - deleted it.")
    bpp = (br / (rate * width * height)) if br else None
    print(f"  checked: {packets} frames, {rate:.6f} fps, first 300 pictures identical to the .mkv"
          + (f", {br / 1e6:.1f} Mbit/s = {bpp:.2f} bits/pixel (FaceReader needs >= 0.15)" if bpp else ""))


def all_frames_identical(a, b):
    """True if every decoded picture of a and b is identical (per-frame checksums, in order)."""
    def sums(path):
        out = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:v:0", *passthrough_flag(),
                              "-f", "framemd5", "-"], capture_output=True, text=True)
        if out.returncode != 0:
            raise RuntimeError(f"ffmpeg could not decode {path}: {out.stderr.strip()[-500:]}")
        return [line.rsplit(",", 1)[-1].strip() for line in out.stdout.splitlines() if line and not line.startswith("#")]
    sa, sb = sums(a), sums(b)
    return len(sa) == len(sb) and len(sa) > 0 and sa == sb, len(sa), len(sb)


def delete_mkv_if_identical(pid, video_external_dir, output_dir):
    mkv = os.path.join(video_external_dir, f"{pid}_1to1.mkv")
    avi = os.path.join(output_dir, f"{pid}_1to1_ffv1.avi")
    if not os.path.exists(mkv):
        print("  no .mkv to delete.")
        return
    if os.path.normcase(os.path.dirname(os.path.abspath(avi))) != os.path.normcase(os.path.abspath(video_external_dir)):
        print(f"  NOT deleting the .mkv: the .avi is in {output_dir}, not next to the .mkv in {video_external_dir} "
              f"(003 and FaceReader look in {video_external_dir}). Move the .avi there first.")
        return
    print("  checking every frame of the .avi against the .mkv before deleting it...")
    same, na, nb = all_frames_identical(mkv, avi)
    if not same:
        print(f"  NOT deleting the .mkv: frames differ ({na} vs {nb} frames or different pixels).")
        return
    os.remove(mkv)
    print(f"  all {na} frames identical - deleted {os.path.basename(mkv)}; {os.path.basename(avi)} is now the only video.")


def convert(pid, video_external_dir, output_dir, method, fps=30.0):
    mkv = os.path.join(video_external_dir, f"{pid}_1to1.mkv")
    ts = os.path.join(video_external_dir, f"{pid}_frame_timestamps.csv")
    for p in (mkv, ts):
        if not os.path.exists(p):
            raise FileNotFoundError(f"{p} not found")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, out_name(pid, method, fps))
    if os.path.exists(output_path):
        raise FileExistsError(f"'{output_path}' already exists - delete it first to redo it.")
    print(f"METHOD: {method.upper()} (from {os.path.basename(mkv)})  ->  {output_path}")

    rows = C.load_timestamps(ts)                         # same checks as when the .mkv was made
    width, height, n = probe(mkv)
    print(f"  .mkv: {n} pictures, {width}x{height};  timestamps: {len(rows)} rows")
    if n != len(rows):
        raise RuntimeError(f"{os.path.basename(mkv)} has {n} pictures but {os.path.basename(ts)} has "
                           f"{len(rows)} rows - they don't belong together (or one is incomplete).")

    if method == "1to1-ffv1avi":
        C.check_ffmpeg()
        remux_ffv1(mkv, rows, n, width, height, output_path)
        print(f"Done. Wrote: {output_path} ({os.path.getsize(output_path) / 1024**3:.2f} GB)")
        return output_path

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
    ap.add_argument("--method", default="1to1-ffv1avi", choices=METHODS,
                    help="1to1-ffv1avi (default, for FaceReader), 1to1-facereader (uncompressed), realtime")
    ap.add_argument("--video-dir", help="folder with <id>_1to1.mkv + <id>_frame_timestamps.csv "
                                        "(default VIDEO_EXTERNAL_DIR in config.py)")
    ap.add_argument("--output-dir", help="where to write (default: the same folder)")
    ap.add_argument("--fps", type=float, default=30.0, help="realtime only: output frame rate (default 30)")
    ap.add_argument("--delete-mkv", action="store_true",
                    help="1to1-ffv1avi only: after checking every frame is identical, delete <id>_1to1.mkv")
    a = ap.parse_args()
    if a.method != "realtime" and a.fps != 30.0:
        ap.error("--fps only applies to --method realtime")
    if a.delete_mkv and a.method != "1to1-ffv1avi":
        ap.error("--delete-mkv only applies to --method 1to1-ffv1avi")

    video_external_dir = a.video_dir or C.default_output_dir()
    output_dir = a.output_dir or video_external_dir
    if a.all:
        pids = sorted(os.path.basename(p)[: -len("_1to1.mkv")]
                      for p in glob.glob(os.path.join(video_external_dir, "*_1to1.mkv")))   # = everyone still with an .mkv
    else:
        pids = a.pids
    if not pids:
        ap.error(f"give participant IDs, or --all (no *_1to1.mkv found in {video_external_dir})" if a.all
                 else "give participant IDs, or --all")

    status = {}
    for pid in pids:
        print(f"\n{'=' * 70}\n{pid}\n{'=' * 70}")
        try:
            if os.path.exists(os.path.join(output_dir, out_name(pid, a.method, a.fps))):
                print("Already converted - not redoing it (delete the output to redo it).")
                status[pid] = "skipped (exists)"
            else:
                convert(pid, video_external_dir, output_dir, a.method, a.fps)
                status[pid] = "OK"
            if a.delete_mkv:
                delete_mkv_if_identical(pid, video_external_dir, output_dir)
        except Exception as e:
            print(f"[ERROR] {e}")
            status[pid] = f"FAILED: {e}"
    print(f"\n{'=' * 70}\nSummary ({a.method})")
    for pid, s in status.items():
        print(f"  {pid:>10} : {s}")
    sys.exit(0 if all(not s.startswith("FAILED") for s in status.values()) else 1)


if __name__ == "__main__":
    main()
