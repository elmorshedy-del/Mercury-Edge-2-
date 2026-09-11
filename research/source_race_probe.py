"""Shadow-only source latency recorder.

Run from repository root:
    PYTHONPATH=engine python research/source_race_probe.py

It NEVER places orders. Every ProofEvent emitted by public workers OR by the
local push bus (LDM/NWWS/FAA adapters) is appended to source_race.jsonl. This
lets us compare identical observations/products by actual first-seen time.

The first fetch from several sources contains historical/backfill observations.
Those records are retained for diagnostics but explicitly tagged ``warm_start``
so they cannot be mistaken for live publication latency.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

from fast_sources import SourceRace  # noqa: E402
from proof_bus import ProofBusReceiver  # noqa: E402

CFG = json.load(open(ROOT / "engine" / "config.json"))
DATA = Path(os.environ.get("WEATHERBOT_DATA_DIR", "/data"))
DATA.mkdir(parents=True, exist_ok=True)
OUT = DATA / "source_race.jsonl"
WARM_START_S = float(os.environ.get("MERCURY_PROBE_WARM_START_S", "30"))

race = SourceRace(CFG)
stop = threading.Event()
bus = ProofBusReceiver(race.push, stop)
running = True
started_wall = datetime.now(timezone.utc)
started_mono = time.monotonic()


def _stop(*_):
    global running
    running = False
    stop.set()
    race.close()


signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)

# Bind the push socket before public workers. External LDM/NWWS/FAA adapters can
# then race the HTTP sources into exactly the same queue.
threading.Thread(target=bus.run, daemon=True, name="proof-bus").start()
race.start()
print(
    f"source-race shadow started -> {OUT}; proof bus={bus.path}; "
    f"warm_start={WARM_START_S:.0f}s",
    flush=True,
)

while running:
    try:
        ev = race.get(timeout=1.0)
    except Exception:
        continue
    now = datetime.now(timezone.utc)
    uptime_s = time.monotonic() - started_mono
    source = (ev.detail.split(" ", 1)[0] if ev.detail else ev.channel)
    obs_lag_ms = None
    observation_age_s = None
    if ev.obs_ts is not None:
        obs_lag_ms = round((ev.seen_ts - ev.obs_ts).total_seconds() * 1000, 3)
        observation_age_s = round((ev.seen_ts - ev.obs_ts).total_seconds(), 3)
    row = {
        "recorded_ts": now.isoformat(),
        "probe_started_ts": started_wall.isoformat(),
        "probe_uptime_s": round(uptime_s, 3),
        "warm_start": uptime_s <= WARM_START_S,
        "seen_ts": ev.seen_ts.isoformat(),
        "obs_ts": ev.obs_ts.isoformat() if ev.obs_ts else None,
        "obs_to_seen_ms": obs_lag_ms,
        "observation_age_s": observation_age_s,
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
