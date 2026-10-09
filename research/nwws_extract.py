"""Fail-closed NOAA NWWS-OI climate product decoding.

NWWS has one national stream, not per-station subscriptions. Filter by exact
AWIPS+WMO identifiers before extracting a station's usable high. A NOAA CLI
commonly summarizes YESTERDAY; it must be assigned to its report date instead
of the issue date. A DSM may include a previous local-standard-time day.

Research results are *observations*, not executable trading orders.
"""
from __future__ import annotations

import re
from datetime import date as Date, datetime, timedelta, timezone

# AWIPS suffix, ICAO station, issuing WFO, bulletin WMO number.
CONFIG = {
    "NYC": ("KNYC", "KOKX", "41"),
    "DEN": ("KDEN", "KBOU", "45"),
    "PHL": ("KPHL", "KPHI", "41"),
    "MDW": ("KMDW", "KLOT", "43"),
    "AUS": ("KAUS", "KEWX", "44"),
    "MIA": ("KMIA", "KMFL", "42"),
    "LAX": ("KLAX", "KLOX", "46"),
}
MONTHS = {m: n for n, m in enumerate((
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"), 1)}
DSM_ROW = re.compile(
    r"(?m)^\s*(K[A-Z0-9]{3})\s+DS\s+(?:COR\s+)?(?:\d{4}\s+)?"
    r"(\d{2})/(\d{2})\s+([^\s/]+)")
DSM_HIGH = re.compile(r"^(\d{2,3})(\d{4})$")
CLI_DATE = re.compile(
    r"\bCLIMATE SUMMARY FOR\s+([A-Z]+)\s+(\d{1,2})\s+(\d{4})\b",re.I)
CLI_TEMPS = re.compile(
    r"\bTEMPERATURE\s*\(F\)\s*([\s\S]*?)(?=\bPRECIPITATION\s*\(|\Z)",re.I)
CLI_MAX = re.compile(
    r"(?m)^\s*(?:TODAY|YESTERDAY)\s*\n\s*MAXIMUM\s+(\d{1,3})(?!\d)",re.I)
METAR_LINE = re.compile(
    r"(?m)^\s*(K[A-Z0-9]{3})\s+(\d{2})(\d{2})(\d{2})Z\b([^\n]*)")
T_GROUP = re.compile(r"\bT([01])(\d{3})([01])(\d{3})\b")
SIXHR = re.compile(r"\b1([01])(\d{3})\b")


def normalize_datetime(s: str | None):
    if not s: return None
    try:
        d = datetime.fromisoformat(s.replace("Z","+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError, TypeError):
        return None


def _year_from_issue(month: int, day: int, issued: datetime):
    candidates = []
    for year in (issued.year-1, issued.year, issued.year+1):
        try:
            d = Date(year, month, day)
        except ValueError:
            continue
        # WFO climate-day report can have the previous calendar date;
        # allow up to two days age in UTC, not an arbitrary old bulletin.
        if -2 <= (issued.date()-d).days <= 3:
            candidates.append(d)
    return min(candidates, key=lambda d: abs((issued.date()-d).days)) if candidates else None


def extract_evidence(event: dict):
    """Return decoded reports, or a reason the product is not usable.

    Only exact DSMxxx/CLIxxx with matching WMO and physical station qualify.
    Missing maxima never create a fabricated 0 or a lower-bound proof.
    """
    awips = event.get("awipsid","").strip().upper()
    ttaaii = event.get("ttaaii","").strip().upper()
    raw = event.get("raw","")
    received = normalize_datetime(event.get("first_seen_utc"))
    issued = normalize_datetime(event.get("issue_utc"))
    result = {"awipsid":awips, "product_type":event.get("product_type"),
              "first_seen_utc":event.get("first_seen_utc"),
              "issue_utc":event.get("issue_utc"),
              "report_key":None, "evidence":[], "reason":None}

    kind = awips[:3]
    suffix = awips[3:]
    if kind not in ("DSM","CLI") or suffix not in CONFIG or len(awips)!=6:
        result["reason"]="not_target_climate_product"
        return result
    station, wfo, number = CONFIG[suffix]
    result["station"]=station
    result["product_type"]=kind
    expected = ("CXUS" if kind=="DSM" else "CDUS")+number
    header = re.search(r"(?m)^\s*"+expected+r"\s+"+wfo+r"\s+(\d{6})\s*$",raw,re.I)
    pil = re.search(r"(?m)^\s*"+re.escape(awips)+r"\s*$",raw,re.I)
    if ttaaii != expected or not header or not pil:
        result["reason"]="wrong_wmo_or_awips_identity"
        return result
    result["report_key"]=f"{expected}:{wfo}:{header.group(1)}:{awips}"

    if kind=="DSM":
        match = next((m for m in DSM_ROW.finditer(raw) if m.group(1)==station),None)
        if not match:
            result["reason"]="station_row_missing"
            return result
        if not issued: 
            result["reason"]="issue_time_missing"
            return result
        climate_day = _year_from_issue(int(match.group(3)),int(match.group(2)),issued)
        if not climate_day:
            result["reason"]="dsm_date_stale_or_invalid"
            return result
        hi = DSM_HIGH.fullmatch(match.group(4))
        if not hi:
            result["reason"]="dsm_max_missing"
            return result
        high, hhmm = int(hi.group(1)), hi.group(2)
        if not (-40 <= high <= 135 and int(hhmm[:2])<=23 and int(hhmm[2:])<=59):
            result["reason"]="dsm_high_out_of_range"
            return result
        result["evidence"]=[{"station":station,"kind":"DSM",
            "climate_date":climate_day.isoformat(),"max_f":high,
            "max_time_lst":hhmm}]
    else:
        m = CLI_DATE.search(raw)
        if not m or not issued:
            result["reason"]="cli_report_date_missing"
            return result
        mon = MONTHS.get(m.group(1).upper())
        try:
            climate_day = Date(int(m.group(3)),mon,int(m.group(2)))
        except (ValueError,TypeError):
            result["reason"]="cli_date_invalid"
            return result
        if not (-2 <= (issued.date()-climate_day).days <= 3):
            result["reason"]="cli_report_date_stale"
            return result
        temps = CLI_TEMPS.search(raw)
        top = CLI_MAX.search(temps.group(1)) if temps else None
        if not top:
            result["reason"]="cli_observed_high_missing"
            return result
        high = int(top.group(1))
        if not (-40 <= high <= 135):
            result["reason"]="cli_high_out_of_range"
            return result
        result["evidence"]=[{"station":station,"kind":"CLI",
            "climate_date":climate_day.isoformat(),"max_f":high}]
    result["reason"]="ok"
    # Receipt age is not necessarily publication delay; do not conflate.
    result["issue_lag_s"]=(
        round((received-issued).total_seconds(),3)
        if received and issued else None)
    return result


def tgftp_url(awipsid: str):
    awipsid=awipsid.upper()
    kind=awipsid[:3]
    suffix=awipsid[3:]
    if kind not in ("DSM","CLI") or suffix not in CONFIG:
        return None
    _,wfo,num=CONFIG[suffix]
    head=("cxus" if kind=="DSM" else "cdus")+num
    return f"https://tgftp.nws.noaa.gov/data/raw/{'cx' if kind=='DSM' else 'cd'}/{head}.{wfo.lower()}.{kind.lower()}.{suffix.lower()}.txt"
