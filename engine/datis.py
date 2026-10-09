"""Fast airport ATIS weather evidence for the Mercury elimination bot.

ATIS Relay hosts multiple airports, but a feed contributes only if its
ATIS information line contains an unambiguous METAR T-group. Do not use
the rounded 2-digit Celsius text to assert an exact whole-F temperature.
ATIS data is not one-minute ASOS/OMO and never substitutes for DSM.
"""
from __future__ import annotations

import html
import logging
import re
import time
import urllib.request
from datetime import datetime, timedelta, timezone

from decode import c10_to_f
from feeds import ProofEvent, TGRP

log = logging.getLogger("datis")
ENDPOINT = "https://atisrelay.com/datis/{icao}"

# Examples from ATIS Relay (multiple airport formats):
# LAX ATIS INFO X 1653Z. ...
# PHL ARR INFO I 1454Z. ...
# PHL DEP INFO V 1454Z. ...
# MDW ATIS INFO O 1333Z SPECIAL. ...
# DEN ARR INFO G 1453Z. ...
HEAD = re.compile(
    r"\b(?P<airport>[A-Z]{3})\s+(?:(?:ARR|DEP)\s+)?(?:ATIS\s+)?INFO\s+"
    r"(?P<letter>[A-Z])\s+(?P<hhmm>\d{4})Z\b(?:\s+SPECIAL)?\.",
    flags=re.IGNORECASE,
)
TEMP_PAIR = re.compile(r"\bM?\d{2}/M?\d{2}\b")
CUTOFF = re.compile(r"(?:\.\.\.\s*ADVS|\bNOTAMS\b|<\s*/\s*p\s*>|<\s*/\s*h[123]\s*>)", re.I)


def decode_page(page: str, icao: str, seen: datetime) -> tuple[datetime, int, str] | None:
    """Return newest exact report as (obs UTC, proven F, ATIS letter); otherwise none.

    Never cross from a station's ATIS sentence into the ordinary METAR widget.
    This is important: that widget can update later than the actual ATIS.
    """
    if not re.fullmatch(r"K[A-Z]{3}", icao):
        return None
    airport = icao[1:]
    candidates = []
    for m in HEAD.finditer(page):
        if m.group("airport").upper() != airport:
            continue
        hhmm = m.group("hhmm")
        hh, mm = int(hhmm[:2]), int(hhmm[2:])
        if not (hh < 24 and mm < 60):
            continue
        # Precision group is in the weather segment near the front of ATIS.
        # Limit the segment to protect against unrelated website METAR text.
        segment = page[m.end():m.end() + 400]
        next_head = HEAD.search(segment)
        if next_head:
            segment = segment[:next_head.start()]
        end = CUTOFF.search(segment)
        if end:
            segment = segment[:end.start()]
        segment = re.sub(r"<[^>]*>", " ", html.unescape(segment))
        if not TEMP_PAIR.search(segment):
            continue
        t = TGRP.search(segment)
        if not t:
            continue
        c10 = int(t.group(2)) / 10 * (-1 if t.group(1) == "1" else 1)
        proven_f = c10_to_f(c10)
        if not (-60 <= proven_f <= 140):
            continue
        obs = seen.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if obs > seen + timedelta(minutes=5):
            obs -= timedelta(days=1)
        age = (seen - obs).total_seconds()
        if not (-300 <= age <= 90 * 60):
            continue
        candidates.append((obs, proven_f, m.group("letter").upper()))
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate[0])


class DATISFeed:
    def __init__(self, icao: str, lst_offset_h: int):
        if not re.fullmatch(r"K[A-Z]{3}", icao):
            raise ValueError("Invalid ICAO identifier")
        self.icao = icao
        self.lst = lst_offset_h
        self._newest_obs: datetime | None = None
        self._seen: set[tuple[datetime, int]] = set()
        self._fail_count = 0
        self._retry_after = 0.0

    def poll(self) -> list[ProofEvent]:
        if time.monotonic() < self._retry_after:
            return []
        req = urllib.request.Request(
            ENDPOINT.format(icao=self.icao),
            headers={"User-Agent": "Mozilla/5.0 (Mercury weather observations)",
                     "Cache-Control": "no-cache"})
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                page = response.read(200000).decode(errors="replace")
        except Exception as exc:
            self._fail_count += 1
            # The ATIS Relay service has been returning HTTP 500s for many
            # airports. Cap repeated retries/log noise, while NOAA's TGFTP
            # official METAR remains independently available.
            backoff_s = min(900, 30 * (2 ** min(self._fail_count - 1, 5)))
            self._retry_after = time.monotonic() + backoff_s
            if self._fail_count in (1, 2, 3, 6, 12) or self._fail_count % 48 == 0:
                log.warning("D-ATIS %s temporarily unavailable: %s (retry in %ds)",
                            self.icao, type(exc).__name__, backoff_s)
            return []
        self._fail_count = 0
        self._retry_after = 0.0
        now = datetime.now(timezone.utc)
        parsed = decode_page(page, self.icao, now)
        if parsed is None:
            return []
        obs, level_f, letter = parsed
        if self._newest_obs is not None and obs < self._newest_obs:
            return []  # Some ATIS pages temporarily regress to old letters.
        self._newest_obs = obs
        key = (obs, level_f)
        if key in self._seen:
            return []
        self._seen.add(key)
        if len(self._seen) > 1024:
            self._seen = {key}
        return [ProofEvent(
            self.icao, (obs + timedelta(hours=self.lst)).date(), level_f,
            "metar", obs, now,
            detail=f"atisrelay-datis letter={letter} obs={obs.isoformat()}",
            source="atisrelay-datis")]
