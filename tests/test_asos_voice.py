from __future__ import annotations

import unittest
from datetime import datetime, timezone

from asos_voice import parse_voice_transcript


class AsosVoiceTests(unittest.TestCase):
    def test_fresh_voice_temperature_produces_whole_c_floor(self):
        seen = datetime(2026, 9, 11, 20, 31, 22, tzinfo=timezone.utc)
        text = (
            "Austin Bergstrom International Airport automated weather observation "
            "two zero three one zulu wind one seven zero at zero eight visibility one zero "
            "sky condition clear temperature three one celsius dew point two two celsius "
            "altimeter three zero zero four"
        )
        ev = parse_voice_transcript("KAUS", -6, text, seen_ts=seen)
        self.assertIsNotNone(ev)
        self.assertEqual(ev.channel, "omo_floor")
        self.assertEqual(ev.obs_ts, datetime(2026, 9, 11, 20, 31, tzinfo=timezone.utc))
        # Whole 31C is consistent with 87/88F; 87F is the safe hard floor.
        self.assertEqual(ev.level_f, 87)

    def test_stale_towered_metar_voice_is_not_latency_actionable(self):
        seen = datetime(2026, 9, 11, 20, 31, 22, tzinfo=timezone.utc)
        text = (
            "automated weather observation one nine five three zulu "
            "temperature three one celsius dew point two two celsius"
        )
        self.assertIsNone(parse_voice_transcript("KAUS", -6, text, seen_ts=seen))

    def test_ambiguous_or_missing_timestamp_fails_closed(self):
        seen = datetime(2026, 9, 11, 20, 31, 22, tzinfo=timezone.utc)
        self.assertIsNone(parse_voice_transcript(
            "KAUS", -6,
            "automated weather observation temperature three one celsius",
            seen_ts=seen,
        ))

    def test_negative_temperature(self):
        seen = datetime(2026, 1, 11, 12, 0, 20, tzinfo=timezone.utc)
        text = (
            "automated weather observation one two zero zero zulu "
            "temperature minus one five celsius dew point minus two zero celsius"
        )
        ev = parse_voice_transcript("KDEN", -7, text, seen_ts=seen)
        self.assertIsNotNone(ev)
        self.assertLess(ev.level_f, 32)


if __name__ == "__main__":
    unittest.main()
