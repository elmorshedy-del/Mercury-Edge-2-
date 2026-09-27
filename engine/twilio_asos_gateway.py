"""Experimental Twilio transport for direct ASOS telephone OMO.

Shadow-only gateway: valid voice proofs and source-latency observations are
written to JSONL. Trading remains disabled when MERCURY_VOICE_REQUIRE_BUS=0.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

from fastapi import FastAPI, Form, Request, Response, WebSocket, WebSocketDisconnect

from asos_voice import parse_voice_transcript
from proof_bus import send_proof
from synoptic_shadow import run_synoptic_shadow
from twilio_shadow import launch_shadow_calls

log = logging.getLogger("twilio_asos")
HERE = Path(__file__).resolve().parent
CFG = json.load(open(HERE / "config.json"))
BY_ICAO = {c["icao"]: c for c in CFG["cities"].values()}
app = FastAPI(title="Mercury ASOS Voice Gateway")
_TRANSCRIPTS: dict[str, deque[tuple[float, str]]] = defaultdict(lambda: deque(maxlen=16))
_LOCK = threading.RLock()


def _public_base(request: Request | None = None) -> str:
    configured = os.getenv("MERCURY_VOICE_PUBLIC_BASE", "").rstrip("/")
    if configured:
        return configured
    if request is None:
        return ""
    return str(request.base_url).rstrip("/")


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def _ws_base(http_base: str) -> str:
    p = urlparse(http_base)
    return f"{'wss' if p.scheme == 'https' else 'ws'}://{p.netloc}{p.path.rstrip('/')}"


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


def _write_shadow(record: dict) -> None:
    path = os.getenv("MERCURY_VOICE_LOG", "").strip()
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")


def _emit_if_valid(icao: str, call_sid: str, transcript: str, received_ts: datetime) -> dict:
    cfg = BY_ICAO.get(icao)
    if not cfg:
        return {"accepted": False, "reason": "unknown_station"}
    for candidate in _candidate_text(call_sid, transcript):
        ev = parse_voice_transcript(
            icao, int(cfg["lst_offset_h"]), candidate, seen_ts=received_ts,
            max_age_s=float(os.getenv("MERCURY_VOICE_MAX_AGE_S", "150")),
        )
        if ev is None:
            continue
        record = {
            "received_ts": received_ts.isoformat(), "station": icao,
            "level_f": ev.level_f,
            "obs_ts": ev.obs_ts.isoformat() if ev.obs_ts else None,
            "obs_to_seen_ms": ((received_ts - ev.obs_ts).total_seconds() * 1000 if ev.obs_ts else None),
            "call_sid": call_sid, "source": "asos-voice",
        }
        _write_shadow(record)
        bus_sent = True
        try:
            send_proof(ev)
        except Exception as exc:
            bus_sent = False
            log.info("proof bus unavailable in voice shadow: %s", exc)
        require_bus = os.getenv("MERCURY_VOICE_REQUIRE_BUS", "1").lower() not in {"0", "false", "no"}
        if require_bus and not bus_sent:
            return {"accepted": False, "reason": "proof_bus_unavailable", "shadow_recorded": bool(os.getenv("MERCURY_VOICE_LOG"))}
        return {"accepted": True, "station": icao, "level_f": ev.level_f,
                "obs_ts": record["obs_ts"], "seen_ts": ev.seen_ts.isoformat(),
                "bus_sent": bus_sent, "shadow_recorded": bool(os.getenv("MERCURY_VOICE_LOG"))}
    return {"accepted": False, "reason": "no_fresh_unambiguous_proof"}


async def _delayed_shadow_start() -> None:
    await asyncio.sleep(8)
    enabled = os.getenv("MERCURY_VOICE_AUTOCALL", "0").lower() in {"1", "true", "yes"}
    log.warning("Twilio smoke startup autocall=%s", enabled)
    base = _public_base()
    if not base:
        log.warning("voice autocall disabled: MERCURY_VOICE_PUBLIC_BASE missing")
        return
    try:
        await launch_shadow_calls(BY_ICAO, base)
    except Exception as exc:
        log.exception("Twilio smoke startup failed: %s", exc)


async def _validate_twilio_auth() -> None:
    """Read-only credential check; never places a call."""
    await asyncio.sleep(3)
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    if not sid or not token:
        log.warning("Twilio auth check skipped: credentials incomplete")
        return
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json",
                auth=(sid, token),
            )
        if response.status_code == 200:
            log.warning("Twilio auth check OK; paid calling remains disabled unless autocall is enabled")
            try:
                calls = await client.get(
                    f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json",
                    auth=(sid, token),
                    params={"PageSize": "5"},
                )
                if calls.status_code == 200:
                    items = calls.json().get("calls", [])
                    for item in items[:5]:
                        log.warning(
                            "Twilio recent call sid=%s status=%s direction=%s start=%s end=%s duration=%s to=%s",
                            item.get("sid"), item.get("status"), item.get("direction"),
                            item.get("start_time"), item.get("end_time"), item.get("duration"),
                            str(item.get("to") or "")[-4:],
                        )
                else:
                    log.warning("Twilio recent-call check failed status=%s", calls.status_code)
            except Exception as exc:
                log.warning("Twilio recent-call check error: %s", str(exc)[:160])
        else:
            log.warning("Twilio auth check failed status=%s", response.status_code)
    except Exception as exc:
        log.warning("Twilio auth check error: %s", str(exc)[:160])


@app.on_event("startup")
async def start_shadow_collectors() -> None:
    # Surface persisted voice outcomes from the previous call before any new
    # collector work. This is read-only diagnostics.
    for record in _tail_jsonl(os.getenv("MERCURY_VOICE_LOG", "/data/asos_voice_shadow.jsonl"), limit=8):
        log.warning(
            "Persisted voice result source=%s station=%s level_f=%s obs_ts=%s received_ts=%s obs_to_seen_ms=%s status=%s duration_s=%s",
            record.get("source"), record.get("station"), record.get("level_f"),
            record.get("obs_ts"), record.get("received_ts"), record.get("obs_to_seen_ms"),
            record.get("status"), record.get("duration_s"),
        )
    asyncio.create_task(run_synoptic_shadow())
    asyncio.create_task(_validate_twilio_auth())
    asyncio.create_task(_delayed_shadow_start())


@app.get("/health")
def health():
    return {
        "ok": True,
        "shadow": os.getenv("MERCURY_VOICE_REQUIRE_BUS", "1") in {"0", "false", "no"},
        "stations": sorted(k for k, v in BY_ICAO.items() if v.get("asos_phone")),
        "synoptic": bool(os.getenv("SYNOPTIC_API_KEY", "").strip()),
        "twilio_autocall": os.getenv("MERCURY_VOICE_AUTOCALL", "0").lower() in {"1", "true", "yes"},
        "twilio_daily_cap_s": int(os.getenv("MERCURY_VOICE_DAILY_CAP_S", "600")),
        "trading": False,
    }


@app.api_route("/twilio/answer/{icao}", methods=["GET", "POST"])
async def twilio_answer(icao: str, request: Request, mode: str = "transcription"):
    icao = icao.upper()
    if icao not in BY_ICAO or not BY_ICAO[icao].get("asos_phone"):
        return Response("unknown station", status_code=404)
    base = _public_base(request)
    pause_s = max(30, min(600, int(os.getenv("MERCURY_VOICE_CALL_TIME_LIMIT_S", "300")))) + 5
    if mode == "media":
        stream = _escape(f"{_ws_base(base)}/twilio/media/{icao}")
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>\n<Response><Start><Stream url="{stream}" track="inbound_track" /></Start><Pause length="{pause_s}" /></Response>'''
    elif mode == "transcription":
        callback = _escape(f"{base}/twilio/transcription/{icao}")
        hints = _escape("automated weather observation,temperature,celsius,zulu,zero,one,two,three,four,five,six,seven,eight,niner,minus")
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>\n<Response><Start><Transcription statusCallbackUrl="{callback}" track="inbound_track" partialResults="true" languageCode="en-US" profanityFilter="false" hints="{hints}" /></Start><Pause length="{pause_s}" /></Response>'''
    else:
        return Response("mode must be transcription or media", status_code=400)
    return Response(content=twiml, media_type="application/xml")


@app.post("/twilio/status/{icao}")
async def twilio_status(icao: str, CallSid: str = Form(default=""), CallStatus: str = Form(default=""),
                        CallDuration: str = Form(default=""), Timestamp: str = Form(default="")):
    record = {
        "source": "twilio-status", "station": icao.upper(), "call_sid": CallSid,
        "status": CallStatus, "duration_s": int(CallDuration) if CallDuration.isdigit() else None,
        "provider_ts": Timestamp or None, "received_ts": datetime.now(timezone.utc).isoformat(),
    }
    _write_shadow(record)
    return {"ok": True}


@app.post("/twilio/transcription/{icao}")
async def twilio_transcription(icao: str, CallSid: str = Form(default=""), Timestamp: str = Form(default=""),
                               TranscriptionData: str = Form(default=""), TranscriptionEvent: str = Form(default=""),
                               Stability: str = Form(default="")):
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


def _tail_jsonl(path: str, limit: int = 8) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        lines = p.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(x) for x in lines if x.strip()]
    except Exception:
        return []


@app.get("/shadow/status")
def shadow_status():
    budget_path = Path(os.getenv("MERCURY_VOICE_BUDGET_LEDGER", "/data/twilio_shadow_budget.json"))
    try:
        budget = json.loads(budget_path.read_text(encoding="utf-8")) if budget_path.exists() else {}
    except Exception:
        budget = {}
    return {
        "trading": False,
        "voice": _tail_jsonl(os.getenv("MERCURY_VOICE_LOG", "/data/asos_voice_shadow.jsonl")),
        "synoptic": _tail_jsonl(os.getenv("SYNOPTIC_LOG", "/data/synoptic_shadow.jsonl")),
        "twilio_budget": budget,
        "twilio_auth_configured": bool(os.getenv("TWILIO_AUTH_TOKEN", "").strip()),
        "weather_source_configured": bool(os.getenv("WEATHERSOURCE_API_KEY", "").strip()),
    }


@app.websocket("/twilio/media/{icao}")
async def twilio_media(icao: str, ws: WebSocket):
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
