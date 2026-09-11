"""Independent low-latency weather-source workers.

The current production runtime serializes cities and sleeps between blocking
requests. This module does the opposite: every wire runs independently and all
valid proofs are pushed into one queue. Duplicate proofs are expected; the kill
engine's fired-state makes the first valid arrival win.

Immediate public wires:
- TGFTP station file: continuous METAR/SPECI watcher (primary public METAR race)
- AviationWeather Data API: independent fallback watcher
- MADIS HF-ASOS public files: dedicated hot polling worker, no city-loop delay
- IEM AFOS DSM: release hunt continues until a new product is actually observed

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
from datetime import datetime, timedelta, timezone
from typing import Callable

import httpx

from decode import c10_to_f
from feeds import DSMFeed, OMOFeed, ProofEvent, SIXHR, TGRP

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


class DSMReleaseWorker:
    """Poll a DSM release until the NEW product is observed, not for N seconds."""

    def __init__(self, city_key: str, cfg: dict, sink: Callable[[ProofEvent], None],
                 stop: threading.Event):
        self.city_key, self.cfg, self.sink, self.stop = city_key, cfg, sink, stop
        self.feed = DSMFeed(cfg["dsm_pil"], cfg["icao"], cfg["lst_offset_h"])
        self.poll_s = float(os.getenv("MERCURY_DSM_HOT_POLL_S", "1.0"))
        self.safety_timeout_s = float(os.getenv("MERCURY_DSM_SAFETY_TIMEOUT_S", "900"))
        self._done: set[str] = set()

    def _targets(self, now: datetime) -> list[datetime]:
        wins = list(self.cfg.get("dsm_windows_utc", []))
        if self.cfg.get("dsm_hourly_sweep"):
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

    def run(self) -> None:
        try:
            self.feed.poll()
        except Exception:
            pass
        while not self.stop.is_set():
            now = datetime.now(timezone.utc)
            candidates = [t for t in self._targets(now)
                          if -30 <= (now - t).total_seconds() <= self.safety_timeout_s]
            candidate = max(candidates, default=None)
            if candidate is None:
                self.stop.wait(0.5)
                continue
            key = candidate.isoformat()
            if key in self._done:
                self.stop.wait(0.5)
                continue
            start = time.monotonic()
            while not self.stop.is_set() and time.monotonic() - start < self.safety_timeout_s:
                evs = self.feed.poll()
                if evs:
                    for ev in evs:
                        self.sink(ProofEvent(
                            ev.station, ev.climate_date, ev.level_f, ev.channel,
                            ev.obs_ts, ev.seen_ts, detail=f"iem-afos {ev.detail}",
                        ))
                    self._done.add(key)
                    break
                self.stop.wait(self.poll_s)
            else:
                if not self.stop.is_set():
                    log.error("DSM release not seen: %s target=%s", self.city_key, candidate)
                    self._done.add(key)


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
            dsm = DSMReleaseWorker(key, c, self.push, self.stop)
            th = threading.Thread(target=dsm.run, daemon=True, name=f"dsm-{key}")
            th.start(); self.threads.append(th)

        omo = OMORaceWorker(self.cfg, self.push, self.stop)
        th = threading.Thread(target=omo.run, daemon=True, name="madis-hf")
        th.start(); self.threads.append(th)

    def close(self) -> None:
        self.stop.set()

    def get(self, timeout: float | None = None) -> ProofEvent:
        return self.events.get(timeout=timeout)
