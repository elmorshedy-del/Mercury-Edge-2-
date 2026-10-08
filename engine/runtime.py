"""runtime.py — the scheduler as an importable, thread-runnable service.
Same logic as the standalone run.py, plus journaling and a shared STATE for the API."""
from __future__ import annotations
import json, time, logging, os, threading, queue
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone, date as Date

import journal
from feeds import DSMFeed, MetarFeed, OMOFeed
from datis import DATISFeed
from minutetemp import MinuteTempFeed, MinuteTempStream
from climate_products import TGFTPClimateFeed
from market import board, quote
from strategy import KillEngine, CityState
import paper
import exec_live

log = logging.getLogger("runtime")
HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json")))
DATA_DIR = journal.DATA_DIR
STATE_PATH = os.path.join(DATA_DIR, "state.json")

STATE = {"started": None, "mode": "PAPER", "last_poll": {}, "latest_proof": {}, "sources": {}, "source_health": {}, "cities": {}}
_state_lock = threading.Lock()

def climate_today(lst_off: int) -> Date:
    return (datetime.now(timezone.utc) + timedelta(hours=lst_off)).date()

class City:
    def __init__(self, key: str, c: dict):
        self.key, self.c = key, c
        self.icao, self.series, self.lst = c["icao"], c["series"], c["lst_offset_h"]
        self.dsm = DSMFeed(c["dsm_pil"], self.icao, self.lst)
        self.metar = MetarFeed(self.icao, self.lst)
        self.datis = DATISFeed(self.icao, self.lst) if c.get("datis") else None
        self.tgftp_cli = TGFTPClimateFeed(self.icao, self.lst, "cli")
        self.tgftp_dsm = TGFTPClimateFeed(self.icao, self.lst, "dsm")
        self.state = CityState(self.icao, self.series)
        self._board_date, self._board = None, []
    def buckets(self):
        d = climate_today(self.lst)
        if d != self._board_date:
            self._board = board(self.series, d)
            self._board_date = d
            log.info("%s board %s: %d buckets", self.key, d, len(self._board))
        return self._board
    def windows_today(self):
        """[(utc_dt, type)] for today's remaining reveal windows."""
        now = datetime.now(timezone.utc)
        out = []
        wins = list(self.c.get("dsm_windows_utc", []))
        if self.c.get("dsm_hourly_sweep"):
            wins += [f"{h:02d}:15" for h in range(24)]
        for w in sorted(set(wins)):
            h, m = map(int, w.split(":"))
            t = now.replace(hour=h, minute=m, second=0, microsecond=0)
            for cand in (t, t + timedelta(days=1)):
                if cand > now - timedelta(minutes=3):
                    out.append((cand, "dsm")); break
        m0 = self.c.get("metar_minute", 51)
        t = now.replace(minute=m0, second=0, microsecond=0)
        if t < now: t += timedelta(hours=1)
        out.append((t, "metar"))
        return sorted(out)
    def in_dsm_window(self, now, half_s):
        wins = list(self.c.get("dsm_windows_utc", []))
        if self.c.get("dsm_hourly_sweep"):
            wins.append(f"{now.hour:02d}:15")
        for w in wins:
            h, m = map(int, w.split(":"))
            t = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if abs((now - t).total_seconds()) <= half_s + 60:
                return True
        return False
    def in_metar_window(self, now, span_s):
        start = now.replace(minute=self.c.get("metar_minute", 51), second=0, microsecond=0)
        return timedelta(0) <= (now - start) <= timedelta(seconds=span_s)

CITIES: list[City] = []
ENGINE: KillEngine | None = None

def _persist():
    blob = {c.key: {"proven": {str(k): v for k, v in c.state.proven_max.items()},
                    "metar": {str(k): v for k, v in c.state.metar_max.items()},
                    "fired": [list(x) for x in c.state.fired]} for c in CITIES}
    json.dump(blob, open(STATE_PATH, "w"))

def _restore():
    if not os.path.exists(STATE_PATH):
        return
    try:
        blob = json.load(open(STATE_PATH))
    except Exception:
        return
    for c in CITIES:
        s = blob.get(c.key)
        if not s:
            continue
        c.state.proven_max = {Date.fromisoformat(k): v for k, v in s.get("proven", {}).items()}
        c.state.metar_max = {Date.fromisoformat(k): v for k, v in s.get("metar", {}).items()}
        c.state.fired = {tuple(x) for x in s.get("fired", [])}

def _handle(city: City, events):
    for ev in events:
        if ev.climate_date != climate_today(city.lst):
            continue
        STATE["latest_proof"][f"{city.key}:{ev.channel}"] = {
            "station": ev.station, "source": ev.detail[:120],
            "level_f": ev.level_f,
            "obs_ts": ev.obs_ts.isoformat() if ev.obs_ts else None,
            "seen_ts": ev.seen_ts.isoformat(),
            "latency_s": round((ev.seen_ts - ev.obs_ts).total_seconds(), 1) if ev.obs_ts else None,
        }
        journal.emit("proof", city=city.key, station=ev.station, channel=ev.channel,
                     level_f=ev.level_f, climate_date=str(ev.climate_date), detail=ev.detail[:120],
                     obs_ts=ev.obs_ts.isoformat() if ev.obs_ts else None,
                     seen_ts=ev.seen_ts.isoformat())
        intents = ENGINE.on_proof(city.state, ev, city.buckets(), quote)
        for it in intents:
            journal.emit("intent", city=city.key, ticker=it.ticker, action=it.action,
                         reason=it.reason[:200], channel=ev.channel, level_f=ev.level_f)
            rec = paper.execute(it, CFG["engine"]["fee_rate"])
            journal.emit("fill", city=city.key, **{k: rec[k] for k in
                         ("ticker", "sim_fill_contracts", "sim_avg_px_cents",
                          "sim_gross_usd", "sim_fee_usd", "best_bid_at_intent", "mode")})
            exec_live.execute(it)

def snapshot_state():
    with _state_lock:
        out = {"started": STATE["started"], "mode": STATE["mode"],
               "last_poll": dict(STATE["last_poll"]),
               "latest_proof": dict(STATE["latest_proof"]),
               "sources": dict(STATE["sources"]),
               "source_health": dict(STATE["source_health"]), "cities": {}}
        for c in CITIES:
            d = climate_today(c.lst)
            out["cities"][c.key] = {
                "icao": c.icao, "series": c.series,
                "climate_date": d.isoformat(),
                "proven_max": c.state.proven_max.get(d),
                "metar_ref": c.state.metar_max.get(d),
                "fired_count": len(c.state.fired),
                "windows": [(t.isoformat(), typ) for t, typ in c.windows_today()[:4]],
            }
        return out

def loop(stop: threading.Event):
    """Nonblocking feed scheduling. Only main thread can touch KillEngine.

    Previously 7 AWC timeouts + MADIS downloads serially delayed independent
    KLAX/KDEN NOAA METARs, DSM, and vendor WebSocket proof events. Every source
    now gets one in-flight request in its own future; late requests never block
    processing new station reports. Futures are consumed on the bot thread.
    """
    global CITIES, ENGINE
    ENGINE = KillEngine(CFG["engine"])
    CITIES = [City(k, c) for k, c in CFG["cities"].items()]
    _restore()
    journal.attach_log_bridge()
    STATE["started"] = datetime.now(timezone.utc).isoformat()
    STATE["mode"] = ("LIVE-ARMED" if os.environ.get("WEATHERBOT_LIVE") == "yes"
                     else "PAPER")
    journal.emit("system", msg=f"runtime started mode={STATE['mode']}")

    omo_stations = {
        c["icao"]: c["lst_offset_h"] for c in CFG["cities"].values()
        if c.get("omo")
    }
    omo = OMOFeed(omo_stations)
    mt_key = os.environ.get("MT_KEY", "")
    mt_feeds = [
        (city, MinuteTempFeed(city.icao, city.lst, mt_key))
        for city in CITIES
    ] if mt_key else []
    mt_queue = queue.Queue(maxsize=500)
    if mt_key:
        offsets = {city.icao: city.lst for city in CITIES}
        stream = MinuteTempStream(mt_key, offsets, mt_queue, stop)
        threading.Thread(
            target=stream.run, daemon=True, name="minutetemp-1m-ws"
        ).start()
    STATE["sources"] = {
        "madis_hf": "enabled" if omo_stations else "not_configured",
        "datis": "enabled_with_backoff",
        "tgftp": "enabled",
        "tgftp_cli": "enabled",
        "tgftp_dsm": "enabled",
        "iem_dsm": "enabled",
        "awc": "fallback_only",
        "minutetemp": "enabled" if mt_key else "missing_MT_KEY",
    }

    pol = CFG["polling"]
    by_icao = {c.icao: c for c in CITIES}
    pending = {}   # key -> (future, city_or_none, submitted_monotonic)
    next_due = {}  # key -> monotonic timestamp

    def submit(pool, key, fn, interval):
        now_s = time.monotonic()
        if key in pending or now_s < next_due.get(key, 0):
            return
        pending[key] = (pool.submit(fn), now_s)
        next_due[key] = now_s + max(1, interval)

    def receive_completed():
        for key, (future, started_s) in list(pending.items()):
            if not future.done():
                continue
            pending.pop(key, None)
            completed_at = datetime.now(timezone.utc)
            try:
                events = future.result()
                if events is None:
                    events = []
                # Explicit verification that every proof claims its own station.
                for ev in events:
                    city = by_icao.get(ev.station)
                    if city:
                        _handle(city, [ev])
                status = "ok" if events else "no_new_proof"
                if key.endswith(":datis"):
                    city = next((c for c in CITIES if key.startswith(c.key + ":")), None)
                    if city and city.datis and city.datis._fail_count:
                        status = "upstream_error_backoff"
                if key.endswith(":awc"):
                    city = next((c for c in CITIES if key.startswith(c.key + ":")), None)
                    if city and city.metar._awc_failures:
                        status = "upstream_error_backoff"
                STATE["source_health"][key] = {
                    "status": status,
                    "completed_at": completed_at.isoformat(),
                    "duration_ms": int(1000 * (time.monotonic() - started_s)),
                    "events": len(events),
                }
            except Exception as exc:
                log.warning("feed %s failed: %s", key, type(exc).__name__)
                STATE["source_health"][key] = {
                    "status": "error",
                    "completed_at": completed_at.isoformat(),
                    "error_type": type(exc).__name__,
                }
            STATE["last_poll"][key] = completed_at.isoformat()

    # Keep enough workers to handle up to 7 simultaneous station GETs for
    # several distinct providers without an AWC timeout tying up all workers.
    with ThreadPoolExecutor(max_workers=32, thread_name_prefix="mercury-feed") as pool:
        while not stop.is_set():
            try:
                # Process the earliest pushed OMO proofs before any networking.
                for _ in range(500):
                    try:
                        ev = mt_queue.get_nowait()
                    except queue.Empty:
                        break
                    city = by_icao.get(ev.station)
                    if city:
                        _handle(city, [ev])
                        STATE["last_poll"][f"{city.key}:minutetemp-ws"] = (
                            datetime.now(timezone.utc).isoformat())
                receive_completed()

                now = datetime.now(timezone.utc)
                for city in CITIES:
                    # Continuous official NOAA station METAR/SPECI, including
                    # 6-hour maxima. This request cannot wait on AWC or ATIS.
                    submit(pool, f"{city.key}:tgftp",
                           lambda c=city: c.metar.poll(fast_only=True),
                           pol.get("tgftp_metar_interval_s", 30))

                    # Full same-day climate products; a published TODAY CLI
                    # daily max is a hard historical lower-bound proof.
                    submit(pool, f"{city.key}:cli",
                           city.tgftp_cli.poll,
                           pol.get("tgftp_climate_interval_s", 30))
                    if city.in_dsm_window(now, pol["dsm_window_halfwidth_s"]):
                        submit(pool, f"{city.key}:tgftp-dsm",
                               city.tgftp_dsm.poll,
                               pol.get("tgftp_climate_interval_s", 30))
                        submit(pool, f"{city.key}:iem-dsm",
                               city.dsm.poll,
                               max(10, pol["dsm_poll_interval_s"]))

                    if city.datis is not None:
                        # Repeated upstream 500s activate DATISFeed backoff.
                        submit(pool, f"{city.key}:datis",
                               city.datis.poll,
                               pol.get("datis_poll_interval_s", 30))

                    # AWC is a supplementary historic SPECI feed, not the
                    # critical path. AWC hangs can never starve TGFTP/MADIS.
                    if city.in_metar_window(now, pol["metar_window_s"]):
                        submit(pool, f"{city.key}:awc",
                               lambda c=city: c.metar.poll(awc_only=True),
                               pol.get("awc_fallback_interval_s", 90))

                if omo_stations:
                    submit(pool, "omo",
                           omo.poll, pol["omo_poll_interval_s"])
                for city, mt in mt_feeds:
                    submit(pool, f"{city.key}:minutetemp-rest",
                           mt.poll,
                           pol.get("minutetemp_poll_interval_s", 90))

                # File writes were previously performed inside individual feed
                # calls. Persist engine ratchets on the main thread only.
                _persist()
                stop.wait(0.5)
            except Exception as exc:
                log.exception("runtime loop error: %s", type(exc).__name__)
                journal.emit("system", level="ERROR",
                             msg=f"runtime loop error: {type(exc).__name__}")
                stop.wait(3)
