from __future__ import annotations

import sys
import unittest
from datetime import date as Date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

from dsm_decode import parse_dsm_line  # noqa: E402
from fast_kalshi import KalshiBookCache, kill_client_order_id  # noqa: E402
from fast_sources import _metar_obs_time, parse_metar_proofs  # noqa: E402
from feeds import ProofEvent  # noqa: E402
from proof_bus import dict_to_event, event_to_dict  # noqa: E402
from strategy import Intent  # noqa: E402


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

    def test_dsm_decoder(self):
        seen = datetime(2026, 9, 11, 21, 16, tzinfo=timezone.utc)
        ev = parse_dsm_line("KNYC DS 2115 11/09 0811450/ /", "KNYC", -5,
                            "unit-dsm", seen)
        self.assertIsNotNone(ev)
        self.assertEqual(ev.level_f, 81)
        self.assertEqual(ev.climate_date, Date(2026, 9, 11))
        self.assertEqual(ev.channel, "dsm")
        self.assertTrue(ev.detail.startswith("unit-dsm"))


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


class IdempotencyAndBusTests(unittest.TestCase):
    @staticmethod
    def _intent(ticker: str) -> Intent:
        ev = ProofEvent(
            station="KNYC",
            climate_date=Date(2026, 9, 11),
            level_f=81,
            channel="dsm",
            obs_ts=datetime(2026, 9, 11, 20, 0, tzinfo=timezone.utc),
            seen_ts=datetime(2026, 9, 11, 20, 0, 1, tzinfo=timezone.utc),
            detail="unit",
        )
        return Intent(
            ts=datetime.now(timezone.utc), ticker=ticker, action="SELL_YES",
            reason="unit", proof=ev, min_px=15, max_size=300,
        )

    def test_kill_client_order_id_is_stable_and_market_specific(self):
        a1 = kill_client_order_id(self._intent("KXHIGHNY-26SEP11-T80"))
        a2 = kill_client_order_id(self._intent("KXHIGHNY-26SEP11-T80"))
        b = kill_client_order_id(self._intent("KXHIGHNY-26SEP11-T82"))
        self.assertEqual(a1, a2)
        self.assertNotEqual(a1, b)
        self.assertTrue(a1.startswith("mk-"))

    def test_proof_bus_serialization_round_trip(self):
        ev = self._intent("KXHIGHNY-26SEP11-T80").proof
        restored = dict_to_event(event_to_dict(ev))
        self.assertEqual(restored, ev)


if __name__ == "__main__":
    unittest.main()
