"""Local zero-poll push bus for external weather decoders.

LDM pqact decoders, FAA CSS-Wx/JMS adapters, or other privileged feed processes
can normalize their observation into a ProofEvent and send one UNIX datagram to
the race process. This keeps provider-specific runtimes outside the trading
critical path while avoiding disk/database polling.
"""
from __future__ import annotations

import json
import os
import socket
import threading
from datetime import datetime, date as Date
from pathlib import Path
from typing import Callable

from feeds import ProofEvent

DEFAULT_SOCKET = os.getenv("MERCURY_PROOF_SOCKET", "/tmp/mercury-proof.sock")


def event_to_dict(ev: ProofEvent) -> dict:
    return {
        "station": ev.station,
        "climate_date": ev.climate_date.isoformat(),
        "level_f": ev.level_f,
        "channel": ev.channel,
        "obs_ts": ev.obs_ts.isoformat() if ev.obs_ts else None,
        "seen_ts": ev.seen_ts.isoformat(),
        "detail": ev.detail,
    }


def dict_to_event(d: dict) -> ProofEvent:
    return ProofEvent(
        station=str(d["station"]),
        climate_date=Date.fromisoformat(d["climate_date"]),
        level_f=int(d["level_f"]),
        channel=str(d["channel"]),
        obs_ts=datetime.fromisoformat(d["obs_ts"]) if d.get("obs_ts") else None,
        seen_ts=datetime.fromisoformat(d["seen_ts"]),
        detail=str(d.get("detail", "")),
    )


def send_proof(ev: ProofEvent, path: str = DEFAULT_SOCKET) -> None:
    payload = json.dumps(event_to_dict(ev), separators=(",", ":")).encode()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sock.sendto(payload, path)
    finally:
        sock.close()


class ProofBusReceiver:
    def __init__(self, sink: Callable[[ProofEvent], None], stop: threading.Event,
                 path: str = DEFAULT_SOCKET):
        self.sink, self.stop, self.path = sink, stop, path
        self.sock: socket.socket | None = None

    def run(self) -> None:
        p = Path(self.path)
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock = sock
        sock.bind(self.path)
        sock.settimeout(0.5)
        try:
            while not self.stop.is_set():
                try:
                    raw = sock.recv(65535)
                except socket.timeout:
                    continue
                ev = dict_to_event(json.loads(raw))
                self.sink(ev)
        finally:
            sock.close()
            self.sock = None
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
