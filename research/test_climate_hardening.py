"""Guards that stop NOAA archive/stale reports and AWC failures becoming trades.

No network, account credentials, orders, or external dependencies required.
Run: python research/test_climate_hardening.py
"""
import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from climate_products import parse_cli, parse_dsm
from feeds import DSBODY, MetarFeed

NOW = datetime(2026, 10, 8, 19, 45, tzinfo=timezone.utc)
CLI = (
    "CDUS45 KBOU 081234\nCLIDEN\n\nCLIMATE REPORT\n"
    "NATIONAL WEATHER SERVICE DENVER/BOULDER\n"
    "...THE DENVER CO CLIMATE SUMMARY FOR OCTOBER 8 2026...\n"
    "VALID AS OF 0600 AM LOCAL TIME.\nTEMPERATURE (F)\n  TODAY\n"
    "   MAXIMUM         62    1225 AM  85 1910 69 -7\n"
    "PRECIPITATION (IN)\n"
)
DSM = (
    "CXUS41 KOKX 081930\nDSMNYC\n"
    "KNYC DS COR 08/10 701423/ 592359// 70/ 60//0070101/T/00/T\n"
)


class BulletinHardeningTests(unittest.TestCase):
    def test_valid_same_day_cli(self):
        e = parse_cli(CLI, "KDEN", -7, NOW)
        self.assertEqual((e.channel, e.level_f), ("cli", 62))

    def test_cached_old_bulletin_with_new_date_rejected(self):
        # Same apparent observed-date is not enough: headers can be cached.
        text = CLI.replace("081234", "161234")
        self.assertIsNone(parse_cli(text, "KDEN", -7, NOW))

    def test_same_day_corrected_dsm(self):
        e = parse_dsm(DSM, "KNYC", -5, NOW)
        self.assertIsNotNone(e)
        self.assertEqual((e.channel, e.level_f), ("dsm", 70))
        self.assertIsNotNone(DSBODY.match(DSM.splitlines()[2]))

    def test_stale_header_corrected_dsm_rejected(self):
        text = DSM.replace("081930", "161930")
        self.assertIsNone(parse_dsm(text, "KNYC", -5, NOW))

    def test_stale_other_city_report_never_trades(self):
        self.assertIsNone(parse_dsm(DSM, "KDEN", -7, NOW))

    def test_awc_failure_backoff_isolation(self):
        # AWC failure cannot prevent fetching a new TGFTP proof.
        report = ("2026/10/08 19:53\nKDEN 081953Z 13009KT 10SM CLR "
                  "25/03 A3001 RMK AO2 T02500030\n")
        feed = MetarFeed("KDEN", -7)
        calls = []
        class FixedDate(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 10, 8, 20, 0, tzinfo=timezone.utc)
        def fetch(url, timeout=4):
            calls.append(url)
            if "aviationweather.gov" in url:
                raise TimeoutError("Test AWC read timeout")
            return report.encode()
        with patch("feeds._get", side_effect=fetch), patch("feeds.datetime", FixedDate):
            self.assertEqual(feed.poll(awc_only=True), [])
            self.assertEqual(feed.poll(awc_only=True), [])
            proof = feed.poll(fast_only=True)
        self.assertEqual(len([u for u in calls if "aviationweather.gov" in u]), 1)
        self.assertTrue(any(e.channel == "metar" for e in proof))
        self.assertEqual(feed.last_awc_error, "TimeoutError")


if __name__ == "__main__":
    unittest.main()
