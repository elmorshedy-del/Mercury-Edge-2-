"""Official NOAA TGFTP climate reports as *date-checked* elimination proofs.

CLI is often yesterday's report and TGFTP DSM snapshots can be years old.
Never promote stale or non-current products to a trading proof. This module
does not replace the IEM DSM channel or METAR six-hour maxima.
"""
from __future__ import annotations
import logging
import re
from datetime import datetime, date, timedelta, timezone
from urllib.request import Request, urlopen

from feeds import ProofEvent

log = logging.getLogger("climate")
BASE = "https://tgftp.nws.noaa.gov/data/raw"
# Exact observed WMO/NWS identifiers, NOT inferred from station airport codes.
PRODUCTS = {
    "KNYC": ("cdus41.kokx.cli.nyc.txt", "cxus41.kokx.dsm.nyc.txt"),
    "KDEN": ("cdus45.kbou.cli.den.txt", "cxus45.kbou.dsm.den.txt"),
    "KPHL": ("cdus41.kphi.cli.phl.txt", "cxus41.kphi.dsm.phl.txt"),
    "KMDW": ("cdus43.klot.cli.mdw.txt", "cxus43.klot.dsm.mdw.txt"),
    "KAUS": ("cdus44.kewx.cli.aus.txt", "cxus44.kewx.dsm.aus.txt"),
    "KMIA": ("cdus42.kmfl.cli.mia.txt", "cxus42.kmfl.dsm.mia.txt"),
    "KLAX": ("cdus46.klox.cli.lax.txt", "cxus46.klox.dsm.lax.txt"),
}
MONTHS = {name: num for num, name in enumerate(
    ("JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
     "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"), 1)}
CLI_DATE = re.compile(
    r"CLIMATE\s+SUMMARY\s+FOR\s+([A-Z]+)\s+(\d{1,2})\s+(\d{4})",
    flags=re.IGNORECASE,
)
CLI_HIGH = re.compile(
    r"\bTEMPERATURE\s*\(F\)\s*\r?\n\s*TODAY\s*\r?\n\s*MAXIMUM\s+(\d{1,3})\b",
    flags=re.IGNORECASE,
)
DSM_ROW = re.compile(
    r"^\s*(K[A-Z0-9]{3})\s+DS\s+(?:COR\s+)?(?:(\d{4})\s+)?"
    r"(\d{2})/(\d{2})\s+(\d{2,3})(\d{4})/",
    re.MULTILINE,
)


def _product(url: str) -> str:
    req = Request(url, headers={"User-Agent": "mercury-edge2-weather/2",
                                "Cache-Control": "no-cache"})
    with urlopen(req, timeout=4) as resp:
        return resp.read(140000).decode("utf-8", errors="replace")


def _current(when: datetime, lst_offset_h: int) -> date:
    return (when + timedelta(hours=lst_offset_h)).date()


def _product_issue_is_recent(text: str, now: datetime, wmo_prefix: str) -> bool:
    # NOAA files can retain a superseded product for years. Validate the WMO
    # header release DDHHMM, station's WFO, and freshness independently.
    head = re.search(
        r"^("+re.escape(wmo_prefix)+r")\s+([A-Z]{4})\s+(\d{2})(\d{2})(\d{2})\s*$",
        text, re.M)
    if not head:
        return False
    day, hour, minute = (int(head.group(i)) for i in (3, 4, 5))
    if not (0 <= hour < 24 and 0 <= minute < 60):
        return False
    # Most recent possible header day; cope safely with month rollover.
    for delta_month in (0, -1, 1):
        y = now.year + (now.month - 1 + delta_month) // 12
        m = (now.month - 1 + delta_month) % 12 + 1
        try:
            stamp = datetime(y, m, day, hour, minute, tzinfo=timezone.utc)
        except ValueError:
            continue
        age = (now - stamp).total_seconds()
        if -10*60 <= age <= 36*3600:
            return True
    return False


def parse_cli(text: str, icao: str, offset: int, now: datetime) -> ProofEvent | None:
    if icao not in PRODUCTS:
        return None
    pil = "CLI" + icao[1:]
    first = text.splitlines()[:4]
    if not any(line.strip() == pil for line in first):
        return None
    if not _product_issue_is_recent(text, now, "CDUS"):
        return None
    match = CLI_DATE.search(text)
    if not match:
        return None
    month = MONTHS.get(match.group(1).upper())
    if month is None:
        return None
    try:
        cdate = date(int(match.group(3)), month, int(match.group(2)))
    except ValueError:
        return None
    # Climate date is LST for each Kalshi settlement station.
    if cdate != _current(now, offset):
        return None
    # The max must be in the TODAY section, never the normal, yesterday,
    # record-value, or month-to-date field; MM data is rejected.
    high = CLI_HIGH.search(text)
    if high is None:
        return None
    max_f = int(high.group(1))
    if not (-60 <= max_f <= 140):
        return None
    # CLI is an official same-day running maximum. The occurrence time is
    # not required, so obs_ts=None; first-seen publication is timestamped.
    return ProofEvent(icao, cdate, max_f, "cli", None, now,
                      detail=f"tgftp-cli {pil} date={cdate}")


def parse_dsm(text: str, icao: str, offset: int, now: datetime) -> ProofEvent | None:
    if icao not in PRODUCTS:
        return None
    pil = "DSM" + icao[1:]
    if not any(line.strip() == pil for line in text.splitlines()[:4]):
        return None
    if not _product_issue_is_recent(text, now, "CXUS"):
        return None
    for row in DSM_ROW.finditer(text):
        if row.group(1) != icao:
            continue
        dd, mm = int(row.group(3)), int(row.group(4))
        local_today = _current(now, offset)
        try:
            cdate = date(local_today.year, mm, dd)
        except ValueError:
            return None
        if cdate != local_today:
            return None
        max_f, hhmm = int(row.group(5)), row.group(6)
        if not (-60 <= max_f <= 140):
            return None
        if int(hhmm[:2]) > 23 or int(hhmm[2:]) > 59:
            return None
        # Local STANDARD time of maximum; convert to UTC. Only use as
        # provenance metadata, not as an inferred publication timestamp.
        obs = datetime(cdate.year, cdate.month, cdate.day,
                       int(hhmm[:2]), int(hhmm[2:]),
                       tzinfo=timezone.utc) - timedelta(hours=offset)
        if obs > now + timedelta(minutes=5):
            return None
        return ProofEvent(icao, cdate, max_f, "dsm", obs, now,
                          detail=f"tgftp-dsm {pil} max={hhmm}LST")
    return None


class TGFTPClimateFeed:
    def __init__(self, icao: str, lst_offset_h: int, product: str):
        if icao not in PRODUCTS or product not in ("cli", "dsm"):
            raise ValueError("Unsupported station or product")
        self.icao = icao
        self.lst = lst_offset_h
        self.product = product
        self._last: tuple | None = None

    def poll(self) -> list[ProofEvent]:
        filename = PRODUCTS[self.icao][0 if self.product == "cli" else 1]
        url = f"{BASE}/{'cd' if self.product == 'cli' else 'cx'}/{filename}"
        try:
            text = _product(url)
            seen = datetime.now(timezone.utc)
            event = (parse_cli(text, self.icao, self.lst, seen)
                     if self.product == "cli" else
                     parse_dsm(text, self.icao, self.lst, seen))
        except Exception as exc:
            log.warning("TGFTP %s %s failed: %s", self.product.upper(),
                        self.icao, type(exc).__name__)
            return []
        if event is None:
            return []
        sig = (event.climate_date, event.level_f, event.detail)
        if sig == self._last:
            return []
        self._last = sig
        return [event]
