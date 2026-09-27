"""Cost-capped Twilio ASOS shadow dialer.

The budget is reserved on disk before dialing, so service restarts cannot create
an unbounded call loop. This module never enables trading.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

log = logging.getLogger("twilio_shadow")


def _e164(number: str) -> str:
    digits = re.sub(r"\D", "", number or "")
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    raise ValueError("phone must be a US E.164-compatible number")


def _ledger_path() -> Path:
    return Path(os.getenv("MERCURY_VOICE_BUDGET_LEDGER", "/data/twilio_shadow_budget.json"))


def _reserve(station: str, seconds: int, cap_seconds: int) -> tuple[bool, dict]:
    path = _ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        data = {}
    if data.get("date") != today:
        data = {"date": today, "reserved_seconds": 0, "calls": []}
    used = int(data.get("reserved_seconds", 0))
    if used + seconds > cap_seconds:
        return False, data
    data["reserved_seconds"] = used + seconds
    data.setdefault("calls", []).append({
        "station": station,
        "reserved_seconds": seconds,
        "reserved_ts": datetime.now(timezone.utc).isoformat(),
    })
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return True, data


async def launch_shadow_calls(by_icao: dict[str, dict], public_base: str) -> None:
    if os.getenv("MERCURY_VOICE_AUTOCALL", "0").lower() not in {"1", "true", "yes"}:
        return
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    if not (account_sid and auth_token and from_number):
        log.warning("Twilio autocall armed but credentials are incomplete; no call placed")
        return

    stations = [x.strip().upper() for x in os.getenv(
        "MERCURY_VOICE_AUTOCALL_STATIONS", "KDEN"
    ).split(",") if x.strip()]
    per_call = max(30, min(600, int(os.getenv("MERCURY_VOICE_CALL_TIME_LIMIT_S", "300"))))
    daily_cap = max(per_call, int(os.getenv("MERCURY_VOICE_DAILY_CAP_S", "600")))
    mode = os.getenv("MERCURY_VOICE_CALL_MODE", "transcription").strip().lower()
    if mode not in {"transcription", "media"}:
        mode = "transcription"

    api = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls.json"
    async with httpx.AsyncClient(timeout=20.0) as client:
        for icao in stations:
            cfg = by_icao.get(icao)
            if not cfg or not cfg.get("asos_phone"):
                log.warning("Skipping %s: no working ASOS phone configured", icao)
                continue
            ok, ledger = await asyncio.to_thread(_reserve, icao, per_call, daily_cap)
            if not ok:
                log.info("Twilio daily shadow cap reached: %ss reserved", ledger.get("reserved_seconds", 0))
                break
            answer_url = f"{public_base.rstrip('/')}/twilio/answer/{icao}?mode={mode}"
            status_url = f"{public_base.rstrip('/')}/twilio/status/{icao}"
            try:
                response = await client.post(
                    api,
                    auth=(account_sid, auth_token),
                    data={
                        "To": _e164(cfg["asos_phone"]),
                        "From": _e164(from_number),
                        "Url": answer_url,
                        "Method": "POST",
                        "TimeLimit": str(per_call),
                        "Timeout": "15",
                        "StatusCallback": status_url,
                        "StatusCallbackMethod": "POST",
                        "StatusCallbackEvent": "initiated ringing answered completed",
                    },
                )
                response.raise_for_status()
                body = response.json()
                log.info("Twilio shadow call placed station=%s sid=%s status=%s cap=%ss",
                         icao, body.get("sid"), body.get("status"), daily_cap)
            except Exception as exc:
                # Reservation is intentionally not refunded: fail-safe favors underspend.
                log.error("Twilio shadow call failed station=%s error=%s", icao, exc)
            await asyncio.sleep(2)
