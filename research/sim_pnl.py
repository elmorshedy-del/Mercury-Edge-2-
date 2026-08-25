#!/usr/bin/env python3
"""sim_pnl.py — full-archive replay of the V1 engine: the operating statement.

Fill model (stated, conservative):
  - price = historical bid at proof availability, minus 1c safety
  - size  = min(max_size, max(floor_fill, 50% of contracts that actually printed
            on that ticker in [avail, avail+5min]))   floor_fill=25 if bid>=15
  - fee   = Kalshi taker 0.07*p*(1-p), ceil to cent
Availability model (measured): METAR/6hr = report+3min; DSM = as-of LST +17min;
OMO floor = 5-min mark +3min (measured 2.3 typical).
All killed buckets settle 0 by construction (proofs are true facts)."""
import csv, math, os, re, statistics, sys
from datetime import datetime, timedelta, timezone, date as Date
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decode import c10_to_f, f_to_wholeC, wholeC_floor, Smoother, half_up
from feeds import DSBODY, MAXTOK, ProofEvent
from market import Bucket, taker_fee_dollars
from strategy import KillEngine, CityState

BT = "/agent/workspace/backtest"
CITIES = {"NYC": ("KNYC", "KXHIGHNY", -5, False), "MDW": ("KMDW", "KXHIGHCHI", -6, True),
          "AUS": ("KAUS", "KXHIGHAUS", -6, True), "MIA": ("KMIA", "KXHIGHMIA", -5, True),
          "DEN": ("KDEN", "KXHIGHDEN", -7, False), "PHL": ("KPHL", "KXHIGHPHIL", -5, True),
          "LAX": ("KLAX", "KXHIGHLAX", -8, True)}
D0, D1 = Date(2026, 7, 19), Date(2026, 8, 17)
CFG = {"min_bid_cents": 15, "max_spread_cents": 5, "max_size_contracts": 300,
       "fat_finger_guard_f": 7, "channels": ["dsm", "metar", "sixhr", "omo_floor"]}
MAXSZ, FLOORFILL, PART = 300, 25, 0.5

def pdt(s):
    dt = datetime.fromisoformat(s.replace("Z", "+00:00").replace(" ", "T"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def daterange():
    d = D0
    while d <= D1:
        yield d; d += timedelta(days=1)

# ---------- boards ----------
boards = defaultdict(list)
settles = {}
with open(f"{BT}/kalshi/manifest.csv") as f:
    for r in csv.DictReader(f):
        st = next(k for k, v in CITIES.items() if v[1] == r["series"])
        fl = int(float(r["floor_strike"])) if r["floor_strike"] else None
        cp = int(float(r["cap_strike"])) if r["cap_strike"] else None
        kind = "bin" if fl is not None and cp is not None else ("top" if fl is not None else "bot")
        boards[(st, r["event_date"])].append(Bucket(r["ticker"], fl, cp, kind, r["subtitle"]))
        if r["expiration_value"]:
            settles[(st, r["event_date"])] = int(round(float(r["expiration_value"])))

# ---------- candles ----------
_c = {}
def candles(t):
    if t in _c: return _c[t]
    rows = []
    try:
        with open(f"{BT}/kalshi/candles/{t}.csv") as f:
            for r in csv.DictReader(f):
                b, a = r["yes_bid_close"], r["yes_ask_close"]
                rows.append((pdt(r["ts_utc"]), int(b) if b else None, int(a) if a else None,
                             float(r["volume"] or 0)))
    except FileNotFoundError:
        pass
    _c[t] = rows; return rows

def quote_at(t, ts):
    b = a = None
    for r in candles(t):
        if r[0] <= ts:
            if r[1] is not None: b = r[1]
            if r[2] is not None: a = r[2]
        else: break
    return b, a

def vol_win(t, t0, mins=5):
    return sum(r[3] for r in candles(t) if t0 <= r[0] <= t0 + timedelta(minutes=mins))

# ---------- proof streams ----------
TG = re.compile(r'\bT([01])(\d{3})[01]\d{3}\b')
SIX = re.compile(r'\b1([01])(\d{3})\b')
def metar_proofs(st, icao, lst):
    out = []
    with open(f"{BT}/wx/metar_{st}.csv") as f:
        for r in csv.DictReader(f):
            ts = pdt(r["valid"]); raw = r.get("metar", "")
            cd = (ts + timedelta(hours=lst)).date()
            m = TG.search(raw)
            if m:
                c10 = int(m.group(2)) / 10 * (-1 if m.group(1) == "1" else 1)
                out.append(ProofEvent(icao, cd, c10_to_f(c10), "metar", ts, ts + timedelta(minutes=3)))
            if (ts + timedelta(minutes=15)).hour in (0, 6, 12, 18):
                s = SIX.search(raw)
                if s:
                    c10 = int(s.group(2)) / 10 * (-1 if s.group(1) == "1" else 1)
                    cd6 = (ts - timedelta(hours=3) + timedelta(hours=lst)).date()
                    out.append(ProofEvent(icao, cd6, c10_to_f(c10), "sixhr", ts, ts + timedelta(minutes=3)))
    return out

def dsm_proofs(st, icao, lst):
    out = []
    for ln in open(f"{BT}/wx/dsm_{st}.txt"):
        m = DSBODY.match(ln.strip())
        if not m or m.group(1) != icao or not m.group(2):
            continue
        tok = m.group(5).split("/")[0].strip()
        mt = MAXTOK.match(tok)
        if not mt: continue
        try: cd = Date(2026, int(m.group(4)), int(m.group(3)))
        except ValueError: continue
        asof = m.group(2)
        avail = (datetime(cd.year, cd.month, cd.day, int(asof[:2]) % 24, int(asof[2:]) % 60,
                          tzinfo=timezone.utc) - timedelta(hours=lst) + timedelta(minutes=17))
        out.append(ProofEvent(icao, cd, int(mt.group(1)), "dsm", None, avail, f"DS {asof}"))
    return out

def omo_proofs(st, icao, lst):
    out, sm = [], Smoother()
    try: f = open(f"{BT}/wx/onemin_{st}.csv")
    except FileNotFoundError: return out
    for r in csv.reader(f):
        if len(r) < 4 or r[0] == "station": continue
        try:
            ts = pdt(r[2]); v = float(r[3])
        except Exception: continue
        s = sm.push(ts.replace(tzinfo=None), v)
        if s is None or ts.minute % 5: continue
        out.append(ProofEvent(icao, (ts + timedelta(hours=lst)).date(),
                              wholeC_floor(f_to_wholeC(s)), "omo_floor", ts, ts + timedelta(minutes=3)))
    return out

# ---------- replay ----------
trades = []
raw_signals = tradeable = 0
for st, (icao, series, lst, omo_cov) in CITIES.items():
    proofs = metar_proofs(st, icao, lst) + dsm_proofs(st, icao, lst)
    if omo_cov: proofs += omo_proofs(st, icao, lst)
    proofs.sort(key=lambda e: e.seen_ts)
    by_day = defaultdict(list)
    for e in proofs: by_day[e.climate_date].append(e)
    for d in daterange():
        key = (st, d.isoformat())
        if key not in boards: continue
        eng = KillEngine(CFG); cs = CityState(icao, series)
        killcount = set()
        for ev in by_day.get(d, []):
            # count raw kill signals (any bucket newly dead, tradeable or not)
            for b in boards[key]:
                kl = b.kill_level
                if kl is not None and kl <= ev.level_f and (b.ticker, kl) not in killcount \
                   and ev.level_f > cs.proven_max.get(d, -999):
                    killcount.add((b.ticker, kl))
            intents = eng.on_proof(cs, ev, boards[key], lambda tk: quote_at(tk, ev.seen_ts))
            for it in intents:
                bid, ask = quote_at(it.ticker, ev.seen_ts)
                v5 = vol_win(it.ticker, ev.seen_ts)
                size = min(MAXSZ, max(FLOORFILL, PART * v5))
                px = bid - 1
                fee = taker_fee_dollars(px, size)
                pnl = px / 100 * size - fee
                cap = (100 - px) / 100 * size
                trades.append({"city": st, "date": d.isoformat(), "ticker": it.ticker,
                               "channel": ev.channel, "avail": ev.seen_ts.isoformat(),
                               "bid": bid, "ask": ask, "px": px, "size": round(size),
                               "vol5": round(v5), "fee": fee, "net": round(pnl, 2),
                               "capital": round(cap, 2)})
        raw_signals += len(killcount)
tradeable = len(trades)

with open("sim_trades.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(trades[0].keys())); w.writeheader(); w.writerows(trades)

# ---------- the operating statement ----------
days = 30
daily = defaultdict(float); dtrades = defaultdict(int)
for t in trades:
    daily[t["date"]] += t["net"]; dtrades[t["date"]] += 1
allday = [daily.get(d.isoformat(), 0.0) for d in daterange()]
nets = sorted(allday)
def pct(p): return nets[min(len(nets)-1, int(p/100*len(nets)))]
fat = [t for t in trades if t["px"] >= 50]
mid = [t for t in trades if 25 <= t["px"] < 50]
smb = [t for t in trades if t["px"] < 25]

print("="*78)
print("V1 ENGINE — FULL-ARCHIVE OPERATING STATEMENT (Jul 19–Aug 17, 7 cities)")
print("="*78)
print(f"\nSIGNALS")
print(f"  raw kill signals (any bucket newly provably dead): {raw_signals}  -> {raw_signals/days:.1f}/day")
print(f"  TRADEABLE signals (bid>=15c, spread<=5c):          {tradeable}  -> {tradeable/days:.2f}/day")
print(f"    by price: fat >=50c: {len(fat)} | 25-49c: {len(mid)} | 15-24c: {len(smb)}")
print(f"\nP&L (fill model: bid-1c, size=min(300,max(25,50% of 5-min printed vol)), fees in)")
tot = sum(t["net"] for t in trades)
print(f"  total net 30 days:  ${tot:,.2f}")
print(f"  per day: mean ${tot/days:.2f} | median ${statistics.median(allday):.2f} | p10 ${pct(10):.2f} | p90 ${pct(90):.2f}")
print(f"  zero-trade days: {sum(1 for x in allday if x==0)}/{days}")
print(f"  best day: ${max(allday):.2f}  ({max(daily, key=daily.get) if daily else '-'})")
print(f"\nPER TRADE")
if trades:
    print(f"  avg size {statistics.mean(t['size'] for t in trades):.0f} contracts | "
          f"avg px {statistics.mean(t['px'] for t in trades):.0f}c | "
          f"avg net ${statistics.mean(t['net'] for t in trades):.2f} | "
          f"median net ${statistics.median(t['net'] for t in trades):.2f}")
    print(f"  avg capital tied per trade ${statistics.mean(t['capital'] for t in trades):.0f} | "
          f"max ${max(t['capital'] for t in trades):.0f}")
print(f"\nBY CITY")
bc = defaultdict(lambda: [0, 0.0])
for t in trades: bc[t["city"]][0] += 1; bc[t["city"]][1] += t["net"]
for c in CITIES:
    n, v = bc[c]; print(f"  {c}: {n:3d} trades  ${v:9,.2f}")
print(f"\nBY CHANNEL")
ch = defaultdict(lambda: [0, 0.0])
for t in trades: ch[t["channel"]][0] += 1; ch[t["channel"]][1] += t["net"]
for k, (n, v) in sorted(ch.items(), key=lambda x: -x[1][1]):
    print(f"  {k:10s}: {n:3d} trades  ${v:9,.2f}")
print(f"\nTOP 10 TRADES")
for t in sorted(trades, key=lambda x: -x["net"])[:10]:
    print(f"  {t['date']} {t['ticker']:26s} {t['channel']:9s} bid={t['bid']:3d} size={t['size']:4d} net=${t['net']:7.2f}")
