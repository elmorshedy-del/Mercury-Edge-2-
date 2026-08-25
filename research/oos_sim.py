#!/usr/bin/env python3
"""oos_sim.py — out-of-sample test: Jun 15 – Jul 18 2026, identical engine,
identical parameters, fresh data. Resumable (skips anything already fetched)."""
import csv, json, os, re, statistics, sys, time, urllib.request
from datetime import datetime, timedelta, timezone, date as Date
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decode import c10_to_f, f_to_wholeC, wholeC_floor, Smoother
from feeds import DSBODY, MAXTOK, ProofEvent
from market import Bucket, taker_fee_dollars
from strategy import KillEngine, CityState

WX = "/agent/workspace/backtest/wx_jun"; os.makedirs(WX, exist_ok=True)
KD = "/agent/workspace/backtest/kalshi_jun"; os.makedirs(f"{KD}/candles", exist_ok=True)
B = "https://api.elections.kalshi.com/trade-api/v2"
CITIES = {"NYC": ("KNYC", "KXHIGHNY", -5, False), "MDW": ("KMDW", "KXHIGHCHI", -6, True),
          "AUS": ("KAUS", "KXHIGHAUS", -6, True), "MIA": ("KMIA", "KXHIGHMIA", -5, True),
          "DEN": ("KDEN", "KXHIGHDEN", -7, False), "PHL": ("KPHL", "KXHIGHPHIL", -5, True),
          "LAX": ("KLAX", "KXHIGHLAX", -8, True)}
D0, D1 = Date(2026, 6, 15), Date(2026, 7, 18)
DAYS = (D1 - D0).days + 1
CFG = {"min_bid_cents": 15, "max_spread_cents": 5, "max_size_contracts": 300,
       "fat_finger_guard_f": 7, "channels": ["dsm", "metar", "sixhr", "omo_floor"]}
MAXSZ, FLOORFILL, PART = 300, 25, 0.5

def fetch(url, timeout=60, tries=4):
    for k in range(tries):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": "weatherbot-oos"})
            return urllib.request.urlopen(r, timeout=timeout).read()
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(5 * (k + 1))

def jget(url):
    return json.loads(fetch(url, 30))

def pdt(s):
    dt = datetime.fromisoformat(s.replace("Z", "+00:00").replace(" ", "T"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def daterange():
    d = D0
    while d <= D1:
        yield d; d += timedelta(days=1)

# ---------- phase 1: weather (skip-if-exists) ----------
def ensure_weather():
    for st, (icao, _, _, omo_cov) in CITIES.items():
        mp = f"{WX}/metar_{st}.csv"
        if not os.path.exists(mp) or os.path.getsize(mp) < 1000:
            u = (f"https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station={st}"
                 f"&data=tmpf&data=metar&year1=2026&month1=6&day1=15&year2=2026&month2=7&day2=19"
                 f"&tz=Etc/UTC&format=onlycomma&latlon=no&elev=no&missing=M&trace=T&direct=no"
                 f"&report_type=3&report_type=4")
            open(mp, "wb").write(fetch(u, 90)); time.sleep(2.5)
            print(f"  metar {st}: {sum(1 for _ in open(mp))} rows")
        dp = f"{WX}/dsm_{st}.txt"
        if not os.path.exists(dp) or os.path.getsize(dp) < 200:
            u = (f"https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?pil=DSM{st if st!='MDW' else 'MDW'}"
                 f"&fmt=text&limit=9999&sdate=2026-06-15T00:00&edate=2026-07-19T12:00")
            open(dp, "wb").write(fetch(u, 90)); time.sleep(2.5)
            print(f"  dsm {st}: {os.path.getsize(dp)} bytes")
        if omo_cov:
            op = f"{WX}/onemin_{st}.csv"
            if not os.path.exists(op) or os.path.getsize(op) < 1000:
                with open(op, "w") as out:
                    hdr = False
                    for (a, b) in [("2026-06-15T00:00Z", "2026-06-25T00:00Z"),
                                   ("2026-06-25T00:00Z", "2026-07-05T00:00Z"),
                                   ("2026-07-05T00:00Z", "2026-07-15T00:00Z"),
                                   ("2026-07-15T00:00Z", "2026-07-19T12:00Z")]:
                        u = (f"https://mesonet.agron.iastate.edu/cgi-bin/request/asos1min.py?station={st}"
                             f"&vars=tmpf&sts={a}&ets={b}&sample=1min&what=download&tz=UTC&delim=comma")
                        txt = fetch(u, 120).decode(errors="replace")
                        for i, ln in enumerate(txt.splitlines()):
                            if i == 0 and hdr: continue
                            out.write(ln + "\n")
                        hdr = True; time.sleep(3)
                print(f"  onemin {st}: {sum(1 for _ in open(op))} rows")

# ---------- phase 2: manifests ----------
MAN = f"{KD}/manifest.csv"
def ensure_manifest():
    if os.path.exists(MAN) and os.path.getsize(MAN) > 1000:
        return
    rows = []
    for st, (_, series, _, _) in CITIES.items():
        cur = ""
        while True:
            u = f"{B}/markets?series_ticker={series}&status=settled&limit=100" + (f"&cursor={cur}" if cur else "")
            d = jget(u); time.sleep(0.25)
            for m in d.get("markets", []):
                tag = m["event_ticker"].split("-")[1]
                try:
                    ed = datetime.strptime(tag, "%y%b%d").date()
                except ValueError:
                    continue
                if D0 <= ed <= D1:
                    rows.append({"city": st, "series": series, "event_date": ed.isoformat(),
                                 "ticker": m["ticker"], "floor": m.get("floor_strike", ""),
                                 "cap": m.get("cap_strike", ""),
                                 "subtitle": m.get("yes_sub_title") or "",
                                 "settle": m.get("expiration_value", "")})
            cur = d.get("cursor", "")
            if not cur: break
        print(f"  manifest {series}: running total {len(rows)}")
    with open(MAN, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

# ---------- candles (lazy, cached) ----------
_c = {}
def candles(tick, ed):
    if tick in _c: return _c[tick]
    path = f"{KD}/candles/{tick}.csv"
    if not os.path.exists(path):
        d0 = datetime.fromisoformat(ed).replace(tzinfo=timezone.utc)
        t0, t1 = int(d0.replace(hour=10).timestamp()), int((d0 + timedelta(hours=29)).timestamp())
        series = tick.split("-")[0]
        try:
            d = jget(f"{B}/series/{series}/markets/{tick}/candlesticks?start_ts={t0}&end_ts={t1}&period_interval=1")
        except Exception:
            _c[tick] = []; return []
        time.sleep(0.22)
        with open(path, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["ts", "bid", "ask", "vol"])
            for c in d.get("candlesticks", []):
                def cv(o, k):
                    if not o: return ""
                    v = o.get(k)
                    if v is not None: return int(v)
                    v = o.get(k + "_dollars")
                    return round(float(v) * 100) if v else ""
                w.writerow([datetime.fromtimestamp(c["end_period_ts"], tz=timezone.utc).isoformat(),
                            cv(c.get("yes_bid"), "close"), cv(c.get("yes_ask"), "close"),
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

# ---------- proofs ----------
TG = re.compile(r'\bT([01])(\d{3})[01]\d{3}\b')
SIX = re.compile(r'\b1([01])(\d{3})\b')
def proofs_for(st, icao, lst, omo_cov):
    out = []
    with open(f"{WX}/metar_{st}.csv") as f:
        for r in csv.DictReader(f):
            try: ts = pdt(r["valid"])
            except Exception: continue
            raw = r.get("metar", "")
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
    for ln in open(f"{WX}/dsm_{st}.txt"):
        m = DSBODY.match(ln.strip())
        if not m or m.group(1) != icao or not m.group(2): continue
        tok = m.group(5).split("/")[0].strip()
        mt = MAXTOK.match(tok)
        if not mt: continue
        try: cd = Date(2026, int(m.group(4)), int(m.group(3)))
        except ValueError: continue
        asof = m.group(2)
        avail = (datetime(cd.year, cd.month, cd.day, int(asof[:2]) % 24, int(asof[2:]) % 60,
                          tzinfo=timezone.utc) - timedelta(hours=lst) + timedelta(minutes=17))
        out.append(ProofEvent(icao, cd, int(mt.group(1)), "dsm", None, avail, f"DS {asof}"))
    if omo_cov and os.path.exists(f"{WX}/onemin_{st}.csv"):
        sm = Smoother()
        for r in csv.reader(open(f"{WX}/onemin_{st}.csv")):
            if len(r) < 4 or r[0] == "station": continue
            try:
                ts = pdt(r[2]); v = float(r[3])
            except Exception: continue
            s = sm.push(ts.replace(tzinfo=None), v)
            if s is None or ts.minute % 5: continue
            out.append(ProofEvent(icao, (ts + timedelta(hours=lst)).date(),
                                  wholeC_floor(f_to_wholeC(s)), "omo_floor", ts, ts + timedelta(minutes=3)))
    out.sort(key=lambda e: e.seen_ts)
    return out

def main():
    print("phase 1: weather"); ensure_weather()
    print("phase 2: manifests"); ensure_manifest()
    boards = defaultdict(list); settles = {}
    with open(MAN) as f:
        for r in csv.DictReader(f):
            fl = int(float(r["floor"])) if r["floor"] not in ("", "None") else None
            cp = int(float(r["cap"])) if r["cap"] not in ("", "None") else None
            kind = "bin" if fl is not None and cp is not None else ("top" if fl is not None else "bot")
            boards[(r["city"], r["event_date"])].append(Bucket(r["ticker"], fl, cp, kind, r["subtitle"]))
            if r["settle"]: settles[(r["city"], r["event_date"])] = int(round(float(r["settle"])))
    print("phase 3: replay")
    trades = []; raw = 0; qc_bad = 0
    for st, (icao, series, lst, omo_cov) in CITIES.items():
        allp = proofs_for(st, icao, lst, omo_cov)
        byd = defaultdict(list)
        for e in allp: byd[e.climate_date].append(e)
        for d in daterange():
            key = (st, d.isoformat())
            if key not in boards: continue
            eng = KillEngine(CFG); cs = CityState(icao, series)
            seen_kills = set()
            for ev in byd.get(d, []):
                for b in boards[key]:
                    kl = b.kill_level
                    if kl is not None and kl <= ev.level_f and (b.ticker, kl) not in seen_kills \
                       and ev.level_f > cs.proven_max.get(d, -999):
                        seen_kills.add((b.ticker, kl))
                for it in eng.on_proof(cs, ev, boards[key], lambda tk: quote_at(tk, d.isoformat(), ev.seen_ts)):
                    bid, ask = quote_at(it.ticker, d.isoformat(), ev.seen_ts)
                    v5 = vol_win(it.ticker, d.isoformat(), ev.seen_ts)
                    size = min(MAXSZ, max(FLOORFILL, PART * v5))
                    px = bid - 1
                    fee = taker_fee_dollars(px, size)
                    trades.append({"city": st, "date": d.isoformat(), "ticker": it.ticker,
                                   "channel": ev.channel, "avail": ev.seen_ts.isoformat(),
                                   "bid": bid, "px": px, "size": round(size),
                                   "net": round(px / 100 * size - fee, 2)})
            raw += len(seen_kills)
            sv = settles.get(key)
            if sv is not None and cs.proven_max.get(d, -999) > sv:
                qc_bad += 1
    with open(f"{KD}/sim_trades_oos.csv", "w", newline="") as f:
        if trades:
            w = csv.DictWriter(f, fieldnames=list(trades[0].keys())); w.writeheader(); w.writerows(trades)
    daily = defaultdict(float)
    for t in trades: daily[t["date"]] += t["net"]
    allday = [daily.get(d.isoformat(), 0.0) for d in daterange()]
    tot = sum(t["net"] for t in trades)
    print("=" * 74)
    print(f"OUT-OF-SAMPLE: Jun 15 – Jul 18 ({DAYS} days) | QC violations: {qc_bad}")
    print(f"raw kills: {raw} ({raw/DAYS:.1f}/d) | TRADEABLE: {len(trades)} ({len(trades)/DAYS:.2f}/d)")
    print(f"net ${tot:,.2f} | mean/day ${tot/DAYS:.2f} | zero days {sum(1 for x in allday if x==0)}/{DAYS} | best ${max(allday):.2f}")
    bc = defaultdict(lambda: [0, 0.0]); ch = defaultdict(lambda: [0, 0.0])
    for t in trades:
        bc[t["city"]][0] += 1; bc[t["city"]][1] += t["net"]
        ch[t["channel"]][0] += 1; ch[t["channel"]][1] += t["net"]
    print("by city: " + " | ".join(f"{c}:{bc[c][0]}tr ${bc[c][1]:,.0f}" for c in CITIES))
    print("by channel: " + " | ".join(f"{k}:{v[0]}tr ${v[1]:,.0f}" for k, v in sorted(ch.items(), key=lambda x: -x[1][1])))
    if trades:
        fat = [t for t in trades if t["px"] >= 50]
        print(f"fat (>=50c): {len(fat)} | avg px {statistics.mean(t['px'] for t in trades):.0f}c | avg net/trade ${statistics.mean(t['net'] for t in trades):.2f}")
        print("TOP 8:")
        for t in sorted(trades, key=lambda x: -x["net"])[:8]:
            print(f"  {t['date']} {t['ticker']:27s} {t['channel']:9s} bid={t['bid']:3d} size={t['size']:4d} net=${t['net']:7.2f} @{t['avail'][11:16]}Z")

if __name__ == "__main__":
    main()
