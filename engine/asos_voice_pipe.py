"""Read ASOS voice transcripts as JSON-lines and inject fresh proofs.

Transport-neutral on purpose. Any SIP/PSTN provider can stream/transcribe calls
and write records such as:

  {"icao":"KLAX","transcript":"... automated weather observation ..."}

The parser is fail-closed; stale or ambiguous messages produce no ProofEvent.
This process never places orders itself.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.load(open(HERE / "config.json"))
BY_ICAO = {c["icao"]: c for c in CFG["cities"].values()}

from asos_voice import parse_voice_transcript  # noqa: E402
from proof_bus import ProofBusSender  # noqa: E402


def _dt(value):
    if not value:
        return datetime.now(timezone.utc)
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def main() -> None:
    sender = ProofBusSender()
    for raw in sys.stdin:
        try:
            obj = json.loads(raw)
            icao = str(obj["icao"]).upper()
            cfg = BY_ICAO[icao]
            ev = parse_voice_transcript(
                icao,
                int(cfg["lst_offset_h"]),
                str(obj["transcript"]),
                seen_ts=_dt(obj.get("received_ts")),
            )
            if ev is not None:
                sender.send(ev)
                print(json.dumps({"accepted": True, "icao": icao,
                                  "level_f": ev.level_f,
                                  "obs_ts": ev.obs_ts.isoformat()}), flush=True)
            else:
                print(json.dumps({"accepted": False, "icao": icao}), flush=True)
        except Exception as exc:
            print(json.dumps({"accepted": False, "error": f"{type(exc).__name__}: {exc}"}),
                  flush=True)


if __name__ == "__main__":
    main()
