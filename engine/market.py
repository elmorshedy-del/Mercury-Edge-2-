"""market.py — Kalshi public market data: boards, orderbooks, fees.
Trading (authenticated) lives in exec_live.py; everything here is public."""
from __future__ import annotations
import json, math, logging, urllib.request
from dataclasses import dataclass
from datetime import date as Date

log = logging.getLogger("market")
BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "weatherbot-v1"}

def _get(url: str, timeout=10):
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=timeout).read())

def _cents(m: dict, key: str) -> int | None:
    v = m.get(key)
    if v is not None:
        return int(v)
    v = m.get(key + "_dollars")
    return round(float(v) * 100) if v not in (None, "") else None

@dataclass
class Bucket:
    ticker: str
    floor: int | None      # yes iff max > floor        (top tail)
    cap: int | None        # yes iff max < cap          (bottom tail)
    kind: str              # 'bin' | 'top' | 'bot'
    subtitle: str
    @property
    def kill_level(self) -> int | None:
        """Running max >= kill_level makes YES mathematically impossible."""
        if self.kind == "bin":
            return self.cap + 1
        if self.kind == "bot":
            return self.cap
        return None            # top tails are never killed by a max increase

def event_ticker(series: str, d: Date) -> str:
    return f"{series}-{d.strftime('%y%b%d').upper()}"

def board(series: str, d: Date) -> list[Bucket]:
    et = event_ticker(series, d)
    out, cur = [], ""
    while True:
        u = f"{BASE}/markets?event_ticker={et}&limit=100" + (f"&cursor={cur}" if cur else "")
        try:
            resp = _get(u)
        except Exception as e:
            log.error("board fetch %s: %s", et, e); return out
        for m in resp.get("markets", []):
            fl = m.get("floor_strike"); cp = m.get("cap_strike")
            fl = int(fl) if fl is not None else None
            cp = int(cp) if cp is not None else None
            kind = "bin" if (fl is not None and cp is not None) else ("top" if fl is not None else "bot")
            out.append(Bucket(m["ticker"], fl, cp, kind,
                              m.get("yes_sub_title") or m.get("subtitle") or ""))
        cur = resp.get("cursor", "")
        if not cur:
            break
    return out

def quote(ticker: str) -> tuple[int | None, int | None]:
    """(yes_bid, yes_ask) in cents from the market object."""
    try:
        m = _get(f"{BASE}/markets/{ticker}").get("market", {})
    except Exception as e:
        log.warning("quote %s: %s", ticker, e); return None, None
    return _cents(m, "yes_bid"), _cents(m, "yes_ask")

def orderbook_yes_bids(ticker: str) -> list[tuple[int, float]]:
    """Resting YES bids [(price_cents, qty), ...] best-first.
    These are what a kill order (sell YES / buy NO) consumes."""
    try:
        ob = _get(f"{BASE}/markets/{ticker}/orderbook")
    except Exception as e:
        log.warning("orderbook %s: %s", ticker, e); return []
    body = ob.get("orderbook_fp") or ob.get("orderbook") or {}
    lv = body.get("yes_dollars") or body.get("yes") or []
    out = []
    for px, qty in lv:
        p = round(float(px) * 100) if isinstance(px, str) else int(px)
        out.append((p, float(qty)))
    out.sort(key=lambda x: -x[0])
    return out

def taker_fee_dollars(price_cents: int, contracts: float, rate: float = 0.07) -> float:
    """Kalshi taker fee: ceil_to_cent(rate * C * P * (1-P))."""
    p = price_cents / 100.0
    return math.ceil(rate * contracts * p * (1 - p) * 100) / 100.0

def sellable(ticker: str, min_px: int, max_size: float) -> tuple[float, float, int]:
    """Given the live book: (contracts fillable at >= min_px, avg price, best_bid)."""
    bids = orderbook_yes_bids(ticker)
    if not bids:
        return 0.0, 0.0, 0
    best = bids[0][0]
    take, notion = 0.0, 0.0
    for px, qty in bids:
        if px < min_px or take >= max_size:
            break
        q = min(qty, max_size - take)
        take += q; notion += q * px
    return take, (notion / take if take else 0.0), best
