"""Independent low-latency weather-source workers.

The current production runtime serializes cities and sleeps between blocking
requests. This module does the opposite: every wire runs independently and all
valid proofs are pushed into one queue. Duplicate proofs are expected; the kill
engine's fired-state makes the first valid arrival win.

Immediate public wires:
- TGFTP station file: continuous METAR/SPECI watcher (primary public METAR race)
- AviationWeather Data API: independent fallback watcher
- MADIS HF-ASOS public files: dedicated hot polling worker, no city-loop delay
- IEM AFOS DSM: one coordinated release hunter for all stations (rate-limit safe)

Push adapters (FAA CSS-Wx OMO, MADIS LDM, IEM LDM, NWWS-OI, Synoptic Push) can
inject the same ProofEvent objects through ``push`` without changing strategy.
"""
from __future__ import annotations

import calendar
import logging
import os
import queue
import re
import threading
import time
from datetime import date as Date, datetime, timedelta, timezone
from typing import Callable

import httpx

from decode import c10_to_f
from feeds import DSBODY, MAXTOK, OMOFeed, ProofEvent, SIXHR, TGRP

log = logging.getLogger("fast_sources")

METAR_TS = re.compile(r"\b(\d{2})(\d{2})(\d{2})Z\b")


def _month_shift(dt: datetime, delta: int) -> tuple[int, int]:
    n = dt.year * 12 + (dt.month - 1) + delta
    return n // 12, n % 12 + 1


def _metar_obs_time(raw: str, now: datetime) -> datetime | None:
    """Resolve DDHHMMZ robustly across month/year boundaries."""
    m = METAR_TS.search(raw)
    if not m:
        return None
    day, hh, mm = map(int, m.groups())
    candidates: list[datetime] = []
    for delta in (-1, 0, 1):
        y, mon = _month_shift(now, delta)
        if day <= calendar.monthrange(y, mon)[1]:
            candidates.append(datetime(y, mon, day, hh, mm, tzinfo=timezone.utc))
    if not candidates:
        return None
    return min(candidates, key=lambda x: abs((x - now).total_seconds()))


def parse_metar_proofs(raw: str, icao: str, lst_offset_h: int,
                       source: str, seen_ts: datetime | None = None) -> list[ProofEvent]:
    """Decode T-group current temperature and six-hour maximum from raw METAR."""
    raw = raw.strip()
    now = seen_ts or datetime.now(timezone.utc)
    if not raw or icao not in raw:
        return []
    obs = _metar_obs_time(raw, now)
    if obs is None:
        return []
    cdate = (obs + timedelta(hours=lst_offset_h)).date()
    out: list[ProofEvent] = []
    t = TGRP.search(raw)
    if t:
        c10 = int(t.group(2)) / 10.0 * (-1 if t.group(1) == "1" else 1)
        out.append(ProofEvent(
            icao, cdate, c10_to_f(c10), "metar", obs, now,
            detail=f"{source} {raw[:95]}",
        ))
    if (obs + timedelta(minutes=15)).hour in (0, 6, 12, 18):
        s = SIXHR.search(raw)
        if s:
            c10 = int(s.group(2)) / 10.0 * (-1 if s.group(1) == "1" else 1)
            cd6 = (obs - timedelta(hours=3) + timedelta(hours=lst_offset_h)).date()
            out.append(ProofEvent(
                icao, cd6, c10_to_f(c10), "sixhr", obs, now,
                detail=f"{source} {raw[:95]}",
            ))
    return out


class _MetarHTTPWorker:
    """One independent persistent-HTTP watcher for one station/source."""

    def __init__(self, name: str, icao: str, lst: int, url: str, interval_s: float,
                 sink: Callable[[ProofEvent], None], stop: threading.Event,
                 tgftp_format: bool = False):
        self.name, self.icao, self.lst = name, icao, lst
        self.url, self.interval_s = url, interval_s
        self.sink, self.stop = sink, stop
        self.tgftp_format = tgftp_format
        self.seen_raw: set[str] = set()
        self.etag: str | None = None
        self.last_modified: str | None = None
        self.client = httpx.Client(
            http2=True,
            timeout=httpx.Timeout(2.5, connect=1.0),
            limits=httpx.Limits(max_keepalive_connections=1, max_connections=1,
                                keepalive_expiry=180.0),
            headers={"User-Agent": "mercury-edge-race/1"},
        )

    def _lines(self, text: str) -> list[str]:
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        if self.tgftp_format:
            return lines[1:] if len(lines) > 1 else []
        return lines

    def run(self) -> None:
        while not self.stop.is_set():
            t0 = time.perf_counter_ns()
            headers = {}
            if self.etag:
                headers["If-None-Match"] = self.etag
            if self.last_modified:
                headers["If-Modified-Since"] = self.last_modified
            try:
                r = self.client.get(self.url, headers=headers)
                if r.status_code != 304:
                    r.raise_for_status()
                    self.etag = r.headers.get("etag", self.etag)
                    self.last_modified = r.headers.get("last-modified", self.last_modified)
                    seen = datetime.now(timezone.utc)
                    wire_ms = (time.perf_counter_ns() - t0) / 1e6
                    for raw in self._lines(r.text):
                        if raw in self.seen_raw:
                            continue
                        self.seen_raw.add(raw)
                        for ev in parse_metar_proofs(raw, self.icao, self.lst,
                                                     self.name, seen):
                            self.sink(ProofEvent(
                                ev.station, ev.climate_date, ev.level_f, ev.channel,
                                ev.obs_ts, ev.seen_ts,
                                detail=f"{ev.detail} http={wire_ms:.1f}ms",
                            ))
            except Exception as exc:
                log.warning("%s %s: %s", self.name, self.icao, exc)
            self.stop.wait(self.interval_s)


class DSMHTTPRaceWorker:
    """Coordinate all IEM-AFOS DSM polling through one rate-limited scheduler.

    The previous implementation launched one hot loop per city. Several :15
    release windows overlap, so those loops could hit IEM simultaneously and
    produce HTTP 429 responses. This worker keeps the same low-latency intent but
    makes only one request at a time, round-robins active releases, and applies a
    global exponential backoff when IEM rate-limits us.

    Expected release time starts the hunt. Seeing a genuinely new DSM line ends
    that station's hunt. A short fixed elapsed window never silently ends it.
    """

    BASE = "https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py"

    def __init__(self, cfg: dict, sink: Callable[[ProofEvent], None],
                 stop: threading.Event):
        self.cfg, self.sink, self.stop = cfg, sink, stop
        self.global_poll_s = float(os.getenv("MERCURY_DSM_GLOBAL_POLL_S", "1.0"))
        self.safety_timeout_s = float(os.getenv("MERCURY_DSM_SAFETY_TIMEOUT_S", "900"))
        self.pre_s = float(os.getenv("MERCURY_DSM_PRE_HUNT_S", "30"))
        self.max_backoff_s = float(os.getenv("MERCURY_DSM_429_MAX_BACKOFF_S", "30"))
        self.client = httpx.Client(
            http2=True,
            timeout=httpx.Timeout(3.0, connect=1.0),
            limits=httpx.Limits(max_keepalive_connections=2, max_connections=2,
                                keepalive_expiry=180.0),
            headers={"User-Agent": "mercury-edge-race/1"},
        )
        self.seen: dict[str, set[str]] = {k: set() for k in cfg["cities"]}
        self.done: set[tuple[str, str]] = set()
        self.backoff_s = 0.0
        self._rr = 0

    @staticmethod
    def _targets(city: dict, now: datetime) -> list[datetime]:
        wins = list(city.get("dsm_windows_utc", []))
        if city.get("dsm_hourly_sweep"):
            for h in ((now - timedelta(hours=1)).hour, now.hour,
                      (now + timedelta(hours=1)).hour):
                wins.append(f"{h:02d}:15")
        out: list[datetime] = []
        for day_delta in (-1, 0, 1):
            base = now + timedelta(days=day_delta)
            for w in set(wins):
                h, m = map(int, w.split(":"))
                out.append(base.replace(hour=h, minute=m, second=0, microsecond=0))
        return sorted(set(out))

    def _active_target(self, key: str, city: dict, now: datetime) -> datetime | None:
        valid = [t for t in self._targets(city, now)
                 if -self.pre_s <= (now - t).total_seconds() <= self.safety_timeout_s
                 and (key, t.isoformat()) not in self.done]
        return max(valid, default=None)

    def _url(self, city: dict) -> str:
        return f"{self.BASE}?pil={city['dsm_pil']}&fmt=text&limit=3"

    def _fetch(self, key: str, city: dict, emit: bool) -> bool:
        """Return True only when a new valid DSM line was observed."""
        t0 = time.perf_counter_ns()
        try:
            r = self.client.get(self._url(city))
            if r.status_code == 429:
                retry = r.headers.get("retry-after")
                try:
                    retry_s = float(retry) if retry is not None else 0.0
                except ValueError:
                    retry_s = 0.0
                self.backoff_s = min(
                    self.max_backoff_s,
                    max(retry_s, 2.0, self.backoff_s * 2 if self.backoff_s else 2.0),
                )
                log.warning("IEM DSM rate limited; global backoff %.1fs", self.backoff_s)
                return False
            r.raise_for_status()
            self.backoff_s = 0.0
        except Exception as exc:
            log.warning("DSM fetch %s failed: %s", city["dsm_pil"], exc)
            return False

        now = datetime.now(timezone.utc)
        wire_ms = (time.perf_counter_ns() - t0) / 1e6
        found = False
        for raw in r.text.splitlines():
            line = raw.strip()
            m = DSBODY.match(line)
            if not m or m.group(1) != city["icao"]:
                continue
            if line in self.seen[key]:
                continue
            self.seen[key].add(line)
            if not emit:
                continue
            hhmm, dd, mm = m.group(2), int(m.group(3)), int(m.group(4))
            tok = m.group(5).split("/")[0].strip()
            mt = MAXTOK.match(tok)
            if not mt:
                continue
            max_f, max_hhmm = int(mt.group(1)), mt.group(2)
            if not (20 <= max_f <= 130):
                continue
            try:
                cdate = Date(now.year, mm, dd)
            except ValueError:
                continue
            obs = None
            try:
                obs = (
                    datetime(cdate.year, cdate.month, cdate.day,
                             int(max_hhmm[:2]) % 24, int(max_hhmm[2:]) % 60,
                             tzinfo=timezone.utc)
                    - timedelta(hours=city["lst_offset_h"])
                )
            except Exception:
                pass
            self.sink(ProofEvent(
                city["icao"], cdate, max_f, "dsm", obs, now,
                detail=(f"iem-afos DS {hhmm or 'final'} max {max_f}F @{max_hhmm} LST "
                        f"http={wire_ms:.1f}ms"),
            ))
            found = True
        return found

    def run(self) -> None:
        # One polite sequential baseline prevents old products from terminating
        # the first release hunt and avoids a startup burst across all PILs.
        for key, city in self.cfg["cities"].items():
            if self.stop.is_set():
                return
            self._fetch(key, city, emit=False)
            self.stop.wait(max(self.global_poll_s, 0.5))

        while not self.stop.is_set():
            now = datetime.now(timezone.utc)
            active: list[tuple[str, dict, datetime]] = []
            for key, city in self.cfg["cities"].items():
                target = self._active_target(key, city, now)
                if target is not None:
                    active.append((key, city, target))

            if not active:
                self.stop.wait(0.5)
                continue

            # Round-robin active PILs. One global request per interval means an
            # overlap of N release hunts yields ~N*interval cadence per station.
            self._rr %= len(active)
            key, city, target = active[self._rr]
            self._rr = (self._rr + 1) % len(active)
            if self._fetch(key, city, emit=True):
                self.done.add((key, target.isoformat()))

            wait_s = self.backoff_s if self.backoff_s else self.global_poll_s
            self.stop.wait(max(wait_s, 0.25))


class OMORaceWorker:
    """Dedicated MADIS HF-ASOS watcher around public five-minute batches."""

    def __init__(self, cfg: dict, sink: Callable[[ProofEvent], None], stop: threading.Event):
        stations = {c["icao"]: c["lst_offset_h"] for c in cfg["cities"].values()
                    if c.get("omo")}
        self.feed = OMOFeed(stations)
        self.sink, self.stop = sink, stop
        self.hot_s = float(os.getenv("MERCURY_OMO_HOT_POLL_S", "1.0"))
        self.cold_s = float(os.getenv("MERCURY_OMO_COLD_POLL_S", "10.0"))
        self.hot_window_s = float(os.getenv("MERCURY_OMO_HOT_WINDOW_S", "120"))

    def run(self) -> None:
        while not self.stop.is_set():
            try:
                for ev in self.feed.poll():
                    self.sink(ProofEvent(
                        ev.station, ev.climate_date, ev.level_f, ev.channel,
                        ev.obs_ts, ev.seen_ts, detail=f"madis-hf {ev.detail}",
                    ))
            except Exception as exc:
                log.warning("MADIS HF watcher: %s", exc)
            now = datetime.now(timezone.utc)
            sec_after_5m = (now.minute % 5) * 60 + now.second
            hot = sec_after_5m <= self.hot_window_s
            self.stop.wait(self.hot_s if hot else self.cold_s)


class SourceRace:
    """Start all public-source workers concurrently and emit ProofEvents to queue."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.stop = threading.Event()
        self.events: queue.Queue[ProofEvent] = queue.Queue()
        self.threads: list[threading.Thread] = []

    def push(self, ev: ProofEvent) -> None:
        """Public ingress for HTTP workers and external push-feed adapters."""
        self.events.put(ev)

    def start(self) -> None:
        for key, c in self.cfg["cities"].items():
            icao, lst = c["icao"], c["lst_offset_h"]
            tg = _MetarHTTPWorker(
                "tgftp", icao, lst,
                f"https://tgftp.nws.noaa.gov/data/observations/metar/stations/{icao}.TXT",
                float(os.getenv("MERCURY_TGFTP_POLL_S", "1.0")), self.push, self.stop,
                tgftp_format=True,
            )
            awc = _MetarHTTPWorker(
                "aviationweather", icao, lst,
                f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw&hours=2",
                float(os.getenv("MERCURY_AWC_POLL_S", "5.0")), self.push, self.stop,
            )
            for name, fn in ((f"tgftp-{key}", tg.run), (f"awc-{key}", awc.run)):
                th = threading.Thread(target=fn, daemon=True, name=name)
                th.start(); self.threads.append(th)

        dsm = DSMHTTPRaceWorker(self.cfg, self.push, self.stop)
        th = threading.Thread(target=dsm.run, daemon=True, name="dsm-iem-coordinator")
        th.start(); self.threads.append(th)

        omo = OMORaceWorker(self.cfg, self.push, self.stop)
        th = threading.Thread(target=omo.run, daemon=True, name="madis-hf")
        th.start(); self.threads.append(th)

    def close(self) -> None:
        self.stop.set()

    def get(self, timeout: float | None = None) -> ProofEvent:
        return self.events.get(timeout=timeout)
