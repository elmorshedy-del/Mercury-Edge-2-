"""replay_test.py — proves the engine on the ACTUAL flagship events using the
archived wire products and the historical order flow. Run: python3 replay_test.py"""
from __future__ import annotations
import csv, os, re, sys
from datetime import datetime, timezone, date as Date
from decode import _selftest
from feeds import DSBODY, MAXTOK, ProofEvent
from market import Bucket
from strategy import KillEngine, CityState, expected_pnl

BT = "/agent/workspace/backtest"
CFG = {"min_bid_cents": 15, "max_spread_cents": 5, "max_size_contracts": 300,
       "fat_finger_guard_f": 12, "channels": ["dsm", "metar", "sixhr", "omo_floor"]}

def parse_dsm_line(line: str, icao: str, year=2026):
    m = DSBODY.match(line.strip())
    if not m or m.group(1) != icao:
        return None
    tok = m.group(5).split("/")[0].strip()
    mt = MAXTOK.match(tok)
    if not mt:
        return None
    return {"max_f": int(mt.group(1)), "hhmm": mt.group(2),
            "date": Date(year, int(m.group(4)), int(m.group(3))), "asof": m.group(2)}

def board_from_manifest(event_ticker: str) -> list[Bucket]:
    out = []
    with open(f"{BT}/kalshi/manifest.csv") as f:
        for r in csv.DictReader(f):
            if r["event_ticker"] != event_ticker:
                continue
            fl = int(float(r["floor_strike"])) if r["floor_strike"] else None
            cp = int(float(r["cap_strike"])) if r["cap_strike"] else None
            kind = "bin" if fl is not None and cp is not None else ("top" if fl is not None else "bot")
            out.append(Bucket(r["ticker"], fl, cp, kind, r["subtitle"]))
    return out

def hist_quote(ticker: str, at_iso: str):
    """bid/ask from archived minute candles at a UTC time."""
    t = datetime.fromisoformat(at_iso).replace(tzinfo=timezone.utc)
    bid = ask = None
    try:
        with open(f"{BT}/kalshi/candles/{ticker}.csv") as f:
            for r in csv.DictReader(f):
                ts = datetime.fromisoformat(r["ts_utc"].replace("Z", "+00:00"))
                if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
                if ts <= t:
                    if r["yes_bid_close"] != "": bid = int(r["yes_bid_close"])
                    if r["yes_ask_close"] != "": ask = int(r["yes_ask_close"])
                else:
                    break
    except FileNotFoundError:
        pass
    return bid, ask

def replay(name, icao, series_event, dsm_txt, dsm_date_frag, at_iso, expect_kill_tickers):
    """Feed ALL of the day's intraday DSM products chronologically (as live would
    see them) and let the engine's monotone proven-max ratchet do its thing."""
    print(f"\n=== REPLAY: {name} ===")
    prods = []
    for ln in open(f"{BT}/wx/{dsm_txt}"):
        p = parse_dsm_line(ln, icao)
        if p and p["date"].strftime("%d/%m") == dsm_date_frag and p["asof"]:
            prods.append((ln.strip(), p))
    assert prods, "no archived DSM products found for that date"
    prods.sort(key=lambda x: x[1]["asof"])          # chronological by as-of HHMM
    eng = KillEngine(CFG)
    st = CityState(icao, series_event.split("-")[0])
    buckets = board_from_manifest(series_event)
    got = {}
    for raw, p in prods:
        ev = ProofEvent(icao, p["date"], p["max_f"], "dsm",
                        None, datetime.now(timezone.utc), raw[:40])
        for i in eng.on_proof(st, ev, buckets, lambda tk: hist_quote(tk, at_iso)):
            got[i.ticker] = (p, i)
    print(f"fed {len(prods)} products; proven-max ratchet ended at "
          f"{st.proven_max.get(list(st.proven_max)[0]) if st.proven_max else '?'}F")
    for tk, (p, i) in got.items():
        bid, ask = hist_quote(tk, at_iso)
        econ = expected_pnl(bid, 150)
        print(f"  FIRED {tk} on 'DS {p['asof']}' (max {p['max_f']}F)  bid={bid} ask={ask}  "
              f"150-lot: net ${econ['net_usd']} (max loss ${econ['max_loss_usd']})")
    missing = set(expect_kill_tickers) - set(got)
    assert not missing, f"engine failed to fire on {missing}"
    print(f"  OK — fired on all expected: {sorted(expect_kill_tickers)}")

def unit_guards():
    print("\n=== UNIT: engine guards ===")
    eng = KillEngine(CFG)
    st = CityState("KTST", "KXTEST")
    b = [Bucket("KXTEST-B81.5", 81, 82, "bin", "81 to 82"),
         Bucket("KXTEST-T90", 90, None, "top", "91 or above")]
    q_ok = lambda tk: (60, 62)
    ev = lambda lvl: ProofEvent("KTST", Date(2026, 8, 24), lvl, "dsm", None,
                                datetime.now(timezone.utc))
    # fires once, then dedupes after a real intent was emitted
    assert len(eng.on_proof(st, ev(83), b, q_ok)) == 1
    assert len(eng.on_proof(st, ev(84), b, q_ok)) == 0, "dedupe failed"
    # never touches top tails
    st2 = CityState("KTST", "KXTEST")
    assert all("T90" not in i.ticker for i in eng.on_proof(st2, ev(95), b, q_ok))

    # Regression: a dead bucket with a temporarily thin bid must NOT be marked
    # fired. The same proven kill must be re-evaluated later and a wide spread
    # must not block taking a stale resting YES bid.
    st3 = CityState("KTST", "KXTEST")
    assert len(eng.on_proof(st3, ev(83), b, lambda tk: (10, 64))) == 0
    assert ("KXTEST-B81.5", 83) not in st3.fired, "thin quote was incorrectly made terminal"
    retry = eng.on_proof(st3, ev(83), b, lambda tk: (34, 64))
    assert len(retry) == 1, "same-level kill was not retried / wide spread incorrectly blocked"
    assert retry[0].ticker == "KXTEST-B81.5"
    assert len(eng.on_proof(st3, ev(83), b, lambda tk: (34, 64))) == 0, "post-intent dedupe failed"

    # plausibility guard: DSM claiming far above the METAR-visible max is held,
    # but a big diurnal jump with a consistent METAR reference passes (Denver case)
    st4 = CityState("KTST", "KXTEST")
    mev = ProofEvent("KTST", Date(2026, 8, 24), 80, "metar", None,
                     datetime.now(timezone.utc))
    eng.on_proof(st4, mev, b, lambda tk: (None, None))       # visible ref = 80
    dsm_wild = ProofEvent("KTST", Date(2026, 8, 24), 101, "dsm", None,
                          datetime.now(timezone.utc))
    assert len(eng.on_proof(st4, dsm_wild, b, q_ok)) == 0, "plausibility guard failed"
    st5 = CityState("KTST", "KXTEST")
    b5 = [Bucket("KXTEST-B95.5", 95, 96, "bin", "95 to 96")]   # dies only at 97
    mev2 = ProofEvent("KTST", Date(2026, 8, 24), 96, "metar", None,
                      datetime.now(timezone.utc))
    eng.on_proof(st5, mev2, b5, lambda tk: (None, None))     # visible ref = 96, no kill
    dsm_ok = ProofEvent("KTST", Date(2026, 8, 24), 97, "dsm", None,
                        datetime.now(timezone.utc))
    assert len(eng.on_proof(st5, dsm_ok, b5, q_ok)) == 1, "legit DSM blocked"
    print("  OK — dedupe, top-tail exclusion, retryable thin books, wide-spread stale bids, plausibility guard")

if __name__ == "__main__":
    print(_selftest())
    unit_guards()
    # Flagship: NYC Jul 24 — DSM 20:15Z proved 83F; B81.5 (81-82) was bid 92
    replay("NYC Jul 24 (the 93.5c event)", "KNYC", "KXHIGHNY-26JUL24",
           "dsm_NYC.txt", "24/07", "2026-07-24T20:17:00",
           {"KXHIGHNY-26JUL24-B81.5"})
    # DEN Aug 11 — DSM 22:15Z proved 97F; B95.5 was bid 82
    replay("DEN Aug 11", "KDEN", "KXHIGHDEN-26AUG11",
           "dsm_DEN.txt", "11/08", "2026-08-11T22:17:00",
           {"KXHIGHDEN-26AUG11-B95.5"})
    print("\nALL REPLAYS PASSED")
