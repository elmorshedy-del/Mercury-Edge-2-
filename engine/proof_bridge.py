"""Authenticate/normalize NWWS climate proofs before Mercury's central engine.

NWWS XMPP credentials live only in the isolated research collector.
That collector POSTs validated *same-day* DSM/CLI evidence signed by a shared
HMAC secret; no API call or username/password is ever stored in the repository.
This module performs no trading and has no network calls.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import time
from datetime import datetime, timedelta, timezone

from feeds import ProofEvent

UTC=timezone.utc
STATION=re.compile(r"^K[A-Z0-9]{3}$")
AWIPS=re.compile(r"^(DSM|CLI)[A-Z0-9]{3}$")
HEX_SHA256=re.compile(r"^[0-9a-f]{64}$")


class InvalidProof(ValueError):
    pass


def _iso(v):
    if not isinstance(v,str) or len(v)>44:
        raise InvalidProof("invalid_timestamp")
    try:
        dt=datetime.fromisoformat(v.replace("Z","+00:00"))
    except ValueError as exc:
        raise InvalidProof("invalid_timestamp") from exc
    if dt.tzinfo is None:
        raise InvalidProof("timezone_required")
    return dt.astimezone(UTC)


def signature(secret: str, timestamp: str, body: bytes):
    return hmac.new(secret.encode("utf-8"),
                    timestamp.encode("ascii")+b"."+body,
                    hashlib.sha256).hexdigest()


def verify_and_decode(raw: bytes, headers: dict, secret: str,
                      stations: dict[str,int], now=None):
    """Return trustworthy channel-neutral ProofEvent or raise InvalidProof.

    Caller separately checks deployment feature flags and queues the proof
    to the bot's one engine thread; never execute KillEngine in HTTP context.
    """
    if not secret or len(secret)<32:
        raise InvalidProof("bridge_not_configured")
    if len(raw)>8192:
        raise InvalidProof("body_too_large")
    stamp=headers.get("x-nwws-time","")
    mac=headers.get("x-nwws-signature","")
    if (not isinstance(stamp,str) or not stamp.isascii() or
            not stamp.isdigit() or len(stamp)>15 or
            not isinstance(mac,str) or not HEX_SHA256.fullmatch(mac)):
        raise InvalidProof("invalid_auth_headers")
    moment=datetime.now(UTC) if now is None else now
    if abs(moment.timestamp()-int(stamp))>75:
        raise InvalidProof("signature_stale")
    if not hmac.compare_digest(signature(secret,stamp,raw),mac):
        raise InvalidProof("bad_signature")
    try:
        obj=json.loads(raw)
    except (ValueError,UnicodeError) as exc:
        raise InvalidProof("invalid_json") from exc
    if not isinstance(obj,dict):
        raise InvalidProof("not_an_object")
    # Only the accredited NWWS XMPP collector is eligible for this endpoint.
    if obj.get("source")!="nwws-oi":
        raise InvalidProof("untrusted_provider")
    station=obj.get("station")
    if station not in stations or not STATION.fullmatch(station):
        raise InvalidProof("station_not_configured")
    kind=obj.get("kind")
    if kind not in ("DSM","CLI"):
        raise InvalidProof("unsupported_channel")
    awips=obj.get("awipsid")
    if not isinstance(awips,str) or not AWIPS.fullmatch(awips) or not awips.startswith(kind):
        raise InvalidProof("invalid_awips")
    key=obj.get("report_key")
    if not isinstance(key,str) or len(key)>120 or awips not in key:
        raise InvalidProof("invalid_bulletin_identity")
    value=obj.get("max_f")
    if type(value) is not int or not (-40<=value<=135):
        raise InvalidProof("invalid_temperature")
    day=obj.get("climate_date")
    if not isinstance(day,str) or len(day)!=10:
        raise InvalidProof("invalid_climate_date")
    try:
        report_date=datetime.strptime(day,"%Y-%m-%d").date()
    except ValueError as exc:
        raise InvalidProof("invalid_climate_date") from exc
    seen=_iso(obj.get("first_seen_utc"))
    issued=_iso(obj.get("issue_utc"))
    if not (-10<=(moment-seen).total_seconds()<=240):
        raise InvalidProof("report_not_fresh")
    if not (-10<=(seen-issued).total_seconds()<=900):
        raise InvalidProof("publication_lag_unreasonable")
    today=(moment+timedelta(hours=stations[station])).date()
    if report_date!=today:
        raise InvalidProof("not_current_climate_date")
    maximum_at=obj.get("max_time_lst")
    if kind=="DSM":
        if (not isinstance(maximum_at,str) or len(maximum_at)!=4 or
                not maximum_at.isdigit() or int(maximum_at[:2])>23 or
                int(maximum_at[2:])>59):
            raise InvalidProof("invalid_dsm_max_time")
    elif maximum_at is not None:
        raise InvalidProof("unexpected_cli_time")
    detail=f"nwws-oi {kind} {key} max={value}F"+(
        f" @{maximum_at} LST" if kind=="DSM" else "")
    return ProofEvent(
        station=station,climate_date=report_date,level_f=value,
        channel=kind.lower(),obs_ts=None,seen_ts=seen,
        detail=detail,source="nwws-oi")
