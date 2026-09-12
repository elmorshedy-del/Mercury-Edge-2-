from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
sys.path.insert(0, str(ROOT / "research"))

from direct_sources import AviationWeatherBatchWorker  # noqa: E402
from faa_csswx_bridge import decode_csswx_message  # noqa: E402
from kalshi_fix import SOH, encode_fix, parse_fix, split_fix_messages  # noqa: E402
from nwws_bus import parse_nwws_product  # noqa: E402
from source_scoreboard import summarize  # noqa: E402


class DummyStop:
    def is_set(self):
        return False

    def wait(self, _):
        return False


CFG = {
    "cities": {
        "PHL": {"icao": "KPHL", "lst_offset_h": -5},
        "MIA": {"icao": "KMIA", "lst_offset_h": -5},
    }
}


class AviationWeatherBatchTests(unittest.TestCase):
    def test_batch_parses_multiple_stations(self):
        got = []
        w = AviationWeatherBatchWorker(CFG, got.append, DummyStop())
        seen = datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc)
        text = (
            "KPHL 111754Z 18005KT 10SM CLR 25/10 A3000 RMK AO2 T02500100\n"
            "SPECI KMIA 111755Z 09008KT 10SM FEW030 30/20 A2998 RMK AO2 T03000200\n"
        )
        n = w._handle_text(text, seen, "http=10.0ms")
        self.assertEqual(n, 2)
        self.assertEqual({x.station for x in got}, {"KPHL", "KMIA"})
        self.assertEqual({x.channel for x in got}, {"metar"})

    def test_batch_cadence_cannot_exceed_60_per_minute(self):
        old = os.environ.get("MERCURY_AWC_BATCH_POLL_S")
        os.environ["MERCURY_AWC_BATCH_POLL_S"] = "0.01"
        try:
            w = AviationWeatherBatchWorker(CFG, lambda _: None, DummyStop())
            self.assertGreaterEqual(w.interval_s, 1.0)
        finally:
            if old is None:
                os.environ.pop("MERCURY_AWC_BATCH_POLL_S", None)
            else:
                os.environ["MERCURY_AWC_BATCH_POLL_S"] = old


class CssWxBridgeTests(unittest.TestCase):
    def test_raw_metar_in_xml_uses_existing_actionable_decoder(self):
        xml = """
        <message>
          <stationIdentifier>KPHL</stationIdentifier>
          <rawText>KPHL 111753Z 18005KT 10SM CLR 20/10 A3000 RMK AO2 T02000100 10222</rawText>
        </message>
        """
        seen = datetime(2026, 9, 11, 17, 54, tzinfo=timezone.utc)
        evs = decode_csswx_message(xml, seen)
        self.assertIn("metar", {e.channel for e in evs})
        self.assertTrue(all(e.detail.startswith("faa-csswx-metar") for e in evs))

    def test_omo_is_measurement_only_not_actionable(self):
        xml = """
        <omo>
          <stationIdentifier>KPHL</stationIdentifier>
          <observationTime>2026-09-11T17:53:00Z</observationTime>
          <airTemperature uom="Cel">25</airTemperature>
        </omo>
        """
        seen = datetime(2026, 9, 11, 17, 53, 5, tzinfo=timezone.utc)
        evs = decode_csswx_message(xml, seen)
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0].channel, "faa_omo_candidate")
        self.assertNotEqual(evs[0].channel, "omo_floor")
        self.assertEqual(evs[0].obs_ts, datetime(2026, 9, 11, 17, 53, tzinfo=timezone.utc))

    def test_omo_without_explicit_units_fails_closed(self):
        xml = """
        <omo>
          <stationIdentifier>KPHL</stationIdentifier>
          <observationTime>2026-09-11T17:53:00Z</observationTime>
          <airTemperature>25</airTemperature>
        </omo>
        """
        seen = datetime(2026, 9, 11, 17, 53, 5, tzinfo=timezone.utc)
        self.assertEqual(decode_csswx_message(xml, seen), [])


class NwwsNormalizationTests(unittest.TestCase):
    def test_collective_dsm_and_metar_use_shared_decoders(self):
        seen = datetime(2026, 9, 11, 21, 16, tzinfo=timezone.utc)
        text = (
            "CDUS27 KZNY 112116\n"
            "KPHL DS 2115 11/09 821500/ /\n"
            "KPHL 112154Z 18005KT 10SM CLR 25/10 A3000 RMK AO2 T02500100\n"
        )
        evs = parse_nwws_product(text, ttaaii="CDUS27", seen_ts=seen)
        self.assertEqual({e.channel for e in evs}, {"dsm", "metar"})
        self.assertTrue(all(e.station == "KPHL" for e in evs))
        self.assertTrue(all(e.detail.startswith("nwws:CDUS27") for e in evs))

    def test_month_rollover_metar_is_resolved_by_shared_parser(self):
        seen = datetime(2026, 10, 1, 0, 2, tzinfo=timezone.utc)
        text = "KDEN 302353Z 18005KT 10SM CLR 20/10 A3000 RMK AO2 T02000100"
        evs = parse_nwws_product(text, ttaaii="SAUS", seen_ts=seen)
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0].obs_ts, datetime(2026, 9, 30, 23, 53, tzinfo=timezone.utc))


class FixCodecTests(unittest.TestCase):
    def test_fix_frame_body_length_checksum_and_stream_split(self):
        msg = encode_fix([
            (35, "0"), (34, "1"), (49, "sender"), (56, "KalshiNR"),
            (52, "20260911-17:53:00.000"),
        ])
        fields = parse_fix(msg)
        self.assertEqual(fields["8"], "FIXT.1.1")
        self.assertEqual(fields["35"], "0")
        # BodyLength is bytes after tag 9's SOH through the SOH before checksum.
        after_9 = msg.split(b"\x01", 2)[2]
        body, checksum_field = after_9.rsplit(b"10=", 1)
        self.assertEqual(int(fields["9"]), len(body))
        expected = sum(msg[:-(len(checksum_field) + 3)]) % 256
        self.assertEqual(int(fields["10"]), expected)
        frames, rest = split_fix_messages(msg + msg + b"partial")
        self.assertEqual(len(frames), 2)
        self.assertEqual(rest, b"partial")


class ScoreboardTests(unittest.TestCase):
    def test_missing_warm_flag_is_not_counted_fresh(self):
        rows = [
            {"source": "old", "station": "KPHL", "seen_ts": "x",
             "channel": "metar", "obs_to_seen_ms": 1000},
            {"source": "fresh", "station": "KPHL", "seen_ts": "x",
             "channel": "metar", "obs_to_seen_ms": 2000, "warm_start": False},
            {"source": "warm", "station": "KPHL", "seen_ts": "x",
             "channel": "metar", "obs_to_seen_ms": 3000, "warm_start": True},
        ]
        s = summarize(rows)
        self.assertEqual(len(s["METAR/SPECI + 6HR"]), 1)
        self.assertEqual(s["METAR/SPECI + 6HR"][0]["source"], "fresh")
        self.assertEqual(s["METAR/SPECI + 6HR"][0]["median_s"], 2.0)


if __name__ == "__main__":
    unittest.main()
