"""Shadow-only source latency recorder.

Run from repository root:
    PYTHONPATH=engine python research/source_race_probe.py

It NEVER places orders. Every ProofEvent emitted by fast_sources is appended to
/data/source_race.jsonl (or WEATHERBOT_DATA_DIR). This lets us compare the same
observation across TGFTP, AviationWeather, MADIS HF and IEM DSM by actual
first-seen time instead of guessing from provider documentation.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

from fast_sources import SourceRace  # noqa: E402

CFG = json.load(open(ROOT / "engine" / "config.json"))
DATA = Path(os.environ.get("WEATHERBOT_DATA_DIR", "/data"))
DATA.mkdir(parents=True, exist_ok=True)
OUT = DATA / "source_race.jsonl"

race = SourceRace(CFG)
running = True


def _stop(*_):
    global running
    running = False
    race.close()


signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)

race.start()
print(f"source-race shadow started -> {OUT}", flush=True)

while running:
    try:
        ev = race.get(timeout=1.0)
    except Exception:
        continue
    now = datetime.now(timezone.utc)
    source = (ev.detail.split(" ", 1)[0] if ev.detail else ev.channel)
    obs_lag_ms = None
    if ev.obs_ts is not None:
        obs_lag_ms = round((ev.seen_ts - ev.obs_ts).total_seconds() * 1000, 3)
    row = {
        "recorded_ts": now.isoformat(),
        "seen_ts": ev.seen_ts.isoformat(),
        "obs_ts": ev.obs_ts.isoformat() if ev.obs_ts else None,
        "obs_to_seen_ms": obs_lag_ms,
        "station": ev.station,
        "climate_date": str(ev.climate_date),
        "level_f": ev.level_f,
        "channel": ev.channel,
        "source": source,
        "detail": ev.detail,
    }
    with OUT.open("a") as f:
        f.write(json.dumps(row, separators=(",", ":")) + "\n")
    print(json.dumps(row, separators=(",", ":")), flush=True)
    time.sleep(0)
