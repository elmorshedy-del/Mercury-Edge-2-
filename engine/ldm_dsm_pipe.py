"""Persistent Unidata-LDM pqact decoder for DSM collectives.

Recommended pqact action (tabs required in real pqact.conf):

    IDS|DDPLUS  ^CDUS27  PIPE  -strip -flush /usr/bin/python3 -u /app/engine/ldm_dsm_pipe.py

Do NOT use -close: pqact then keeps this decoder process/pipe open and flushes
new products into it, avoiding process startup on every DSM. The decoder scans
DSM lines and sends normalized ProofEvents to the local UNIX proof bus.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.load(open(HERE / "config.json"))

from dsm_decode import parse_dsm_text  # noqa: E402
from proof_bus import send_proof  # noqa: E402


def main() -> None:
    # pqact writes a stream and flushes each product. Reading line-by-line is
    # sufficient because the settlement line itself carries station/date/max.
    for raw in sys.stdin.buffer:
        text = raw.decode(errors="replace")
        now = datetime.now(timezone.utc)
        for ev in parse_dsm_text(text, CFG["cities"], "iem-ldm", now):
            send_proof(ev)


if __name__ == "__main__":
    main()
