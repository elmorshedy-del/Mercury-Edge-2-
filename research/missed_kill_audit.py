"""Read-only counterfactual audit for the pre-fix kill-entry bug.

Replays persisted proof events against the nearest *preceding* saved order-book
snapshot. This is intentionally conservative about evidence: it never uses a
post-proof snapshot to manufacture a fill. Exact `spread filter:` journal rows
are used for the contemporaneous best bid when available; saved depth supplies
quantity/average fill. Results are therefore a race-snapshot replay, not a
claim of tick-perfect historical execution.
"""
from __future__ import annotations

import json, math, os, re
from collections import defaultdict
from datetime import datetime, timezone

SPREAD_RE = re.compile(r"spread filter:\s+(\S+)\s+bid=(\d+)\s+ask=(\d+)")
B_RE = re.compile(r"-B(\d+)\.5$")
T_RE = re.compile(r"-T(\d+)$")


def _dt(s: str) -> datetime:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for ln in f:
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
    return out


def _event_prefix(series: str, climate_date: str) -> str:
    d = datetime.strptime(climate_date, "%Y-%m-%d")
    return f"{series}-{d.strftime('%y%b%d').upper()}"


def _infer_kills(tickers: set[str]) -> dict[str, int | None]:
    """Infer daily-high bucket kill levels from ticker strikes.

    B79.5 is 79-80 and dies at 81. Of the two T strikes on a board, the lower
    strike is the bottom tail and dies at its strike; the upper T is the top
    tail and is not killed by a rising daily maximum.
    """
    out: dict[str, int | None] = {}
    by_event: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for tk in tickers:
        m = B_RE.search(tk)
        if m:
            out[tk] = int(m.group(1)) + 2
            continue
        m = T_RE.search(tk)
        if m:
            by_event[tk.rsplit("-", 1)[0]].append((tk, int(m.group(1))))
    for rows in by_event.values():
        rows.sort(key=lambda x: x[1])
        if rows:
            out[rows[0][0]] = rows[0][1]
        for tk, _ in rows[1:]:
            out[tk] = None
    return out


def _fee(avg_px_cents: float, contracts: float, rate: float) -> float:
    if contracts <= 0:
        return 0.0
    p = round(avg_px_cents) / 100.0
    return math.ceil(rate * contracts * p * (1 - p) * 100) / 100.0


def _fill(levels: list, min_px: int, max_size: float) -> tuple[float, float]:
    take = notion = 0.0
    clean = []
    for row in levels or []:
        try:
            clean.append((int(row[0]), float(row[1])))
        except Exception:
            pass
    clean.sort(key=lambda x: -x[0])
    for px, qty in clean:
        if px < min_px or take >= max_size:
            break
        q = min(qty, max_size - take)
        take += q
        notion += q * px
    return take, (notion / take if take else 0.0)


def audit(data_dir: str, cfg: dict,
          start_iso: str = "2026-08-25T12:46:00+00:00",
          end_iso: str = "2026-08-29T19:37:00+00:00",
          max_snapshot_age_s: int = 240) -> dict:
    events = _jsonl(os.path.join(data_dir, "events.jsonl"))
    depth = _jsonl(os.path.join(data_dir, "depth_log.jsonl"))
    start, end = _dt(start_iso), _dt(end_iso)

    events = [e for e in events if e.get("ts") and start <= _dt(e["ts"]) < end]
    depth = [r for r in depth if r.get("ts") and start <= _dt(r["ts"]) < end]

    # Saved depth per ticker, sorted for predecessor lookup.
    dby: dict[str, list[dict]] = defaultdict(list)
    tickers: set[str] = set()
    for r in depth:
        tk = r.get("ticker")
        if tk:
            tickers.add(tk)
            dby[tk].append(r)
    for rows in dby.values():
        rows.sort(key=lambda r: _dt(r["ts"]))
    kill_level = _infer_kills(tickers)

    # Exact old-code spread rejections: contemporaneous best bid/ask evidence.
    spread_by_ticker: dict[str, list[dict]] = defaultdict(list)
    spread_rows = []
    for e in events:
        m = SPREAD_RE.search(e.get("msg", ""))
        if not m:
            continue
        row = {"ts": e["ts"], "ticker": m.group(1),
               "bid": int(m.group(2)), "ask": int(m.group(3))}
        spread_by_ticker[row["ticker"]].append(row)
        spread_rows.append(row)

    def preceding_depth(tk: str, when: datetime):
        best = None
        for r in dby.get(tk, []):
            t = _dt(r["ts"])
            if t > when:
                break
            if (when - t).total_seconds() <= max_snapshot_age_s:
                best = r
        return best

    def exact_spread_bid(tk: str, when: datetime):
        # Warning is emitted synchronously after the proof, but quote calls for
        # several buckets can take seconds. Permit 45s, never before the proof.
        best = None
        for r in spread_by_ticker.get(tk, []):
            t = _dt(r["ts"])
            delta = (t - when).total_seconds()
            if 0 <= delta <= 45:
                best = r
                break
        return best

    min_bid = int(cfg["engine"].get("min_bid_cents", 15))
    max_size = float(cfg["engine"].get("max_size_contracts", 300))
    fat = int(cfg["engine"].get("fat_finger_guard_f", 12))
    fee_rate = float(cfg["engine"].get("fee_rate", 0.07))
    channels = set(cfg["engine"].get("channels", []))

    proofs_by_city_date: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for e in events:
        if e.get("kind") == "proof" and e.get("channel") in channels:
            proofs_by_city_date[(e.get("city"), e.get("climate_date"))].append(e)
    for rows in proofs_by_city_date.values():
        rows.sort(key=lambda e: _dt(e["ts"]))

    series_by_city = {k: v["series"] for k, v in cfg["cities"].items()}
    trades = []
    pending_quote_unknown_depth = []
    audit_skips = defaultdict(int)

    for (city, cdate), proofs in sorted(proofs_by_city_date.items()):
        series = series_by_city.get(city)
        if not series or not cdate:
            continue
        prefix = _event_prefix(series, cdate)
        board_tickers = sorted(t for t in tickers if t.startswith(prefix + "-"))
        if not board_tickers:
            continue

        proven = -999
        metar_ref = None
        fired: set[str] = set()
        final_seen = max(int(p.get("level_f", -999)) for p in proofs)

        for ev in proofs:
            level = int(ev.get("level_f", -999))
            ch = ev.get("channel")
            when = _dt(ev["ts"])
            if ch in ("metar", "sixhr") and (metar_ref is None or level > metar_ref):
                metar_ref = level

            if level > proven:
                if ch in ("dsm", "omo_floor") and metar_ref is not None and level > metar_ref + fat:
                    audit_skips["plausibility_guard"] += 1
                    continue
                proven = level

            if proven == -999:
                continue

            for tk in board_tickers:
                kl = kill_level.get(tk)
                if kl is None or kl > proven or tk in fired:
                    continue

                dep = preceding_depth(tk, when)
                warning = exact_spread_bid(tk, when)
                bid = warning["bid"] if warning else None
                if bid is None and dep and dep.get("yes_bids"):
                    try:
                        bid = max(int(x[0]) for x in dep["yes_bids"])
                    except Exception:
                        bid = None
                if bid is None or bid < min_bid:
                    audit_skips["thin_or_no_bid_retry"] += 1
                    continue

                # Corrected placer would emit the intent here regardless of ask.
                min_px = max(min_bid, bid - 8)
                if dep:
                    qty, avg = _fill(dep.get("yes_bids", []), min_px, max_size)
                else:
                    qty, avg = 0.0, 0.0

                if qty <= 0:
                    # We know an executable top bid existed from the exact warning,
                    # but lack a saved quantity snapshot close enough to size it.
                    if warning:
                        pending_quote_unknown_depth.append({
                            "ts": ev["ts"], "city": city, "ticker": tk,
                            "proof_channel": ch, "proof_level_f": level,
                            "proven_f": proven, "kill_level": kl,
                            "exact_bid": bid, "exact_ask": warning["ask"],
                            "reason": "exact rejected quote exists; no preceding depth snapshot for size"
                        })
                    audit_skips["bid_but_no_saved_depth"] += 1
                    # Corrected strategy would have fired based on quote, so do not
                    # invent a later second entry for the same ticker.
                    fired.add(tk)
                    continue

                fired.add(tk)
                gross = qty * avg / 100.0
                fee = _fee(avg, qty, fee_rate)
                won = final_seen >= kl
                pnl = gross - fee if won else gross - qty - fee
                trades.append({
                    "ts": ev["ts"], "city": city, "ticker": tk,
                    "proof_channel": ch, "proof_level_f": level,
                    "proven_f": proven, "kill_level": kl,
                    "quote_bid_cents": bid,
                    "exact_spread_rejection": bool(warning),
                    "depth_ts": dep.get("ts") if dep else None,
                    "depth_age_s": round((when - _dt(dep["ts"])).total_seconds(), 1) if dep else None,
                    "min_fill_px_cents": min_px,
                    "contracts": round(qty, 2),
                    "avg_px_cents": round(avg, 2),
                    "gross_usd": round(gross, 2),
                    "fee_usd": fee,
                    "final_proof_max_f": final_seen,
                    "won": won,
                    "net_pnl_usd": round(pnl, 2),
                })

    wins = sum(1 for t in trades if t["won"])
    losses = len(trades) - wins
    total = round(sum(t["net_pnl_usd"] for t in trades), 2)
    by_day = defaultdict(float)
    by_city = defaultdict(float)
    for t in trades:
        by_day[t["ts"][:10]] += t["net_pnl_usd"]
        by_city[t["city"]] += t["net_pnl_usd"]

    return {
        "method": "counterfactual replay using proof journal + nearest preceding saved depth; exact old spread-rejection bid substituted when present",
        "window": {"start": start_iso, "end": end_iso},
        "snapshot_max_age_s": max_snapshot_age_s,
        "limitations": [
            "depth collector sampled race minutes rather than every quote update",
            "no post-proof depth snapshot is used to manufacture fills",
            "rows with an exact rejected bid but no preceding depth are listed separately and excluded from dollar PnL",
        ],
        "aggregate": {
            "sized_executable_trades": len(trades),
            "wins": wins, "losses": losses,
            "success_rate_pct": round(100 * wins / len(trades), 2) if trades else None,
            "net_pnl_usd": total,
            "avg_net_per_trade_usd": round(total / len(trades), 2) if trades else None,
            "spread_rejections_logged": len(spread_rows),
            "exact_bid_unknown_depth_count": len(pending_quote_unknown_depth),
        },
        "by_day": {k: round(v, 2) for k, v in sorted(by_day.items())},
        "by_city": {k: round(v, 2) for k, v in sorted(by_city.items())},
        "trades": trades,
        "exact_bid_unknown_depth": pending_quote_unknown_depth,
        "spread_rejections": spread_rows,
        "audit_skips": dict(audit_skips),
        "source_counts": {"events": len(events), "depth_rows": len(depth)},
    }
