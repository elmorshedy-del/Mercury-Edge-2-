"""runtime.py — the scheduler as an importable, thread-runnable service.
Same logic as the standalone run.py, plus journaling and a shared STATE for the API."""
from __future__ import annotations
import json, time, logging, os, threading, queue
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timedelta, timezone, date as Date

import journal
from feeds import DSMFeed, MetarFeed, OMOFeed
from datis import DATISFeed
from climate_products import TGFTPClimateFeed
from minutetemp import MinuteTempFeed, MinuteTempStream
from market import board, quote
from strategy import KillEngine, CityState
import paper
import exec_live

log = logging.getLogger("runtime")
HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json")))
DATA_DIR = journal.DATA_DIR
STATE_PATH = os.path.join(DATA_DIR, "state.json")

STATE = {"started": None, "mode": "PAPER", "last_poll": {}, "latest_proof": {}, "sources": {}, "cities": {}}
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
               "sources": dict(STATE["sources"]), "cities": {}}
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
    """One proof-processing owner; isolated parallel network fetchers.

    AWC, ATIS Relay, MADIS and DSM can hang or timeout. Submitting their
    I/O to independent workers prevents one station/source from delaying
    other weather evidence. Trading decisions and state updates stay on
    this one runtime thread (never in the network workers).
    """
    global CITIES, ENGINE
    ENGINE = KillEngine(CFG["engine"])
    CITIES = [City(k, c) for k, c in CFG["cities"].items()]
    _restore()
    journal.attach_log_bridge()
    STATE["started"] = datetime.now(timezone.utc).isoformat()
    STATE["mode"] = "LIVE-ARMED" if os.environ.get("WEATHERBOT_LIVE") == "yes" else "PAPER"
    journal.emit("system", msg=f"runtime started mode={STATE['mode']}")
    by_icao = {c.icao: c for c in CITIES}
    omo_stations = {
        c["icao"]: c["lst_offset_h"]
        for c in CFG["cities"].values() if c.get("omo")
    }
    omo = OMOFeed(omo_stations)
    mt_key = os.environ.get("MT_KEY", "")
    mt_feeds = [(c, MinuteTempFeed(c.icao, c.lst, mt_key))
                for c in CITIES] if mt_key else []
    mt_queue = queue.Queue(maxsize=500)
    if mt_key:
        offsets = {c.icao: c.lst for c in CITIES}
        stream = MinuteTempStream(mt_key, offsets, mt_queue, stop)
        threading.Thread(
            target=stream.run, daemon=True,
            name="minutetemp-1m-ws").start()
    STATE["sources"] = {
        "madis_hf": "enabled" if omo_stations else "not_configured",
        "datis": "enabled_with_upstream_backoff",
        "tgftp_metar": "enabled",
        "tgftp_dsm": "enabled_date_guarded",
        "tgftp_cli": "enabled_date_guarded",
        "awc_metar": "supplementary_with_backoff",
        "minutetemp": "configured" if mt_key else "missing_MT_KEY",
    }
    pol = CFG["polling"]
    # No synchronous 'warm start': all sources get an immediate initial
    # request, and their results are consumed independently as they finish.
    inflight: dict[str, Future] = {}
    owners: dict[str, City | None] = {}
    submitted_at: dict[str, float] = {}
    tasks_started = 0

    with ThreadPoolExecutor(max_workers=24, thread_name_prefix="mercury-feed") as pool:
        def schedule(key, owner, fn, interval_s: float, now_mono: float,
                     now_utc: datetime):
            nonlocal tasks_started
            if key in inflight:
                return
            if now_mono - submitted_at.get(key, -1.e10) < interval_s:
                return
            inflight[key] = pool.submit(fn)
            owners[key] = owner
            submitted_at[key] = now_mono
            STATE["last_poll"][key] = now_utc.isoformat()
            tasks_started += 1

        while not stop.is_set():
            try:
                now_utc = datetime.now(timezone.utc)
                now_mono = time.monotonic()

                # Vendor push observations have priority over polling.
                for _ in range(500):
                    try:
                        ev = mt_queue.get_nowait()
                    except queue.Empty:
                        break
                    city = by_icao.get(ev.station)
                    if city:
                        _handle(city, [ev])

                # Completed worker tasks are the only other entry point
                # into KillEngine; the queue can never cause parallel trades.
                for key, task in list(inflight.items()):
                    if not task.done():
                        continue
                    inflight.pop(key, None)
                    owner = owners.pop(key, None)
                    try:
                        events = task.result()
                        if key == "omo":
                            for ev in events:
                                city = by_icao.get(ev.station)
                                if city is not None:
                                    _handle(city, [ev])
                        elif owner is not None and events:
                            _handle(owner, events)
                    except Exception as exc:
                        # No misleading "last success" timestamp here:
                        # last_poll records the attempted network poll only.
                        log.warning("feed task failed %s: %s", key, type(exc).__name__)

                for c in CITIES:
                    # 30s station-file polling catches hourly METAR + SPECI
                    # and their six-hour maxima regardless of AWC availability.
                    schedule(f"{c.key}:tgftp", c,
                             lambda c=c: c.metar.poll(fast_only=True),
                             pol.get("fast_metar_poll_interval_s", 30),
                             now_mono, now_utc)

                    if c.datis is not None:
                        schedule(f"{c.key}:datis", c, c.datis.poll,
                                 pol.get("datis_poll_interval_s", 30),
                                 now_mono, now_utc)

                    # A same-day CLI release can establish a running max.
                    # Yesterday's reports are skipped in the feed parser.
                    schedule(f"{c.key}:cli", c, c.tgftp_cli.poll,
                             pol.get("cli_poll_interval_s", 60),
                             now_mono, now_utc)

                    # DSM sources race only around their configured release
                    # windows; stale TGFTP station files fail date validation.
                    if c.in_dsm_window(now_utc, pol["dsm_window_halfwidth_s"]):
                        schedule(f"{c.key}:dsm-tgftp", c,
                                 c.tgftp_dsm.poll,
                                 pol.get("dsm_tgftp_poll_interval_s", 15),
                                 now_mono, now_utc)
                        schedule(f"{c.key}:dsm-iem", c,
                                 c.dsm.poll,
                                 max(10, pol.get("dsm_poll_interval_s", 15)),
                                 now_mono, now_utc)

                    if c.in_metar_window(now_utc, pol["metar_window_s"]):
                        # History lane independent of TGFTP. Per-station
                        # exponential backoff handles HTTP read timeouts.
                        schedule(f"{c.key}:awc", c,
                                 lambda c=c: c.metar.poll(awc_only=True),
                                 pol.get("awc_poll_interval_s", 60),
                                 now_mono, now_utc)

                # Licensed REST catch-up is optional; WS is the fastest
                # minuteTemp path when MT_KEY is present.
                for c, feed in mt_feeds:
                    schedule(f"{c.key}:minutetemp-rest", c, feed.poll,
                             pol.get("minutetemp_poll_interval_s", 70),
                             now_mono, now_utc)

                if omo_stations:
                    schedule("omo", None, omo.poll,
                             pol.get("omo_poll_interval_s", 60),
                             now_mono, now_utc)
                _persist()
                stop.wait(0.5)
            except Exception as exc:
                log.error("loop error: %s", exc)
                journal.emit("system", level="ERROR", msg=f"loop error: {type(exc).__name__}: {exc}")
                stop.wait(3)
