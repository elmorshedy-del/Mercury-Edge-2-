"""FAA CSS-Wx / SWIM payload -> Mercury ProofEvent bridge.

CSS-Wx subscription access is JMS/NEMS (SWIFT/SWIM) and the broker/JNDI details
are provisioned per consumer. This module deliberately separates *transport*
from *weather semantics*: the eventual JMS receiver only has to pass each
message body into ``decode_csswx_message``.

Safety policy
-------------
* METAR/SPECI: actionable only when a raw coded report is present. It is fed to
  Mercury's already-tested METAR decoder.
* One Minute Observation (OMO): recorded as ``faa_omo_candidate`` only. Direct
  OMO is upstream and potentially much faster, but a raw one-minute sensor value
  is not assumed to equal the settlement temperature statistic. It cannot reach
  the current kill strategy because that channel is not enabled there.

Once real provisioned payloads are available, save examples and tighten the
schema-specific selectors before considering OMO actionability.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from feeds import ProofEvent
from fast_sources import parse_metar_proofs
from proof_bus import send_proof

HERE = Path(__file__).resolve().parent
CFG = json.load(open(HERE / "config.json"))
CITY_BY_ICAO = {c["icao"]: c for c in CFG["cities"].values()}
ICAOS = set(CITY_BY_ICAO)

RAW_NAMES = {
    "rawtext", "rawreport", "reporttext", "metartext", "rawmetar",
    "observationtext", "codedreport",
}
STATION_NAMES = {
    "stationidentifier", "stationid", "icaoidentifier", "icao", "airportid",
    "locationindicatoricao", "aerodrome", "designator",
}
TIME_NAMES = {
    "observationtime", "phenomenontime", "validtime", "datetime", "timeposition",
}
TEMP_NAMES = {"airtemperature", "temperature", "temperaturevalue", "temp"}
ICAO_RE = re.compile(r"\bK[A-Z0-9]{3}\b")
RAW_METAR_RE = re.compile(r"(?:(?:METAR|SPECI)\s+)?K[A-Z0-9]{3}\s+\d{6}Z\b.*")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1].lower()


def _texts(root: ET.Element, names: set[str]) -> Iterable[tuple[ET.Element, str]]:
    for el in root.iter():
        if _local(el.tag) in names and el.text and el.text.strip():
            yield el, el.text.strip()


def _parse_time(text: str) -> datetime | None:
    s = text.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        # Compact SWIM-ish timestamp fallback: YYYYMMDDHHMMSS[.sss]
        m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?:\.\d+)?", s)
        if not m:
            return None
        dt = datetime(*map(int, m.groups()), tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _station(root: ET.Element) -> str | None:
    candidates = []
    for _el, txt in _texts(root, STATION_NAMES):
        candidates.extend(ICAO_RE.findall(txt.upper()))
        if txt.upper() in ICAOS:
            candidates.append(txt.upper())
    # Attributes are common in XML exchange models.
    for el in root.iter():
        for key, value in el.attrib.items():
            if _local(key) in STATION_NAMES:
                candidates.extend(ICAO_RE.findall(str(value).upper()))
    unique = [x for x in dict.fromkeys(candidates) if x in ICAOS]
    return unique[0] if len(unique) == 1 else None


def _obs_time(root: ET.Element) -> datetime | None:
    vals = []
    for _el, txt in _texts(root, TIME_NAMES):
        dt = _parse_time(txt)
        if dt:
            vals.append(dt)
    # Prefer the earliest plausible recent time when wrappers contain issue time
    # and observation time together. The real CSS-Wx schema will let us tighten
    # this after first payload capture.
    now = datetime.now(timezone.utc)
    vals = [v for v in vals if abs((now - v).total_seconds()) < 48 * 3600]
    return min(vals) if vals else None


def _raw_reports(root: ET.Element) -> list[str]:
    out = []
    for _el, txt in _texts(root, RAW_NAMES):
        for line in txt.splitlines():
            line = line.strip()
            if RAW_METAR_RE.match(line):
                out.append(line)
    # Some envelopes put the coded report in a generic text node. Restrict this
    # fallback to text that unmistakably looks like a METAR/SPECI.
    if not out:
        for el in root.iter():
            if not el.text:
                continue
            for line in el.text.splitlines():
                line = line.strip()
                if RAW_METAR_RE.match(line):
                    out.append(line)
    return list(dict.fromkeys(out))


def _temperature_c(root: ET.Element) -> float | None:
    """Return temperature in C only when units are explicit/unambiguous."""
    found = []
    for el, txt in _texts(root, TEMP_NAMES):
        try:
            value = float(txt)
        except ValueError:
            continue
        uom = " ".join(str(v) for k, v in el.attrib.items()
                       if _local(k) in {"uom", "unit", "units"}).lower()
        if not uom:
            continue
        if any(x in uom for x in ("cel", "degc", "celsius")):
            found.append(value)
        elif uom in {"k", "kelvin"} or "kelvin" in uom:
            found.append(value - 273.15)
        elif any(x in uom for x in ("degf", "fahrenheit")):
            found.append((value - 32.0) * 5.0 / 9.0)
    if not found:
        return None
    # Fail closed if one message contains contradictory temperatures.
    if max(found) - min(found) > 0.25:
        return None
    return found[0]


def _unwrap(payload: bytes | str) -> str:
    text = payload.decode(errors="replace") if isinstance(payload, bytes) else payload
    text = text.strip()
    if text.startswith("{"):
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return text
        for key in ("payload", "body", "message", "xml", "data"):
            val = obj.get(key)
            if isinstance(val, str) and val.lstrip().startswith("<"):
                return val
    return text


def decode_csswx_message(payload: bytes | str,
                         seen_ts: datetime | None = None) -> list[ProofEvent]:
    seen = seen_ts or datetime.now(timezone.utc)
    text = _unwrap(payload)
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        # Some provisioned products may be a raw coded report rather than XML.
        out = []
        for line in text.splitlines():
            line = line.strip()
            m = ICAO_RE.search(line)
            if not m or m.group(0) not in ICAOS or not RAW_METAR_RE.match(line):
                continue
            c = CITY_BY_ICAO[m.group(0)]
            out.extend(parse_metar_proofs(line, m.group(0), int(c["lst_offset_h"]),
                                          "faa-csswx-metar", seen))
        return out

    out: list[ProofEvent] = []
    # Actionable route: coded METAR/SPECI only.
    for raw in _raw_reports(root):
        m = ICAO_RE.search(raw)
        if not m or m.group(0) not in ICAOS:
            continue
        icao = m.group(0)
        c = CITY_BY_ICAO[icao]
        out.extend(parse_metar_proofs(raw, icao, int(c["lst_offset_h"]),
                                      "faa-csswx-metar", seen))

    # Measurement-only OMO route.
    icao = _station(root)
    obs = _obs_time(root)
    temp_c = _temperature_c(root)
    if icao and obs and temp_c is not None:
        age = (seen - obs).total_seconds()
        if -30 <= age <= 3600:
            city = CITY_BY_ICAO[icao]
            cdate = (obs + timedelta(hours=int(city["lst_offset_h"]))).date()
            # This is deliberately NOT an enabled strategy channel. The value is
            # only a conservative numeric marker for latency comparison.
            level_f = math.floor(temp_c * 9.0 / 5.0 + 32.0)
            out.append(ProofEvent(
                icao, cdate, level_f, "faa_omo_candidate", obs, seen,
                detail=f"faa-csswx-omo temp_c={temp_c:.3f} measurement_only",
            ))
    return out


def main() -> None:
    """Transport-neutral bridge.

    The provisioned JMS/Solace receiver can invoke this function's decoder
    directly. For integration testing, stdin accepts one JSON/XML message per
    ASCII record-separator (0x1e), or one compact JSON/XML record per line.
    """
    data = sys.stdin.buffer.read()
    records = data.split(b"\x1e") if b"\x1e" in data else data.splitlines()
    for raw in records:
        if not raw.strip():
            continue
        for ev in decode_csswx_message(raw):
            send_proof(ev)
            print(json.dumps({
                "station": ev.station,
                "channel": ev.channel,
                "level_f": ev.level_f,
                "obs_ts": ev.obs_ts.isoformat() if ev.obs_ts else None,
                "seen_ts": ev.seen_ts.isoformat(),
                "detail": ev.detail,
            }, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
