"""runtime.py — the scheduler as an importable, thread-runnable service.
Same logic as the standalone run.py, plus journaling and a shared STATE for the API."""
from __future__ import annotations
import json, time, logging, os, threading
from datetime import datetime, timedelta, timezone, date as Date

import journal
from feeds import DSMFeed, MetarFeed, OMOFeed
from market import board, quote
from strategy import KillEngine, CityState
import paper
import exec_live

log = logging.getLogger("runtime")
HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json")))
DATA_DIR = journal.DATA_DIR
STATE_PATH = os.path.join(DATA_DIR, "state.json")

STATE = {"started": None, "mode": "PAPER", "last_poll": {}, "cities": {}}
_state_lock = threading.Lock()

def climate_today(lst_off: int) -> Date:
    return (datetime.now(timezone.utc) + timedelta(hours=lst_off)).date()

class City:
    def __init__(self, key: str, c: dict):
        self.key, self.c = key, c
        self.icao, self.series, self.lst = c["icao"], c["series"], c["lst_offset_h"]
        self.dsm = DSMFeed(c["dsm_pil"], self.icao, self.lst)
        self.metar = MetarFeed(self.icao, self.lst)
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
        journal.emit("proof", city=city.key, station=ev.station, channel=ev.channel,
                     level_f=ev.level_f, climate_date=str(ev.climate_date), detail=ev.detail[:120])
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
               "last_poll": dict(STATE["last_poll"]), "cities": {}}
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
    global CITIES, ENGINE
    ENGINE = KillEngine(CFG["engine"])
    CITIES = [City(k, c) for k, c in CFG["cities"].items()]
    _restore()
    journal.attach_log_bridge()
    STATE["started"] = datetime.now(timezone.utc).isoformat()
    STATE["mode"] = "LIVE-ARMED" if os.environ.get("WEATHERBOT_LIVE") == "yes" else "PAPER"
    journal.emit("system", msg=f"runtime started mode={STATE['mode']}")
    omo_stations = {c["icao"]: c["lst_offset_h"] for c in CFG["cities"].values() if c.get("omo")}
    omo = OMOFeed(omo_stations)
    pol = CFG["polling"]
    # warm start
    for c in CITIES:
        try:
            _handle(c, c.metar.poll()); time.sleep(0.4)
            _handle(c, c.dsm.poll());  time.sleep(0.4)
        except Exception as e:
            log.warning("warm start %s: %s", c.key, e)
    _persist()
    last_omo = 0.0
    while not stop.is_set():
        try:
            now = datetime.now(timezone.utc)
            busy = False
            for c in CITIES:
                if c.in_dsm_window(now, pol["dsm_window_halfwidth_s"]):
                    _handle(c, c.dsm.poll()); busy = True
                    STATE["last_poll"][f"{c.key}:dsm"] = now.isoformat()
                    stop.wait(pol["dsm_poll_interval_s"])
                if c.in_metar_window(now, pol["metar_window_s"]):
                    _handle(c, c.metar.poll()); busy = True
                    STATE["last_poll"][f"{c.key}:metar"] = now.isoformat()
                    stop.wait(pol["metar_poll_interval_s"])
            if omo_stations and time.time() - last_omo >= pol["omo_poll_interval_s"]:
                evs = omo.poll(); last_omo = time.time()
                STATE["last_poll"]["omo"] = now.isoformat()
                for ev in evs:
                    city = next((c for c in CITIES if c.icao == ev.station), None)
                    if city:
                        _handle(city, [ev])
            _persist()
            if not busy:
                stop.wait(pol["idle_interval_s"])
        except Exception as e:
            log.error("loop error: %s", e)
            journal.emit("system", level="ERROR", msg=f"loop error: {e}")
            stop.wait(10)
