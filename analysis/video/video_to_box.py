r"""
video_to_box.py
===============
End-of-day archive of the webcam data: for every participant on the external drive whose
video files are not (all) on Box yet, make what's missing and upload it to Box over SFTP.

A participant is COMPLETE on Box when 3_Data/video holds all three (same rule as the QC report):
    <id>_frames.zip            the PNG frames (the lossless original), zipped without compression
    <id>_1to1_ffv1.avi         1:1 lossless video (000_convert_png_to_avi.py --method 1to1)
    <id>_frame_timestamps.csv  one row per frame (written by the experiment)
"On Box" means a file with that name AND the same size as the local file, so a half-finished
upload never counts.

Participants: every <id>_frames folder + <id>_frame_timestamps.csv in WEBCAM_PNG_EXTERNAL_DIR
(D:\Biosignals2_png_data) that isn't complete on Box. Two passes, so the videos (needed for the
analyses) reach Box before the slow zips:

PASS 1 - videos, for each participant:
  video   - runs 000_convert_png_to_avi.py --method 1to1 if VIDEO_EXTERNAL_DIR has no video yet
  check   - the video's frame count must equal the number of PNGs and of timestamp rows
            (catches a video left half-written by an interrupted conversion)
  upload  - the timestamps CSV and the video
PASS 2 - frames, for each participant whose pass 1 succeeded:
  zip     - <id>_frames.zip next to the frames folder (contains the <id>_frames folder, no
            compression: PNGs are already compressed), written as .part, CRC-tested, then renamed
  upload  - the zip
Uploads go to BOX_VIDEO_REMOTE_DIR as .part, are renamed when complete, and their size on Box is
checked. A failure for one participant is logged and the run moves on to the next.

NOTHING IS EVER DELETED - not on the drive, not on Box. Free up drive space yourself once the
QC report shows the participant complete.

Re-running is safe: finished steps are detected and skipped, unfinished ones redone.

Setup (once):
    pip install paramiko keyring
    ffmpeg/ffprobe on PATH (already needed by 000)
    config.py: BOX_SFTP_USER (your Box email), BOX_VIDEO_REMOTE_DIR (see config_template.py)
    python video_to_box.py --set-password     # stores your Box password in Windows Credential Manager

Usage:
    python video_to_box.py --dry-run          # who/what would be done; connects to Box to check, changes nothing
    python video_to_box.py                    # do it
    python video_to_box.py r2433 s9686        # only these participants
"""
import argparse
import datetime as dt
import getpass
import glob
import importlib.util
import os
import posixpath
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
CONVERT_SCRIPT = os.path.join(HERE, "000_convert_png_to_avi.py")
KEYRING_SERVICE = "Biosignals2 Box SFTP"


# ── config ─────────────────────────────────────────────────────────────────────
def load_config():
    folder = HERE
    while not os.path.isfile(os.path.join(folder, "config.py")):
        parent = os.path.dirname(folder)
        if parent == folder:
            sys.exit(f"No config.py found in {HERE} or above")
        folder = parent
    spec = importlib.util.spec_from_file_location("bs2_config", os.path.join(folder, "config.py"))
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    c = {
        "png_dir": str(getattr(cfg, "WEBCAM_PNG_EXTERNAL_DIR", "") or r"D:\Biosignals2_png_data"),
        "video_dir": str(getattr(cfg, "VIDEO_EXTERNAL_DIR", "") or r"D:\Biosignals2_video"),
        "server_root": str(getattr(cfg, "SERVER_ROOT", "") or ""),
        "host": str(getattr(cfg, "BOX_SFTP_HOST", "") or "sftp.services.box.com"),
        "port": int(getattr(cfg, "BOX_SFTP_PORT", 22) or 22),
        "user": str(getattr(cfg, "BOX_SFTP_USER", "") or ""),
        "remote_dir": str(getattr(cfg, "BOX_VIDEO_REMOTE_DIR", "") or "/Project_Biosignals_study_2/3_Data/video"),
        "fingerprint": str(getattr(cfg, "BOX_SFTP_FINGERPRINT", "") or "An60IqVqISRa3o2GRscno7QLnsTrIy0BGIchIAvJ9ZM"),
    }
    return c


# ── logging ────────────────────────────────────────────────────────────────────
LOG_FH = None

def log(msg=""):
    line = f"{dt.datetime.now():%H:%M:%S}  {msg}" if msg else ""
    print(line, flush=True)
    if LOG_FH:
        LOG_FH.write(line + "\n")
        LOG_FH.flush()


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024


# ── finding participants ───────────────────────────────────────────────────────
def pid_of(name):
    return os.path.basename(name.rstrip("\\/")).split("_")[0].lower()


def find_local(png_dir, only):
    """pid -> {frames_dir, ts_csv}; plus a list of problems."""
    if not os.path.isdir(png_dir):
        sys.exit(f"External drive folder not found: {png_dir} (is the drive connected?)")
    frames, stamps, problems = {}, {}, []
    for entry in os.scandir(png_dir):
        n = entry.name.lower()
        if entry.is_dir() and n.endswith("_frames"):
            frames.setdefault(pid_of(entry.name), []).append(entry.path)
        elif entry.is_file() and n.endswith("_frame_timestamps.csv"):
            stamps.setdefault(pid_of(entry.name), []).append(entry.path)
    out = {}
    for pid in sorted(frames):
        if only and pid not in only:
            continue
        if len(frames[pid]) > 1 or len(stamps.get(pid, [])) > 1:
            problems.append((pid, "more than one frames folder or timestamps file - sort out by hand"))
        elif pid not in stamps:
            problems.append((pid, "frames folder but no <id>_frame_timestamps.csv"))
        else:
            out[pid] = {"frames_dir": frames[pid][0], "ts_csv": stamps[pid][0]}
    for pid in only or []:
        if pid not in out and not any(p == pid for p, _ in problems):
            problems.append((pid, f"no {pid}_frames folder in {png_dir}"))
    return out, problems


def count_pngs(frames_dir):
    return sum(1 for e in os.scandir(frames_dir) if e.is_file() and e.name.lower().endswith(".png"))


def count_ts_rows(ts_csv):
    with open(ts_csv, "rb") as f:
        lines = [l for l in f.read().splitlines() if l.strip()]
    return max(len(lines) - 1, 0)  # minus header


def video_frames(path):
    """Frame count via ffprobe (counts packets: exact for FFV1, one packet per frame)."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
         "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", path],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {r.stderr.strip()[:300]}")
    return int(r.stdout.strip().split(",")[0])


# ── steps ──────────────────────────────────────────────────────────────────────
def step_video(pid, p, video_dir, dry):
    avi = os.path.join(video_dir, f"{pid}_1to1_ffv1.avi")
    if os.path.exists(avi):
        log(f"  video   : exists ({human(os.path.getsize(avi))})")
        return avi
    if dry:
        log("  video   : would convert with 000_convert_png_to_avi.py --method 1to1 (slow)")
        return avi
    log("  video   : converting (this takes a while)...")
    t0 = time.time()
    r = subprocess.run([sys.executable, CONVERT_SCRIPT, p["frames_dir"], p["ts_csv"],
                        "--method", "1to1", "--output-dir", video_dir],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(avi):
        tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-8:])
        raise RuntimeError(f"000_convert_png_to_avi.py failed:\n{tail}")
    log(f"  video   : done in {(time.time() - t0) / 60:.0f} min ({human(os.path.getsize(avi))})")
    return avi


def step_precheck(pid, p):
    """Before the slow conversion: PNGs and timestamp rows must match."""
    n_png = count_pngs(p["frames_dir"])
    n_ts = count_ts_rows(p["ts_csv"])
    if n_png != n_ts:
        raise RuntimeError(f"{n_png} PNGs but {n_ts} timestamp rows - check the recording")
    return n_png, n_ts


def step_check(pid, p, avi, dry):
    n_png, n_ts = step_precheck(pid, p)
    if dry and not os.path.exists(avi):
        log(f"  check   : {n_png} PNGs = {n_ts} timestamp rows (video checked after conversion)")
        return
    n_vid = video_frames(avi)
    if n_vid != n_png:
        raise RuntimeError(
            f"video has {n_vid} frames but there are {n_png} PNGs - probably a conversion that was "
            f"interrupted. Delete {avi} and run again.")
    log(f"  check   : {n_vid} video frames = {n_png} PNGs = {n_ts} timestamp rows")


def step_zip(pid, p, dry):
    frames_dir = p["frames_dir"]
    zpath = os.path.join(os.path.dirname(frames_dir), f"{pid}_frames.zip")
    if os.path.exists(zpath):
        with zipfile.ZipFile(zpath) as z:
            n = sum(1 for i in z.infolist() if i.filename.lower().endswith(".png"))
        if n == count_pngs(frames_dir):
            log(f"  zip     : exists ({n} PNGs, {human(os.path.getsize(zpath))})")
            return zpath
        raise RuntimeError(f"{zpath} has {n} PNGs, the folder has {count_pngs(frames_dir)} - "
                           "delete or rename the zip and run again")
    if dry:
        log("  zip     : would zip the frames folder (no compression)")
        return zpath
    log("  zip     : zipping...")
    t0 = time.time()
    part = zpath + ".part"
    folder_name = os.path.basename(frames_dir.rstrip("\\/"))
    names = sorted(e.name for e in os.scandir(frames_dir) if e.is_file())
    with zipfile.ZipFile(part, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
        for name in names:
            z.write(os.path.join(frames_dir, name), arcname=f"{folder_name}/{name}")
    with zipfile.ZipFile(part) as z:
        bad = z.testzip()
    if bad:
        raise RuntimeError(f"zip test failed at {bad} - {part} left for inspection")
    os.replace(part, zpath)
    log(f"  zip     : done in {(time.time() - t0) / 60:.0f} min ({len(names)} files, {human(os.path.getsize(zpath))})")
    return zpath


class Box:
    def __init__(self, c, password):
        import paramiko
        self.c = c
        self.transport = paramiko.Transport((c["host"], c["port"]))
        self.transport.default_window_size = 64 * 1024 * 1024   # faster for large files
        self.transport.start_client(timeout=30)
        # Check it's really Box before sending the password (fingerprint published by Box:
        # support.box.com "Using Box with SFTP"; override with BOX_SFTP_FINGERPRINT in config.py).
        import base64, hashlib
        key = self.transport.get_remote_server_key()
        fp = base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
        if c["host"] == "sftp.services.box.com" and fp != c["fingerprint"]:
            self.transport.close()
            raise RuntimeError(f"server key fingerprint SHA256:{fp} is not Box's (SHA256:{c['fingerprint']}) - "
                               "not sending the password. If Box has changed its key, update BOX_SFTP_FINGERPRINT.")
        self.transport.auth_password(username=c["user"], password=password)
        self.sftp = paramiko.SFTPClient.from_transport(self.transport)
        self.sftp.get_channel().settimeout(300)
        try:
            self.sftp.stat(c["remote_dir"])
        except IOError:
            self.close()
            raise RuntimeError(f"Box folder {c['remote_dir']} not found over SFTP - check BOX_VIDEO_REMOTE_DIR")

    def sizes(self):
        """name -> size for every file in the remote folder (one listing)."""
        return {a.filename: a.st_size for a in self.sftp.listdir_attr(self.c["remote_dir"])}

    def upload(self, local, sizes):
        name = os.path.basename(local)
        remote = posixpath.join(self.c["remote_dir"], name)
        part = remote + ".part"
        size = os.path.getsize(local)
        last = [0]
        def progress(done, total):
            pct = int(done * 100 / total) if total else 100
            if pct >= last[0] + 10:
                last[0] = pct - pct % 10
                log(f"            {name}: {last[0]}%")
        t0 = time.time()
        self.sftp.put(local, part, callback=progress, confirm=True)
        if name in sizes:   # an incomplete/older copy: replace it (Box keeps the old one as a version)
            self.sftp.remove(remote)
        self.sftp.rename(part, remote)
        got = self.sftp.stat(remote).st_size
        if got != size:
            raise RuntimeError(f"{name}: {human(got)} on Box but {human(size)} locally")
        mins = (time.time() - t0) / 60
        log(f"  upload  : {name} done ({human(size)}, {mins:.0f} min)")

    def close(self):
        try:
            self.sftp.close()
        finally:
            self.transport.close()


def on_box(name, local, sizes):
    return name in sizes and os.path.exists(local) and sizes[name] == os.path.getsize(local)


# ── main ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pids", nargs="*", help="only these participant IDs (default: everyone on the drive)")
    ap.add_argument("--dry-run", action="store_true", help="show what would be done; change nothing")
    ap.add_argument("--set-password", action="store_true", help="store the Box password in Windows Credential Manager")
    a = ap.parse_args()
    c = load_config()

    import keyring
    if not c["user"]:
        sys.exit("Set BOX_SFTP_USER (your Box email) in config.py first.")
    if a.set_password:
        pw = getpass.getpass(f"Box password for {c['user']} (the one FileZilla uses): ")
        keyring.set_password(KEYRING_SERVICE, c["user"], pw)
        print("Saved in Windows Credential Manager.")
        return 0
    password = keyring.get_password(KEYRING_SERVICE, c["user"])
    if not password:
        sys.exit("No Box password stored. Run: python video_to_box.py --set-password")

    global LOG_FH
    log_dir = c["server_root"] if c["server_root"] and os.path.isdir(c["server_root"]) else c["png_dir"]
    LOG_FH = open(os.path.join(log_dir, "video_to_box_runs.log"), "a", encoding="utf-8")
    log("=" * 70)
    log(f"video_to_box {'DRY RUN ' if a.dry_run else ''}started {dt.datetime.now():%Y-%m-%d %H:%M}")
    log(f"Drive: {c['png_dir']} | videos: {c['video_dir']} | Box: {c['host']}:{c['remote_dir']}")

    only = [p.lower() for p in a.pids]
    local, problems = find_local(c["png_dir"], only)

    try:
        box = Box(c, password)
    except Exception as e:
        log(f"Could not connect to Box over SFTP: {e}")
        return 2
    results = []
    try:
        sizes = box.sizes()
        todo = []
        for pid, p in local.items():
            avi = os.path.join(c["video_dir"], f"{pid}_1to1_ffv1.avi")
            zpath = os.path.join(os.path.dirname(p["frames_dir"]), f"{pid}_frames.zip")
            names = {f"{pid}_frames.zip": zpath, f"{pid}_1to1_ffv1.avi": avi,
                     os.path.basename(p["ts_csv"]): p["ts_csv"]}
            # Complete = all three names on Box. Sizes are compared for files that exist locally.
            missing = [n for n, l in names.items()
                       if n not in sizes or (os.path.exists(l) and sizes[n] != os.path.getsize(l))]
            if missing:
                todo.append(pid)
        log(f"On the drive: {len(local)} | complete on Box: {len(local) - len(todo)} | to do: {len(todo)} {todo}")
        for pid, why in problems:
            log(f"SKIPPED {pid}: {why}")
            results.append((pid, "skipped", why))

        def upload_if_needed(local_path):
            name = os.path.basename(local_path)
            if on_box(name, local_path, sizes):
                log(f"  upload  : {name} already on Box")
            elif a.dry_run:
                size = human(os.path.getsize(local_path)) if os.path.exists(local_path) else "not made yet"
                log(f"  upload  : would upload {name} ({size})")
            else:
                log(f"  upload  : {name} ({human(os.path.getsize(local_path))})...")
                box.upload(local_path, sizes)

        status = {}   # pid -> "ok" / "FAILED: ..."
        log("")
        log("PASS 1: videos + timestamps")
        for pid in todo:
            p = local[pid]
            log(f"── {pid} ──")
            try:
                step_precheck(pid, p)
                avi = step_video(pid, p, c["video_dir"], a.dry_run)
                step_check(pid, p, avi, a.dry_run)
                upload_if_needed(p["ts_csv"])
                upload_if_needed(avi)
                status[pid] = "ok"
            except Exception as e:
                log(f"  FAILED  : {e}")
                status[pid] = "FAILED (video): " + str(e).splitlines()[0]

        log("")
        log("PASS 2: zipped frames")
        for pid in todo:
            if status[pid] != "ok":
                log(f"── {pid} ── skipped (pass 1 failed)")
                continue
            p = local[pid]
            log(f"── {pid} ──")
            try:
                zname = f"{pid}_frames.zip"
                zlocal = os.path.join(os.path.dirname(p["frames_dir"]), zname)
                if zname in sizes and not os.path.exists(zlocal):
                    # Already on Box (e.g. zipped and uploaded by hand) and no local copy to compare:
                    # keep the Box copy rather than re-zipping and replacing it.
                    log(f"  zip     : {zname} already on Box ({human(sizes[zname])}) - kept")
                    continue
                zpath = step_zip(pid, p, a.dry_run)
                upload_if_needed(zpath)
            except Exception as e:
                log(f"  FAILED  : {e}")
                status[pid] = "FAILED (zip): " + str(e).splitlines()[0]

        for pid in todo:
            st = status[pid]
            if st == "ok":
                results.append((pid, "would do" if a.dry_run else "done", ""))
            else:
                results.append((pid, "FAILED", st.split(": ", 1)[1] if ": " in st else st))
    finally:
        box.close()

    log("")
    log("Summary:")
    for pid, res, why in results:
        log(f"  {pid:<10} {res:<9} {why}")
    if not results:
        log("  nothing to do - everyone on the drive is complete on Box")
    log("Nothing was deleted. Check the QC report's Video tab before clearing space on the drive.")
    n_failed = sum(r[1] == "FAILED" for r in results)
    return 1 if n_failed else 0


if __name__ == "__main__":
    sys.exit(main())
