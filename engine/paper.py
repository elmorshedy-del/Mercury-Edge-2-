"""paper.py — paper-execution: snapshot the live book at intent time, simulate
the fill against displayed depth, persist everything for later settlement P&L."""
from __future__ import annotations
import json, logging, os
from datetime import datetime, timezone
from market import sellable, taker_fee_dollars
from strategy import Intent

log = logging.getLogger("paper")
LEDGER = os.path.join(os.environ.get("WEATHERBOT_DATA_DIR", os.path.dirname(__file__)), "paper_ledger.jsonl")

def execute(intent: Intent, fee_rate=0.07) -> dict:
    take, avg_px, best = sellable(intent.ticker, intent.min_px, intent.max_size)
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "ticker": intent.ticker,
        "action": intent.action,
        "reason": intent.reason,
        "proof_channel": intent.proof.channel,
        "proof_level_f": intent.proof.level_f,
        "proof_obs_ts": intent.proof.obs_ts.isoformat() if intent.proof.obs_ts else None,
        "proof_seen_ts": intent.proof.seen_ts.isoformat(),
        "best_bid_at_intent": best,
        "sim_fill_contracts": round(take, 2),
        "sim_avg_px_cents": round(avg_px, 2),
        "sim_gross_usd": round(take * avg_px / 100.0, 2),
        "sim_fee_usd": taker_fee_dollars(int(round(avg_px)) if take else 0, take, fee_rate),
        "mode": "PAPER",
    }
    with open(LEDGER, "a") as f:
        f.write(json.dumps(rec) + "\n")
    log.info("PAPER FILL %s: %.0f @ %.1fc (best %s) gross $%.2f",
             intent.ticker, take, avg_px, best, rec["sim_gross_usd"])
    return rec
