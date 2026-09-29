"""Pure DSM decoder shared by HTTP, LDM and NWWS push adapters."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone, date as Date

from feeds import ProofEvent

DSBODY = re.compile(r"^(K\w{3})\s+DS\s+(?:(\d{4})\s+)?(\d{2})/(\d{2})\s+(.*)$")
MAXTOK = re.compile(r"^(\d{2,3})(\d{4})$")


def _closest_date(month: int, day: int, now: datetime) -> Date | None:
    candidates: list[Date] = []
    for y in (now.year - 1, now.year, now.year + 1):
        try:
            candidates.append(Date(y, month, day))
        except ValueError:
            pass
    if not candidates:
        return None
    return min(candidates, key=lambda d: abs((datetime(d.year, d.month, d.day,
                                                       tzinfo=timezone.utc) - now).total_seconds()))


def parse_dsm_line(line: str, icao: str, lst_offset_h: int, source: str,
                   seen_ts: datetime | None = None) -> ProofEvent | None:
    now = seen_ts or datetime.now(timezone.utc)
    m = DSBODY.match(line.strip())
    if not m or m.group(1) != icao:
        return None
    hhmm, dd, mm = m.group(2), int(m.group(3)), int(m.group(4))
    token = m.group(5).split("/")[0].strip()
    mt = MAXTOK.match(token)
    if not mt:
        return None
    max_f, max_hhmm = int(mt.group(1)), mt.group(2)
    if not 20 <= max_f <= 130:
        return None
    cdate = _closest_date(mm, dd, now)
    if cdate is None:
        return None
    obs = None
    try:
        # DSM max_hhmm is local-standard time. Convert to UTC using configured
        # fixed LST offset, matching the settlement decoder's convention.
        local = datetime(cdate.year, cdate.month, cdate.day,
                         int(max_hhmm[:2]) % 24, int(max_hhmm[2:]) % 60,
                         tzinfo=timezone.utc)
        obs = local - timedelta(hours=lst_offset_h)
    except Exception:
        pass
    return ProofEvent(
        station=icao,
        climate_date=cdate,
        level_f=max_f,
        channel="dsm",
        obs_ts=obs,
        seen_ts=now,
        detail=f"{source} DS {hhmm or 'final'} max {max_f}F @{max_hhmm} LST",
    )


def parse_dsm_text(text: str, city_cfgs: dict[str, dict], source: str,
                   seen_ts: datetime | None = None) -> list[ProofEvent]:
    now = seen_ts or datetime.now(timezone.utc)
    by_icao = {c["icao"]: c for c in city_cfgs.values()}
    out: list[ProofEvent] = []
    for raw in text.splitlines():
        line = raw.strip()
        m = DSBODY.match(line)
        if not m:
            continue
        c = by_icao.get(m.group(1))
        if not c:
            continue
        ev = parse_dsm_line(line, c["icao"], c["lst_offset_h"], source, now)
        if ev:
            out.append(ev)
    return out
