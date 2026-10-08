"""Read the D-ATIS weather sentence at KLAX from ATIS Relay's public page.

This is an independent, earlier METAR-temperature proof lane, *not* OMO or DSM.
Require an exact T-group; rounded spoken temperatures are never trade evidence.
ATIS Relay can regress to old letters, hence monotone observation-time filtering.
"""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timedelta, timezone
import urllib.request

from decode import c10_to_f
from feeds import ProofEvent, TGRP

log = logging.getLogger("datis")
ATIS_URL = "https://atisrelay.com/datis/KLAX"
# Observed D-ATIS format: "LAX ATIS INFO X 1653Z. ... T02560211. INST..."
HEAD = re.compile(r"\bLAX\s+ATIS\s+INFO\s+([A-Z])\s+(\d{4})Z\.", re.I)
BODY_END = re.compile(r"(?:\.\s*INST\b|\.\.\.\s*ADVS\b|</p>|</meta>|</script>)", re.I)


def decode_klax_page(page: str, seen: datetime) -> tuple[datetime, int, str] | None:
    """Return (observation_utc, proven_whole_F, ATIS_letter), or fail closed."""
    m = HEAD.search(page)
    if not m:
        return None
    hhmm = m.group(2)
    h, minute = int(hhmm[:2]), int(hhmm[2:])
    if not (h < 24 and minute < 60):
        return None
    raw = page[m.end():m.end() + 600]
    cutoff = BODY_END.search(raw)
    if cutoff:
        raw = raw[:cutoff.start()]
    body = re.sub(r"<[^>]*>", " ", html.unescape(raw))
    if not re.search(r"\bM?\d{2}/M?\d{2}\b", body):
        return None  # basic weather-wording sanity check
    t = TGRP.search(body)
    if not t:
        return None
    c10 = int(t.group(2)) / 10 * (-1 if t.group(1) == "1" else 1)
    obs = seen.replace(hour=h, minute=minute, second=0, microsecond=0)
    if obs > seen + timedelta(minutes=5):
        obs -= timedelta(days=1)
    age = (seen - obs).total_seconds()
    if age < -300 or age > 95 * 60:
        return None
    proven = c10_to_f(c10)
    if not (-60 <= proven <= 140):
        return None
    return obs, proven, m.group(1).upper()


class DATISFeed:
    def __init__(self, icao: str, lst_offset_h: int):
        if icao != "KLAX":
            raise ValueError("Only measured KLAX D-ATIS has been validated")
        self.icao = icao
        self.lst = lst_offset_h
        self._newest_obs: datetime | None = None
        self._seen: set[tuple] = set()

    def poll(self) -> list[ProofEvent]:
        now = datetime.now(timezone.utc)
        req = urllib.request.Request(
            ATIS_URL, headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
        try:
            with urllib.request.urlopen(req, timeout=4) as response:
                page = response.read(250000).decode("utf-8", errors="replace")
        except Exception as exc:
            log.warning("D-ATIS KLAX unavailable: %s", exc)
            return []
        parsed = decode_klax_page(page, datetime.now(timezone.utc))
        if parsed is None:
            return []
        obs, level_f, letter = parsed
        if self._newest_obs is not None and obs < self._newest_obs:
            return []  # ATIS Relay sometimes returns a prior letter briefly.
        self._newest_obs = obs
        key = (obs, level_f)
        if key in self._seen:
            return []
        self._seen.add(key)
        if len(self._seen) > 1000:
            self._seen = {key}  # bound long-lived state
        seen = datetime.now(timezone.utc)
        return [ProofEvent(
            self.icao, (obs + timedelta(hours=self.lst)).date(), level_f,
            "metar", obs, seen, f"datis-atisrelay letter={letter} obs={obs.isoformat()}")]
