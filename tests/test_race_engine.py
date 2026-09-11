from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

from fast_kalshi import KalshiBookCache  # noqa: E402
from fast_sources import _metar_obs_time, parse_metar_proofs  # noqa: E402


class FakeSigner:
    available = False


class FastSourceTests(unittest.TestCase):
    def test_metar_month_rollover_uses_nearest_valid_month(self):
        now = datetime(2026, 10, 1, 0, 2, tzinfo=timezone.utc)
        obs = _metar_obs_time("KDEN 302353Z AUTO", now)
        self.assertEqual(obs, datetime(2026, 9, 30, 23, 53, tzinfo=timezone.utc))

    def test_t_group_and_six_hour_group_decode(self):
        raw = (
            "KDEN 111753Z 17008KT 10SM CLR 20/10 A3000 RMK AO2 "
            "SLP100 T02000100 10222 20150"
        )
        seen = datetime(2026, 9, 11, 17, 55, tzinfo=timezone.utc)
        evs = parse_metar_proofs(raw, "KDEN", -7, "unit", seen)
        self.assertEqual({e.channel for e in evs}, {"metar", "sixhr"})
        levels = {e.channel: e.level_f for e in evs}
        self.assertEqual(levels["metar"], 68)
        self.assertEqual(levels["sixhr"], 72)


class BookCacheTests(unittest.TestCase):
    def setUp(self):
        self.book = KalshiBookCache(FakeSigner())

    def test_snapshot_quote_uses_yes_bid_and_inverse_no_bid(self):
        self.book._apply_snapshot({
            "market_ticker": "TEST",
            "yes_dollars_fp": [["0.1800", "300.00"], ["0.1700", "20.00"]],
            "no_dollars_fp": [["0.8100", "100.00"]],
        })
        self.assertEqual(self.book.quote("TEST"), (18, 19))

    def test_delta_updates_quantity_and_deletes_zero_level(self):
        self.book._apply_snapshot({
            "market_ticker": "TEST",
            "yes_dollars_fp": [["0.1800", "300.00"]],
            "no_dollars_fp": [],
        })
        self.book._apply_delta({
            "market_ticker": "TEST", "side": "yes",
            "price_dollars": "0.1800", "delta_fp": "-300.00", "ts_ms": 1,
        })
        self.assertEqual(self.book.quote("TEST"), (None, None))

    def test_yes_levels_are_best_first(self):
        self.book._apply_snapshot({
            "market_ticker": "TEST",
            "yes_dollars_fp": [["0.1500", "1.00"], ["0.3100", "2.00"]],
            "no_dollars_fp": [],
        })
        self.assertEqual(self.book.yes_levels("TEST")[0], (31.0, 2.0))


if __name__ == "__main__":
    unittest.main()
