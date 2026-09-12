"""Human-readable Mercury source latency scoreboard.

Usage:
    PYTHONPATH=engine python research/source_scoreboard.py /data/source_race.jsonl

Design goal: one screen, no ambiguous startup/backfill races. A record is treated
as fresh only when ``warm_start is False`` explicitly. Older rows that predate
that field are not silently promoted to fresh data.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT = Path("/data/source_race.jsonl")


def load(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open(errors="replace") as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("source") and r.get("station") and r.get("seen_ts"):
                rows.append(r)
    return rows


def pct(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    p = (len(ys) - 1) * q
    lo, hi = int(p), min(int(p) + 1, len(ys) - 1)
    f = p - lo
    return ys[lo] * (1 - f) + ys[hi] * f


def family(channel: str) -> str:
    if channel in {"metar", "sixhr"}:
        return "METAR/SPECI + 6HR"
    if channel in {"omo_floor", "faa_omo_candidate"}:
        return "OMO"
    if channel == "dsm":
        return "DSM"
    return channel.upper() or "OTHER"


def verdict(median_s: float | None, n: int) -> str:
    if median_s is None or n == 0:
        return "NO FRESH DATA"
    if median_s <= 15:
        return "FAST"
    if median_s <= 60:
        return "GOOD"
    if median_s <= 180:
        return "SLOW"
    if median_s <= 300:
        return "VERY SLOW"
    return "BACKUP ONLY"


def summarize(rows: list[dict]) -> dict[str, list[dict]]:
    # Explicit False only. Missing flags from old probe versions are unknown.
    fresh = [r for r in rows if r.get("warm_start") is False]
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in fresh:
        grouped[(family(str(r.get("channel", ""))), str(r["source"]))].append(r)

    out: dict[str, list[dict]] = defaultdict(list)
    for (fam, src), rs in grouped.items():
        lags = [float(r["obs_to_seen_ms"]) / 1000.0 for r in rs
                if r.get("obs_to_seen_ms") is not None
                and 0 <= float(r["obs_to_seen_ms"]) <= 24 * 3600 * 1000]
        med = statistics.median(lags) if lags else None
        p90 = pct(lags, .90)
        out[fam].append({
            "source": src,
            "n": len(lags),
            "median_s": round(med, 3) if med is not None else None,
            "p90_s": round(p90, 3) if p90 is not None else None,
            "verdict": verdict(med, len(lags)),
        })
    for fam in out:
        out[fam].sort(key=lambda x: (
            x["median_s"] is None,
            x["median_s"] if x["median_s"] is not None else 1e99,
            x["source"],
        ))
    return dict(out)


def render(summary: dict[str, list[dict]]) -> str:
    order = ["METAR/SPECI + 6HR", "OMO", "DSM"]
    lines = []
    for fam in order + sorted(set(summary) - set(order)):
        lines.append(f"\n{fam}")
        rows = summary.get(fam, [])
        if not rows:
            lines.append("  no fresh measurements")
            continue
        for r in rows:
            med = "-" if r["median_s"] is None else f"{r['median_s']:.1f}s"
            p90 = "-" if r["p90_s"] is None else f"{r['p90_s']:.1f}s"
            lines.append(
                f"  {r['source']:<24} median {med:>8}  p90 {p90:>8}  "
                f"n={r['n']:<4}  {r['verdict']}"
            )
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    print(render(summarize(load(path))), end="")


if __name__ == "__main__":
    main()
