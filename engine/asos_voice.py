"""Parse ASOS computer-generated telephone/radio voice transcripts into proofs.

ASOS voice temperature is spoken in whole degrees Celsius. That is not enough to
reconstruct the exact whole-F value in every case, but it *is* enough to prove a
hard Fahrenheit floor using the same whole-C inversion already used by Mercury's
OMO path.

At towered airports controllers may select either current OMO or a METAR for the
voice message. We therefore do not assume every call is one-minute data. A voice
message is latency-actionable only when its own spoken Zulu valid time is fresh.
Old/repeated METAR voice remains harmless and produces no fast-path proof.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from decode import wholeC_floor
from feeds import ProofEvent

DIGIT = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "niner": "9",
    "nine": "9",
}
TOKEN_RE = re.compile(r"[a-z]+|[-+]?\d+", re.I)


def _nearest_utc_time(hh: int, mm: int, now: datetime) -> datetime:
    candidates = []
    for d in (-1, 0, 1):
        base = now + timedelta(days=d)
        candidates.append(base.replace(hour=hh, minute=mm, second=0, microsecond=0))
    return min(candidates, key=lambda x: abs((x - now).total_seconds()))


def _digit_sequence(tokens: list[str]) -> int | None:
    if not tokens:
        return None
    sign = 1
    if tokens[0] in ("minus", "negative"):
        sign = -1
        tokens = tokens[1:]
    if not tokens:
        return None
    digits = []
    for tok in tokens:
        if tok in DIGIT:
            digits.append(DIGIT[tok])
        elif re.fullmatch(r"\d+", tok):
            # ASR providers often normalize spoken digits to a number.
            digits.extend(list(tok))
        else:
            return None
    if not 1 <= len(digits) <= 3:
        return None
    return sign * int("".join(digits))


def _spoken_zulu(tokens: list[str]) -> tuple[int, int] | None:
    """Find the final four spoken digits immediately preceding 'zulu'."""
    for i, tok in enumerate(tokens):
        if tok != "zulu":
            continue
        # Walk backwards collecting individual digits/numeric groups.
        collected: list[str] = []
        j = i - 1
        while j >= 0 and len(collected) < 4:
            t = tokens[j]
            if t in DIGIT:
                collected.append(DIGIT[t])
            elif re.fullmatch(r"\d+", t):
                collected.extend(reversed(list(t)))
            else:
                break
            j -= 1
        if len(collected) >= 4:
            s = "".join(reversed(collected[:4]))
            hh, mm = int(s[:2]), int(s[2:])
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                return hh, mm
    return None


def parse_voice_transcript(icao: str, lst_offset_h: int, transcript: str,
                           seen_ts: datetime | None = None,
                           max_age_s: float = 150.0) -> ProofEvent | None:
    """Return an OMO-floor proof only for an unambiguous, fresh ASOS voice line."""
    now = seen_ts or datetime.now(timezone.utc)
    text = " ".join(TOKEN_RE.findall(transcript.lower()))
    tokens = text.split()
    if "automated" not in tokens or "weather" not in tokens or "observation" not in tokens:
        return None
    z = _spoken_zulu(tokens)
    if z is None:
        return None
    obs = _nearest_utc_time(z[0], z[1], now)
    age = (now - obs).total_seconds()
    if age < -30 or age > max_age_s:
        return None

    try:
        ti = tokens.index("temperature")
        ci = tokens.index("celsius", ti + 1)
    except ValueError:
        return None
    temp_c = _digit_sequence(tokens[ti + 1:ci])
    if temp_c is None or not -60 <= temp_c <= 60:
        return None

    floor_f = wholeC_floor(temp_c)
    cdate = (obs + timedelta(hours=lst_offset_h)).date()
    return ProofEvent(
        station=icao,
        climate_date=cdate,
        level_f=floor_f,
        channel="omo_floor",
        obs_ts=obs,
        seen_ts=now,
        detail=(f"asos-voice {temp_c}C floor={floor_f}F age={age:.1f}s "
                f"transcript={text[:140]}"),
    )
