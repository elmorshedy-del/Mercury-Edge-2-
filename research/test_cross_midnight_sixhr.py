"""Regression for the 2026-09-15 KDEN cross-midnight six-hour proof bug.

Run from repo root:
    python3 research/test_cross_midnight_sixhr.py

This test intentionally uses the actual Sep 15 report shape that produced the
invalid Mercury paper trade. It does not call the network.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from feeds import MetarFeed


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 15, 18, 30, tzinfo=timezone.utc)


def poll_kden(raw: str):
    with patch("feeds._get", return_value=raw.encode()), patch("feeds.datetime", FixedDateTime):
        return MetarFeed("KDEN", -7).poll()


def test_cross_midnight_12z_group_is_not_hard_proof():
    # KDEN 151153Z carried 10228 = +22.8 C = 73 F six-hour maximum.
    # The nominal 06Z-12Z window is 23:00 Sep 14 through 05:00 Sep 15 MST,
    # so the 73 F occurrence cannot be assigned to Sep 15 from this group alone.
    raw = (
        "METAR KDEN 151153Z 35011KT 10SM OVC021 13/01 A3025 "
        "RMK AO2 SLP210 T01280006 10228 20128 53010"
    )
    events = poll_kden(raw)
    sixhr = [e for e in events if e.channel == "sixhr"]
    assert sixhr == [], f"cross-midnight six-hour max became hard proof: {sixhr}"


def test_same_day_18z_group_remains_hard_proof():
    # KDEN 151753Z carries the 18Z six-hour group. Its nominal 12Z-18Z
    # window is 05:00-11:00 MST, wholly inside Sep 15, so it is safe.
    raw = (
        "METAR KDEN 151753Z 12008KT 10SM FEW080 20/05 A3010 "
        "RMK AO2 SLP100 T02000050 10200 20100 53010"
    )
    events = poll_kden(raw)
    sixhr = [e for e in events if e.channel == "sixhr"]
    assert len(sixhr) == 1, sixhr
    assert sixhr[0].climate_date.isoformat() == "2026-09-15", sixhr[0]
    assert sixhr[0].level_f == 68, sixhr[0]


if __name__ == "__main__":
    test_cross_midnight_12z_group_is_not_hard_proof()
    test_same_day_18z_group_remains_hard_proof()
    print("PASS: cross-midnight six-hour proof guard")
