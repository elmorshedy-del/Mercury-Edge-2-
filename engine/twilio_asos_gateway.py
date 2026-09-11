"""Experimental Twilio transport for direct ASOS telephone OMO.

This module is intentionally NOT part of the deployed weather source-race branch.
It lives on ``feature/asos-voice-transport`` so telephony development does not
restart/contaminate the clean IAD shadow measurements.

Two transport modes are exposed:
1. Twilio Real-Time Transcription with partial results.
2. Raw Media Streams capture for a local grammar recognizer benchmark.

The existing fail-closed ``asos_voice.py`` parser is the only component allowed
to turn speech into a ProofEvent. No call is placed by this server.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Form, Request, Response, WebSocket, WebSocketDisconnect

from asos_voice import parse_voice_transcript
from proof_bus import ProofBusSender

log = logging.getLogger("twilio_asos")
HERE = Path(__file__).resolve().parent
CFG = json.load(open(HERE / "config.json"))
BY_ICAO = {c["icao"]: c for c in CFG["cities"].values()}

app = FastAPI(title="Mercury ASOS Voice Gateway")
BUS = ProofBusSender()
_TRANSCRIPTS: dict[str, deque[tuple[float, str]]] = defaultdict(lambda: deque(maxlen=16))
_LOCK = threading.RLock()


def _public_base(request: Request) -> str:
    configured = os.getenv("MERCURY_VOICE_PUBLIC_BASE", "").rstrip("/")
    return configured or str(request.base_url).rstrip("/")


def _escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace('"', "&quot;")
             .replace("<", "&lt;").replace(">", "&gt;"))


def _candidate_text(call_sid: str, newest: str) -> list[str]:
    now = time.monotonic()
    with _LOCK:
        q = _TRANSCRIPTS[call_sid]
        q.append((now, newest.strip()))
        while q and now - q[0][0] > 45:
            q.popleft()
        recent = [t for _, t in q if t]
    texts = [newest.strip()]
    for n in range(2, min(8, len(recent)) + 1):
        texts.append(" ".join(recent[-n:]))
    return list(dict.fromkeys(x for x in texts if x))


def _emit_if_valid(icao: str, call_sid: str, transcript: str,
                   received_ts: datetime) -> dict:
    cfg = BY_ICAO.get(icao)
    if not cfg:
        return {"accepted": False, "reason": "unknown_station"}
    for candidate in _candidate_text(call_sid, transcript):
        ev = parse_voice_transcript(
            icao, int(cfg["lst_offset_h"]), candidate,
            seen_ts=received_ts,
            max_age_s=float(os.getenv("MERCURY_VOICE_MAX_AGE_S", "150")),
        )
        if ev is not None:
            try:
                BUS.send(ev)
            except Exception as exc:
                log.warning("proof bus send failed: %s", exc)
                return {"accepted": False, "reason": "proof_bus_unavailable"}
            return {
                "accepted": True,
                "station": icao,
                "level_f": ev.level_f,
                "obs_ts": ev.obs_ts.isoformat() if ev.obs_ts else None,
                "seen_ts": ev.seen_ts.isoformat(),
            }
    return {"accepted": False, "reason": "no_fresh_unambiguous_proof"}


@app.get("/health")
def health():
    return {"ok": True,
            "stations": sorted(k for k, v in BY_ICAO.items() if v.get("asos_phone"))}


@app.api_route("/twilio/answer/{icao}", methods=["GET", "POST"])
async def twilio_answer(icao: str, request: Request):
    """Return TwiML that forks the remote ASOS audio into live transcription."""
    icao = icao.upper()
    if icao not in BY_ICAO or not BY_ICAO[icao].get("asos_phone"):
        return Response("unknown station", status_code=404)
    callback = _escape(f"{_public_base(request)}/twilio/transcription/{icao}")
    hints = _escape(
        "automated weather observation,temperature,celsius,zulu,zero,one,two,three,"
        "four,five,six,seven,eight,niner,minus"
    )
    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Start>
    <Transcription statusCallbackUrl="{callback}"
                   track="inbound_track"
                   partialResults="true"
                   languageCode="en-US"
                   profanityFilter="false"
                   hints="{hints}" />
  </Start>
  <Pause length="300" />
</Response>'''
    return Response(content=twiml, media_type="application/xml")


@app.post("/twilio/transcription/{icao}")
async def twilio_transcription(
    icao: str,
    CallSid: str = Form(default=""),
    Timestamp: str = Form(default=""),
    TranscriptionData: str = Form(default=""),
    TranscriptionEvent: str = Form(default=""),
    Stability: str = Form(default=""),
):
    try:
        payload = json.loads(TranscriptionData or "{}")
    except json.JSONDecodeError:
        payload = {}
    transcript = str(payload.get("transcript") or payload.get("text") or "").strip()
    now = datetime.now(timezone.utc)
    out = _emit_if_valid(icao.upper(), CallSid or "unknown", transcript, now)
    out.update({"event": TranscriptionEvent, "stability": Stability or None,
                "received_ts": now.isoformat(), "provider_ts": Timestamp or None})
    return out


@app.websocket("/twilio/media/{icao}")
async def twilio_media(icao: str, ws: WebSocket):
    """Capture Twilio's raw 8-kHz mu-law stream for local-ASR benchmarking."""
    icao = icao.upper()
    if icao not in BY_ICAO:
        await ws.close(code=1008)
        return
    await ws.accept()
    fifo = os.getenv("MERCURY_VOICE_RAW_FIFO", "")
    fh = None
    if fifo:
        try:
            fh = open(fifo.format(icao=icao), "ab", buffering=0)
        except Exception as exc:
            log.warning("raw fifo open failed: %s", exc)
    try:
        async for raw in ws.iter_text():
            try:
                obj = json.loads(raw)
            except Exception:
                continue
            if obj.get("event") != "media":
                continue
            payload = obj.get("media", {}).get("payload")
            if not payload:
                continue
            received_ns = time.time_ns()
            try:
                audio = base64.b64decode(payload)
            except Exception:
                continue
            if fh:
                fh.write(received_ns.to_bytes(8, "big") + len(audio).to_bytes(4, "big") + audio)
    except WebSocketDisconnect:
        pass
    finally:
        if fh:
            fh.close()
