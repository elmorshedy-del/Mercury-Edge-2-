"""Place one experimental ASOS dial-in call through Twilio.

Secrets are read only from environment variables; nothing is persisted.
This script refuses to run unless all required settings exist.

Usage:
  PYTHONPATH=engine python research/call_asos_voice.py KPHL transcription
  PYTHONPATH=engine python research/call_asos_voice.py KPHL media
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[1]
CFG = json.load(open(ROOT / "engine" / "config.json"))
BY_ICAO = {c["icao"]: c for c in CFG["cities"].values()}


def e164_us(number: str) -> str:
    digits = re.sub(r"\D", "", number or "")
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    raise ValueError("ASOS phone must be a 10-digit US number")


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def launch(icao: str, mode: str = "transcription") -> dict:
    icao = icao.upper()
    if mode not in {"transcription", "media"}:
        raise ValueError("mode must be transcription or media")
    station = BY_ICAO.get(icao)
    if not station or not station.get("asos_phone"):
        raise ValueError(f"no configured ASOS dial-in for {icao}")

    sid = required("TWILIO_ACCOUNT_SID")
    token = required("TWILIO_AUTH_TOKEN")
    from_number = e164_us(required("TWILIO_FROM_NUMBER"))
    public_base = required("MERCURY_VOICE_PUBLIC_BASE").rstrip("/")
    if not public_base.startswith("https://"):
        raise ValueError("MERCURY_VOICE_PUBLIC_BASE must be https://")

    answer_url = f"{public_base}/twilio/answer/{quote(icao)}?mode={quote(mode)}"
    api = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
    timeout_s = float(os.getenv("MERCURY_VOICE_CALL_TIMEOUT_S", "15"))
    time_limit = int(os.getenv("MERCURY_VOICE_CALL_TIME_LIMIT_S", "120"))

    with httpx.Client(timeout=timeout_s) as client:
        response = client.post(
            api,
            auth=(sid, token),
            data={
                "To": e164_us(station["asos_phone"]),
                "From": from_number,
                "Url": answer_url,
                "Method": "POST",
                "TimeLimit": str(time_limit),
            },
        )
    response.raise_for_status()
    data = response.json()
    # Return only non-secret diagnostics.
    return {
        "sid": data.get("sid"),
        "status": data.get("status"),
        "station": icao,
        "mode": mode,
        "to": e164_us(station["asos_phone"]),
        "answer_url": answer_url,
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: call_asos_voice.py ICAO [transcription|media]")
    print(json.dumps(launch(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "transcription"), indent=2))


if __name__ == "__main__":
    main()
