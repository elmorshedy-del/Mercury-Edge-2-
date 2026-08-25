# Mercury Edge 2

**The dead-bucket kill engine + live console for Kalshi daily-temperature markets.**

One trade, executed well: when a fact about the past proves a bucket dead
(report-latency race or hidden-data floor), sell it before the crowd finishes
reading. Retrospective moments only — no winner-picking, no forecasting.
Backtested over 64 station-days (replay-verified, red-teamed, out-of-sample
confirmed): ~0.33–0.55 tradeable signals/day, ~$58–79/day at current depth.

## What runs here (one Railway service, three workers + dashboard)

```
app/server.py          FastAPI: dashboard + JSON APIs + background threads
 ├─ bot worker         engine/runtime.py — poll windows (DSM :15s, METAR :51-:56,
 │                     OMO 60s) → ProofEvents → KillEngine → paper fills → ledger
 ├─ depth collector    orderbook snapshots at race minutes → data/depth_log.jsonl
 └─ census worker      watches 17 pre-registered Kalshi weather series for launch day
engine/                decode (settlement-exact), feeds (DSM/METAR/6hr/OMO),
                       strategy (kill engine + guards), market, paper, exec_live,
                       nwws_adapter (push feed, pending NWWS-OI credentials)
app/static/index.html  the console: P&L, trades, city boards, proof feed, countdowns
research/              backtest + replay suite (paths reference the research sandbox)
docs/                  NWWS-OI application draft + engine docs
```

## Deploy on Railway

1. Connect this repo to a new Railway service (Nixpacks auto-detects Python;
   `railway.json` supplies the start command + healthcheck `/health`).
2. **Attach a volume** mounted at `/data` and set `WEATHERBOT_DATA_DIR=/data`
   — otherwise the ledger/journal reset on every redeploy.
3. Optional env:
   | var | purpose |
   |---|---|
   | `WEATHERBOT_DATA_DIR` | persistence dir (set to the volume mount) |
   | `KALSHI_KEY_ID`, `KALSHI_PRIVATE_KEY` | live trading creds (leave unset for paper) |
   | `WEATHERBOT_LIVE=yes` | arms real orders — only after the paper gate passes |
   | `NWWS_USER`, `NWWS_PASS` | NWWS-OI push feed (see docs/NWWS_APPLICATION.md) |

Paper mode is the default and is hard-enforced: without the three live vars the
executor logs intents and never places orders.

## Local dev

```
pip install -r requirements.txt
uvicorn app.server:app --reload --port 8000     # dashboard at localhost:8000
python3 research/replay_test.py                 # engine test suite (needs research data)
```

## The go-live gate

2–4 weeks of paper: intents inside the first minute of reveals, sim fills within
~2¢ of tape, zero unexplained guard events → arm live with flat stakes
≤0.25–0.5% of bankroll per event. The dashboard's trades table + event feed are
the evidence log.
