"""Hardened public-source race for Mercury.

This module is intentionally separate from ``fast_sources.py`` so the deployed
IAD shadow can continue collecting clean measurements while the next version is
validated.

Changes versus the first shadow:
- TGFTP station watchers remain independent because they have been reliable and
  cheap from IAD.
- AviationWeather is ONE batched request for all Mercury stations rather than
  seven independent HTTP/2 connections. This stays within the documented API
  request budget and avoids the repeated connection-termination failures seen
  in the first shadow.
- IEM DSM HTTP is explicitly a fallback. A 429 opens a circuit breaker instead
  of hammering the service every few seconds. LDM/NWWS push are the intended
  production DSM wires.
- MADIS HF remains a measurement/fallback source only.

Privileged/direct feeds (FAA CSS-Wx, LDM, NWWS) inject ProofEvents through the
existing local proof bus and race these public sources.
"""
from __future__ import annotations

import logging
import os
import queue
import re
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Callable

import httpx

from dsm_decode import parse_dsm_text
from feeds import ProofEvent
from fast_sources import _MetarHTTPWorker, OMORaceWorker, parse_metar_proofs

log = logging.getLogger("direct_sources")
STATION_RE = re.compile(r"^(?:(?:METAR|SPECI)\s+)?([A-Z0-9]{4})\b")


def _http_client(timeout_s: float = 2.5) -> httpx.Client:
    return httpx.Client(
        http2=True,
        timeout=httpx.Timeout(timeout_s, connect=1.0),
        limits=httpx.Limits(max_keepalive_connections=2, max_connections=2,
                            keepalive_expiry=90.0),
        headers={"User-Agent": "mercury-edge-race/2"},
    )


class AviationWeatherBatchWorker:
    """Poll all Mercury METAR/SPECI stations with one API request.

    The public AviationWeather API documents a 100 request/minute ceiling. The
    default 1.5 s cadence is 40 requests/minute total, not 7 workers x 12/min.
    It also makes one HTTP/2 connection disposable: repeated transport errors
    rebuild the client instead of leaving a poisoned long-lived connection.
    """

    BASE = "https://aviationweather.gov/api/data/metar"

    def __init__(self, cfg: dict, sink: Callable[[ProofEvent], None],
                 stop: threading.Event):
        self.sink, self.stop = sink, stop
        self.lst = {c["icao"]: int(c["lst_offset_h"])
                    for c in cfg["cities"].values()}
        self.icaos = sorted(self.lst)
        requested = float(os.getenv("MERCURY_AWC_BATCH_POLL_S", "1.5"))
        # Fail-safe against accidentally exceeding the public API ceiling.
        self.interval_s = max(1.0, requested)
        self.max_backoff_s = float(os.getenv("MERCURY_AWC_MAX_BACKOFF_S", "15"))
        self.seen_raw: set[str] = set()
        self.client = _http_client()
        self.failures = 0

    @property
    def url(self) -> str:
        ids = ",".join(self.icaos)
        return f"{self.BASE}?ids={ids}&format=raw&hours=2"

    def _reset_client(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass
        self.client = _http_client()

    def _handle_text(self, text: str, seen: datetime, meta: str) -> int:
        emitted = 0
        for raw in text.splitlines():
            raw = raw.strip()
            if not raw or raw in self.seen_raw:
                continue
            m = STATION_RE.match(raw)
            if not m:
                continue
            icao = m.group(1)
            if icao not in self.lst:
                continue
            self.seen_raw.add(raw)
            for ev in parse_metar_proofs(raw, icao, self.lst[icao],
                                         "aviationweather-batch", seen):
                self.sink(ProofEvent(
                    ev.station, ev.climate_date, ev.level_f, ev.channel,
                    ev.obs_ts, ev.seen_ts, detail=f"{ev.detail} {meta}",
                ))
                emitted += 1
        return emitted

    def run(self) -> None:
        while not self.stop.is_set():
            t0 = time.perf_counter_ns()
            try:
                r = self.client.get(self.url)
                r.raise_for_status()
                seen = datetime.now(timezone.utc)
                wire_ms = (time.perf_counter_ns() - t0) / 1e6
                meta = (
                    f"http={wire_ms:.1f}ms "
                    f"server_date={r.headers.get('date', '-')}"
                )
                self._handle_text(r.text, seen, meta)
                self.failures = 0
                wait_s = self.interval_s
            except Exception as exc:
                self.failures += 1
                log.warning("aviationweather batch failure #%d: %s",
                            self.failures, exc)
                self._reset_client()
                wait_s = min(self.max_backoff_s,
                             self.interval_s * (2 ** min(self.failures, 4)))
            self.stop.wait(wait_s)


class DSMHTTPFallbackWorker:
    """Rate-limit-safe IEM DSM fallback.

    This path is deliberately NOT optimized as the primary race wire. If IEM
    returns 429, the worker stops all IEM requests for a cooldown period. That
    prevents the pathological 429 loop observed in the first IAD shadow.
    """

    BASE = "https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py"

    def __init__(self, cfg: dict, sink: Callable[[ProofEvent], None],
                 stop: threading.Event):
        self.cfg, self.sink, self.stop = cfg, sink, stop
        self.poll_s = max(5.0, float(os.getenv("MERCURY_DSM_FALLBACK_POLL_S", "15")))
        self.cooldown_s = max(60.0, float(os.getenv("MERCURY_DSM_429_COOLDOWN_S", "300")))
        self.pre_s = float(os.getenv("MERCURY_DSM_PRE_HUNT_S", "30"))
        self.hunt_s = float(os.getenv("MERCURY_DSM_FALLBACK_HUNT_S", "900"))
        self.groups: dict[str, dict[str, dict]] = defaultdict(dict)
        for key, city in cfg["cities"].items():
            pil = city.get("dsm_collective_pil")
            if pil:
                self.groups[pil][key] = city
        self.client = _http_client(3.0)
        self.seen_lines: dict[str, set[str]] = {p: set() for p in self.groups}
        self.done: set[tuple[str, str]] = set()
        self.circuit_until = 0.0
        self._rr = 0

    @staticmethod
    def _targets(city: dict, now: datetime) -> list[datetime]:
        wins = list(city.get("dsm_windows_utc", []))
        if city.get("dsm_hourly_sweep"):
            for h in ((now - timedelta(hours=1)).hour, now.hour,
                      (now + timedelta(hours=1)).hour):
                wins.append(f"{h:02d}:15")
        out = []
        for day_delta in (-1, 0, 1):
            base = now + timedelta(days=day_delta)
            for w in set(wins):
                h, m = map(int, w.split(":"))
                out.append(base.replace(hour=h, minute=m, second=0, microsecond=0))
        return sorted(set(out))

    def _active_target(self, key: str, city: dict,
                       now: datetime) -> datetime | None:
        valid = [t for t in self._targets(city, now)
                 if -self.pre_s <= (now - t).total_seconds() <= self.hunt_s
                 and (key, t.isoformat()) not in self.done]
        return max(valid, default=None)

    def _fetch(self, pil: str, members: dict[str, dict],
               targets: dict[str, datetime] | None, emit: bool) -> set[str]:
        t0 = time.perf_counter_ns()
        try:
            r = self.client.get(f"{self.BASE}?pil={pil}&fmt=text&limit=3")
            if r.status_code == 429:
                retry_after = 0.0
                try:
                    retry_after = float(r.headers.get("retry-after") or 0)
                except ValueError:
                    pass
                self.circuit_until = time.monotonic() + max(self.cooldown_s, retry_after)
                log.warning("IEM DSM 429: circuit open for %.0fs",
                            max(self.cooldown_s, retry_after))
                return set()
            r.raise_for_status()
        except Exception as exc:
            log.warning("DSM fallback %s failed: %s", pil, exc)
            return set()

        seen = datetime.now(timezone.utc)
        wire_ms = (time.perf_counter_ns() - t0) / 1e6
        fresh = []
        for raw in r.text.splitlines():
            line = raw.strip()
            if not line or line in self.seen_lines[pil]:
                continue
            self.seen_lines[pil].add(line)
            fresh.append(line)
        if not emit or not fresh:
            return set()

        events = parse_dsm_text("\n".join(fresh), members,
                                f"iem-http-fallback:{pil}", seen)
        by_icao = {city["icao"]: key for key, city in members.items()}
        completed = set()
        for ev in events:
            key = by_icao.get(ev.station)
            if key is None or (targets is not None and key not in targets):
                continue
            self.sink(ProofEvent(
                ev.station, ev.climate_date, ev.level_f, ev.channel,
                ev.obs_ts, ev.seen_ts,
                detail=(f"{ev.detail} http={wire_ms:.1f}ms "
                        f"last_modified={r.headers.get('last-modified', '-')}"),
            ))
            completed.add(key)
        return completed

    def run(self) -> None:
        # Baseline slowly so pre-existing products are never called fresh.
        for pil, members in self.groups.items():
            if self.stop.is_set():
                return
            if time.monotonic() < self.circuit_until:
                break
            self._fetch(pil, members, None, emit=False)
            self.stop.wait(self.poll_s)

        while not self.stop.is_set():
            now_mono = time.monotonic()
            if now_mono < self.circuit_until:
                self.stop.wait(min(5.0, self.circuit_until - now_mono))
                continue

            now = datetime.now(timezone.utc)
            active = []
            for pil, members in self.groups.items():
                targets = {key: t for key, city in members.items()
                           if (t := self._active_target(key, city, now)) is not None}
                if targets:
                    active.append((pil, members, targets))
            if not active:
                self.stop.wait(1.0)
                continue

            self._rr %= len(active)
            pil, members, targets = active[self._rr]
            self._rr += 1
            completed = self._fetch(pil, members, targets, emit=True)
            for key in completed:
                self.done.add((key, targets[key].isoformat()))
            self.stop.wait(self.poll_s)


class DirectSourceRace:
    """Next-generation public race; direct/push feeds enter through ProofBus."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.stop = threading.Event()
        self.events: queue.Queue[ProofEvent] = queue.Queue()
        self.threads: list[threading.Thread] = []

    def push(self, ev: ProofEvent) -> None:
        self.events.put(ev)

    def _start(self, name: str, fn) -> None:
        th = threading.Thread(target=fn, daemon=True, name=name)
        th.start()
        self.threads.append(th)

    def start(self) -> None:
        # TGFTP: one tiny station file per city. Keep these independent so a
        # slow station/server response never blocks another station.
        for key, c in self.cfg["cities"].items():
            icao, lst = c["icao"], int(c["lst_offset_h"])
            worker = _MetarHTTPWorker(
                "tgftp", icao, lst,
                f"https://tgftp.nws.noaa.gov/data/observations/metar/stations/{icao}.TXT",
                max(0.5, float(os.getenv("MERCURY_TGFTP_POLL_S", "1.0"))),
                self.push, self.stop, tgftp_format=True,
            )
            self._start(f"tgftp-{key}", worker.run)

        awc = AviationWeatherBatchWorker(self.cfg, self.push, self.stop)
        self._start("aviationweather-batch", awc.run)

        dsm = DSMHTTPFallbackWorker(self.cfg, self.push, self.stop)
        self._start("dsm-http-fallback", dsm.run)

        # Still collect MADIS HF so its actual lag remains measurable. It is not
        # assumed to be the winning OMO source.
        omo = OMORaceWorker(self.cfg, self.push, self.stop)
        self._start("madis-hf", omo.run)

    def close(self) -> None:
        self.stop.set()

    def get(self, timeout: float | None = None) -> ProofEvent:
        return self.events.get(timeout=timeout)
