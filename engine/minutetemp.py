"""Optional minuteTemp one-minute ASOS source for Mercury's elimination bot.

Supply MT_KEY in Mercury's Railway service variables. Do not query when no
key is present. Always use the lower *uncertainty bound* for elimination
rather than the displayed reconstructed Fahrenheit point estimate.
"""
from __future__ import annotations

import json
import logging
import math
import os
import urllib.request
from datetime import datetime, timedelta, timezone

from feeds import ProofEvent

log = logging.getLogger("minutetemp")
BASE = "https://api.minutetemp.com/api/v1/stations/{icao}/observations/latest"


def _parse_time(value):
    if isinstance(value, (int, float)):
        # Support documented or future Unix epoch timestamps; reject milliseconds
        if not (1_000_000_000 <= float(value) <= 4_000_000_000):
            return None
        return datetime.fromtimestamp(value, timezone.utc)
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def decode_latest(payload: dict, icao: str, lst_offset_h: int, seen: datetime):
    """Fail closed without station, precise observation time, or temp_min_f."""
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    obs = data.get("observation")
    if not isinstance(obs, dict) or obs.get("is_locf") is True:
        return None
    st = data.get("station")
    station = obs.get("station_id")
    if not station and isinstance(st, dict):
        station = st.get("station_id")
    if str(station).upper() != icao:
        return None
    observed = None
    for name in ("observation_time", "observed_at", "obs_ts", "timestamp",
                 "time", "valid_time", "observed_time", "datetime"):
        observed = _parse_time(obs.get(name))
        if observed:
            break
    if observed is None:
        return None
    age_s = (seen - observed).total_seconds()
    if not (-120 <= age_s <= 20 * 60):
        return None
    minimum = obs.get("temp_min_f")
    if isinstance(minimum, bool) or not isinstance(minimum, (int, float)):
        return None
    if not math.isfinite(minimum) or not (-80 <= minimum <= 140):
        return None
    temperature = obs.get("temperature_f")
    if (temperature is not None and isinstance(temperature, (int, float))
        and math.isfinite(temperature) and minimum > temperature + 0.1):
        return None
    # The minimum of the vendor's precision envelope is a lower bound on
    # possible true F; flooring cannot overstate an observed whole-F maximum.
    return ProofEvent(icao, (observed + timedelta(hours=lst_offset_h)).date(),
                      math.floor(minimum), "omo_floor", observed, seen,
                      detail=f"minutetemp-rest lower={minimum:.2f}F obs={observed.isoformat()}")


class MinuteTempFeed:
    def __init__(self, icao: str, lst_offset_h: int, api_key: str):
        self.icao = icao
        self.lst = lst_offset_h
        self.api_key = api_key
        self._seen = set()

    def poll(self) -> list[ProofEvent]:
        req = urllib.request.Request(
            BASE.format(icao=self.icao),
            headers={"X-API-Key": self.api_key, "User-Agent": "MercuryEdge2/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                raw = json.loads(response.read(100000))
            seen = datetime.now(timezone.utc)
            ev = decode_latest(raw, self.icao, self.lst, seen)
        except Exception as exc:
            # Deliberately never include req headers or API key in logs.
            log.warning("minuteTemp %s request/decode failed: %s", self.icao, type(exc).__name__)
            return []
        if ev is None:
            return []
        key = (ev.obs_ts, ev.level_f)
        if key in self._seen:
            return []
        self._seen.add(key)
        if len(self._seen) > 1000:
            self._seen = {key}
        return [ev]
