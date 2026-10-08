"""Deterministic regression tests for fast elimination feed integration.

Run: python3 -m unittest discover -s research -p 'test_fast_weather_feeds.py'
No outbound HTTP, Kalshi calls, or orders.
"""
import os
import sys
import unittest
import json
import queue
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from datis import decode_page, DATISFeed
from feeds import MetarFeed
from minutetemp import decode_latest, MinuteTempStream


def utc(h, m=0):
    return datetime(2026, 10, 8, h, m, tzinfo=timezone.utc)


KLAX = ("LAX ATIS INFO X 1653Z. 22005KT 10SM SCT009 26/21 "
        "A2987 (TWO NINER EIGHT SEVEN) RMK AO2 SLP113 T02560211. "
        "INST... ADVS YOU HAVE INFO X.")
PHL = ("PHL ARR INFO I 1454Z. 30010KT 10SM FEW070 SCT150 22/10 "
       "A2991 RMK AO2 SLP127 T02220100 50012. ARRIVALS...")
MDW = ("MDW ATIS INFO O 1333Z SPECIAL. 19005KT 4SM RA BR "
       "BKN012 16/15 A2997 RMK AO2 P0006 T01610150. ...")
KDEN = ("DEN ARR INFO G 1453Z. 12009KT 10SM 18/M03 A3010 "
        "RMK AO2 T01831028. ARRIVALS...")


class FakeResponse:
    def __init__(self, text):
        self.text = text
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, _limit):
        return self.text.encode()


class DatisTests(unittest.TestCase):
    def test_lax_precise_temperature(self):
        obs, level, letter = decode_page(KLAX, "KLAX", utc(16, 54))
        self.assertEqual(obs, utc(16, 53))
        self.assertEqual(level, 78)  # 25.6 Celsius -> whole-F ASOS floor
        self.assertEqual(letter, "X")

    def test_philadelphia_arrival(self):
        obs, level, _ = decode_page(PHL, "KPHL", utc(15, 0))
        self.assertEqual(obs, utc(14, 54))
        self.assertEqual(level, 72)

    def test_chicago_midway_special(self):
        obs, level, _ = decode_page(MDW, "KMDW", utc(13, 40))
        self.assertEqual(obs, utc(13, 33))
        self.assertEqual(level, 61)

    def test_denver_arrival(self):
        obs, level, _ = decode_page(KDEN, "KDEN", utc(15, 0))
        self.assertEqual(obs, utc(14, 53))
        self.assertEqual(level, 65)

    def test_multiple_messages_choose_newest(self):
        old = KLAX.replace("X 1653Z", "W 1553Z").replace("T02560211", "T02440206")
        obs, level, letter = decode_page(old + KLAX, "KLAX", utc(17, 0))
        self.assertEqual((obs, level, letter), (utc(16, 53), 78, "X"))

    def test_no_precise_tgroup_no_tradable_proof(self):
        page = "AUS ATIS INFO S 1653Z. 04008KT 10SM FEW060 30/15 A3001. ARRIVALS..."
        self.assertIsNone(decode_page(page, "KAUS", utc(17, 0)))

    def test_never_cross_into_metar_sidebar(self):
        page = "AUS ATIS INFO S 1653Z. 04008KT 10SM FEW060 30/15 A3001. " \
               + "X" * 400 + " METAR KAUS 081653Z T03000150"
        self.assertIsNone(decode_page(page, "KAUS", utc(17, 0)))

    def test_station_mismatch_rejected(self):
        self.assertIsNone(decode_page(PHL, "KDEN", utc(15, 0)))

    def test_outdated_data_rejected(self):
        self.assertIsNone(decode_page(KLAX, "KLAX", utc(19, 0)))

    def test_midnight_observation_utc(self):
        page = KLAX.replace("1653Z", "2353Z")
        obs, _, _ = decode_page(page, "KLAX",
                                datetime(2026, 10, 9, 0, 3, tzinfo=timezone.utc))
        self.assertEqual(obs.date().isoformat(), "2026-10-08")

    def test_datis_dedup_and_climate_date(self):
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 10, 8, 16, 54, tzinfo=timezone.utc)
        feed = DATISFeed("KLAX", -8)
        with patch("datis.urllib.request.urlopen", return_value=FakeResponse(KLAX)), \
             patch("datis.datetime", FixedDateTime):
            first = feed.poll()
            again = feed.poll()
        self.assertEqual(len(first), 1)
        self.assertEqual(again, [])
        self.assertEqual(first[0].channel, "metar")
        self.assertEqual(first[0].climate_date.isoformat(), "2026-10-08")


class StationFileTests(unittest.TestCase):
    def test_tgftp_temperature_and_six_hour_group(self):
        # The 18Z group covers 12-18Z, entirely in LA's LST day.
        raw = ("2026/10/08 17:53\n"
               "KLAX 081753Z 20006KT 10SM FEW090 26/20 A2989 "
               "RMK AO2 SLP110 T02560200 10256 20120\n")
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 10, 8, 18, 0, tzinfo=timezone.utc)
        with patch("feeds._get", return_value=raw.encode()), \
             patch("feeds.datetime", FixedDateTime):
            evs = MetarFeed("KLAX", -8).poll(fast_only=True)
        self.assertEqual({ev.channel for ev in evs}, {"metar", "sixhr"})
        self.assertTrue(all(ev.climate_date.isoformat() == "2026-10-08" for ev in evs))


class MinuteTempTests(unittest.TestCase):
    def sample(self, stamp="2026-10-08T17:25:00Z"):
        # Recorded shape of the minuteTemp KLAX paid WS observation on Oct 8.
        return {
            "type": "observation", "station_id": "KLAX",
            "observed_at": stamp, "temperature_f": 78.8,
            "temperature_c": 26, "temp_min_f": 77.9, "temp_max_f": 79.7,
            "persistence_status": "uncommitted",
        }

    def test_minute_provider_floor_and_age(self):
        packet = self.sample()
        seen = datetime(2026, 10, 8, 17, 27, 14, tzinfo=timezone.utc)
        ev = decode_latest({"data": {"station": {"station_id": "KLAX"},
                                     "observation": packet}}, "KLAX", -8, seen)
        self.assertIsNotNone(ev)
        self.assertEqual(ev.level_f, 77)
        self.assertEqual(ev.channel, "omo_floor")
        self.assertEqual((ev.seen_ts - ev.obs_ts).total_seconds(), 134)

    def test_requires_minimum_interval_temperature(self):
        seen = datetime(2026, 10, 8, 17, 27, tzinfo=timezone.utc)
        packet = self.sample()
        packet.pop("temp_min_f")
        self.assertIsNone(decode_latest(
            {"data": {"station": {"station_id": "KLAX"}, "observation": packet}},
            "KLAX", -8, seen))

    def test_rejects_vendor_carried_forward_and_stale(self):
        seen = datetime(2026, 10, 8, 17, 27, tzinfo=timezone.utc)
        packet = self.sample()
        packet["is_locf"] = True
        self.assertIsNone(decode_latest(
            {"data": {"station": {"station_id": "KLAX"}, "observation": packet}},
            "KLAX", -8, seen))
        packet = self.sample("2026-10-08T16:30:00Z")
        self.assertIsNone(decode_latest(
            {"data": {"station": {"station_id": "KLAX"}, "observation": packet}},
            "KLAX", -8, seen))

    def test_websocket_event_deduplicates_preliminary_committed(self):
        q = queue.Queue(maxsize=10)
        ws = MinuteTempStream("dummy", {"KLAX": -8}, q, threading.Event())
        packet = self.sample()
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 10, 8, 17, 27, 14, tzinfo=timezone.utc)
        with patch("minutetemp.datetime", FixedDateTime):
            ws._on_message(json.dumps(packet))
            packet["persistence_status"] = "committed"
            ws._on_message(json.dumps(packet))
        self.assertEqual(q.qsize(), 1)
        self.assertTrue(q.get_nowait().detail.startswith("minutetemp-ws"))


if __name__ == "__main__":
    unittest.main()
