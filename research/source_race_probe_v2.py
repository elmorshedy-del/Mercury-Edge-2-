"""Second-generation shadow latency probe.

Uses ``DirectSourceRace`` and NEVER places orders. It is intended to run beside,
not replace, the original IAD shadow while the hardened source architecture is
validated.

Bootstrap protection is intentionally conservative: the first two minutes are
excluded from fresh latency statistics so initial source caches/backfill cannot
be mistaken for publication latency. Old rows also carry an explicit
``measurement_valid`` field for future reports.
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

from direct_sources import DirectSourceRace  # noqa: E402
from network_probe import NetworkProbeWorker  # noqa: E402
from proof_bus import ProofBusReceiver  # noqa: E402

CFG = json.load(open(ROOT / "engine" / "config.json"))
DATA = Path(os.environ.get("WEATHERBOT_DATA_DIR", "/data"))
DATA.mkdir(parents=True, exist_ok=True)
OUT = DATA / "source_race_v2.jsonl"
WARM_START_S = max(120.0, float(os.getenv("MERCURY_PROBE_WARM_START_S", "120")))
MAX_MEASUREMENT_AGE_S = float(os.getenv("MERCURY_MAX_MEASUREMENT_AGE_S", "3600"))

race = DirectSourceRace(CFG)
stop = threading.Event()
bus = ProofBusReceiver(race.push, stop)
network = NetworkProbeWorker(stop, DATA)
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
threading.Thread(target=bus.run, daemon=True, name="proof-bus").start()
threading.Thread(target=network.run, daemon=True, name="network-probe").start()
race.start()
print(
    f"source-race-v2 shadow -> {OUT}; proof_bus={bus.path}; "
    f"bootstrap={WARM_START_S:.0f}s",
    flush=True,
)

while running:
    try:
        ev = race.get(timeout=1.0)
    except Exception:
        continue
    now = datetime.now(timezone.utc)
    uptime_s = time.monotonic() - started_mono
    source = ev.detail.split(" ", 1)[0] if ev.detail else ev.channel
    lag_s = None
    if ev.obs_ts is not None:
        lag_s = (ev.seen_ts - ev.obs_ts).total_seconds()
    warm = uptime_s <= WARM_START_S
    valid = (
        not warm
        and lag_s is not None
        and 0 <= lag_s <= MAX_MEASUREMENT_AGE_S
    )
    row = {
        "schema": 2,
        "recorded_ts": now.isoformat(),
        "probe_started_ts": started_wall.isoformat(),
        "probe_uptime_s": round(uptime_s, 3),
        "warm_start": warm,
        "measurement_valid": valid,
        "seen_ts": ev.seen_ts.isoformat(),
        "obs_ts": ev.obs_ts.isoformat() if ev.obs_ts else None,
        "obs_to_seen_ms": round(lag_s * 1000, 3) if lag_s is not None else None,
        "observation_age_s": round(lag_s, 3) if lag_s is not None else None,
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
