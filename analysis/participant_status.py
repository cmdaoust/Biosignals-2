"""
participant_status.py - read analysis/participant_status.csv from Python scripts.

    from participant_status import pilot_ids, excluded_ids, status_of
    if status_of(pid) != "main": ...

Same file and rules as participant_status.R (see that file for the column meanings).
Anyone not listed is a main-study participant.
"""
import csv
import os

STATUS_VALUES = ("pilot", "test", "excluded")
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "participant_status.csv")


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
