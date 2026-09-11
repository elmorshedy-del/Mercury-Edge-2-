from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
sys.path.insert(0, str(ROOT / "research"))

from call_asos_voice import e164_us  # noqa: E402
from source_race_report import build_report  # noqa: E402
from twilio_asos_gateway import _ws_base  # noqa: E402


class FreshnessClassificationTests(unittest.TestCase):
    @staticmethod
    def row(source: str, seen: str, warm_marker="missing") -> dict:
        r = {
            "station": "KMIA",
            "obs_ts": "2026-09-11T20:27:00+00:00",
            "channel": "metar",
            "level_f": 88,
            "source": source,
            "seen_ts": seen,
            "obs_to_seen_ms": 1000,
            "detail": "unit http=10ms",
        }
        if warm_marker != "missing":
            r["warm_start"] = warm_marker
        return r

    def test_legacy_missing_marker_never_counts_as_fresh(self):
        rows = [
            self.row("tgftp", "2026-09-11T20:30:10+00:00"),
            self.row("aviationweather", "2026-09-11T20:30:11+00:00", False),
        ]
        report = build_report(rows)
        self.assertEqual(report["exact_source_wins"], {})
        self.assertEqual(report["sources"]["tgftp"]["fresh_records"], 0)
        self.assertEqual(report["sources"]["tgftp"]["unknown_freshness_records"], 1)
        self.assertEqual(len(report["unknown_freshness_races"]), 1)

    def test_two_explicit_fresh_rows_count(self):
        rows = [
            self.row("tgftp", "2026-09-11T20:30:10+00:00", False),
            self.row("aviationweather", "2026-09-11T20:30:12+00:00", False),
        ]
        self.assertEqual(build_report(rows)["exact_source_wins"], {"tgftp": 1})


class VoiceTransportHelpersTests(unittest.TestCase):
    def test_e164_normalization(self):
        self.assertEqual(e164_us("215-492-9617"), "+12154929617")
        self.assertEqual(e164_us("1 (215) 492-9617"), "+12154929617")
        with self.assertRaises(ValueError):
            e164_us("123")

    def test_websocket_base(self):
        self.assertEqual(_ws_base("https://voice.example.com"), "wss://voice.example.com")


if __name__ == "__main__":
    unittest.main()
