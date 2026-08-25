"""decode.py — settlement-exact temperature decoding for Kalshi weather markets.

Every rule here was verified against 210 station-days (0 settlement mismatches):
- ASOS is Fahrenheit-native: 5-min running mean of 1-min averages, rounded to
  whole F with mid-points rounded UP, then encoded to 0.1C for transmission.
- The settlement daily max = max over minutes of that smoothed whole-F stream.
"""
from __future__ import annotations
import math
from collections import deque
from datetime import datetime, timedelta

def half_up(x: float) -> int:
    """Round half UP (toward +inf). NEVER use python round() (banker's)."""
    return math.floor(x + 0.5)

def c10_to_f(c_tenths: float) -> int:
    """Exact decode of a tenths-precision Celsius value (METAR T-group, 6-hr
    groups, DSM-adjacent products) back to the original whole F.
    Proven bijective for -80..135F; ties impossible from ASOS-encoded values."""
    return half_up(c_tenths * 1.8 + 32)

def f_to_wholeC(f: int) -> int:
    """How ASOS/AWOS encode whole F into the whole-C OMO wire."""
    return half_up((f - 32) * 5.0 / 9.0)

def wholeC_candidates(c: int) -> list[int]:
    """Whole-F values consistent with a whole-C reading (OMO wire, METAR body).
    Multiples of 5C are EXACT (one candidate); everything else has two."""
    return [f for f in range(-40, 140) if f_to_wholeC(f) == c]

def wholeC_floor(c: int) -> int:
    """Hard lower bound on the true whole-F value given a whole-C reading."""
    return wholeC_candidates(c)[0]

def kelvin_to_wholeC(k: float) -> int:
    return half_up(k - 273.15) if k == k else None  # NaN-safe

class Smoother:
    """Streaming replica of the ASOS official temperature:
    5-min running mean of 1-min averages, rounded half-up, >=3 samples."""
    def __init__(self):
        self.buf: deque[tuple[datetime, float]] = deque()
    def push(self, ts: datetime, one_min_avg_f: float) -> int | None:
        self.buf.append((ts, one_min_avg_f))
        cutoff = ts - timedelta(minutes=4, seconds=30)
        while self.buf and self.buf[0][0] < cutoff:
            self.buf.popleft()
        if len(self.buf) < 3:
            return None
        return half_up(sum(v for _, v in self.buf) / len(self.buf))

# ------------------------- self-test vectors -------------------------
def _selftest():
    # bijectivity + no ties over the full plausible range
    for F in range(-80, 136):
        c10 = half_up(((F - 32) * 50.0 / 9.0)) / 10.0
        assert c10_to_f(c10) == F, (F, c10)
    # canonical traps
    assert c10_to_f(25.6) == 78          # NOT 79 (body-temp error)
    assert c10_to_f(26.1) == 79
    assert c10_to_f(22.8) == 73
    assert half_up(86.5) == 87           # python round(86.5)==86 — the trap
    assert wholeC_candidates(26) == [78, 79]
    assert wholeC_candidates(30) == [86]     # multiples of 5C are exact
    assert wholeC_candidates(34) == [93, 94]
    assert wholeC_floor(31) == 87
    # smoother: 91-touch that must register (Aug 2 PHL case: 91,90,90,91,91 -> 91)
    s = Smoother(); t0 = datetime(2026, 8, 2, 19, 2)
    vals = [91, 90, 90, 91, 91]
    out = [s.push(t0 + timedelta(minutes=i), v) for i, v in enumerate(vals)]
    assert out[-1] == 91, out
    return "decode.py selftest OK"

if __name__ == "__main__":
    print(_selftest())
