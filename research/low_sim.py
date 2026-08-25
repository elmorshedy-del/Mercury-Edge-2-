#!/usr/bin/env python3
"""low_sim.py — extend the V1 operating statement to the KXLOW* series.
Mirror of sim_pnl.py: proven-MIN ratchet; bins die when min < floor;
top tails ('X or above') die when min <= floor. Bottom tails never killed."""
import csv, json, math, os, re, statistics, sys, time, urllib.request
from datetime import datetime, timedelta, timezone, date as Date
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decode import c10_to_f, f_to_wholeC, wholeC_candidates, Smoother
from feeds import DSBODY, MAXTOK
from market import taker_fee_dollars

BT = "/agent/workspace/backtest"
LOWDIR = f"{BT}/kalshi_low"; os.makedirs(f"{LOWDIR}/candles", exist_ok=True)
B = "https://api.elections.kalshi.com/trade-api/v2"
CITIES = {"NYC": ("KNYC", "KXLOWNY", -5, False), "MDW": ("KMDW", "KXLOWCHI", -6, True),
          "AUS": ("KAUS", "KXLOWAUS", -6, True), "MIA": ("KMIA", "KXLOWMIA", -5, True),
          "DEN": ("KDEN", "KXLOWDEN", -7, False), "PHL": ("KPHL", "KXLOWPHIL", -5, True),
          "LAX": ("KLAX", "KXLOWLAX", -8, True)}
D0, D1 = Date(2026, 7, 19), Date(2026, 8, 17)
MIN_BID, MAX_SPREAD, MAXSZ, FLOORFILL, PART, GUARD_F = 15, 5, 300, 25, 0.5, 7

def get(u, tries=3):
    for k in range(tries):
        try:
            r = urllib.request.Request(u, headers={"User-Agent": "weatherbot-lowsim"})
            return json.loads(urllib.request.urlopen(r, timeout=30).read())
        except Exception:
            if k == tries - 1: raise
            time.sleep(2 * (k + 1))

def pdt(s):
    dt = datetime.fromisoformat(s.replace("Z", "+00:00").replace(" ", "T"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def daterange():
    d = D0
    while d <= D1:
        yield d; d += timedelta(days=1)

# ---------------- manifest (cached) ----------------
MAN = f"{LOWDIR}/manifest.csv"
if not os.path.exists(MAN):
    rows = []
    for st, (_, series, _, _) in CITIES.items():
        cur = ""
        while True:
            u = f"{B}/markets?series_ticker={series}&status=settled&limit=100" + (f"&cursor={cur}" if cur else "")
            d = get(u); time.sleep(0.25)
            for m in d.get("markets", []):
                et = m["event_ticker"]
                tag = et.split("-")[1]
                try:
                    ed = datetime.strptime(tag, "%y%b%d").date()
                except ValueError:
                    continue
                if D0 <= ed <= D1:
                    rows.append({"city": st, "series": series, "event_date": ed.isoformat(),
                                 "ticker": m["ticker"],
                                 "floor": m.get("floor_strike", ""), "cap": m.get("cap_strike", ""),
                                 "subtitle": m.get("yes_sub_title") or "",
                                 "settle": m.get("expiration_value", "")})
            cur = d.get("cursor", "")
            if not cur: break
    with open(MAN, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"manifest: {len(rows)} low markets saved")

boards = defaultdict(list); settles = {}
with open(MAN) as f:
    for r in csv.DictReader(f):
        fl = int(float(r["floor"])) if r["floor"] not in ("", "None") else None
        cp = int(float(r["cap"])) if r["cap"] not in ("", "None") else None
        kind = "bin" if fl is not None and cp is not None else ("top" if fl is not None else "bot")
        # kill threshold T: dead once proven_min <= T
        T = (fl - 1) if kind == "bin" else (fl if kind == "top" else None)
        boards[(r["city"], r["event_date"])].append(
            {"ticker": r["ticker"], "T": T, "sub": r["subtitle"], "kind": kind})
        if r["settle"]:
            settles[(r["city"], r["event_date"])] = int(round(float(r["settle"])))

# ---------------- candles (lazy, disk-cached) ----------------
_c = {}
def candles(tick, ed: str):
    if tick in _c: return _c[tick]
    path = f"{LOWDIR}/candles/{tick}.csv"
    if not os.path.exists(path):
        d0 = datetime.fromisoformat(ed).replace(tzinfo=timezone.utc)
        t0, t1 = int(d0.timestamp()), int((d0 + timedelta(hours=29)).timestamp())
        series = tick.split("-")[0]
        try:
            d = get(f"{B}/series/{series}/markets/{tick}/candlesticks?start_ts={t0}&end_ts={t1}&period_interval=1")
        except Exception:
            _c[tick] = []; return []
        time.sleep(0.25)
        with open(path, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["ts", "bid", "ask", "vol"])
            for c in d.get("candlesticks", []):
                ts = datetime.fromtimestamp(c["end_period_ts"], tz=timezone.utc).isoformat()
                def cv(o, k):
                    if not o: return ""
                    v = o.get(k)
                    if v is not None: return int(v)
                    v = o.get(k + "_dollars")
                    return round(float(v) * 100) if v else ""
                w.writerow([ts, cv(c.get("yes_bid"), "close"), cv(c.get("yes_ask"), "close"),
                            c.get("volume") or c.get("volume_fp") or 0])
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append((pdt(r["ts"]), int(r["bid"]) if r["bid"] else None,
                         int(r["ask"]) if r["ask"] else None, float(r["vol"] or 0)))
    _c[tick] = rows; return rows

def quote_at(tick, ed, ts):
    b = a = None
    for r in candles(tick, ed):
        if r[0] <= ts:
            if r[1] is not None: b = r[1]
            if r[2] is not None: a = r[2]
        else: break
    return b, a

def vol_win(tick, ed, t0, mins=5):
    return sum(r[3] for r in candles(tick, ed) if t0 <= r[0] <= t0 + timedelta(minutes=mins))

# ---------------- proof streams (minima) ----------------
TG = re.compile(r'\bT([01])(\d{3})[01]\d{3}\b')
SIXMIN = re.compile(r'\b2([01])(\d{3})\b')
def proofs_for(st, icao, lst, omo_cov):
    out = []
    with open(f"{BT}/wx/metar_{st}.csv") as f:
        for r in csv.DictReader(f):
            ts = pdt(r["valid"]); raw = r.get("metar", "")
            cd = (ts + timedelta(hours=lst)).date()
            m = TG.search(raw)
            if m:
                c10 = int(m.group(2)) / 10 * (-1 if m.group(1) == "1" else 1)
                out.append((ts + timedelta(minutes=3), cd, c10_to_f(c10), "metar"))
            if (ts + timedelta(minutes=15)).hour in (0, 6, 12, 18):
                s = SIXMIN.search(raw)
                if s:
                    c10 = int(s.group(2)) / 10 * (-1 if s.group(1) == "1" else 1)
                    cd6 = (ts - timedelta(hours=3) + timedelta(hours=lst)).date()
                    out.append((ts + timedelta(minutes=3), cd6, c10_to_f(c10), "sixhr_min"))
    for ln in open(f"{BT}/wx/dsm_{st}.txt"):
        m = DSBODY.match(ln.strip())
        if not m or m.group(1) != icao or not m.group(2): continue
        parts = [p.strip() for p in m.group(5).split("/")]
        if len(parts) < 2: continue
        mt = MAXTOK.match(parts[1])
        if not mt: continue
        try: cd = Date(2026, int(m.group(4)), int(m.group(3)))
        except ValueError: continue
        asof = m.group(2)
        avail = (datetime(cd.year, cd.month, cd.day, int(asof[:2]) % 24, int(asof[2:]) % 60,
                          tzinfo=timezone.utc) - timedelta(hours=lst) + timedelta(minutes=17))
        out.append((avail, cd, int(mt.group(1)), "dsm"))
    if omo_cov:
        sm = Smoother()
        try:
            with open(f"{BT}/wx/onemin_{st}.csv") as f:
                for r in csv.reader(f):
                    if len(r) < 4 or r[0] == "station": continue
                    try:
                        ts = pdt(r[2]); v = float(r[3])
                    except Exception: continue
                    s = sm.push(ts.replace(tzinfo=None), v)
                    if s is None or ts.minute % 5: continue
                    ceil_f = wholeC_candidates(f_to_wholeC(s))[-1]   # min <= ceiling
                    out.append((ts + timedelta(minutes=3), (ts + timedelta(hours=lst)).date(),
                                ceil_f, "omo_ceil"))
        except FileNotFoundError:
            pass
    out.sort(key=lambda x: x[0])
    return out

# ---------------- replay ----------------
trades = []; raw_signals = 0; qc_bad = 0; qc_n = 0
for st, (icao, series, lst, omo_cov) in CITIES.items():
    allp = proofs_for(st, icao, lst, omo_cov)
    by_day = defaultdict(list)
    for p in allp: by_day[p[1]].append(p)
    for d in daterange():
        key = (st, d.isoformat())
        if key not in boards: continue
        proven = 999; vis_ref = 999; fired = set()
        for avail, cd, level, ch in by_day.get(d, []):
            if ch in ("metar", "sixhr_min"):
                vis_ref = min(vis_ref, level)
            if level >= proven: continue
            if ch in ("dsm", "omo_ceil") and vis_ref < 999 and level < vis_ref - GUARD_F:
                continue  # plausibility guard (mirror)
            newly = [b for b in boards[key] if b["T"] is not None and proven > b["T"] >= level]
            proven = level
            for b in newly:
                k = b["ticker"]
                if k in fired: continue
                fired.add(k)
                raw_signals += 1
                bid, ask = quote_at(k, d.isoformat(), avail)
                if bid is None or bid < MIN_BID: continue
                if ask is not None and ask - bid > MAX_SPREAD: continue
                v5 = vol_win(k, d.isoformat(), avail)
                size = min(MAXSZ, max(FLOORFILL, PART * v5))
                px = bid - 1
                fee = taker_fee_dollars(px, size)
                trades.append({"city": st, "date": d.isoformat(), "ticker": k, "channel": ch,
                               "avail": avail.isoformat(), "bid": bid, "ask": ask, "px": px,
                               "size": round(size), "vol5": round(v5), "fee": fee,
                               "net": round(px / 100 * size - fee, 2)})
        # QC: final proven min vs settle
        sv = settles.get(key)
        if sv is not None and proven < 999:
            qc_n += 1
            if proven > sv:  # we never proved down to settle — fine (channels sparse)
                pass
            if proven < sv:  # we "proved" below settle — would be a bug
                qc_bad += 1

with open(f"{LOWDIR}/sim_trades_low.csv", "w", newline="") as f:
    if trades:
        w = csv.DictWriter(f, fieldnames=list(trades[0].keys())); w.writeheader(); w.writerows(trades)

days = 30
daily = defaultdict(float)
for t in trades: daily[t["date"]] += t["net"]
allday = [daily.get(d.isoformat(), 0.0) for d in daterange()]
tot = sum(t["net"] for t in trades)
print("=" * 74)
print("LOW SERIES (KXLOW*) — V1 ENGINE OPERATING STATEMENT, same 30 days")
print("=" * 74)
print(f"QC: city-days with proofs below settlement value (would be bugs): {qc_bad}/{qc_n}")
print(f"raw kill signals: {raw_signals} ({raw_signals/days:.1f}/day)")
print(f"TRADEABLE: {len(trades)} ({len(trades)/days:.2f}/day) | total net ${tot:,.2f} | mean/day ${tot/days:.2f}")
print(f"zero-trade days: {sum(1 for x in allday if x == 0)}/{days} | best day ${max(allday):.2f}")
bc = defaultdict(lambda: [0, 0.0]); ch = defaultdict(lambda: [0, 0.0])
for t in trades:
    bc[t["city"]][0] += 1; bc[t["city"]][1] += t["net"]
    ch[t["channel"]][0] += 1; ch[t["channel"]][1] += t["net"]
print("by city: " + " | ".join(f"{c}:{bc[c][0]}tr ${bc[c][1]:,.0f}" for c in CITIES))
print("by channel: " + " | ".join(f"{k}:{v[0]}tr ${v[1]:,.0f}" for k, v in sorted(ch.items(), key=lambda x: -x[1][1])))
if trades:
    print(f"per trade: avg px {statistics.mean(t['px'] for t in trades):.0f}c | avg net ${statistics.mean(t['net'] for t in trades):.2f}")
    print("\nTOP 10:")
    for t in sorted(trades, key=lambda x: -x["net"])[:10]:
        print(f"  {t['date']} {t['ticker']:26s} {t['channel']:9s} bid={t['bid']:3d} size={t['size']:4d} net=${t['net']:7.2f}  @{t['avail'][11:16]}Z")
