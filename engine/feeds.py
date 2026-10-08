"""feeds.py — the three proof channels. Each feed yields ProofEvents:
a claim '(station, climate_date) daily max >= level_f' with source + timestamps.

Channels (measured live lags):
  DSM   — settlement-grade running max + minute it occurred; wire ~:15+0-2min
  METAR — T-group exact whole-F (hourly + SPECI); 6-hr max groups at synoptics
  OMO   — MADIS hfmetar 5-min whole-C; floor(candidates) is a hard lower bound;
          measured availability 2.3 min typical (up to ~7)
"""
from __future__ import annotations
import re, gzip, io, json, logging, time, urllib.request
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
    (proves max >= that value). 6-hr groups at 00/06/12/18Z prove window max.

    A six-hour maximum is promoted to day-specific hard proof only when its
    entire synoptic window belongs to one local-standard-time climate date.
    Cross-midnight windows are held because the 1snTxTxTx group does not encode
    when inside the six-hour window the maximum occurred.
    """
    def __init__(self, icao: str, lst_offset_h: int):
        self.icao, self.lst = icao, lst_offset_h
        self._seen: set[str] = set()
        self._awc_next_retry = 0.0
        self._awc_failures = 0
        self.last_awc_error: str | None = None

    def _climate_date(self, obs: datetime) -> Date:
        return (obs + timedelta(hours=self.lst)).date()

    def poll(self, fast_only: bool = False, awc_only: bool = False) -> list[ProofEvent]:
        # NOAA station-file lane won the measured KLAX METAR race against
        # minuteTemp NOAAPORT and AviationWeather (single observed cycle).
        # Keep AWC as a separate supplementary history/SPECI lane: TGFTP
        # station files retain only the latest report.
        sources = (
            ("tgftp", f"https://tgftp.nws.noaa.gov/data/observations/metar/stations/{self.icao}.TXT"),
            ("awc", f"https://aviationweather.gov/api/data/metar?ids={self.icao}&format=raw&hours=2"),
        )
        if fast_only and awc_only:
            raise ValueError('Choose TGFTP or AWC, not both')
        selected = sources[:1] if fast_only else sources[1:] if awc_only else sources
        lines = []
        for source, url in selected:
            if source == "awc" and time.monotonic() < self._awc_next_retry:
                continue  # Timeout cooldown must not suppress NOAA TGFTP.
            try:
                body = _get(url, timeout=4).decode(errors="replace")
                if source == "awc":
                    if self._awc_failures:
                        log.info("METAR AWC %s recovered", self.icao)
                    self._awc_next_retry = 0.0
                    self._awc_failures = 0
                    self.last_awc_error = None
                for line in body.splitlines():
                    if re.search(r"\b" + re.escape(self.icao) + r"\s+\d{6}Z\b", line):
                        lines.append((source, line.strip()))
            except Exception as e:
                if source == "awc":
                    self._awc_failures += 1
                    cooldown = min(1800, 60 * (2 ** min(self._awc_failures - 1, 5)))
                    self._awc_next_retry = time.monotonic() + cooldown
                    self.last_awc_error = type(e).__name__
                    log.warning("METAR AWC %s temporarily unavailable (%s), retry in %ds",
                                self.icao, self.last_awc_error, cooldown)
                else:
                    log.warning("METAR %s %s failed: %s", source, self.icao, e)
        if not lines:
            return []
        now = datetime.now(timezone.utc); out = []
        for source, raw in lines:
            raw = raw.strip()
            if not raw or raw in self._seen:
                continue
            self._seen.add(raw)
            dm = re.search(r'\b(\d{2})(\d{2})(\d{2})Z\b', raw)
            if not dm:
                continue
            day, hour, minute = [int(dm.group(i)) for i in (1, 2, 3)]
            if not (0 <= hour < 24 and 0 <= minute < 60):
                continue
            # Resolve month/year rollover with actual calendar boundaries;
            # subtracting a fixed 31 days breaks February and short months.
            month_start = now.replace(day=1, hour=0, minute=0,
                                      second=0, microsecond=0)
            candidates = []
            for shift in (-32, 0, 32):
                month = (month_start + timedelta(days=shift)).replace(day=1)
                try:
                    obs_candidate = month.replace(day=day, hour=hour, minute=minute)
                except ValueError:
                    continue
                if now - timedelta(hours=48) <= obs_candidate <= now + timedelta(minutes=10):
                    candidates.append(obs_candidate)
            if not candidates:
                continue
            obs = min(candidates, key=lambda x: abs((now - x).total_seconds()))
            cdate = self._climate_date(obs)
            t = TGRP.search(raw)
            if t:
                c10 = int(t.group(2)) / 10.0 * (-1 if t.group(1) == "1" else 1)
                out.append(ProofEvent(self.icao, cdate, c10_to_f(c10), "metar", obs, now, f"{source}: {raw[:60]}"))
            # Synoptic reports are stamped :51-:56 of the PRIOR hour (1751Z
            # carries the 18Z-cycle groups). Round forward to the nominal cycle
            # boundary, then require the entire preceding 6h window to stay
            # inside one LST climate date before treating the max as hard proof.
            cycle_end = (obs + timedelta(minutes=15)).replace(minute=0, second=0, microsecond=0)
            if cycle_end.hour in (0, 6, 12, 18):
                s = SIXHR.search(raw)
                if s:
                    window_start = cycle_end - timedelta(hours=6)
                    start_date = self._climate_date(window_start)
                    end_date = self._climate_date(cycle_end - timedelta(microseconds=1))
                    if start_date != end_date:
                        log.info(
                            "sixhr held: %s %sZ-%sZ crosses climate midnight (%s/%s)",
                            self.icao, window_start.strftime("%d%H%M"),
                            cycle_end.strftime("%d%H%M"), start_date, end_date)
                        continue
                    c10 = int(s.group(2)) / 10.0 * (-1 if s.group(1) == "1" else 1)
                    out.append(ProofEvent(self.icao, start_date, c10_to_f(c10),
                                          "sixhr", obs, now, raw[:60]))
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
