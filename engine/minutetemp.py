"""Optional minuteTemp one-minute ASOS source for Mercury's elimination bot.

Supply MT_KEY in Mercury's Railway service variables. Do not query when no
key is present. Always use the lower *uncertainty bound* for elimination
rather than the displayed reconstructed Fahrenheit point estimate.
"""
from __future__ import annotations

import json
import logging
import math
import os
import urllib.request
from datetime import date as Date, datetime, timedelta, timezone

from feeds import ProofEvent

log = logging.getLogger("minutetemp")
BASE = "https://api.minutetemp.com/api/v1/stations/{icao}/observations/latest"


def _parse_time(value):
    if isinstance(value, (int, float)):
        # Support documented or future Unix epoch timestamps; reject milliseconds
        if not (1_000_000_000 <= float(value) <= 4_000_000_000):
            return None
        return datetime.fromtimestamp(value, timezone.utc)
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def decode_latest(payload: dict, icao: str, lst_offset_h: int, seen: datetime):
    """Fail closed without station, precise observation time, or temp_min_f."""
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    obs = data.get("observation")
    if not isinstance(obs, dict) or obs.get("is_locf") is True:
        return None
    st = data.get("station")
    station = obs.get("station_id")
    if not station and isinstance(st, dict):
        station = st.get("station_id")
    if str(station).upper() != icao:
        return None
    observed = None
    for name in ("observation_time", "observed_at", "obs_ts", "timestamp",
                 "time", "valid_time", "observed_time", "datetime"):
        observed = _parse_time(obs.get(name))
        if observed:
            break
    if observed is None:
        return None
    age_s = (seen - observed).total_seconds()
    if not (-120 <= age_s <= 20 * 60):
        return None
    minimum = obs.get("temp_min_f")
    if isinstance(minimum, bool) or not isinstance(minimum, (int, float)):
        return None
    if not math.isfinite(minimum) or not (-80 <= minimum <= 140):
        return None
    temperature = obs.get("temperature_f")
    if (temperature is not None and isinstance(temperature, (int, float))
        and math.isfinite(temperature) and minimum > temperature + 0.1):
        return None
    # The minimum of the vendor's precision envelope is a lower bound on
    # possible true F; flooring cannot overstate an observed whole-F maximum.
    return ProofEvent(icao, (observed + timedelta(hours=lst_offset_h)).date(),
                      math.floor(minimum), "omo_floor", observed, seen,
                      detail=f"minutetemp-rest lower={minimum:.2f}F obs={observed.isoformat()}",
                      source="minutetemp-rest")



def decode_dsm_station_report(msg: dict, offsets: dict[str, int], seen: datetime):
    """Only accept fresh, whole-F, exact-station same-day DSM official reports.

    Important: this is the vendor's *reported* maximum, not an observation
    precision envelope. Decode into the existing provider-agnostic DSM channel.
    """
    if msg.get("type") != "station_report" or msg.get("report_type") != "dsm":
        return None
    station = msg.get("station_id")
    if station not in offsets:
        return None
    try:
        climate_date = Date.fromisoformat(msg.get("report_date", ""))
    except (TypeError, ValueError):
        return None
    offset = offsets[station]
    if climate_date != (seen + timedelta(hours=offset)).date():
        return None
    issued = _parse_time(msg.get("wmo_emit_time") or msg.get("issuance_time"))
    observed = _parse_time(msg.get("max_temp_time_utc"))
    if issued is None or observed is None:
        return None
    if not (-120 <= (seen - issued).total_seconds() <= 3600):
        return None
    if observed > seen + timedelta(minutes=2):
        return None
    if (observed + timedelta(hours=offset)).date() != climate_date:
        return None
    value = msg.get("max_temp_f")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or not (-40 <= value <= 135):
        return None
    if abs(value - round(value)) > 0.000001:
        return None
    report_key = str(msg.get("report_id") or "")[:70]
    published = str(msg.get("live_published_at") or "")[:40]
    detail = (f"minutetemp-ws DSM {station} report={report_key} "
              f"issued={issued.isoformat()} published={published} "
              f"max={int(round(value))}F")
    return ProofEvent(station, climate_date, int(round(value)), "dsm",
                      observed, seen, detail=detail, source="minutetemp-ws")


class MinuteTempFeed:
    def __init__(self, icao: str, lst_offset_h: int, api_key: str):
        self.icao = icao
        self.lst = lst_offset_h
        self.api_key = api_key
        self._seen = set()

    def poll(self) -> list[ProofEvent]:
        req = urllib.request.Request(
            BASE.format(icao=self.icao),
            headers={"X-API-Key": self.api_key, "User-Agent": "MercuryEdge2/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                raw = json.loads(response.read(100000))
            seen = datetime.now(timezone.utc)
            ev = decode_latest(raw, self.icao, self.lst, seen)
        except Exception as exc:
            # Deliberately never include req headers or API key in logs.
            log.warning("minuteTemp %s request/decode failed: %s", self.icao, type(exc).__name__)
            return []
        if ev is None:
            return []
        key = (ev.obs_ts, ev.level_f)
        if key in self._seen:
            return []
        self._seen.add(key)
        if len(self._seen) > 1000:
            self._seen = {key}
        return [ev]


class MinuteTempStream:
    """Push the earliest vendor observation into a bounded queue.

    Calls no trading code from WebSocket threads. REST source is a fallback and
    covers any stations not included in Starter's 6-city WS subscription cap.
    """
    def __init__(self, api_key: str, station_offsets: dict[str, int], out_queue, stop):
        self.api_key = api_key
        self.station_offsets = station_offsets
        self.out_queue = out_queue
        self.stop = stop
        self._seen: set[tuple[str, datetime, int]] = set()

    def _ticket(self):
        req = urllib.request.Request(
            "https://api.minutetemp.com/api/v1/ws-ticket",
            method="POST", data=b"",
            headers={"X-API-Key": self.api_key, "User-Agent": "MercuryEdge2/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            payload = json.loads(response.read(10000))
        return payload["data"]["ticket"]

    def _slugs(self):
        req = urllib.request.Request(
            "https://api.minutetemp.com/api/v1/cities",
            headers={"X-API-Key": self.api_key, "User-Agent": "MercuryEdge2/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            payload = json.loads(response.read(200000))
        # Reserve the sixth subscription for the independent KLAX shadow.
        # Prioritize KLAX and KNYC DSM push in Mercury's five slots.
        # MIA and MDW retain independent REST / other feed coverage.
        want = ["KLAX", "KNYC", "KDEN", "KPHL", "KAUS", "KMIA", "KMDW"]
        found = {}
        for city in payload.get("data", []):
            slug = city.get("slug")
            for station in city.get("stations", []):
                sid = station.get("station_id")
                if sid in self.station_offsets and slug:
                    found[sid] = slug
        # Hard cap: five Mercury subscriptions, one reserved for shadow.
        selected = list(dict.fromkeys(found[s] for s in want if s in found))[:5]
        log.info("minuteTemp WS allocation: %d active city subscriptions", len(selected))
        return selected

    def _on_message(self, raw):
        try:
            msg = json.loads(raw)
            if msg.get("type") == "subscribed":
                accepted = msg.get("accepted", {})
                rejected = msg.get("rejected", [])
                log.warning("minuteTemp WS subscription response accepted=%s rejected=%s",
                            json.dumps(accepted)[:500], json.dumps(rejected)[:500])
                return
            if msg.get("type") == "station_report":
                ev = decode_dsm_station_report(
                    msg, self.station_offsets, datetime.now(timezone.utc))
                if ev is None:
                    return
                key = ("dsm", ev.station, msg.get("report_id"),
                       msg.get("report_revision"), ev.level_f)
                if key in self._seen:
                    return
                self._seen.add(key)
                if len(self._seen) > 5000:
                    self._seen = {key}
                self.out_queue.put_nowait(ev)
                log.info("minuteTemp DSM queued station=%s max=%sF issued=%s seen=%s",
                         ev.station, ev.level_f, msg.get("wmo_emit_time"),
                         ev.seen_ts.isoformat())
                return
            if msg.get("type") != "observation":
                return
            station = msg.get("station_id")
            if station not in self.station_offsets:
                return
            seen = datetime.now(timezone.utc)
            ev = decode_latest(
                {"data": {"station": {"station_id": station}, "observation": msg}},
                station, self.station_offsets[station], seen)
            if ev is None:
                return
            key = (ev.station, ev.obs_ts, ev.level_f)
            if key in self._seen:
                return
            self._seen.add(key)
            if len(self._seen) > 5000:
                self._seen = {key}
            ev = ProofEvent(
                ev.station, ev.climate_date, ev.level_f, ev.channel,
                ev.obs_ts, ev.seen_ts, ev.detail.replace("minutetemp-rest", "minutetemp-ws"),
                source="minutetemp-ws")
            self.out_queue.put_nowait(ev)
        except Exception as exc:
            if type(exc).__name__ != "Full":
                log.warning("minuteTemp observation discarded: %s", type(exc).__name__)

    def run(self):
        try:
            import websocket
        except ImportError:
            log.error("websocket-client package missing; minuteTemp stream disabled")
            return
        backoff = 3
        while not self.stop.is_set():
            try:
                slugs = self._slugs()
                if not slugs:
                    raise RuntimeError("no supported city slugs")
                ticket = self._ticket()
                stream = websocket.WebSocketApp(
                    "wss://api.minutetemp.com/ws/api/1m",
                    subprotocols=["bearer", ticket],
                    on_open=lambda ws: ws.send(json.dumps({
                        "type": "subscribe", "cities": slugs})),
                    on_message=lambda ws, message: self._on_message(message),
                    on_error=lambda ws, error: log.warning(
                        "minuteTemp websocket error: %s", type(error).__name__),
                    on_close=lambda ws, code, reason: log.warning(
                        "minuteTemp WS closed code=%s", code),
                )
                log.info("minuteTemp WS connecting: %d cities", len(slugs))
                stream.run_forever(ping_interval=30, ping_timeout=10)
                backoff = 3
            except Exception as exc:
                log.warning("minuteTemp WS reconnect: %s", type(exc).__name__)
                backoff = min(60, backoff * 2)
            self.stop.wait(backoff)
