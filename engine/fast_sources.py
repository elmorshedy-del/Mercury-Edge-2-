"""Independent low-latency weather-source workers.

All public wires run independently and emit normalized ProofEvents. The first
valid proof wins; duplicate arrivals are retained for latency measurement.

Immediate public wires:
- NWS TGFTP station file: continuous METAR/SPECI watcher.
- AviationWeather Data API: independent METAR/SPECI fallback.
- MADIS public HF-ASOS netCDF: isolated five-minute-batch watcher.
- IEM AFOS raw ARTCC DSM collectives: coordinated, rate-limit-safe fallback.

Privileged/direct adapters (FAA CSS-Wx, MADIS/IEM LDM, NWWS-OI, Synoptic Push)
can inject the same ProofEvent objects through SourceRace.push().
"""
from __future__ import annotations

import calendar
import logging
import os
import queue
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Callable

import httpx

from decode import c10_to_f
from dsm_decode import parse_dsm_text
from feeds import OMOFeed, ProofEvent, SIXHR, TGRP

log = logging.getLogger("fast_sources")

import re
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
        return lines[1:] if self.tgftp_format and len(lines) > 1 else lines

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
                    meta = (
                        f"http={wire_ms:.1f}ms "
                        f"last_modified={r.headers.get('last-modified', '-')} "
                        f"server_date={r.headers.get('date', '-')}"
                    )
                    for raw in self._lines(r.text):
                        if raw in self.seen_raw:
                            continue
                        self.seen_raw.add(raw)
                        for ev in parse_metar_proofs(raw, self.icao, self.lst,
                                                     self.name, seen):
                            self.sink(ProofEvent(
                                ev.station, ev.climate_date, ev.level_f, ev.channel,
                                ev.obs_ts, ev.seen_ts, detail=f"{ev.detail} {meta}",
                            ))
            except Exception as exc:
                log.warning("%s %s: %s", self.name, self.icao, exc)
            self.stop.wait(self.interval_s)


class DSMCollectiveHTTPWorker:
    """Race raw CDUS27 ARTCC DSM collectives before IEM's station split.

    IEM documents airport-specific DSM PILs as a value-added split from the raw
    collective. We therefore query one raw collective per ARTCC and parse the
    target stations locally. NYC and PHL share ZNY, reducing request count too.

    One scheduler owns all requests, round-robins only active release hunts, and
    applies a global exponential backoff on HTTP 429. Seeing a new station line
    ends only that station's current expected-release hunt.
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
        self.groups: dict[str, dict[str, dict]] = defaultdict(dict)
        for key, city in cfg["cities"].items():
            pil = city.get("dsm_collective_pil")
            if pil:
                self.groups[pil][key] = city
        self.seen_lines: dict[str, set[str]] = {pil: set() for pil in self.groups}
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

    def _url(self, pil: str) -> str:
        return f"{self.BASE}?pil={pil}&fmt=text&limit=3"

    def _fetch(self, pil: str, members: dict[str, dict], emit: bool,
               active_targets: dict[str, datetime] | None = None) -> set[str]:
        """Return city keys for which a genuinely new station DSM was seen."""
        t0 = time.perf_counter_ns()
        try:
            r = self.client.get(self._url(pil))
            if r.status_code == 429:
                retry = r.headers.get("retry-after")
                try:
                    retry_s = float(retry) if retry else 0.0
                except ValueError:
                    retry_s = 0.0
                self.backoff_s = min(
                    self.max_backoff_s,
                    max(retry_s, 2.0, self.backoff_s * 2 if self.backoff_s else 2.0),
                )
                log.warning("IEM DSM collective rate limited; global backoff %.1fs",
                            self.backoff_s)
                return set()
            r.raise_for_status()
            self.backoff_s = 0.0
        except Exception as exc:
            log.warning("DSM collective %s failed: %s", pil, exc)
            return set()

        seen = datetime.now(timezone.utc)
        wire_ms = (time.perf_counter_ns() - t0) / 1e6
        meta = (
            f"http={wire_ms:.1f}ms "
            f"last_modified={r.headers.get('last-modified', '-')} "
            f"server_date={r.headers.get('date', '-')}"
        )
        fresh_lines = []
        for raw in r.text.splitlines():
            line = raw.strip()
            if not line or line in self.seen_lines[pil]:
                continue
            self.seen_lines[pil].add(line)
            fresh_lines.append(line)
        if not emit or not fresh_lines:
            return set()

        member_cfgs = {k: v for k, v in members.items()}
        events = parse_dsm_text("\n".join(fresh_lines), member_cfgs,
                                f"iem-collective:{pil}", seen)
        by_icao = {c["icao"]: k for k, c in members.items()}
        completed: set[str] = set()
        for ev in events:
            key = by_icao.get(ev.station)
            if key is None:
                continue
            # If this collective was fetched for active hunts, ignore a station
            # that is not currently hunting; its line remains useful as baseline.
            if active_targets is not None and key not in active_targets:
                continue
            self.sink(ProofEvent(
                ev.station, ev.climate_date, ev.level_f, ev.channel,
                ev.obs_ts, ev.seen_ts, detail=f"{ev.detail} {meta}",
            ))
            completed.add(key)
        return completed

    def run(self) -> None:
        # Sequential baseline of raw collectives. This avoids treating existing
        # products as a fresh release and avoids a startup request burst.
        for pil, members in self.groups.items():
            if self.stop.is_set():
                return
            self._fetch(pil, members, emit=False)
            self.stop.wait(max(self.global_poll_s, 1.0))

        while not self.stop.is_set():
            now = datetime.now(timezone.utc)
            active_groups: list[tuple[str, dict[str, dict], dict[str, datetime]]] = []
            for pil, members in self.groups.items():
                active_targets = {}
                for key, city in members.items():
                    target = self._active_target(key, city, now)
                    if target is not None:
                        active_targets[key] = target
                if active_targets:
                    active_groups.append((pil, members, active_targets))

            if not active_groups:
                self.stop.wait(0.5)
                continue

            self._rr %= len(active_groups)
            pil, members, active_targets = active_groups[self._rr]
            self._rr = (self._rr + 1) % len(active_groups)
            completed = self._fetch(pil, members, emit=True,
                                    active_targets=active_targets)
            for key in completed:
                self.done.add((key, active_targets[key].isoformat()))

            wait_s = self.backoff_s if self.backoff_s else self.global_poll_s
            self.stop.wait(max(wait_s, 0.5))


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

        dsm = DSMCollectiveHTTPWorker(self.cfg, self.push, self.stop)
        th = threading.Thread(target=dsm.run, daemon=True, name="dsm-iem-collectives")
        th.start(); self.threads.append(th)

        omo = OMORaceWorker(self.cfg, self.push, self.stop)
        th = threading.Thread(target=omo.run, daemon=True, name="madis-hf")
        th.start(); self.threads.append(th)

    def close(self) -> None:
        self.stop.set()

    def get(self, timeout: float | None = None) -> ProofEvent:
        return self.events.get(timeout=timeout)
