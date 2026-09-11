"""Summarize Mercury source-race measurements without confusing backfill with latency.

Usage:
    PYTHONPATH=engine python research/source_race_report.py
    PYTHONPATH=engine python research/source_race_report.py /data/source_race.jsonl

The report deliberately separates:
- exact races: every compared arrival was observed after probe warm-up;
- left-censored races: one source already had the observation at warm start, so
  we know it beat another source by *at least* the observed gap but not when it
  first became available upstream.

The economic question is which source first reaches Mercury, not merely the age
of the underlying weather observation.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT = Path("/data/source_race.jsonl")
HTTP_RE = re.compile(r"\bhttp=([0-9.]+)ms\b")


def percentile(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    pos = (len(ys) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ys) - 1)
    frac = pos - lo
    return ys[lo] * (1 - frac) + ys[hi] * frac


def load_rows(path: Path) -> list[dict]:
    out = []
    if not path.exists():
        return out
    with path.open(errors="replace") as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("seen_ts") and r.get("station") and r.get("source"):
                out.append(r)
    return out


def signature(r: dict) -> tuple:
    # obs_ts is the strongest cross-source identity for METAR/OMO. level/channel
    # protect against accidental pairing when a source emits multiple proof types.
    return (
        r.get("station"), r.get("obs_ts"), r.get("channel"), r.get("level_f"),
    )


def iso_seconds(s: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(s).timestamp()


def build_report(rows: list[dict]) -> dict:
    by_source = defaultdict(list)
    transport = defaultdict(list)
    for r in rows:
        by_source[r["source"]].append(r)
        m = HTTP_RE.search(r.get("detail") or "")
        if m:
            transport[r["source"]].append(float(m.group(1)))

    source_stats = {}
    for src, rs in sorted(by_source.items()):
        fresh = [r for r in rs if not r.get("warm_start")]
        lags = [float(r["obs_to_seen_ms"]) for r in fresh
                if r.get("obs_to_seen_ms") is not None]
        rtts = transport.get(src, [])
        source_stats[src] = {
            "records": len(rs),
            "fresh_records": len(fresh),
            "obs_to_seen_ms_median": round(statistics.median(lags), 3) if lags else None,
            "obs_to_seen_ms_p90": round(percentile(lags, .90), 3) if lags else None,
            "obs_to_seen_ms_p95": round(percentile(lags, .95), 3) if lags else None,
            "http_ms_median": round(statistics.median(rtts), 3) if rtts else None,
            "http_ms_p95": round(percentile(rtts, .95), 3) if rtts else None,
        }

    grouped = defaultdict(list)
    for r in rows:
        if r.get("obs_ts"):
            grouped[signature(r)].append(r)

    exact_wins = Counter()
    exact_pair_gaps = defaultdict(list)
    censored = []
    races = []

    for sig, rs in grouped.items():
        # Earliest appearance per source for this exact observation/proof.
        first = {}
        for r in rs:
            src = r["source"]
            if src not in first or r["seen_ts"] < first[src]["seen_ts"]:
                first[src] = r
        if len(first) < 2:
            continue
        ordered = sorted(first.values(), key=lambda r: r["seen_ts"])
        winner = ordered[0]
        runner = ordered[1]
        gap_ms = (iso_seconds(runner["seen_ts"]) - iso_seconds(winner["seen_ts"])) * 1000
        race = {
            "signature": sig,
            "winner": winner["source"],
            "runner_up": runner["source"],
            "gap_ms": round(gap_ms, 3),
            "winner_warm_start": bool(winner.get("warm_start")),
            "runner_warm_start": bool(runner.get("warm_start")),
        }
        races.append(race)
        if not winner.get("warm_start") and not runner.get("warm_start"):
            exact_wins[winner["source"]] += 1
            exact_pair_gaps[(winner["source"], runner["source"])].append(gap_ms)
        elif winner.get("warm_start") and not runner.get("warm_start"):
            censored.append({
                **race,
                "interpretation": (
                    f"{winner['source']} beat {runner['source']} by at least "
                    f"{gap_ms/1000:.3f}s; winner was already present at warm start"
                ),
            })

    pairwise = {}
    for (a, b), gaps in sorted(exact_pair_gaps.items()):
        pairwise[f"{a}>{b}"] = {
            "count": len(gaps),
            "median_lead_ms": round(statistics.median(gaps), 3),
            "p90_lead_ms": round(percentile(gaps, .90), 3),
        }

    return {
        "records": len(rows),
        "sources": source_stats,
        "exact_source_wins": dict(exact_wins),
        "exact_pairwise": pairwise,
        "left_censored_races": censored[-50:],
        "race_count": len(races),
    }


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    report = build_report(load_rows(path))
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
