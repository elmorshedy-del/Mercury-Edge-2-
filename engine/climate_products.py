"""TGFTP NOAA climate products: same-day CLI and DSM elimination proofs.

These are additive to IEM DSM and METAR/SIXHR. NOAA station-file paths can
contain very old products or products for neighboring airports. Reject rather
than guess: check WFO, AWIPS ID, station, report date, and reported maximum.
Never interpret a 'YESTERDAY' CLI or the *normals* table as a live proof.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone, date as Date
import logging
import re

from feeds import ProofEvent, DSBODY, MAXTOK, _get

log = logging.getLogger("climate_products")
ROOT = "https://tgftp.nws.noaa.gov/data/raw"
# (WFO, WMO/CX number, product city, permitted station).
STATIONS = {
    "KNYC": ("KOKX", "41", "NYC"),
    "KDEN": ("KBOU", "45", "DEN"),
    "KPHL": ("KPHI", "41", "PHL"),
    "KMDW": ("KLOT", "43", "MDW"),
    "KAUS": ("KEWX", "44", "AUS"),
    "KMIA": ("KMFL", "42", "MIA"),
    "KLAX": ("KLOX", "46", "LAX"),
}
MONTH = {name: i for i, name in enumerate(
    ("JANUARY","FEBRUARY","MARCH","APRIL","MAY","JUNE","JULY",
     "AUGUST","SEPTEMBER","OCTOBER","NOVEMBER","DECEMBER"), 1)}
CLI_SUMMARY = re.compile(
    r"\bCLIMATE SUMMARY FOR\s+([A-Z]+)\s+(\d{1,2})\s+(\d{4})\b", re.I)
TEMP_SECTION = re.compile(
    r"TEMPERATURE\s*\(F\)\s*\n([\s\S]*?)(?:\bPRECIPITATION\b|\bSNOWFALL\b|\Z)",
    re.I)
TODAY_MAX = re.compile(
    r"^\s*TODAY\s*\n\s*MAXIMUM\s+(\d{1,3})\b", re.I | re.M)


def _fresh_bulletin_header(line: str, now: datetime) -> bool:
    """Reject cached/stale NOAA WMO products even when day/month coincides.

    WMO DDHHMM has no month/year. Require a recent release from the closest
    candidate month; this handles real month and year rollovers without
    assuming every NOAA file updates daily.
    """
    m = re.fullmatch(r"(?:CDUS|CXUS)\d{2}\s+[A-Z]{4}\s+"
                     r"(\d{2})(\d{2})(\d{2})", line.strip(), re.I)
    if m is None:
        return False
    day, hour, minute = map(int, m.groups())
    if hour >= 24 or minute >= 60:
        return False
    for dmonth in (-1, 0, 1):
        ym = now.year * 12 + now.month - 1 + dmonth
        year, month0 = divmod(ym, 12)
        try:
            issued = datetime(year, month0 + 1, day, hour, minute,
                              tzinfo=timezone.utc)
        except ValueError:
            continue
        age = (now - issued).total_seconds()
        if -600 <= age <= 36 * 3600:
            return True
    return False


def urls(icao: str) -> dict[str, str]:
    office, number, city = STATIONS[icao]
    office = office.lower()
    city = city.lower()
    return {
        "cli": f"{ROOT}/cd/cdus{number}.{office}.cli.{city}.txt",
        "dsm": f"{ROOT}/cx/cxus{number}.{office}.dsm.{city}.txt",
    }


def parse_cli(text: str, icao: str, lst_off: int, now: datetime) -> ProofEvent | None:
    """Only today's observed MAXIMUM, never yesterday, forecast, or normal."""
    if icao not in STATIONS:
        return None
    wfo, number, city = STATIONS[icao]
    # Require the exact official bulletin header, AWIPS ID, and report label.
    top = text.splitlines()
    if len(top) < 4:
        return None
    if not re.fullmatch(
        rf"CDUS{number}\s+{wfo}\s+\d{{6}}", top[0].strip(), flags=re.I):
        return None
    if not _fresh_bulletin_header(top[0], now):
        return None
    if top[1].strip().upper() != "CLI" + city:
        return None
    if "CLIMATE REPORT" not in text[:250].upper():
        return None
    header = CLI_SUMMARY.search(text)
    if not header:
        return None
    month = MONTH.get(header.group(1).upper())
    if month is None:
        return None
    try:
        reported = Date(int(header.group(3)), month, int(header.group(2)))
    except ValueError:
        return None
    today_lst = (now + timedelta(hours=lst_off)).date()
    if reported != today_lst:
        return None

    section = TEMP_SECTION.search(text)
    if not section:
        return None
    segment = section.group(1)
    # Today max must be in the observed temperature block. A normal shown
    # elsewhere in the report must never be promoted into tradable evidence.
    maximum = TODAY_MAX.search(segment)
    if not maximum:
        return None
    level = int(maximum.group(1))
    if not (-50 <= level <= 135):
        return None
    return ProofEvent(icao, reported, level, "cli", None, now,
                      f"tgftp CLI{city} official TODAY maximum={level}F",source="tgftp")


def parse_dsm(text: str, icao: str, lst_off: int, now: datetime) -> ProofEvent | None:
    if icao not in STATIONS:
        return None
    wfo, number, city = STATIONS[icao]
    rows = text.splitlines()
    if len(rows) < 3:
        return None
    if not re.fullmatch(
        rf"CXUS{number}\s+{wfo}\s+\d{{6}}", rows[0].strip(), flags=re.I):
        return None
    if not _fresh_bulletin_header(rows[0], now):
        return None
    if rows[1].strip().upper() != "DSM" + city:
        return None
    today = (now + timedelta(hours=lst_off)).date()
    for row in rows[2:]:
        m = DSBODY.match(row.strip())
        if not m or m.group(1) != icao:
            continue
        if int(m.group(3)) != today.day or int(m.group(4)) != today.month:
            continue
        tok = m.group(5).split("/")[0].strip()
        max_match = MAXTOK.fullmatch(tok)
        if not max_match:
            continue
        level = int(max_match.group(1))
        stamp = max_match.group(2)
        h, minute = int(stamp[:2]), int(stamp[2:])
        if not (0 <= h <= 23 and 0 <= minute <= 59 and -50 <= level <= 135):
            continue
        observed = datetime(today.year, today.month, today.day, h, minute,
                            tzinfo=timezone.utc) - timedelta(hours=lst_off)
        if observed > now + timedelta(minutes=5):
            continue
        return ProofEvent(icao, today, level, "dsm", observed, now,
                          f"tgftp DSM{city} max={level}F time={stamp} LST",
                          source="tgftp")
    return None


class TGFTPClimateFeed:
    def __init__(self, icao: str, lst_offset_h: int, kind: str):
        if icao not in STATIONS or kind not in ("dsm", "cli"):
            raise ValueError("Unknown climate product")
        self.icao, self.lst, self.kind = icao, lst_offset_h, kind
        self.url = urls(icao)[kind]
        self._seen = set()

    def poll(self) -> list[ProofEvent]:
        try:
            raw = _get(self.url, timeout=4).decode(errors="replace")
        except Exception as exc:
            log.debug("tgftp %s %s unavailable: %s",
                      self.kind, self.icao, type(exc).__name__)
            return []
        now = datetime.now(timezone.utc)
        ev = (parse_cli(raw, self.icao, self.lst, now)
              if self.kind == "cli"
              else parse_dsm(raw, self.icao, self.lst, now))
        if ev is None:
            return []
        fingerprint = (ev.climate_date, ev.level_f, ev.obs_ts)
        if fingerprint in self._seen:
            return []
        self._seen.add(fingerprint)
        if len(self._seen) > 300:
            self._seen = {fingerprint}
        return [ev]
