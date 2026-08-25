"""strategy.py — the V1 kill engine.

ONE trade: when a proof channel establishes 'daily max >= L' for a station,
every bucket with kill_level <= L is factually dead. If its bid is still fat,
sell YES into the resting bids (equivalently buy NO).

Retrospective-only by construction: we act on facts about the past, never on
trajectory opinions. Top tails are never traded (that's a winner-pick, V2)."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime, date as Date, timezone
from feeds import ProofEvent
from market import Bucket, taker_fee_dollars

log = logging.getLogger("strategy")

@dataclass
class Intent:
    ts: datetime
    ticker: str
    action: str           # 'SELL_YES'
    reason: str
    proof: ProofEvent
    min_px: int           # don't fill below this
    max_size: float

@dataclass
class CityState:
    icao: str
    series: str
    proven_max: dict = field(default_factory=dict)   # climate_date -> int
    metar_max: dict = field(default_factory=dict)    # climate_date -> int (visible reference)
    fired: set = field(default_factory=set)          # (ticker, kill_level)

class KillEngine:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.min_bid = cfg.get("min_bid_cents", 15)
        self.max_spread = cfg.get("max_spread_cents", 5)
        self.max_size = cfg.get("max_size_contracts", 300)
        self.fat_finger_f = cfg.get("fat_finger_guard_f", 12)
        self.channels = set(cfg.get("channels", ["dsm", "metar", "sixhr", "omo_floor"]))

    def on_proof(self, st: CityState, ev: ProofEvent,
                 buckets: list[Bucket],
                 quote_fn) -> list[Intent]:
        """quote_fn(ticker) -> (bid, ask) cents."""
        if ev.channel not in self.channels:
            return []
        # keep the METAR-visible reference current (it flows through as proofs)
        if ev.channel in ("metar", "sixhr"):
            if ev.level_f > st.metar_max.get(ev.climate_date, -999):
                st.metar_max[ev.climate_date] = ev.level_f
        cur = st.proven_max.get(ev.climate_date, -999)
        if ev.level_f <= cur:
            return []
        # Physical-plausibility guard: a DSM/OMO claim can never exceed the day's
        # METAR-visible max by more than the invisible-gap bound (measured <=4F;
        # we allow fat_finger_guard_f). Big diurnal jumps vs a stale morning max
        # are NORMAL (Denver +21F) — so we guard against the live reference, not
        # against the previous proof.
        ref = st.metar_max.get(ev.climate_date)
        if (ev.channel in ("dsm", "omo_floor") and ref is not None
                and ev.level_f > ref + self.fat_finger_f):
            log.error("GUARD: %s %s claims %sF via %s but METAR-visible max is %sF "
                      "(+%d limit) — held for confirmation",
                      ev.station, ev.climate_date, ev.level_f, ev.channel, ref,
                      self.fat_finger_f)
            return []
        st.proven_max[ev.climate_date] = ev.level_f
        intents = []
        for b in buckets:
            kl = b.kill_level
            if kl is None or kl > ev.level_f:
                continue
            key = (b.ticker, kl)
            if key in st.fired:
                continue
            bid, ask = quote_fn(b.ticker)
            if bid is None or bid < self.min_bid:
                st.fired.add(key)          # dead-or-thin: don't revisit
                continue
            if ask is not None and (ask - bid) > self.max_spread:
                log.warning("spread filter: %s bid=%s ask=%s — skip", b.ticker, bid, ask)
                st.fired.add(key)
                continue
            st.fired.add(key)
            intents.append(Intent(
                ts=datetime.now(timezone.utc), ticker=b.ticker, action="SELL_YES",
                reason=f"proof {ev.channel}: max>={ev.level_f}F kills [{b.subtitle}] "
                       f"(kill_level {kl}); bid {bid}c",
                proof=ev, min_px=max(self.min_bid, bid - 8), max_size=self.max_size))
            log.info("INTENT %s %s | %s", b.ticker, f"bid={bid}", intents[-1].reason)
        return intents

def expected_pnl(avg_px_cents: float, contracts: float, fee_rate=0.07) -> dict:
    """Kill trade economics: sell YES at avg_px, bucket settles 0."""
    gross = avg_px_cents / 100.0 * contracts
    fee = taker_fee_dollars(int(round(avg_px_cents)), contracts, fee_rate)
    max_loss = (100 - avg_px_cents) / 100.0 * contracts   # only if proof was wrong
    return {"gross_usd": round(gross, 2), "fee_usd": fee,
            "net_usd": round(gross - fee, 2), "max_loss_usd": round(max_loss, 2)}
