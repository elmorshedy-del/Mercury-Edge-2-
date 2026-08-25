"""census.py — daily universe census: alert the moment Kalshi lists its first
market in a pre-registered weather series (lows, Houston, new cities).
Week-one books in a new market class are the softest they will ever be.

  cron:  0 13 * * *  cd /path/weatherbot && python3 census.py
Exit code 2 + CENSUS ALERT line when something new is live (grep-able / hookable)."""
from __future__ import annotations
import json, sys, time, urllib.request

B = "https://api.elections.kalshi.com/trade-api/v2"
WATCH = ["KXLOWNY", "KXLOWCHI", "KXLOWAUS", "KXLOWDEN", "KXLOWLAX", "KXLOWMIA",
         "KXLOWPHIL", "KXHIGHOU", "KXHIGHHOU", "KXHIGHSEA", "KXHIGHPHX",
         "KXHIGHLV", "KXHIGHSF", "KXHIGHATL", "KXHIGHDC", "KXHIGHBOS", "KXHIGHDFW"]

def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "weatherbot-census"})
    return json.loads(urllib.request.urlopen(r, timeout=20).read())

alerts = []
for s in WATCH:
    try:
        ms = get(f"{B}/markets?series_ticker={s}&limit=3").get("markets", [])
        if ms:
            alerts.append((s, ms[0].get("event_ticker"), ms[0].get("status")))
    except Exception:
        pass
    time.sleep(0.3)

if alerts:
    for s, ev, st in alerts:
        print(f"CENSUS ALERT: {s} has live markets! first event {ev} status={st}")
    sys.exit(2)
print("census: nothing new (all watched series still empty)")
