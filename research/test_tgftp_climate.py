"""Fail-closed TGFTP CLI/DSM regression and independent METAR lanes.

Run from repo root: python3 research/test_tgftp_climate.py
No network, orders, or external services required.
"""
import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "engine"))

from climate_products import parse_cli, parse_dsm, urls, TGFTPClimateFeed
from feeds import MetarFeed


def now_utc(h=18):
    return datetime(2026, 10, 8, h, 0, tzinfo=timezone.utc)


DEN_CLI = """CDUS45 KBOU 081234
CLIDEN

CLIMATE REPORT
NATIONAL WEATHER SERVICE DENVER/BOULDER
634 AM MDT THU OCT 08 2026

...THE DENVER CO CLIMATE SUMMARY FOR OCTOBER 8 2026...
VALID AS OF 0600 AM LOCAL TIME.
TEMPERATURE (F)
  TODAY
   MAXIMUM         62   1225 AM  85    1910  69
   MINIMUM         59    459 AM  22    1970  40
PRECIPITATION (IN)
  TODAY 0.00
THE DENVER CO CLIMATE NORMALS FOR TOMORROW
  MAXIMUM TEMPERATURE (F)   68
"""

DEN_DSM = """CXUS45 KBOU 081216
DSMDEN
KDEN DS 0500 08/10 620049/ 540430// 71/ 54//0010451/00/
00/00/00/00/00/00/00/00/00
"""
MIAMI_MISMATCH = """CXUS42 KMFL 081216
DSMMIA
KFPR DS 0500 08/10 890049/ 730430// 89/ 73//0010451/00/
"""


class NOAAClimateTests(unittest.TestCase):
    def test_cli_den_same_day_hard_proof(self):
        proof = parse_cli(DEN_CLI, "KDEN", -7, now_utc(18))
        self.assertIsNotNone(proof)
        self.assertEqual(proof.channel, "cli")
        self.assertEqual(proof.level_f, 62)
        self.assertEqual(proof.climate_date.isoformat(), "2026-10-08")

    def test_cli_yesterday_never_trades(self):
        self.assertIsNone(parse_cli(
            DEN_CLI.replace("  TODAY\n", "  YESTERDAY\n"),
            "KDEN", -7, now_utc(18)))

    def test_cli_previous_day_never_trades(self):
        self.assertIsNone(parse_cli(
            DEN_CLI.replace("OCTOBER 8 2026", "OCTOBER 7 2026"),
            "KDEN", -7, now_utc(18)))

    def test_cli_other_station_never_trades(self):
        self.assertIsNone(parse_cli(DEN_CLI, "KNYC", -5, now_utc(18)))

    def test_cli_rejects_forecast_normals_only(self):
        txt = DEN_CLI.replace("   MAXIMUM         62", "   MAXIMUM         MM")
        self.assertIsNone(parse_cli(txt, "KDEN", -7, now_utc(18)))

    def test_dsm_den_same_day(self):
        proof = parse_dsm(DEN_DSM, "KDEN", -7, now_utc(18))
        self.assertIsNotNone(proof)
        self.assertEqual(proof.level_f, 62)
        self.assertEqual(proof.channel, "dsm")
        self.assertIn("tgftp", proof.detail)

    def test_dsm_very_old_date_is_rejected(self):
        self.assertIsNone(parse_dsm(
            DEN_DSM.replace("08/10", "16/09"), "KDEN", -7, now_utc(18)))

    def test_miami_filename_different_station_rejected(self):
        self.assertIsNone(parse_dsm(MIAMI_MISMATCH, "KMIA", -5, now_utc(18)))

    def test_no_cross_station_dsm_or_cli(self):
        self.assertIsNone(parse_dsm(DEN_DSM, "KLAX", -8, now_utc(18)))
        self.assertIsNone(parse_cli(DEN_CLI, "KPHL", -5, now_utc(18)))

    def test_all_station_url_mappings(self):
        self.assertTrue(urls("KDEN")["cli"].endswith("cdus45.kbou.cli.den.txt"))
        self.assertTrue(urls("KMIA")["dsm"].endswith("cxus42.kmfl.dsm.mia.txt"))
        self.assertEqual(len({urls(s)["cli"] for s in (
            "KNYC", "KDEN", "KPHL", "KMDW", "KAUS", "KMIA", "KLAX")}), 7)

    def test_metar_awc_isolated_from_tgftp(self):
        # The old AWC timeout must not delay TGFTP proofs.
        report = "KDEN 081753Z 13006KT 10SM FEW070 19/10 A3002 RMK AO2 T01940100"
        with patch("feeds._get", return_value=report.encode()) as getter:
            MetarFeed("KDEN", -7).poll(fast_only=True)
            self.assertEqual(getter.call_count, 1)
            self.assertIn("tgftp", getter.call_args[0][0])
            getter.reset_mock()
            MetarFeed("KDEN", -7).poll(awc_only=True)
            self.assertEqual(getter.call_count, 1)
            self.assertIn("aviationweather", getter.call_args[0][0])

    def test_tgftp_feed_dedup(self):
        class FixedDate(datetime):
            @classmethod
            def now(cls, tz=None):
                return now_utc(18)
        f = TGFTPClimateFeed("KDEN", -7, "cli")
        with patch("climate_products._get", return_value=DEN_CLI.encode()), \
             patch("climate_products.datetime", FixedDate):
            self.assertEqual(len(f.poll()), 1)
            self.assertEqual(f.poll(), [])


if __name__ == "__main__":
    unittest.main()
