"""feeds.py — the three proof channels. Each feed yields ProofEvents:
a claim '(station, climate_date) daily max >= level_f' with source + timestamps.

Channels (measured live lags):
  DSM   — settlement-grade running max + minute it occurred; wire ~:15+0-2min
  METAR — T-group exact whole-F (hourly + SPECI); 6-hr max groups at synoptics
  OMO   — MADIS hfmetar 5-min whole-C; floor(candidates) is a hard lower bound;
          measured availability 2.3 min typical (up to ~7)
"""
from __future__ import annotations
import re, gzip, io, json, logging, urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone, date as Date
from decode import c10_to_f, kelvin_to_wholeC, wholeC_floor

log = logging.getLogger("feeds")
UA = {"User-Agent": "weatherbot-v1"}

def _get(url: str, timeout=15) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()

@dataclass(frozen=True)
class ProofEvent:
    station: str            # ICAO, e.g. KNYC
    climate_date: Date      # LST calendar date the claim applies to
    level_f: int            # proven: daily max >= level_f
    channel: str            # 'dsm' | 'metar' | 'sixhr' | 'omo_floor'
    obs_ts: datetime | None # when the underlying observation happened (UTC)
    seen_ts: datetime       # when WE saw it (UTC)
    detail: str = ""

# --------------------------------------------------------------- DSM
DSBODY = re.compile(r'^(K\w{3})\s+DS\s+(?:(\d{4})\s+)?(\d{2})/(\d{2})\s+(.*)$')
MAXTOK = re.compile(r'^(\d{2,3})(\d{4})$')

class DSMFeed:
    """Polls IEM AFOS for DSM products. Settlement-grade whole F + max minute.
    Poll ONLY inside configured windows (be polite); NWWS-OI push replaces this
    for production latency (see README)."""
    def __init__(self, pil: str, icao: str, lst_offset_h: int):
        self.pil, self.icao, self.lst = pil, icao, lst_offset_h
        self._seen: set[str] = set()

    def poll(self) -> list[ProofEvent]:
        url = f"https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?pil={self.pil}&fmt=text&limit=3"
        try:
            txt = _get(url).decode(errors="replace")
        except Exception as e:
            log.warning("DSM poll %s failed: %s", self.pil, e); return []
        now = datetime.now(timezone.utc)
        out = []
        for ln in txt.splitlines():
            m = DSBODY.match(ln.strip())
            if not m or m.group(1) != self.icao:
                continue
            key = ln.strip()
            if key in self._seen:
                continue
            self._seen.add(key)
            hhmm, dd, mm = m.group(2), int(m.group(3)), int(m.group(4))
            tok = m.group(5).split("/")[0].strip()
            mt = MAXTOK.match(tok)
            if not mt:
                continue
            max_f, max_hhmm = int(mt.group(1)), mt.group(2)
            try:
                cdate = Date(now.year, mm, dd)
            except ValueError:
                continue
            obs = None
            try:
                obs = (datetime(cdate.year, cdate.month, cdate.day,
                                int(max_hhmm[:2]) % 24, int(max_hhmm[2:]) % 60,
                                tzinfo=timezone.utc) - timedelta(hours=self.lst))
            except Exception:
                pass
            # sanity: plausible temperature, date is today/yesterday in LST
            if not (20 <= max_f <= 130):
                log.error("DSM sanity reject %s max=%s", self.pil, max_f); continue
            out.append(ProofEvent(self.icao, cdate, max_f, "dsm", obs, now,
                                  detail=f"DS {hhmm or 'final'} max {max_f}F @{max_hhmm} LST"))
        return out

# ------------------------------------------------------------- METAR
TGRP  = re.compile(r'\bT([01])(\d{3})([01])(\d{3})\b')
SIXHR = re.compile(r'\b1([01])(\d{3})\b')

class MetarFeed:
    """aviationweather.gov raw METARs. T-group = exact whole F 'current temp'
    (proves max >= that value). 6-hr groups at 00/06/12/18Z prove window max."""
    def __init__(self, icao: str, lst_offset_h: int):
        self.icao, self.lst = icao, lst_offset_h
        self._seen: set[str] = set()

    def _climate_date(self, obs: datetime) -> Date:
        return (obs + timedelta(hours=self.lst)).date()

    def poll(self) -> list[ProofEvent]:
        url = f"https://aviationweather.gov/api/data/metar?ids={self.icao}&format=raw&hours=2"
        try:
            txt = _get(url).decode(errors="replace")
        except Exception as e:
            log.warning("METAR poll %s failed: %s", self.icao, e); return []
        now = datetime.now(timezone.utc); out = []
        for raw in txt.splitlines():
            raw = raw.strip()
            if not raw or raw in self._seen:
                continue
            self._seen.add(raw)
            dm = re.search(r'\b(\d{2})(\d{2})(\d{2})Z\b', raw)
            if not dm:
                continue
            obs = now.replace(day=int(dm.group(1)), hour=int(dm.group(2)),
                              minute=int(dm.group(3)), second=0, microsecond=0)
            if obs > now + timedelta(hours=1):   # month boundary
                obs -= timedelta(days=31)
            cdate = self._climate_date(obs)
            t = TGRP.search(raw)
            if t:
                c10 = int(t.group(2)) / 10.0 * (-1 if t.group(1) == "1" else 1)
                out.append(ProofEvent(self.icao, cdate, c10_to_f(c10), "metar", obs, now, raw[:60]))
            # synoptic reports are stamped :51-:56 of the PRIOR hour (1751Z carries
            # the 18Z-cycle groups) — detect by rounding forward 15 minutes
            if (obs + timedelta(minutes=15)).hour in (0, 6, 12, 18):
                s = SIXHR.search(raw)
                if s:
                    c10 = int(s.group(2)) / 10.0 * (-1 if s.group(1) == "1" else 1)
                    # 6-hr window can straddle the LST midnight — attribute to the
                    # climate date of (obs - 3h) which is inside the window.
                    cd6 = self._climate_date(obs - timedelta(hours=3))
                    out.append(ProofEvent(self.icao, cd6, c10_to_f(c10), "sixhr", obs, now, raw[:60]))
        return out

# --------------------------------------------------------------- OMO
class OMOFeed:
    """MADIS hfmetar current-hour netCDF. Whole-C wire -> hard F floors.
    Covered stations only (NOT KNYC/KDEN). Uses If-Modified-Since."""
    URL = "https://madis-data.ncep.noaa.gov/madisPublic1/data/LDAD/hfmetar/netCDF/{ymd}_{h}00.gz"
    def __init__(self, station_ids: dict[str, int]):  # {ICAO: lst_offset_h}
        self.stations = station_ids
        self._last_mod: dict[str, str] = {}
        self._seen: set[tuple] = set()

    def poll(self) -> list[ProofEvent]:
        try:
            from netCDF4 import Dataset, chartostring
            import numpy as np
        except ImportError:
            log.error("netCDF4 not installed — OMO feed disabled"); return []
        now = datetime.now(timezone.utc); out = []
        for hourfile in (now, now - timedelta(hours=1)):
            url = self.URL.format(ymd=hourfile.strftime("%Y%m%d"), h=hourfile.strftime("%H"))
            req = urllib.request.Request(url, headers={**UA,
                    **({"If-Modified-Since": self._last_mod[url]} if url in self._last_mod else {})})
            try:
                resp = urllib.request.urlopen(req, timeout=30)
            except urllib.error.HTTPError as e:
                if e.code in (304, 404):
                    continue
                log.warning("OMO %s: %s", url, e); continue
            except Exception as e:
                log.warning("OMO %s: %s", url, e); continue
            self._last_mod[url] = resp.headers.get("Last-Modified", "")
            buf = io.BytesIO(gzip.decompress(resp.read()))
            open("/tmp/_omo_live.nc", "wb").write(buf.read())
            ds = Dataset("/tmp/_omo_live.nc")
            sid = np.array([s.strip() for s in chartostring(ds.variables["stationId"][:])])
            T  = np.ma.filled(ds.variables["temperature"][:], float("nan")).astype(float)
            OT = np.ma.filled(ds.variables["observationTime"][:], float("nan")).astype(float)
            for icao, lst in self.stations.items():
                for i in np.where(sid == icao)[0]:
                    if T[i] != T[i]:
                        continue
                    obs = datetime.fromtimestamp(OT[i], tz=timezone.utc)
                    key = (icao, OT[i])
                    if key in self._seen:
                        continue
                    self._seen.add(key)
                    c = kelvin_to_wholeC(T[i])
                    out.append(ProofEvent(icao, (obs + timedelta(hours=lst)).date(),
                                          wholeC_floor(c), "omo_floor", obs, now,
                                          detail=f"{c}C wire"))
            ds.close()
        return out
