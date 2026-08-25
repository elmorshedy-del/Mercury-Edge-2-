"""depth_collector.py — snapshot live orderbooks at the race minutes daily.
Capacity data can't be backfilled; this accrues it. Run alongside run.py:

  python3 depth_collector.py --once        # snapshot now
  cron:  12,14,16 20,21,22,23 * * *  cd /path/weatherbot && python3 depth_collector.py --once
         50,53,56 * * * *             cd /path/weatherbot && python3 depth_collector.py --once

Appends JSONL rows to depth_log.jsonl: ts, ticker, yes-bid ladder (top 8), best ask."""
from __future__ import annotations
import json, time, argparse, os
from datetime import datetime, timedelta, timezone
from market import board, orderbook_yes_bids, _get, BASE

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json")))
LOG = os.path.join(HERE, "depth_log.jsonl")

def snapshot():
    now = datetime.now(timezone.utc)
    rows = 0
    for key, c in CFG["cities"].items():
        d = (now + timedelta(hours=c["lst_offset_h"])).date()
        for b in board(c["series"], d):
            bids = orderbook_yes_bids(b.ticker)[:8]
            ask = None
            try:
                m = _get(f"{BASE}/markets/{b.ticker}").get("market", {})
                v = m.get("yes_ask") or m.get("yes_ask_dollars")
                ask = int(v) if isinstance(v, int) else (round(float(v) * 100) if v else None)
            except Exception:
                pass
            with open(LOG, "a") as f:
                f.write(json.dumps({"ts": now.isoformat(), "ticker": b.ticker,
                                    "yes_bids": bids, "best_ask": ask}) + "\n")
            rows += 1
            time.sleep(0.15)
    print(f"{now.isoformat()} snapshot: {rows} books")

if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--once",action="store_true"); p.parse_args()
    snapshot()
