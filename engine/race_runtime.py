"""Mercury low-latency race runtime.

This is intentionally separate from runtime.py. Nothing imports it from the web
application today, so production behavior is unchanged until explicitly wired.

Critical-path rules:
1. boards are loaded before the race;
2. Kalshi order books are streamed into RAM before weather arrives;
3. weather sources run independently and race into one queue;
4. a proof performs only in-memory strategy work, then sends the order;
5. logging/persistence happens after the order submission attempt.

By default this runtime is SHADOW ONLY. Set MERCURY_RACE_LIVE=yes in addition to
WEATHERBOT_LIVE=yes and valid Kalshi credentials to permit live submission.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date as Date
from pathlib import Path

import journal
from fast_kalshi import BOOK, EXECUTOR
from fast_sources import SourceRace
from market import Bucket, board
from strategy import CityState, KillEngine

log = logging.getLogger("race_runtime")
HERE = Path(__file__).resolve().parent
CFG = json.load(open(HERE / "config.json"))


@dataclass
class RaceCity:
    key: str
    cfg: dict
    state: CityState
    board_date: Date | None = None
    buckets: list[Bucket] | None = None

    @property
    def icao(self) -> str:
        return self.cfg["icao"]

    def climate_today(self) -> Date:
        return (datetime.now(timezone.utc) + timedelta(hours=self.cfg["lst_offset_h"])).date()

    def load_board(self) -> list[Bucket]:
        d = self.climate_today()
        if d != self.board_date or self.buckets is None:
            self.buckets = board(self.cfg["series"], d)
            self.board_date = d
        return self.buckets


class RaceRuntime:
    def __init__(self):
        self.stop = threading.Event()
        self.engine = KillEngine(CFG["engine"])
        self.cities = {
            c["icao"]: RaceCity(k, c, CityState(c["icao"], c["series"]))
            for k, c in CFG["cities"].items()
        }
        self.sources = SourceRace(CFG)
        self.live = (os.getenv("MERCURY_RACE_LIVE") == "yes"
                     and os.getenv("WEATHERBOT_LIVE") == "yes")
        self._tickers: list[str] = []
        mode = "live" if self.live else "shadow"
        self.state_path = Path(journal.DATA_DIR) / f"race_state_{mode}.json"

    def _restore(self) -> None:
        if not self.state_path.exists():
            return
        try:
            blob = json.loads(self.state_path.read_text())
        except Exception as exc:
            log.warning("race state restore failed: %s", exc)
            return
        for city in self.cities.values():
            raw = blob.get(city.key)
            if not raw:
                continue
            city.state.proven_max = {
                Date.fromisoformat(k): int(v) for k, v in raw.get("proven", {}).items()
            }
            city.state.metar_max = {
                Date.fromisoformat(k): int(v) for k, v in raw.get("metar", {}).items()
            }
            city.state.fired = {tuple(x) for x in raw.get("fired", [])}

    def _persist(self) -> None:
        """Persist only after the critical send path; atomic replace on restart state."""
        blob = {
            city.key: {
                "proven": {str(k): v for k, v in city.state.proven_max.items()},
                "metar": {str(k): v for k, v in city.state.metar_max.items()},
                "fired": [list(x) for x in city.state.fired],
            }
            for city in self.cities.values()
        }
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(blob, separators=(",", ":")))
            os.replace(tmp, self.state_path)
        except Exception as exc:
            log.warning("race state persist failed: %s", exc)

    def prepare(self) -> None:
        """Do all slow work before weather can trigger a trade."""
        self._restore()
        tickers: list[str] = []
        for city in self.cities.values():
            bs = city.load_board()
            tickers.extend(b.ticker for b in bs if b.kill_level is not None)
        self._tickers = sorted(set(tickers))

        if BOOK.signer.available and self._tickers:
            BOOK.start(self._tickers)
            deadline = time.monotonic() + float(os.getenv("MERCURY_BOOK_WARMUP_S", "8"))
            while not BOOK.connected and time.monotonic() < deadline:
                time.sleep(0.02)
            if not BOOK.connected:
                log.warning("Kalshi WS not warm; source race may run shadow-only without quotes")
        else:
            log.warning("Kalshi credentials absent; orderbook WebSocket disabled")

        self.sources.start()
        journal.emit("system", msg=(
            f"race runtime started live={self.live} tickers={len(self._tickers)} "
            f"kalshi_ws={BOOK.connected}"
        ))

    def _quote(self, ticker: str):
        return BOOK.quote(ticker)

    @staticmethod
    def _unfire(city: RaceCity, ticker: str) -> None:
        """Allow retry after an order request that definitely/ambiguously failed.

        The order's deterministic client_order_id protects against duplicate fills
        if an HTTP timeout actually occurred after Kalshi accepted the first send.
        """
        for b in city.buckets or []:
            if b.ticker == ticker and b.kill_level is not None:
                city.state.fired.discard((b.ticker, b.kill_level))
                return

    def _handle(self, ev) -> None:
        city = self.cities.get(ev.station)
        if city is None or ev.climate_date != city.climate_today():
            return

        t_received_ns = time.perf_counter_ns()
        buckets = city.load_board()  # cache hit on normal critical path
        intents = self.engine.on_proof(city.state, ev, buckets, self._quote)
        t_decision_ns = time.perf_counter_ns()

        for intent in intents:
            result = {"mode": "SHADOW"}
            error = None
            t_submit_start_ns = time.perf_counter_ns()
            if self.live:
                try:
                    result = EXECUTOR.execute(intent)
                except Exception as exc:
                    # Do not permanently suppress this mathematically dead bucket.
                    # Later proof traffic may retry with the same idempotency key.
                    self._unfire(city, intent.ticker)
                    error = f"{type(exc).__name__}: {exc}"
            t_submit_done_ns = time.perf_counter_ns()

            # Everything below is deliberately after the order-send attempt.
            journal.emit(
                "race_intent",
                city=city.key,
                station=ev.station,
                ticker=intent.ticker,
                channel=ev.channel,
                source=(ev.detail.split(" ", 1)[0] if ev.detail else ev.channel),
                level_f=ev.level_f,
                bid_cents=self._quote(intent.ticker)[0],
                min_px=intent.min_px,
                live=self.live,
                seen_ts=ev.seen_ts.isoformat(),
                obs_ts=ev.obs_ts.isoformat() if ev.obs_ts else None,
                decision_us=round((t_decision_ns - t_received_ns) / 1000, 1),
                submit_us=round((t_submit_done_ns - t_submit_start_ns) / 1000, 1),
                result_latency=(result.get("_mercury_latency_ms") if isinstance(result, dict) else None),
                result_mode=(result.get("mode") if isinstance(result, dict) else None),
                error=error,
            )

        # Proof journaling + state persistence are off the critical path.
        journal.emit(
            "race_proof",
            city=city.key,
            station=ev.station,
            channel=ev.channel,
            source=(ev.detail.split(" ", 1)[0] if ev.detail else ev.channel),
            level_f=ev.level_f,
            climate_date=str(ev.climate_date),
            seen_ts=ev.seen_ts.isoformat(),
            obs_ts=ev.obs_ts.isoformat() if ev.obs_ts else None,
            decision_us=round((t_decision_ns - t_received_ns) / 1000, 1),
            intents=len(intents),
        )
        self._persist()

    def run(self) -> None:
        self.prepare()
        while not self.stop.is_set():
            try:
                ev = self.sources.get(timeout=0.5)
            except Exception:
                continue
            try:
                self._handle(ev)
            except Exception:
                log.exception("race proof handler failed")

    def close(self) -> None:
        self.stop.set()
        self.sources.close()
        BOOK.stop()
        self._persist()


def main() -> None:
    rt = RaceRuntime()

    def _stop(*_):
        rt.close()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    rt.run()


if __name__ == "__main__":
    main()
