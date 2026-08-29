"""Mercury Edge 2 — API server + background workers (bot, depth collector, census).
Run: uvicorn app.server:app --host 0.0.0.0 --port $PORT"""
from __future__ import annotations
import json, os, sys, time, threading
from datetime import datetime, timedelta, timezone
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

import journal, runtime
from market import board, quote, orderbook_yes_bids

DATA = journal.DATA_DIR
LEDGER = os.path.join(DATA, "paper_ledger.jsonl")
DEPTH = os.path.join(DATA, "depth_log.jsonl")
CENSUS = os.path.join(DATA, "census_last.json")
CFG = json.load(open(os.path.join(ROOT, "engine", "config.json")))

app = FastAPI(title="Mercury Edge 2")
_stop = threading.Event()

# ---------------- background workers ----------------
def _worker_bot():
    runtime.loop(_stop)

def _worker_collector():
    """Depth snapshots at race minutes (12,14,16 past 20-23Z; :50/:53/:56 hourly)."""
    while not _stop.is_set():
        now = datetime.now(timezone.utc)
        race = (now.minute in (12, 14, 16) and now.hour in (20, 21, 22, 23)) or now.minute in (50, 53, 56)
        if race:
            try:
                rows = 0
                for key, c in CFG["cities"].items():
                    d = (now + timedelta(hours=c["lst_offset_h"])).date()
                    for b in board(c["series"], d):
                        bids = orderbook_yes_bids(b.ticker)[:8]
                        with open(DEPTH, "a") as f:
                            f.write(json.dumps({"ts": now.isoformat(), "ticker": b.ticker,
                                                "yes_bids": bids}) + "\n")
                        rows += 1
                        time.sleep(0.12)
                journal.emit("system", msg=f"depth snapshot: {rows} books")
            except Exception as e:
                journal.emit("system", level="WARN", msg=f"depth collector: {e}")
            _stop.wait(70)
        else:
            _stop.wait(20)

def _worker_census():
    import urllib.request
    WATCH = ["KXLOWNY", "KXLOWCHI", "KXLOWAUS", "KXLOWDEN", "KXLOWLAX", "KXLOWMIA",
             "KXLOWPHIL", "KXHIGHOU", "KXHIGHHOU", "KXHIGHSEA", "KXHIGHPHX",
             "KXHIGHLV", "KXHIGHSF", "KXHIGHATL", "KXHIGHDC", "KXHIGHBOS", "KXHIGHDFW"]
    B = "https://api.elections.kalshi.com/trade-api/v2"
    while not _stop.is_set():
        alerts = []
        for s in WATCH:
            try:
                r = urllib.request.Request(f"{B}/markets?series_ticker={s}&limit=2",
                                           headers={"User-Agent": "mercury-edge"})
                ms = json.loads(urllib.request.urlopen(r, timeout=20).read()).get("markets", [])
                if ms:
                    alerts.append({"series": s, "first_event": ms[0].get("event_ticker")})
            except Exception:
                pass
            time.sleep(0.3)
        payload = {"ts": datetime.now(timezone.utc).isoformat(), "alerts": alerts,
                   "watched": len(WATCH)}
        json.dump(payload, open(CENSUS, "w"))
        if alerts:
            journal.emit("census", **payload)
        _stop.wait(6 * 3600)

@app.on_event("startup")
def _startup():
    for fn in (_worker_bot, _worker_collector, _worker_census):
        threading.Thread(target=fn, daemon=True, name=fn.__name__).start()

@app.on_event("shutdown")
def _shutdown():
    _stop.set()

# ---------------- helpers ----------------
def _ledger(limit=5000):
    if not os.path.exists(LEDGER):
        return []
    with open(LEDGER) as f:
        lines = f.readlines()[-limit:]
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    return out

_qcache: dict = {"ts": 0, "data": {}}
def _boards_with_quotes():
    if time.time() - _qcache["ts"] < 60:
        return _qcache["data"]
    out = {}
    now = datetime.now(timezone.utc)
    for key, c in CFG["cities"].items():
        d = (now + timedelta(hours=c["lst_offset_h"])).date()
        rows = []
        try:
            for b in board(c["series"], d):
                bid, ask = quote(b.ticker)
                rows.append({"ticker": b.ticker, "sub": b.subtitle, "kind": b.kind,
                             "kill_level": b.kill_level, "bid": bid, "ask": ask})
        except Exception:
            pass
        rows.sort(key=lambda r: (r["kill_level"] is None, r["kill_level"] or 999))
        out[key] = rows
    _qcache.update(ts=time.time(), data=out)
    return out

# ---------------- API ----------------
@app.get("/api/status")
def api_status():
    st = runtime.snapshot_state()
    started = st.get("started")
    uptime = None
    if started:
        uptime = int((datetime.now(timezone.utc) - datetime.fromisoformat(started)).total_seconds())
    windows = []
    for ck, cv in st["cities"].items():
        for t, typ in cv.get("windows", []):
            windows.append({"city": ck, "type": typ, "at": t})
    windows.sort(key=lambda w: w["at"])
    led = _ledger()
    today = datetime.now(timezone.utc).date().isoformat()
    return {"now": datetime.now(timezone.utc).isoformat(), "mode": st["mode"],
            "uptime_s": uptime, "cities": st["cities"], "last_poll": st["last_poll"],
            "next_windows": windows[:8],
            "trades_total": len(led),
            "trades_today": sum(1 for t in led if t["ts"][:10] == today)}

@app.get("/api/boards")
def api_boards():
    return _boards_with_quotes()

@app.get("/api/trades")
def api_trades(limit: int = 200):
    return list(reversed(_ledger()))[:limit]

@app.get("/api/pnl")
def api_pnl():
    led = _ledger()
    by_day, by_city, by_ch = defaultdict(float), defaultdict(float), defaultdict(float)
    cum, run = [], 0.0
    for t in led:
        net = round(t.get("sim_gross_usd", 0) - t.get("sim_fee_usd", 0), 2)
        day = t["ts"][:10]
        by_day[day] += net
        by_city[t.get("ticker", "??")[2:].split("-")[0].replace("KXHIGH", "")] += net
        by_ch[t.get("proof_channel", "?")] += net
        run += net
        cum.append({"ts": t["ts"], "cum": round(run, 2)})
    today = datetime.now(timezone.utc).date().isoformat()
    return {"total_net": round(run, 2), "today_net": round(by_day.get(today, 0), 2),
            "n_trades": len(led),
            "avg_net": round(run / len(led), 2) if led else 0,
            "by_day": [{"date": k, "net": round(v, 2)} for k, v in sorted(by_day.items())],
            "by_city": {k: round(v, 2) for k, v in by_city.items()},
            "by_channel": {k: round(v, 2) for k, v in by_ch.items()},
            "cum": cum}

@app.get("/api/events")
def api_events(limit: int = 250):
    return journal.tail(limit)

@app.get("/api/depth")
def api_depth():
    if not os.path.exists(DEPTH):
        return {"last": None, "rows": 0}
    with open(DEPTH) as f:
        lines = f.readlines()
    last = json.loads(lines[-1]) if lines else None
    return {"rows": len(lines), "last_ts": last["ts"] if last else None}

@app.get("/api/audit/missed-kills")
def api_audit_missed_kills():
    """Read-only replay of the original zero-paper-trade bug period."""
    from research.missed_kill_audit import audit
    return audit(DATA, CFG)

@app.get("/api/census")
def api_census():
    if os.path.exists(CENSUS):
        return json.load(open(CENSUS))
    return {"ts": None, "alerts": [], "watched": 0}

@app.get("/api/config")
def api_config():
    return CFG

@app.get("/")
def index():
    return FileResponse(os.path.join(ROOT, "app", "static", "index.html"))

@app.get("/health")
def health():
    return {"ok": True}
