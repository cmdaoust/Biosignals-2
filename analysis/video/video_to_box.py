r"""
video_to_box.py
===============
End-of-day archive of the webcam data: for every participant on the external drive whose
video files are not (all) on Box yet, make what's missing and upload it to Box over SFTP.

A participant is COMPLETE on Box when 3_Data/video holds all three (same rule as the QC report):
    <id>_frames.zip            the PNG frames (the lossless original), zipped without compression
    <id>_1to1_ffv1.avi         1:1 lossless video (000_convert_png_to_avi.py --method 1to1)
    <id>_frame_timestamps.csv  one row per frame (written by the experiment)
"On Box" means a file with that name (in any upper/lower case: Box ignores case) whose size is
right, so a half-finished upload never counts. The size is checked against, in order:
  - the local copy, if it's still on the drive (exact);
  - video_to_box_manifest.csv, the size recorded when this script uploaded it (exact);
  - otherwise (e.g. uploaded by hand, then deleted from the drive) a plausibility check against
    the participant's PNG frames, which are still on the drive: a zip must be >= 90% of the PNGs'
    total size, a video >= 10% of the frames' raw size (frames x width x height x 3). A file that
    fails is treated as missing and re-made; one that passes is accepted and noted in the log.
The script's own uploads go to <name>.part and are only renamed once complete and size-checked,
so an upload cut off part-way never appears under the real name.

Participants: every <id>_frames folder + <id>_frame_timestamps.csv in WEBCAM_PNG_EXTERNAL_DIR
(D:\Biosignals2_png_data) that isn't complete on Box. Two passes, so the videos (needed for the
analyses) reach Box before the slow zips:

PASS 1 - videos, for each participant:
  precheck- the number of PNGs must equal the number of timestamp rows, EXCEPT when the last rows
            have no PNG (the experiment closed before the last frames were written) and the PNGs
            still reach the end of the LAST recovery block (Positive or Negative Recovery, whichever
            came last: block order is counterbalanced) + VIDEO_TRIM_MARGIN_S (config.py, default 1 s).
            Then the video stops at the last frame with a PNG ("trimmed"). The block end comes from
            the participant's PsychoPy file in PSYCHOPY_DATA_DIR, using 001_generate_event_onsets.py's
            own event logic (else from <id>_video_events.csv in FACEREADER_ONSETS_DIR). No PsychoPy
            file, fewer than 2 recovery blocks, or missing PNGs mid-recording -> fails as before.
  video   - runs 000_convert_png_to_avi.py --method 1to1 if VIDEO_EXTERNAL_DIR has no video yet
  check   - the video's frame count must equal the number of PNGs and of timestamp rows used
            (catches a video left half-written by an interrupted conversion)
  upload  - the timestamps CSV and the video. For a trimmed participant, <id>_frame_timestamps.csv
            on Box is the TRIMMED copy (same rows as the video, from VIDEO_EXTERNAL_DIR), and the
            original goes up as <id>_frame_timestamps_untrimmed.csv (replacing a full copy already
            on Box; Box keeps the old one as a version)
  (a video already on Box is never re-made, even if it's no longer on the drive)
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
        "trim_margin_s": float(getattr(cfg, "VIDEO_TRIM_MARGIN_S", DEFAULT_TRIM_MARGIN_S)),
        "psychopy_dir": str(getattr(cfg, "PSYCHOPY_DATA_DIR", "") or ""),
        "onsets_dir": str(getattr(cfg, "FACEREADER_ONSETS_DIR", "") or ""),
    }
    return c


DEFAULT_TRIM_MARGIN_S = 1.0   # PNGs must reach this far past the end of the last recovery block
EVENTS_SCRIPT = os.path.join(HERE, "001_generate_event_onsets.py")
_MODULES = {}

def _module(path, name):
    if path not in _MODULES:
        spec = importlib.util.spec_from_file_location(name, path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _MODULES[path] = m
    return _MODULES[path]

def converter():
    """000_convert_png_to_avi.py as a module, so the trimming rule is the same in both scripts."""
    return _module(CONVERT_SCRIPT, "convert_png_to_avi")


def last_block_end(pid, c):
    """-> (seconds since recording start when the LAST recovery block ended, event name, source).
    Same clock as time_since_recording_start in the timestamps CSV. Raises if it can't be found
    or the session doesn't have both recovery blocks."""
    ev = _module(EVENTS_SCRIPT, "generate_event_onsets")
    tried = []
    d = c["psychopy_dir"]
    if d and os.path.isdir(d):
        files = [f for f in glob.glob(os.path.join(d, "*_*Psychopy*.csv"))
                 if pid_of(f) == pid and not f.lower().endswith("_biometrics.csv")]
        if len(files) > 1:
            raise RuntimeError(f"several PsychoPy files for {pid} in {d}: {[os.path.basename(f) for f in files]}")
        if files:
            import pandas as pd
            exp = pd.read_csv(files[0])
            fmt = ev.detect_format(exp.columns)
            if fmt is None:
                raise RuntimeError(f"{os.path.basename(files[0])} has no timing columns")
            events, _, _ = ev.extract_events(exp, fmt)
            rec = [(e["offset_s"], e["event"]) for e in events if e["event"].endswith("Recovery")]
            src = os.path.basename(files[0])
        else:
            tried.append(f"no {pid}_...Psychopy...csv in {d}")
    else:
        tried.append(f"PSYCHOPY_DATA_DIR {d or '(not set)'} not found")
    if tried:   # fall back on 001's output
        f = os.path.join(c["onsets_dir"], f"{pid}_video_events.csv") if c["onsets_dir"] else ""
        if not (f and os.path.exists(f)):
            raise RuntimeError("can't find when the last block ended: " + "; ".join(tried) +
                               f"; no {pid}_video_events.csv in FACEREADER_ONSETS_DIR")
        import pandas as pd
        df = pd.read_csv(f)
        rec = [(float(r.offset_s), r.event) for r in df.itertuples() if str(r.event).endswith("Recovery")]
        src = os.path.basename(f)
    n_blocks = len(ev.BLOCK_VALENCES["neg_first"])
    if len(rec) != n_blocks:
        raise RuntimeError(f"{src} has {len(rec)} recovery block(s), expected {n_blocks} (experiment stopped early?)")
    end, name = max(rec)
    return end, name, src


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
def step_video(pid, p, video_dir, dry, plan):
    avi = os.path.join(video_dir, f"{pid}_1to1_ffv1.avi")
    if os.path.exists(avi):
        log(f"  video   : exists ({human(os.path.getsize(avi))})")
        return avi
    if dry:
        log(f"  video   : would convert with 000_convert_png_to_avi.py --method 1to1 (slow)"
            f"{', trimmed' if plan['n_trim'] else ''}")
        return avi
    log("  video   : converting (this takes a while)...")
    t0 = time.time()
    r = subprocess.run([sys.executable, CONVERT_SCRIPT, p["frames_dir"], p["ts_csv"],
                        "--method", "1to1", "--output-dir", video_dir]
                       + (["--trim-if-complete-until", repr(plan["complete_until_s"])] if plan["n_trim"] else []),
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(avi):
        tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-8:])
        raise RuntimeError(f"000_convert_png_to_avi.py failed:\n{tail}")
    log(f"  video   : done in {(time.time() - t0) / 60:.0f} min ({human(os.path.getsize(avi))})")
    return avi


def step_precheck(pid, p, c):
    """Before the slow conversion: PNGs and timestamp rows must match, or the only difference
    must be PNGs missing at the very end, after the last recovery block ended (+ margin): those
    rows are trimmed off.
    -> plan dict: n_png, n_ts, n_keep (frames the video will have), n_trim, keep (frame indices)."""
    n_png = count_pngs(p["frames_dir"])
    n_ts = count_ts_rows(p["ts_csv"])
    plan = {"n_png": n_png, "n_ts": n_ts, "n_keep": n_ts, "n_trim": 0, "keep": None}
    if n_png == n_ts:
        return plan
    if n_png > n_ts:
        raise RuntimeError(f"{n_png} PNGs but {n_ts} timestamp rows - check the recording")
    conv = converter()
    rows = conv.load_timestamps(p["ts_csv"])
    try:
        end, block, src = last_block_end(pid, c)
    except Exception as e:
        raise RuntimeError(f"{n_png} PNGs but {n_ts} timestamp rows, and can't check whether the missing "
                           f"PNGs are after the last block: {e}")
    need = end + c["trim_margin_s"]
    try:
        kept, n_trim, trim_s = conv.trim_missing_tail(rows, conv.png_indices(p["frames_dir"]), need)
    except FileNotFoundError as e:
        raise RuntimeError(f"{n_png} PNGs but {n_ts} timestamp rows: {e}")
    log(f"  TRIM    : {n_png} PNGs but {n_ts} timestamp rows - the last {n_trim} rows have no PNG "
        f"({trim_s:.1f} s). Video will stop at frame {kept[-1][0]}, {conv.mmss(kept[-1][1])} into the "
        f"recording (was {conv.mmss(rows[-1][1])}); {block} ended at {conv.mmss(end)} ({src}), "
        f"so {kept[-1][1] - end:.1f} s of frames after it are kept.")
    plan.update(n_keep=len(kept), n_trim=n_trim, keep={i for i, _ in kept}, complete_until_s=need)
    return plan


def companion_ts(pid, video_dir):
    """The timestamps copy that sits next to the video (written by 000)."""
    return os.path.join(video_dir, f"{pid}_frame_timestamps.csv")


def step_timestamps(pid, p, plan, video_dir, dry):
    """-> the timestamps file to put on Box as <id>_frame_timestamps.csv: the original, or for a
    trimmed participant the trimmed copy next to the video (made here if 000 hasn't yet)."""
    if not plan["n_trim"]:
        return p["ts_csv"]
    ts = companion_ts(pid, video_dir)
    if os.path.exists(ts) and count_ts_rows(ts) == plan["n_keep"]:
        return ts
    if dry:
        log(f"  stamps  : would write the trimmed copy {ts} ({plan['n_keep']} rows)")
        return ts
    if os.path.exists(ts) and count_ts_rows(ts) != plan["n_ts"]:
        raise RuntimeError(f"{ts} has {count_ts_rows(ts)} rows, expected {plan['n_keep']} (trimmed) - "
                           "check which recording it belongs to, delete it and run again")
    os.makedirs(video_dir, exist_ok=True)
    converter().write_timestamps_subset(p["ts_csv"], ts, plan["keep"])   # replaces an untrimmed copy
    log(f"  stamps  : wrote the trimmed copy {ts} ({plan['n_keep']} rows)")
    return ts


def step_check(pid, p, avi, dry, plan):
    n_png, n_ts, n_keep = plan["n_png"], plan["n_ts"], plan["n_keep"]
    rows_txt = (f"{n_keep} timestamp rows" if not plan["n_trim"]
                else f"{n_keep} of {n_ts} timestamp rows (last {plan['n_trim']} have no PNG)")
    if dry and not os.path.exists(avi):
        log(f"  check   : {n_png} PNGs, {rows_txt} (video checked after conversion)")
        return
    n_vid = video_frames(avi)
    if n_vid != n_keep:
        raise RuntimeError(
            f"video has {n_vid} frames but should have {n_keep} ({n_png} PNGs, {rows_txt}) - probably a "
            f"conversion that was interrupted. Delete {avi} and run again.")
    log(f"  check   : {n_vid} video frames = {rows_txt} ({n_png} PNGs)")


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
    """SFTP connection to Box that reconnects when needed. Conversions and zips take hours, and
    an idle connection gets closed (by Box or the network) - so the connection is checked before
    every listing/upload, kept alive while idle, and an upload cut off part-way is retried."""
    RETRIES = 3

    def __init__(self, c, password):
        self.c, self.password = c, password
        self.transport = self.sftp = None
        self.connect()
        try:
            self.sftp.stat(c["remote_dir"])
        except IOError:
            self.close()
            raise RuntimeError(f"Box folder {c['remote_dir']} not found over SFTP - check BOX_VIDEO_REMOTE_DIR")

    def connect(self):
        import paramiko, base64, hashlib
        c = self.c
        self.close()
        t = paramiko.Transport((c["host"], c["port"]))
        t.default_window_size = 64 * 1024 * 1024   # faster for large files
        t.start_client(timeout=30)
        # Check it's really Box before sending the password (fingerprint published by Box:
        # support.box.com "Using Box with SFTP"; override with BOX_SFTP_FINGERPRINT in config.py).
        key = t.get_remote_server_key()
        fp = base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
        if c["host"] == "sftp.services.box.com" and fp != c["fingerprint"]:
            t.close()
            raise RuntimeError(f"server key fingerprint SHA256:{fp} is not Box's (SHA256:{c['fingerprint']}) - "
                               "not sending the password. If Box has changed its key, update BOX_SFTP_FINGERPRINT.")
        t.auth_password(username=c["user"], password=self.password)
        t.set_keepalive(30)
        self.transport = t
        self.sftp = paramiko.SFTPClient.from_transport(t)
        self.sftp.get_channel().settimeout(300)

    def ensure(self):
        """Reconnect if the connection has dropped (e.g. while a video was converting)."""
        alive = self.transport is not None and self.transport.is_active()
        if alive:
            try:
                self.sftp.stat(self.c["remote_dir"])
                return
            except Exception:
                pass
        log("  (re)connecting to Box...")
        self.connect()

    def sizes(self):
        """lower-case name -> (name as on Box, size) for every file in the remote folder.
        Box ignores case in file names (R2433_x.avi and r2433_x.avi are the same file), so
        names are matched case-insensitively."""
        self.ensure()
        return {a.filename.lower(): (a.filename, a.st_size)
                for a in self.sftp.listdir_attr(self.c["remote_dir"])}

    def upload(self, local, sizes, name=None):
        name = name or os.path.basename(local)
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
        for attempt in range(1, self.RETRIES + 1):
            try:
                self.ensure()
                last[0] = 0
                self.sftp.put(local, part, callback=progress, confirm=True)   # a retry overwrites the .part
                break
            except Exception as e:
                if attempt == self.RETRIES:
                    raise RuntimeError(f"upload of {name} failed {self.RETRIES} times (last error: {e})")
                log(f"  upload  : {name} interrupted ({e}) - reconnecting and retrying ({attempt + 1}/{self.RETRIES})")
                self.close()
                time.sleep(30 * attempt)
        self.ensure()
        if name.lower() in sizes:   # an incomplete/older copy: replace it (Box keeps the old one as a version)
            self.sftp.remove(posixpath.join(self.c["remote_dir"], sizes[name.lower()][0]))
        self.sftp.rename(part, remote)
        got = self.sftp.stat(remote).st_size
        sizes[name.lower()] = (name, got)
        if got != size:
            raise RuntimeError(f"{name}: {human(got)} on Box but {human(size)} locally")
        record_upload(name, size)
        mins = (time.time() - t0) / 60
        log(f"  upload  : {name} done ({human(size)}, {mins:.0f} min)")

    def close(self):
        for x in (self.sftp, self.transport):
            try:
                if x is not None:
                    x.close()
            except Exception:
                pass
        self.sftp = self.transport = None


def box_size(name, sizes):
    """Size of the file on Box with this name (any case), or None."""
    hit = sizes.get(name.lower())
    return hit[1] if hit else None


def on_box(name, local, sizes):
    return os.path.exists(local) and box_size(name, sizes) == os.path.getsize(local)


# Sizes of files this script uploaded (name -> bytes), so they can be checked exactly later,
# after the local copy has been deleted.
MANIFEST = {"path": None, "sizes": {}}

def load_manifest(path):
    MANIFEST["path"] = path
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f.read().splitlines()[1:]:
                parts = line.split(",")
                if len(parts) >= 3 and parts[2].isdigit():
                    MANIFEST["sizes"][parts[1].lower()] = int(parts[2])

def record_upload(name, size):
    new = not os.path.exists(MANIFEST["path"])
    with open(MANIFEST["path"], "a", encoding="utf-8") as f:
        if new:
            f.write("uploaded_at,name,bytes\n")
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S},{name},{size}\n")
    MANIFEST["sizes"][name.lower()] = size


ZIP_MIN_FRACTION = 0.90   # of the PNGs' total size
AVI_MIN_FRACTION = 0.10   # of the frames' raw size (frames x width x height x 3 bytes)

def png_stats(frames_dir, _cache={}):
    """(number of PNGs, total bytes, width, height) - cached per folder."""
    if frames_dir not in _cache:
        pngs = [e for e in os.scandir(frames_dir) if e.is_file() and e.name.lower().endswith(".png")]
        w = h = 0
        if pngs:
            with open(pngs[0].path, "rb") as f:
                head = f.read(24)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                w, h = int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
        _cache[frames_dir] = (len(pngs), sum(e.stat().st_size for e in pngs), w, h)
    return _cache[frames_dir]


def box_check(name, local, sizes, frames_dir):
    """('ok' | 'missing' | 'wrong size' | 'too small', message). See the docstring."""
    size = box_size(name, sizes)
    if size is None:
        return "missing", "not on Box"
    if os.path.exists(local):
        if size == os.path.getsize(local):
            return "ok", "same size as the local copy"
        return "wrong size", f"{human(size)} on Box but {human(os.path.getsize(local))} locally"
    if name.lower() in MANIFEST["sizes"]:
        want = MANIFEST["sizes"][name.lower()]
        if size == want:
            return "ok", "same size as when uploaded"
        return "wrong size", f"{human(size)} on Box but {human(want)} when uploaded"
    n, total, w, h = png_stats(frames_dir)
    if name.lower().endswith(".zip"):
        need, basis = ZIP_MIN_FRACTION * total, "of the PNGs' total size"
        frac = size / total if total else 0
    else:
        raw = n * w * h * 3
        need, basis = AVI_MIN_FRACTION * raw, "of the frames' raw size"
        frac = size / raw if raw else 0
    if size < need or size == 0:
        return "too small", f"only {human(size)} on Box ({frac:.0%} {basis}) - probably an unfinished upload"
    return "ok", f"{human(size)}, {frac:.0%} {basis} (no local copy: checked for plausibility only)"


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
    load_manifest(os.path.join(log_dir, "video_to_box_manifest.csv"))
    log("=" * 70)
    log(f"video_to_box {'DRY RUN ' if a.dry_run else ''}started {dt.datetime.now():%Y-%m-%d %H:%M}")
    log(f"Drive: {c['png_dir']} | videos: {c['video_dir']} | Box: {c['host']}:{c['remote_dir']}")
    log(f"Missing PNGs at the end of a recording: trimmed off only if the PNGs reach the end of the last "
        f"recovery block + {c['trim_margin_s']:g} s")

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
                     f"{pid}_frame_timestamps.csv": p["ts_csv"]}
            comp = companion_ts(pid, c["video_dir"])
            if (os.path.exists(comp) and count_ts_rows(comp) < count_ts_rows(p["ts_csv"])):
                # trimmed participant: the trimmed copy is the one that belongs with the video
                names[f"{pid}_frame_timestamps.csv"] = comp
                names[f"{pid}_frame_timestamps_untrimmed.csv"] = p["ts_csv"]
            # Complete = all three names on Box. Sizes are compared for files that exist locally.
            missing = [n for n, l in names.items() if box_check(n, l, sizes, p["frames_dir"])[0] != "ok"]
            if missing:
                todo.append(pid)
        log(f"On the drive: {len(local)} | complete on Box: {len(local) - len(todo)} | to do: {len(todo)} {todo}")
        for pid, why in problems:
            log(f"SKIPPED {pid}: {why}")
            results.append((pid, "skipped", why))

        def upload_if_needed(local_path, name=None):
            name = name or os.path.basename(local_path)
            if on_box(name, local_path, sizes):
                log(f"  upload  : {name} already on Box (same size)")
            elif a.dry_run:
                size = human(os.path.getsize(local_path)) if os.path.exists(local_path) else "not made yet"
                log(f"  upload  : would upload {name} ({size})")
            else:
                log(f"  upload  : {name} ({human(os.path.getsize(local_path))})...")
                box.upload(local_path, sizes, name)

        status = {}   # pid -> "ok" / "FAILED: ..."
        log("")
        log("PASS 1: videos + timestamps")
        for pid in todo:
            p = local[pid]
            log(f"── {pid} ──")
            try:
                avi = os.path.join(c["video_dir"], f"{pid}_1to1_ffv1.avi")
                vstate, vmsg = box_check(os.path.basename(avi), avi, sizes, p["frames_dir"])
                try:
                    plan = step_precheck(pid, p, c)
                except RuntimeError as e:
                    if vstate != "ok":
                        raise
                    # video already on Box (e.g. uploaded by hand): don't block the timestamps/zip
                    log(f"  WARNING : {e} (video already on Box, so carrying on)")
                    plan = {"n_trim": 0}
                ts = step_timestamps(pid, p, plan, c["video_dir"], a.dry_run)
                upload_if_needed(ts, f"{pid}_frame_timestamps.csv")
                if plan["n_trim"]:
                    upload_if_needed(p["ts_csv"], f"{pid}_frame_timestamps_untrimmed.csv")
                if vstate == "ok":
                    log(f"  video   : already on Box - kept ({vmsg})")
                else:
                    if vstate != "missing":
                        log(f"  video   : problem on Box: {vmsg} - will replace it")
                    avi = step_video(pid, p, c["video_dir"], a.dry_run, plan)
                    step_check(pid, p, avi, a.dry_run, plan)
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
                zstate, zmsg = box_check(zname, zlocal, sizes, p["frames_dir"])
                if zstate == "ok":
                    log(f"  zip     : already on Box - kept ({zmsg})")
                    continue
                if zstate != "missing":
                    log(f"  zip     : problem on Box: {zmsg} - will replace it")
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
