"""Read-only Synoptic shadow collector for Mercury.

Uses a private Synoptic API key only to obtain a public token. Prefers Push
Streaming for first-seen timestamps and independently samples Synoptic's Latency
service so observation time, Synoptic ingest delay, and Mercury receive time stay
separate.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import httpx
import websockets

log = logging.getLogger("synoptic_shadow")
_WRITE_LOCK = asyncio.Lock()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _stations() -> list[str]:
    return [x.strip().upper() for x in os.getenv(
        "SYNOPTIC_STATIONS", "KDEN1M,KLAX1M,KPHL1M"
    ).split(",") if x.strip()]


def _log_path() -> Path:
    return Path(os.getenv("SYNOPTIC_LOG", "/data/synoptic_shadow.jsonl"))


async def _write(record: dict) -> None:
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n"
    async with _WRITE_LOCK:
        await asyncio.to_thread(_append, path, line)


def _append(path: Path, line: str) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def _parse_obs_ts(value: str) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value[:-1] + "+00:00")
        if "T" in value:
            dt = datetime.fromisoformat(value)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        return None


async def _public_token(api_key: str) -> str:
    cache = Path(os.getenv("SYNOPTIC_TOKEN_CACHE", "/data/synoptic_public_token"))
    if cache.exists():
        token = cache.read_text(encoding="utf-8").strip()
        if token:
            return token
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get("https://api.synopticdata.com/auth/v2/", headers=headers)
        response.raise_for_status()
        token = str(response.json().get("TOKEN") or "").strip()
    if not token:
        raise RuntimeError("Synoptic credential API returned no TOKEN")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(token, encoding="utf-8")
    return token


async def _latency_loop(token: str) -> None:
    interval = max(60, int(os.getenv("SYNOPTIC_LATENCY_POLL_S", "300")))
    stations = ",".join(_stations())
    while True:
        now = _utcnow()
        start = now - timedelta(minutes=15)
        params = {
            "token": token,
            "stid": stations,
            "start": start.strftime("%Y%m%d%H%M"),
            "end": now.strftime("%Y%m%d%H%M"),
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    "https://api.synopticdata.com/v2/stations/latency", params=params
                )
                response.raise_for_status()
                payload = response.json()
            received = _utcnow()
            for station in payload.get("STATION", []):
                lat = station.get("LATENCY") or {}
                dates = lat.get("date_time") or []
                values = lat.get("values") or []
                for obs, minutes in list(zip(dates, values))[-5:]:
                    await _write({
                        "source": "synoptic-latency-api",
                        "station": station.get("STID"),
                        "obs_ts": obs,
                        "synoptic_latency_min": minutes,
                        "queried_ts": received.isoformat(),
                    })
        except Exception as exc:
            await _write({"source": "synoptic-latency-api", "event": "error",
                          "seen_ts": _utcnow().isoformat(), "error": str(exc)[:240]})
        await asyncio.sleep(interval)


async def _latest_loop(token: str) -> None:
    """Low-rate fallback when Push Streaming is not included in the account."""
    interval = max(15, int(os.getenv("SYNOPTIC_LATEST_POLL_S", "30")))
    seen: set[tuple[str, str]] = set()
    while True:
        params = {
            "token": token,
            "stid": ",".join(_stations()),
            "vars": "air_temp",
            "within": "15",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://api.synopticdata.com/v2/stations/latest", params=params
                )
                response.raise_for_status()
                payload = response.json()
            received = _utcnow()
            for station in payload.get("STATION", []):
                stid = str(station.get("STID") or "")
                observations = station.get("OBSERVATIONS") or {}
                for key, item in observations.items():
                    if not key.startswith("air_temp") or not isinstance(item, dict):
                        continue
                    obs_s = str(item.get("date_time") or "")
                    ident = (stid, obs_s)
                    if not obs_s or ident in seen:
                        continue
                    seen.add(ident)
                    obs = _parse_obs_ts(obs_s)
                    await _write({
                        "source": "synoptic-latest-first-seen",
                        "station": stid,
                        "obs_ts": obs_s,
                        "value_c": item.get("value"),
                        "seen_ts": received.isoformat(),
                        "obs_to_seen_ms": ((received - obs).total_seconds() * 1000 if obs else None),
                        "poll_interval_s": interval,
                    })
        except Exception as exc:
            await _write({"source": "synoptic-latest-first-seen", "event": "error",
                          "seen_ts": _utcnow().isoformat(), "error": str(exc)[:240]})
        await asyncio.sleep(interval)


async def _push_loop(token: str) -> None:
    query = urlencode({
        "stid": ",".join(_stations()),
        "vars": "air_temp",
        "units": "metric",
        "metadata": "0",
    })
    url = f"wss://push.synopticdata.com/feed/{token}/?{query}"
    while True:
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                await _write({"source": "synoptic-push", "event": "connected",
                              "seen_ts": _utcnow().isoformat(), "stations": _stations()})
                async for raw in ws:
                    received = _utcnow()
                    obj = json.loads(raw)
                    if obj.get("type") == "auth" and obj.get("status") in {
                        "invalid_token", "push_not_permitted", "no_data_available"
                    }:
                        raise PermissionError(str(obj.get("status")))
                    if obj.get("type") != "data":
                        continue
                    for item in obj.get("data", []):
                        if item.get("sensor") != "air_temp":
                            continue
                        obs_s = str(item.get("date") or "")
                        obs = _parse_obs_ts(obs_s)
                        await _write({
                            "source": "synoptic-push",
                            "station": item.get("stid"),
                            "obs_ts": obs_s,
                            "value_c": item.get("value"),
                            "qc": item.get("qc"),
                            "seen_ts": received.isoformat(),
                            "obs_to_seen_ms": ((received - obs).total_seconds() * 1000 if obs else None),
                        })
        except PermissionError:
            raise
        except Exception as exc:
            await _write({"source": "synoptic-push", "event": "reconnect",
                          "seen_ts": _utcnow().isoformat(), "error": str(exc)[:240]})
            await asyncio.sleep(5)


async def run_synoptic_shadow() -> None:
    # Public API tokens are the native credential for Synoptic data products.
    # Prefer a directly configured token; retain the private-key exchange only
    # as a backwards-compatible fallback.
    token = os.getenv("SYNOPTIC_TOKEN", "").strip()
    if not token:
        api_key = os.getenv("SYNOPTIC_API_KEY", "").strip()
        if not api_key:
            log.info("Synoptic shadow disabled: SYNOPTIC_TOKEN/SYNOPTIC_API_KEY missing")
            return
        try:
            token = await _public_token(api_key)
        except Exception as exc:
            await _write({"source": "synoptic", "event": "auth_error",
                          "seen_ts": _utcnow().isoformat(), "error": str(exc)[:240]})
            return

    latency_task = asyncio.create_task(_latency_loop(token))
    try:
        await _push_loop(token)
    except PermissionError as exc:
        await _write({"source": "synoptic-push", "event": "fallback_to_latest",
                      "seen_ts": _utcnow().isoformat(), "reason": str(exc)})
        await _latest_loop(token)
    finally:
        latency_task.cancel()
