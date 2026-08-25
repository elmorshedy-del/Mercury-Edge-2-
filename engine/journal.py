"""journal.py — append-only event journal powering the dashboard.
Kinds: proof | intent | fill | guard | system | census | window"""
from __future__ import annotations
import json, os, logging, threading
from datetime import datetime, timezone

DATA_DIR = os.environ.get("WEATHERBOT_DATA_DIR",
                          os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
PATH = os.path.join(DATA_DIR, "events.jsonl")
_lock = threading.Lock()

def emit(kind: str, **payload):
    row = {"ts": datetime.now(timezone.utc).isoformat(), "kind": kind, **payload}
    with _lock, open(PATH, "a") as f:
        f.write(json.dumps(row) + "\n")
    return row

def tail(limit: int = 300) -> list[dict]:
    if not os.path.exists(PATH):
        return []
    with open(PATH) as f:
        lines = f.readlines()[-limit:]
    out = []
    for ln in reversed(lines):
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    return out

class JournalHandler(logging.Handler):
    """Mirror WARNING+ from engine loggers (guards, spread filters) into the journal."""
    def emit(self, record):
        try:
            if record.levelno >= logging.WARNING:
                globals()["emit"]("guard" if "GUARD" in record.getMessage() else "system",
                                 logger=record.name, level=record.levelname,
                                 msg=record.getMessage()[:400])
        except Exception:
            pass

def attach_log_bridge():
    h = JournalHandler()
    for name in ("strategy", "feeds", "market", "runtime"):
        logging.getLogger(name).addHandler(h)
