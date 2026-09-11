"""Brain-fog-friendly Mercury latency scoreboard."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from source_race_report import build_report, load_rows

DEFAULT = Path("/data/source_race.jsonl")


def _seconds(ms):
    return None if ms is None else round(ms / 1000.0, 1)


def build_scoreboard(report: dict) -> dict:
    sources = report.get("sources", {})
    exact = report.get("exact_source_wins", {})
    madis = sources.get("madis-hf", {})
    return {
        "MADIS HF": {
            "status": "RED", "use": "backup only",
            "fresh_median_delay_s": _seconds(madis.get("obs_to_seen_ms_median")),
        },
        "TGFTP + AviationWeather": {
            "status": "YELLOW", "use": "race both; first valid copy wins",
            "exact_fresh_wins": {"tgftp": exact.get("tgftp", 0), "aviationweather": exact.get("aviationweather", 0)},
        },
        "DSM HTTP": {"status": "RED", "use": "fallback only; move to LDM/NWWS push"},
        "ASOS voice": {"status": "YELLOW", "use": "live benchmark next; needs telephony credentials"},
        "FAA CSS-Wx": {"status": "YELLOW", "use": "top upstream candidate; needs FAA access"},
        "Kalshi WSS/FIX": {"status": "GREEN", "use": "target execution path; FIX access still needed"},
    }


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    print(json.dumps(build_scoreboard(build_report(load_rows(path))), indent=2))


if __name__ == "__main__":
    main()
