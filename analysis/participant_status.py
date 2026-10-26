"""
participant_status.py - read participant_status.csv from Python scripts.

The file lives on Box (3_Data) and must NOT be committed to git; its
location comes from config.py at the repo root (PARTICIPANT_STATUS_PATH, else
SERVER_ROOT/participant_status.csv).

    from participant_status import pilot_ids, excluded_ids, status_of
    if status_of(pid) != "main": ...

Same file and rules as participant_status.R (see that file for the column meanings).
Anyone not listed is a main-study participant.
"""
import csv
import os

STATUS_VALUES = ("pilot", "test", "excluded")
def _default_path():
    import importlib.util
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.py")
    if not os.path.isfile(cfg_path):
        raise FileNotFoundError(f"participant_status.csv: no config.py at {cfg_path}")
    spec = importlib.util.spec_from_file_location("_ps_config", cfg_path)
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    if getattr(cfg, "PARTICIPANT_STATUS_PATH", None):
        return cfg.PARTICIPANT_STATUS_PATH
    return os.path.join(cfg.SERVER_ROOT, "participant_status.csv")


PATH = _default_path()


def norm_id(x):
    return "".join(str(x).split()).upper()


def read_participant_status(path=PATH):
    rows = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            pid = norm_id(r.get("participant_id", ""))
            if not pid:
                continue
            status = (r.get("status") or "").strip().lower()
            reason = (r.get("reason") or "").strip()
            if status not in STATUS_VALUES:
                raise ValueError(f"participant_status.csv: unknown status {status!r} for {pid}")
            if pid in rows:
                raise ValueError(f"participant_status.csv: {pid} listed more than once")
            if status == "excluded" and not reason:
                raise ValueError(f"participant_status.csv: {pid} excluded without a reason")
            rows[pid] = {"status": status, "reason": reason}
    return rows


STATUS = read_participant_status()


def status_of(pid):
    """'main', 'pilot', 'test' or 'excluded'."""
    return STATUS.get(norm_id(pid), {}).get("status", "main")


def pilot_ids():
    return [p for p, r in STATUS.items() if r["status"] == "pilot"]


def excluded_ids():
    """Test sessions + rejected participants."""
    return [p for p, r in STATUS.items() if r["status"] in ("test", "excluded")]
