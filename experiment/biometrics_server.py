"""
biometrics_server.py — receive webcam-biometrics data in Python.

A tiny, zero-dependency (pure stdlib) WebSocket server that the browser streams
biometric data to. You provide an `on_frame(frame)` callback and that's it —
everything else (the WebSocket protocol, clock synchronisation) is handled for you.

    from biometrics_server import BiometricsServer, to_row

    def on_frame(frame):
        # `frame` is the JSON the browser sent. All timing is under frame["times"]:
        #   times["capture"] : browser performance.now() when the frame was captured
        #   times["video"]   : camera frame timestamp (relative spacing only)
        #   times["frame"]   : monotonic frame counter
        # plus two added here:
        #   times["server"]  : this process's clock when the frame arrived
        #   times["aligned"] : capture-time mapped onto this clock (None until first sync)
        # to_row(frame) flattens it all to a friendly flat dict for logging/analysis.
        print(to_row(frame))

    BiometricsServer(on_frame=on_frame).run()   # ws://localhost:8080, Ctrl-C to stop

Why a server (not a client)? Browsers can only be WebSocket *clients*, so Python
hosts the server and the browser dials in.

For PsychoPy: run the server in a background thread and have `on_frame` push frames
into a queue.Queue that your experiment loop drains each flip — or use the
BiometricsRecorder helper below. Pass `clock=core.getTime` so `times["aligned"]` lands
on PsychoPy's experiment clock. See ws_receiver.py / psychopy_example.py.

The interesting parts are BiometricsServer, BiometricsRecorder, to_row, and ClockSync.
The WebSocket wire-protocol helpers at the bottom are boilerplate you can ignore.
"""

import base64
import hashlib
import json
import socket
import struct
import threading
import time
from typing import Callable, Optional


# ─── Clock synchronisation ────────────────────────────────────────────────────
class ClockSync:
    """
    Maps the browser's clock onto ours.

    The browser and Python each have their own stopwatch with a different zero, so
    a raw browser timestamp means nothing here. We periodically ping the browser; it
    echoes the ping back with its own clock reading. From the round-trip we estimate

        offset = browser_clock_seconds - our_clock_seconds

    keeping the estimate from the lowest round-trip (least network jitter → most
    accurate). Then any browser time converts to our timeline via `to_local`.
    """

    def __init__(self) -> None:
        self.offset: Optional[float] = None   # None until the first sync completes
        self.best_rtt = float("inf")
        self.samples = 0

    def add_sample(self, t_sent: float, browser_ms: float, t_received: float) -> None:
        rtt = t_received - t_sent
        midpoint = t_sent + rtt / 2.0          # when the browser echoed, on our clock
        offset = browser_ms / 1000.0 - midpoint
        self.samples += 1
        if rtt < self.best_rtt:
            self.best_rtt = rtt
            self.offset = offset

    def to_local(self, browser_ms: float) -> Optional[float]:
        if self.offset is None:
            return None
        return browser_ms / 1000.0 - self.offset


# ─── Server ───────────────────────────────────────────────────────────────────
class BiometricsServer:
    """
    Receives streamed biometric frames and calls `on_frame(frame)` for each one.

    Args:
        on_frame:      called with each frame (a dict). frame["times"] is enriched
                       with `server` and `aligned` (see module docstring / to_row).
        host, port:    where to listen. Default localhost:8080.
        clock:         a function returning monotonic seconds. Default
                       time.perf_counter. Pass psychopy.core.getTime to align
                       frames to your experiment clock.
        sync_interval: seconds between clock-sync pings. Default 1.5.
    """

    def __init__(
        self,
        on_frame: Callable[[dict], None],
        host: str = "localhost",
        port: int = 8080,
        clock: Callable[[], float] = time.perf_counter,
        sync_interval: float = 1.5,
        mono_clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self.on_frame = on_frame
        self.host = host
        self.port = port
        self.clock = clock
        self.sync_interval = sync_interval
        # Optional monotonic reference clock (e.g. core.getTime), sampled at frame
        # arrival into times['mono'] → the reset-proof `mono_time` column. Because it's
        # read at the same instant as the main clock, times['server'] - times['mono'] is
        # the exact, jitter-free offset; a jump in it means the main clock was reset.
        self.mono_clock = mono_clock

        self._server_sock: Optional[socket.socket] = None
        self._running = False

    # ── Lifecycle ──────────────────────────────────────────────────────────
    def run(self) -> None:
        """Listen and handle connections. Blocks until stop() or Ctrl-C."""
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(1)
        self._running = True
        print(f"biometrics server listening on ws://{self.host}:{self.port}")

        try:
            while self._running:
                conn, addr = self._server_sock.accept()
                # One experiment = one browser; handle each connection in a thread
                # so a disconnect/reconnect is clean.
                threading.Thread(
                    target=self._handle_connection, args=(conn, addr), daemon=True
                ).start()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def start(self) -> threading.Thread:
        """Run the server in a background thread (for PsychoPy). Returns the thread."""
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self._running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except OSError:
                pass
            self._server_sock = None

    # ── Per-connection handling ────────────────────────────────────────────
    def _handle_connection(self, conn: socket.socket, addr) -> None:
        if not _ws_handshake(conn):
            conn.close()
            return
        print(f"browser connected: {addr}")

        sync = ClockSync()
        send_lock = threading.Lock()
        alive = threading.Event()
        alive.set()

        # Ping the browser periodically for clock sync.
        def sync_loop() -> None:
            while alive.is_set():
                t_sent = self.clock()
                try:
                    _ws_send_json(conn, {"type": "sync", "tPySend": t_sent}, send_lock)
                except OSError:
                    return
                time.sleep(self.sync_interval)

        threading.Thread(target=sync_loop, daemon=True).start()

        try:
            while alive.is_set():
                opcode, payload = _ws_recv_frame(conn)
                if opcode == _OP_CLOSE:
                    break
                if opcode == _OP_PING:
                    _ws_send_frame(conn, payload, _OP_PONG)
                    continue
                if opcode != _OP_TEXT:
                    continue

                try:
                    msg = json.loads(payload.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    continue

                if msg.get("type") == "sync":
                    # The browser's echo of our ping — feed the round-trip to ClockSync.
                    t_send, browser_ms = msg.get("tPySend"), msg.get("tJs")
                    if t_send is not None and browser_ms is not None:
                        sync.add_sample(t_send, browser_ms, self.clock())
                    continue

                # A data frame. Add server + aligned timing under `times`, then hand off.
                times = msg.setdefault("times", {})
                times["server"] = self.clock()
                # Sample the monotonic reference at the SAME arrival instant (so
                # times['server'] - times['mono'] is the exact, jitter-free clock offset).
                if self.mono_clock is not None:
                    times["mono"] = self.mono_clock()
                capture = times.get("capture")
                times["aligned"] = sync.to_local(capture) if capture is not None else None
                self.on_frame(msg)
        except (ConnectionError, OSError):
            pass
        finally:
            alive.clear()
            conn.close()
            print(f"browser disconnected: {addr} "
                  f"(sync samples={sync.samples}, best_rtt={sync.best_rtt * 1000:.2f} ms)")


# The 52 MediaPipe face-blendshape names, in MediaPipe's own category order. Listed
# explicitly (not discovered from a frame) so the CSV keeps a stable column set even
# before the first frame arrives — ROW_COLUMNS is derived from to_row({}). These are
# the AU-equivalent expression coefficients (0..1), split left/right; map them onto
# FACS Action Units offline. See the AU mapping table in the examples README.
BLENDSHAPE_NAMES = [
    "_neutral",
    "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
    "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft", "eyeLookDownRight",
    "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight",
    "eyeLookUpLeft", "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight",
    "eyeWideLeft", "eyeWideRight",
    "jawForward", "jawLeft", "jawOpen", "jawRight",
    "mouthClose", "mouthDimpleLeft", "mouthDimpleRight", "mouthFrownLeft", "mouthFrownRight",
    "mouthFunnel", "mouthLeft", "mouthLowerDownLeft", "mouthLowerDownRight",
    "mouthPressLeft", "mouthPressRight", "mouthPucker", "mouthRight",
    "mouthRollLower", "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper",
    "mouthSmileLeft", "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight",
    "mouthUpperUpLeft", "mouthUpperUpRight", "noseSneerLeft", "noseSneerRight",
]


# ─── Flatten a frame to a friendly flat row ───────────────────────────────────
# Column names here are the documented analysis schema (see psychopy.md). Edit this
# one function if you want to rename columns or add fields.
def to_row(frame: dict) -> dict:
    times = frame.get("times") or {}
    gaze = frame.get("gaze") or {}
    heart = frame.get("heart") or {}
    signal = heart.get("signal") or {}
    bpm = heart.get("bpm") or {}
    blendshapes = frame.get("blendshapes") or {}
    row = {
        "time": times.get("aligned"),       # experiment clock (globalClock) — main time axis
        "mono_time": times.get("mono"),      # monotonic clock at arrival — reset-proof reference
        "capture_time": times.get("capture"),  # browser clock at capture
        "video_time": times.get("video"),   # camera clock (relative spacing only)
        "server_time": times.get("server"),  # arrival on the experiment clock (server - mono = exact offset)
        "frame": times.get("frame"),
        "face": frame.get("faceDetected"),
        "gaze_x": gaze.get("x"),
        "gaze_y": gaze.get("y"),
        "gaze_state": gaze.get("state"),
        "hr_raw": signal.get("raw"),
        "hr_filtered": signal.get("filtered"),
        "hr_peak": heart.get("peakDetected"),  # beat detected this frame
        "bpm_peak": bpm.get("peak"),
        "bpm_fft": bpm.get("fft"),
    }
    # One bs_<name> column per blendshape — None when no face was detected this frame.
    for name in BLENDSHAPE_NAMES:
        row["bs_" + name] = blendshapes.get(name)
    return row


ROW_COLUMNS = list(to_row({}).keys())   # stable column order for CSV headers


# ─── Recorder: collect frames into a list you can slice per trial ─────────────
class BiometricsRecorder:
    """
    Convenience wrapper for experiments (e.g. PsychoPy Builder). Runs the server in a
    background thread and:
      - (if `log` is given) writes EVERY frame to one continuous CSV for the whole
        session — the tidy, analysis-friendly file;
      - collects frames into an in-memory list you can slice per trial.

        bio = BiometricsRecorder(clock=core.getTime,
                                 log='session_biometrics.csv').start()  # Begin Experiment
        bio.clear()                                                     # Begin Routine
        rows = bio.rows()                                               # End Routine (flat dicts)
        bio.stop()                                                      # End Experiment

    The continuous log is independent of clear()/take() — those only affect the
    in-memory per-trial list. All methods are thread-safe.
    """

    def __init__(self, host: str = "localhost", port: int = 8080,
                 clock: Callable[[], float] = time.perf_counter,
                 log: Optional[str] = None,
                 mono_clock: Optional[Callable[[], float]] = None) -> None:
        self._lock = threading.Lock()
        self.frames: list = []
        self._log = open(log, "w", encoding="utf-8") if log else None
        if self._log:
            self._log.write(",".join(ROW_COLUMNS) + "\n")
        self._server = BiometricsServer(on_frame=self._collect, host=host, port=port,
                                        clock=clock, mono_clock=mono_clock)

    def _collect(self, frame: dict) -> None:
        row = to_row(frame)
        with self._lock:
            self.frames.append(frame)
            if self._log:
                self._log.write(",".join(str(row[c]) for c in ROW_COLUMNS) + "\n")
                self._log.flush()

    def start(self) -> "BiometricsRecorder":
        self._server.start()
        return self

    def stop(self) -> None:
        self._server.stop()
        if self._log:
            self._log.close()
            self._log = None

    def clear(self) -> None:
        """Drop collected frames (call at the start of a trial)."""
        with self._lock:
            self.frames = []

    def take(self) -> list:
        """Return collected frames and clear in one step (call at end of a trial)."""
        with self._lock:
            collected, self.frames = self.frames, []
        return collected

    def rows(self) -> list:
        """Snapshot of collected frames as flat dicts (see to_row)."""
        with self._lock:
            return [to_row(f) for f in self.frames]

    def write_clocksync(self, path: str, extra: "dict | None" = None) -> None:
        """Write a clock-relationship record: the main (experiment), monotonic, and wall
        clocks read back-to-back at one instant, so you can convert between them offline.
        Offsets: globalClock↔mono = t_mono - t_main;  mono↔wall = t_wall - t_mono.

        Pass `extra` to append any session-constant clock bases you read yourself —
        these get merged into the record verbatim. The Builder example passes the two
        reset times so you can also reach the absolute monotonic / PTB GetSecs base:
            extra={"mono_reset":   monotonicClock.getLastResetTime(),
                   "global_reset": globalClock.getLastResetTime()}
        See psychopy.md."""
        # Capture the live readings back-to-back first; merge caller-supplied constants after.
        record = {"t_main": self._server.clock(), "t_wall": time.time()}
        if self._server.mono_clock is not None:
            record["t_mono"] = self._server.mono_clock()
        if extra:
            record.update(extra)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)


# ─── WebSocket wire protocol (boilerplate — safe to ignore) ───────────────────
# A minimal RFC 6455 implementation: just enough to accept a browser connection and
# exchange text frames. You shouldn't need to touch any of this.

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_OP_TEXT, _OP_CLOSE, _OP_PING, _OP_PONG = 0x1, 0x8, 0x9, 0xA


def _ws_handshake(conn: socket.socket) -> bool:
    """Complete the HTTP Upgrade handshake. Returns True on success."""
    request = b""
    while b"\r\n\r\n" not in request:
        chunk = conn.recv(4096)
        if not chunk:
            return False
        request += chunk

    key = None
    for line in request.decode("latin-1").split("\r\n")[1:]:
        name, _, value = line.partition(":")
        if name.strip().lower() == "sec-websocket-key":
            key = value.strip()
            break
    if not key:
        return False

    accept = base64.b64encode(hashlib.sha1((key + _WS_GUID).encode()).digest()).decode()
    conn.sendall((
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
    ).encode())
    return True


def _recv_exact(conn: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed mid-frame")
        buf += chunk
    return buf


def _ws_recv_frame(conn: socket.socket):
    """Read one WebSocket frame. Returns (opcode, payload_bytes)."""
    header = _recv_exact(conn, 2)
    opcode = header[0] & 0x0F
    masked = (header[1] & 0x80) != 0
    length = header[1] & 0x7F
    if length == 126:
        length = struct.unpack(">H", _recv_exact(conn, 2))[0]
    elif length == 127:
        length = struct.unpack(">Q", _recv_exact(conn, 8))[0]

    mask = _recv_exact(conn, 4) if masked else b"\x00\x00\x00\x00"
    payload = bytearray(_recv_exact(conn, length))
    if masked:
        for i in range(length):
            payload[i] ^= mask[i % 4]
    return opcode, bytes(payload)


def _ws_send_frame(conn: socket.socket, payload: bytes, opcode: int = _OP_TEXT) -> None:
    """Send one unmasked frame (servers must not mask)."""
    header = bytearray([0x80 | opcode])     # FIN=1 + opcode
    length = len(payload)
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.append(126)
        header += struct.pack(">H", length)
    else:
        header.append(127)
        header += struct.pack(">Q", length)
    conn.sendall(bytes(header) + payload)


def _ws_send_json(conn: socket.socket, obj: dict, lock: threading.Lock) -> None:
    data = json.dumps(obj).encode("utf-8")
    with lock:   # the sync thread and main reader can both send; serialise them
        _ws_send_frame(conn, data, _OP_TEXT)
