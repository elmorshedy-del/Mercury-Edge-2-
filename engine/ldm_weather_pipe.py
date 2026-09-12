"""Persistent Unidata-LDM PIPE decoder for Mercury weather proofs.

This process is intentionally transport-thin: pqact keeps it alive, products are
flushed into stdin, and each complete weather line is normalized through the
same decoders used by the HTTP/NWWS race.

Typical LDM actions (actual feedtype/product regex depends on the approved
upstream feed; tabs are required in pqact.conf):

    IDS|DDPLUS  ^CDUS27  PIPE  -strip -flush /usr/bin/python3 -u /app/engine/ldm_weather_pipe.py

A separate METAR/SA product pattern may point to the same persistent decoder.
Do not add ``-close``: keeping the process alive avoids interpreter startup in
the critical path.

The decoder does not infer product timestamps from LDM metadata. ``seen_ts`` is
taken immediately when the line reaches userspace; METAR observation time comes
from DDHHMMZ and DSM max semantics come from the DSM line itself.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
CFG = json.load(open(HERE / "config.json"))
BY_ICAO = {c["icao"]: c for c in CFG["cities"].values()}
METAR_LINE = re.compile(r"^(?:(?:METAR|SPECI)\s+)?(K[A-Z0-9]{3})\s+\d{6}Z\b")

from dsm_decode import parse_dsm_text  # noqa: E402
from fast_sources import parse_metar_proofs  # noqa: E402
from feeds import ProofEvent  # noqa: E402
from proof_bus import send_proof  # noqa: E402


def parse_ldm_line(text: str, seen_ts: datetime | None = None,
                   source: str = "ldm-ids") -> list[ProofEvent]:
    """Parse one line from a persistent pqact PIPE; fail closed otherwise."""
    seen = seen_ts or datetime.now(timezone.utc)
    line = text.strip()
    if not line:
        return []

    out: list[ProofEvent] = []
    # DSM parser ignores non-DS lines and stations Mercury does not trade.
    out.extend(parse_dsm_text(line, CFG["cities"], source, seen))

    m = METAR_LINE.match(line)
    if m:
        icao = m.group(1)
        city = BY_ICAO.get(icao)
        if city:
            out.extend(parse_metar_proofs(
                line, icao, int(city["lst_offset_h"]), source, seen,
            ))
    return out


def decode_stream(lines: Iterable[bytes | str]) -> Iterable[ProofEvent]:
    for raw in lines:
        if isinstance(raw, bytes):
            text = raw.decode(errors="replace")
        else:
            text = raw
        # Timestamp as close as possible to userspace receipt of this line.
        seen = datetime.now(timezone.utc)
        yield from parse_ldm_line(text, seen)


def main() -> None:
    for ev in decode_stream(sys.stdin.buffer):
        send_proof(ev)


if __name__ == "__main__":
    main()
