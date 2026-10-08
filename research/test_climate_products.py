"""Deterministic verification of NOAA climate proof guards and source fallback.

Execute without external requests, credentials, or trading:
    python3 research/test_climate_products.py
"""
from __future__ import annotations

import os
import sys
import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from climate_products import parse_cli, parse_dsm, TGFTPClimateFeed
from feeds import MetarFeed
from strategy import CityState, KillEngine

NOW = datetime(2026, 10, 8, 19, 55, tzinfo=timezone.utc)

DEN_TODAY = (
    "CDUS45 KBOU 081234\n"
    "CLIDEN\n\nCLIMATE REPORT\n"
    "NATIONAL WEATHER SERVICE DENVER/BOULDER\n"
    "634 AM MDT THU OCT 08 2026\n"
    "...THE DENVER CO CLIMATE SUMMARY FOR OCTOBER 8 2026...\n"
    "VALID AS OF 0600 AM LOCAL TIME.\n"
    "TEMPERATURE (F)\n"
    "  TODAY\n"
    "   MAXIMUM         62   1225 AM  85    1910  69     -7       80\n"
    "   MINIMUM         59    459 AM\n"
    "THE DENVER CO CLIMATE NORMALS FOR TOMORROW\n"
    " MAXIMUM TEMPERATURE (F) 68 87 1910\n"
)
AUS_TODAY = (
    "CDUS44 KEWX 081239\nCLIAUS\n"
    "...THE AUSTIN BERGSTROM CLIMATE SUMMARY FOR OCTOBER 8 2026...\n"
    "VALID AS OF 0700 AM LOCAL TIME.\n"
    "TEMPERATURE (F)\n  TODAY\n   MAXIMUM         64   1:42 AM  96    1990\n"
)
LAX_YESTERDAY = (
    "CDUS46 KLOX 080840\nCLILAX\n"
    "...THE LOS ANGELES INTL AIRPORT CA CLIMATE SUMMARY FOR OCTOBER 7 2026...\n"
    "TEMPERATURE (F)\n  YESTERDAY\n   MAXIMUM         86  10:05 AM 96 1951\n"
    "THE LOS ANGELES INTL AIRPORT CA CLIMATE NORMALS FOR TODAY\n"
    " MAXIMUM TEMPERATURE (F) 75\n"
)
DEN_DSM_STALE = (
    "CXUS45 KBOU 161216\nDSMDEN\n"
    "KDEN DS 0500 16/09 620049/ 540430// 71/ 54//0010451/00/\n"
)
DEN_DSM_CURRENT = (
    "CXUS45 KBOU 081916\nDSMDEN\n"
    "KDEN DS 1830 08/10 831115/ 540430// 71/ 54//0010451/00/\n"
)
NYC_CORRECTED_CURRENT = (
    "CXUS41 KOKX 081930\nDSMNYC\n"
    "KNYC DS COR 08/10 701423/ 592359// 70/ 60//0070101/T/00/T\n"
)


class ClimateProductTest(unittest.TestCase):
    def test_denver_cli_today_exact(self):
        e = parse_cli(DEN_TODAY, "KDEN", -7, NOW)
        self.assertIsNotNone(e)
        self.assertEqual(e.channel, "cli")
        self.assertEqual(e.level_f, 62)
        self.assertEqual(e.climate_date, date(2026, 10, 8))
        self.assertIsNone(e.obs_ts)

    def test_austin_cli_today(self):
        e = parse_cli(AUS_TODAY, "KAUS", -6, NOW)
        self.assertEqual((e.channel, e.level_f), ("cli", 64))

    def test_prior_day_cli_not_tradable(self):
        self.assertIsNone(parse_cli(LAX_YESTERDAY, "KLAX", -8, NOW))
        # Even if wording says "TODAY", wrong report date is blocked.
        changed = LAX_YESTERDAY.replace("OCTOBER 7 2026", "OCTOBER 8 2026")
        self.assertIsNone(parse_cli(changed, "KLAX", -8, NOW))

    def test_station_mixup_rejected(self):
        self.assertIsNone(parse_cli(DEN_TODAY, "KNYC", -5, NOW))
        self.assertIsNone(parse_dsm(DEN_DSM_CURRENT, "KPHL", -5, NOW))

    def test_future_date_or_old_header_rejected(self):
        wrong_date = DEN_TODAY.replace("OCTOBER 8 2026", "OCTOBER 9 2026")
        self.assertIsNone(parse_cli(wrong_date, "KDEN", -7, NOW))
        old_header = DEN_TODAY.replace("081234", "161234")
        self.assertIsNone(parse_cli(old_header, "KDEN", -7, NOW))

    def test_missing_or_record_high_not_hard_proof(self):
        self.assertIsNone(parse_cli(DEN_TODAY.replace("MAXIMUM         62", "MAXIMUM         MM"),
                                     "KDEN", -7, NOW))
        self.assertIsNone(parse_cli(DEN_TODAY.replace("  TODAY\n", "  YESTERDAY\n"),
                                     "KDEN", -7, NOW))

    def test_september_denver_dsm_is_stale(self):
        self.assertIsNone(parse_dsm(DEN_DSM_STALE, "KDEN", -7, NOW))

    def test_same_day_denver_dsm(self):
        e = parse_dsm(DEN_DSM_CURRENT, "KDEN", -7, NOW)
        self.assertEqual((e.channel, e.level_f), ("dsm", 83))
        self.assertEqual(e.obs_ts.isoformat(), "2026-10-08T18:15:00+00:00")

    def test_cor_date_format(self):
        e = parse_dsm(NYC_CORRECTED_CURRENT, "KNYC", -5, NOW)
        self.assertEqual((e.channel, e.level_f), ("dsm", 70))

    def test_cli_eliminates_when_valid(self):
        e = parse_cli(DEN_TODAY, "KDEN", -7, NOW)
        engine = KillEngine({"channels": ["cli"], "min_bid_cents": 15})
        city = CityState("KDEN", "KXHIGHDEN")
        bucket = SimpleNamespace(ticker="KXHIGHDEN-26OCT08-T60",
                                 subtitle="60 or below", kill_level=60)
        intents = engine.on_proof(city, e, [bucket], lambda _: (27, 30))
        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].proof.channel, "cli")
        self.assertEqual(city.proven_max[date(2026, 10, 8)], 62)

    def test_cli_extreme_jump_guard(self):
        e = parse_cli(DEN_TODAY.replace("MAXIMUM         62", "MAXIMUM         99"),
                      "KDEN", -7, NOW)
        engine = KillEngine({"channels": ["cli"], "fat_finger_guard_f": 7})
        city = CityState("KDEN", "KXHIGHDEN")
        city.metar_max[date(2026, 10, 8)] = 63
        bucket = SimpleNamespace(ticker="X", subtitle="dead", kill_level=65)
        self.assertEqual(engine.on_proof(city, e, [bucket], lambda _: (40, 40)), [])
        self.assertNotIn(date(2026, 10, 8), city.proven_max)

    def test_product_feed_dedup(self):
        feed = TGFTPClimateFeed("KDEN", -7, "cli")
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return NOW
        with patch("climate_products._product", return_value=DEN_TODAY), \
             patch("climate_products.datetime", FixedDateTime):
            first = feed.poll()
            second = feed.poll()
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])


class AWCAndFallbackTest(unittest.TestCase):
    def test_awc_backoff_does_not_block_tgftp(self):
        feed = MetarFeed("KDEN", -7)
        raw = ("2026/10/08 19:53\nKDEN 081953Z 13009KT 10SM CLR 25/03 "
               "A3001 RMK AO2 SLP100 T02500030")
        calls = []
        def request(url, timeout=4):
            calls.append(url)
            if "aviationweather.gov" in url:
                raise TimeoutError("AWC intentionally timed out")
            return raw.encode()
        with patch("feeds._get", side_effect=request):
            self.assertEqual(feed.poll(awc_only=True), [])
            self.assertEqual(feed.poll(awc_only=True), [])
            evs = feed.poll(fast_only=True)
        self.assertEqual(len([c for c in calls if "aviationweather.gov" in c]), 1)
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0].channel, "metar")


if __name__ == "__main__":
    unittest.main()
