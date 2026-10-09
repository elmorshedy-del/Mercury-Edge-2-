"""Authenticated NOAA NWWS-OI source racer. Isolated research-only Railway worker.

NWWS delivers NWS text products over XMPP; it is NOT an ASOS one-minute
OMO binary feed. Detect/report whatever aviation or climate products
actually appear. All timestamps below are first seen by OUR Railway
process, not hypothetical NOAA publication times.

Never imports Mercury's elimination engine, Kalshi client, or trades.
Run one worker only per NOAA-issued credential.
Configuration via Railway environment variables: NWWS_USER, NWWS_PASS.
Output: append-only NDJSON in NWWS_DATA_DIR (/data on attached volume),
plus compact real-time event logs prefixed NWWS_.
"""
from __future__ import annotations
import asyncio
import hashlib
import json
import logging
import os
import re
import time
from collections import Counter, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from nwws_extract import extract_evidence
from nwws_tgftp import TGFTPRacer
from nwws_iem import IEMRacer

HOST = "nwws-oi.weather.gov"
ROOM = "nwws@conference.nwws-oi.weather.gov"
STATIONS = {"KNYC", "KDEN", "KPHL", "KMDW", "KAUS", "KMIA", "KLAX"}
AWIPS = {
    "DSMNYC": "KNYC", "DSMDEN": "KDEN", "DSMPHL": "KPHL",
    "DSMMDW": "KMDW", "DSMAUS": "KAUS", "DSMMIA": "KMIA",
    "DSMLAX": "KLAX",
    "CLINYC": "KNYC", "CLIDEN": "KDEN", "CLIPHL": "KPHL",
    "CLIMDW": "KMDW", "CLIAUS": "KAUS", "CLIMIA": "KMIA",
    "CLILAX": "KLAX",
}
AIRPORT = re.compile(r"\bK(?:NYC|DEN|PHL|MDW|AUS|MIA|LAX)\b")
OBSSTAMP = re.compile(
    r"\b(K(?:NYC|DEN|PHL|MDW|AUS|MIA|LAX))\s+(\d{2})(\d{2})(\d{2})Z\b"
)
PRECISE_T = re.compile(r"\bT([01])(\d{3})([01])(\d{3})\b")
SIXHR = re.compile(r"\b1([01])(\d{3})\b")
METAR_PREFIX = ("MTR", "MET", "SPE")
CLIMATE_PREFIX = ("DSM", "CLI")
log = logging.getLogger("nwws-race")


def utcnow():
    return datetime.now(timezone.utc)


def safe_report_time(day: int, hh: int, mm: int, received: datetime):
    if not (1 <= day <= 31 and 0 <= hh < 24 and 0 <= mm < 60):
        return None
    matches = []
    # Use month-index arithmetic: subtracting 32 days from Jan 1 jumps
    # to NOVEMBER, not December, and loses year-boundary reports.
    for month_offset in (-1, 0, 1):
        absolute = received.year * 12 + received.month - 1 + month_offset
        year, zero_month = divmod(absolute, 12)
        try:
            obs = datetime(year, zero_month + 1, day, hh, mm, tzinfo=timezone.utc)
        except ValueError:
            continue
        if -600 <= (received - obs).total_seconds() <= 48 * 3600:
            matches.append(obs)
    return min(matches, key=lambda x: abs((received-x).total_seconds())) if matches else None


def analyze_product(awipsid: str, ttaaii: str, body: str,
                    received: datetime, issue: str = "", product_id: str = ""):
    """Classify observed wire data; never invent one-minute OMO availability."""
    awipsid, ttaaii = awipsid.strip().upper(), ttaaii.strip().upper()
    stations = set(AIRPORT.findall(body))
    if awipsid in AWIPS:
        stations.add(AWIPS[awipsid])

    if awipsid.startswith("DSM"):
        kind = "DSM"
    elif awipsid.startswith("CLI"):
        kind = "CLI"
    elif awipsid.startswith(METAR_PREFIX) or ttaaii.startswith(("SA", "SP")):
        kind = "METAR_OR_SPECI"
    elif "OMO" in awipsid:
        kind = "OMO_CANDIDATE_UNVERIFIED"
    else:
        kind = "OTHER"

    # If a WMO collective lacks the expected station tokens, do not attribute.
    seen_icao = []
    observations = []
    for m in OBSSTAMP.finditer(body):
        station = m.group(1)
        obs = safe_report_time(*map(int, m.groups()[1:]), received)
        if obs is None:
            continue
        line = body[m.start():body.find("\n",m.start()) if "\n" in body[m.start():] else len(body)]
        t = PRECISE_T.search(line)
        six = SIXHR.search(line)
        precise_c = ((-1 if t.group(1) == "1" else 1) * int(t.group(2))/10) if t else None
        sixhr_c = ((-1 if six.group(1) == "1" else 1) * int(six.group(2))/10) if six else None
        observations.append({
            "station": station, "obs_utc": obs.isoformat(),
            "obs_age_s": round((received-obs).total_seconds(), 3),
            "precision_c": precise_c, "sixhr_c_candidate": sixhr_c,
        })
        seen_icao.append(station)
    stations.update(seen_icao)

    issued = None
    try:
        issued = datetime.fromisoformat(issue.replace("Z", "+00:00"))
        if issued.tzinfo is None:
            issued = None
    except (ValueError, TypeError):
        issued = None
    row = {
        "kind":"NWWS_RECEIPT", "source":"NOAA_NWWS_OI",
        "first_seen_utc":received.isoformat(),
        "issue_utc":issued.isoformat() if issued else None,
        "issue_lag_s":round((received-issued).total_seconds(),3) if issued else None,
        "awipsid":awipsid, "ttaaii":ttaaii, "product_type":kind,
        "stations":sorted(stations),
        "report_stamps":observations[:30],
        "product_id":product_id[:80],
        "payload_sha256":hashlib.sha256(body.encode()).hexdigest(),
        "payload_length":len(body), "raw":body[:15000],
    }
    return row


class RaceRecorder:
    def __init__(self, location: str):
        self.data = Path(location)
        self.data.mkdir(parents=True, exist_ok=True)
        self.seen = set()
        self.recent = deque(maxlen=30000)
        self.received = 0
        self.matched = 0
        self.types = Counter()
        self.validated = Counter()
        self.parse_rejected = Counter()
        self.last_evidence = None
        self.first_seen_by_bulletin = {}
        self.completed_pairs = set()
        self.observations = {}
        self.evidence_pairs = set()
        self.iem_racer = None
        self.tgftp_racer = None
        self.last_arrival = None
        self.started_at = utcnow()
        self.last_health = time.monotonic()

    def backfill_archived_climate(self):
        """Parse earlier stored NWWS raw products without falsifying live latency.

        The first collector archived wire payloads but never decoded their
        maxima. This handles that research debt without changing the recorded
        first_seen_utc for any product.
        """
        product_count = 0
        successes = []
        failures = Counter()
        for path in sorted(self.data.glob("nwws-oi-first-seen-*.jsonl"))[-4:]:
            try:
                with path.open(encoding="utf-8") as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            if entry.get("product_type") not in ("DSM","CLI"):
                                continue
                            product_count += 1
                            parsed = extract_evidence(entry)
                            if parsed["evidence"]:
                                successes.append(parsed)
                            else:
                                failures[parsed["reason"]] += 1
                        except (ValueError, TypeError, KeyError):
                            failures["archive_record_invalid"] += 1
            except OSError:
                failures["archive_unreadable"] += 1
        log.info("NWWS_BACKFILL %s", json.dumps({
            "at":utcnow().isoformat(), "stored_climate_bulletins":product_count,
            "verified":len(successes), "rejected":dict(failures),
            "evidence":successes[-40:],
            "historical_only":True,
        }, separators=(",",":")))

    def observe_race(self, source, decoded, bootstrap=False):
        """Compare exact bulletins separately from equivalent station proofs.

        A regional IEM DSM (e.g. DSMZNY) can carry a matching maximum
        without representing the same AWIPS bulletin as DSMNYC. Never
        report a same-bulletin speed win for that case.
        """
        proof=decoded.get("evidence",[])
        if not proof:
            return
        seen=decoded.get("first_seen_utc")
        if not seen:
            return
        key=decoded.get("report_key")
        ev=proof[0]
        identity=(ev["station"],ev["climate_date"],ev["kind"],
                  ev["max_f"],ev.get("max_time_lst"))
        evidence_id=":".join(str(p) for p in identity)
        entry={
            "at":seen,"bootstrap":bool(bootstrap),
            "max_f":ev["max_f"],
            "climate_date":ev["climate_date"],
            "station":ev["station"],
            "verified_identity":bool(decoded.get("wire_identity_verified",source!="IEM")),
        }
        # Always record the first observation of each station+max via each
        # source; an older replay may be recorded but marked bootstrap.
        row=self.observations.setdefault(evidence_id,{})
        if source not in row:
            row[source]=entry
            self._compare_sources(row,evidence_id,"station_evidence",
                                  self.evidence_pairs)
        # Only full WMO+AWIPS IDs support exact-bulletin races.
        if key:
            by_source=self.first_seen_by_bulletin.setdefault(key,{})
            if source not in by_source:
                by_source[source]=entry
                self._compare_sources(by_source,key,"same_bulletin",
                                      self.completed_pairs)
        if len(self.observations)>5000:
            self.observations=dict(list(self.observations.items())[-1000:])
        if len(self.first_seen_by_bulletin)>5000:
            self.first_seen_by_bulletin=dict(
                list(self.first_seen_by_bulletin.items())[-1000:])
        loggerow={
            "source":source,"report_key":key,
            "station_evidence_key":evidence_id,
            "station":ev["station"],"product_type":ev["kind"],
            "climate_date":ev["climate_date"],
            "max_f":ev["max_f"],"max_time_lst":ev.get("max_time_lst"),
            "first_seen_utc":seen,"issue_utc":decoded.get("issue_utc"),
            "wire_identity_verified":entry["verified_identity"],
            "bootstrap":bool(bootstrap),
        }
        log.info("SOURCE_CLIMATE %s",
                 json.dumps(loggerow,separators=(",",":")))

    def _compare_sources(self, reports, key, comparison_kind, completed):
        choices=("NWWS","IEM","TGFTP")
        for i,left in enumerate(choices):
            for right in choices[i+1:]:
                if left not in reports or right not in reports:
                    continue
                comparison_key=(key,left,right)
                if comparison_key in completed:
                    continue
                completed.add(comparison_key)
                a,b=reports[left],reports[right]
                delta=(datetime.fromisoformat(b["at"]) -
                       datetime.fromisoformat(a["at"])).total_seconds()
                result={
                    "comparison":comparison_kind,"key":key,
                    "source_a":left,"source_b":right,
                    "first_seen_a":a["at"],"first_seen_b":b["at"],
                    "delta_b_minus_a_s":round(delta,3),
                    "winner":left if delta>0 else right if delta<0 else "tie",
                    "station":a["station"],"climate_date":a["climate_date"],
                    "same_max":a["max_f"]==b["max_f"],
                    "fair_live_race":not (a["bootstrap"] or b["bootstrap"]),
                    "startup_or_old_report":a["bootstrap"] or b["bootstrap"],
                    "same_bulletin":comparison_kind=="same_bulletin",
                }
                target=self.data/f"nwws-multisource-races-{utcnow():%Y%m%d}.jsonl"
                with target.open("a",encoding="utf-8") as f:
                    f.write(json.dumps(result,separators=(",",":"))+"\n")
                log.info("NWWS_RACE_COMPARE %s",
                         json.dumps(result,separators=(",",":")))
                # Compatibility log for earlier TGFTP-specific scoreboard.
                if comparison_kind=="same_bulletin" and left=="NWWS" and right=="TGFTP":
                    legacy={
                        "key":key,"station":a["station"],
                        "nwws_seen_utc":a["at"],"tgftp_seen_utc":b["at"],
                        "delta_tgftp_minus_nwws_s":round(delta,3),
                        "nwws_max_f":a["max_f"],"tgftp_max_f":b["max_f"],
                        "same_max":a["max_f"]==b["max_f"],
                        "fair_live_race":result["fair_live_race"],
                    }
                    with (self.data/f"nwws-tgftp-matches-{utcnow():%Y%m%d}.jsonl"
                          ).open("a",encoding="utf-8") as f:
                        f.write(json.dumps(legacy,separators=(",",":"))+"\n")
                    log.info("NWWS_TGFTP_COMPARISON %s",
                             json.dumps(legacy,separators=(",",":")))

    def write(self, event):
        self.received += 1
        kind = event.get("product_type","OTHER")
        self.types[kind] += 1
        # NOAA delivers one national room. It is not a per-airport query.
        # SYNBOU embeds OLD METAR observations in a forecast: never record
        # that as a direct, competitive ASOS observation.
        if not event.get("stations") or kind not in ("DSM","CLI","METAR_OR_SPECI"):
            return
        digest = event["payload_sha256"] + "/" + event["awipsid"]
        if digest in self.seen:
            return
        self.seen.add(digest)
        self.recent.append(digest)
        if len(self.recent) == self.recent.maxlen:
            self.seen = set(self.recent)
        self.matched += 1
        self.last_arrival = event["first_seen_utc"]
        if kind in ("DSM","CLI"):
            parsed = extract_evidence(event)
            event["parsed"] = parsed
            if parsed["evidence"]:
                self.validated[kind] += 1
                self.last_evidence = parsed
                self.observe_race("NWWS",parsed)
                log.info("NWWS_EVIDENCE %s", json.dumps(parsed,separators=(",",":")))
            else:
                self.parse_rejected[parsed["reason"]] += 1
                log.warning("NWWS_UNUSABLE %s",json.dumps({
                    "awipsid":event["awipsid"],"station":parsed.get("station"),
                    "received_at":event["first_seen_utc"],"reason":parsed["reason"]
                },separators=(",",":")))
        else:
            # A direct METAR/SPECI is never one-minute OMO. Station/report
            # timestamp and precision are retained, but not promoted as a
            # trading-grade proof without parser validation.
            log.info("NWWS_METAR_CANDIDATE %s",json.dumps({
                "awipsid":event["awipsid"],
                "stations":event["stations"],"report_stamps":event["report_stamps"],
                "received_at":event["first_seen_utc"]
            },separators=(",",":")))
        datepart = utcnow().strftime("%Y%m%d")
        dest = self.data / f"nwws-oi-first-seen-{datepart}.jsonl"
        with dest.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, separators=(",",":"))+"\n")
        summary = {k:v for k,v in event.items() if k not in ("raw","payload_sha256","parsed")}
        log.info("NWWS_RECEIPT %s",json.dumps(summary,separators=(",",":")))

    def heartbeat(self):
        t = time.monotonic()
        if t-self.last_health < 60:
            return
        self.last_health = t
        log.info("NWWS_STATUS %s",json.dumps({
            "at":utcnow().isoformat(),"total_products":self.received,
            "matched_station_products":self.matched,
            "last_matched_utc":self.last_arrival,
            "kind_counts":dict(self.types),
            "validated_highs":dict(self.validated),
            "invalid_climate_reports":dict(self.parse_rejected),
            "last_evidence":self.last_evidence,
            "iem_comparison":{
                "checks":self.iem_racer.checks,"changed_snapshots":self.iem_racer.updates,
                "errors":self.iem_racer.errors,"rate_limits":self.iem_racer.rate_limits,
                "validated_records":self.iem_racer.verified,
            } if self.iem_racer else {},
            "race_pairs":len(self.completed_pairs),
            "station_evidence_pairs":len(self.evidence_pairs),
            "tgftp_comparison":{
                "checks":self.tgftp_racer.checks,"product_updates":self.tgftp_racer.updates,
                "unavailable":self.tgftp_racer.unavailable,
                "paired_bulletins":len(self.completed_pairs),
            } if self.tgftp_racer else {},
        }, separators=(",",":")))


async def race():
    import slixmpp
    user = os.environ.get("NWWS_USER","").strip()
    password = os.environ.get("NWWS_PASS","")
    if not user or not password:
        raise RuntimeError("NWWS_USER and NWWS_PASS must be supplied in Railway Variables")
    location = os.environ.get("NWWS_DATA_DIR","/data")
    recorder = RaceRecorder(location)
    recorder.backfill_archived_climate()
    recorder.tgftp_racer = TGFTPRacer(recorder)
    asyncio.create_task(recorder.tgftp_racer.run(),name="tgftp-climate-reference")
    recorder.iem_racer = IEMRacer(recorder)
    asyncio.create_task(recorder.iem_racer.run(),name="iem-afos-climate-reference")
    nickname = "weather-race"
    attempt = 0

    while True:
        attempt += 1
        class NWWSClient(slixmpp.ClientXMPP):
            def __init__(self):
                super().__init__(f"{user}@{HOST}/nwws",password)
                self.register_plugin("xep_0045")
                self.register_plugin("xep_0199")
                self.add_event_handler("session_start",self.on_session)
                self.add_event_handler("groupchat_message",self.on_message)
                self.add_event_handler("failed_auth",self.on_failed_auth)
                self.add_event_handler("session_end",self.on_session_end)
                self.session_ok = False
                self.auth_failed = False
                self.room_joined = False

            def on_failed_auth(self,event):
                self.auth_failed = True
                log.error("NWWS_AUTH_FAILED %s",json.dumps(
                    {"at":utcnow().isoformat(),"attempt":attempt,
                     "action":"verify account activation or NOAA outage"}))
                self.disconnect()

            async def on_session(self,event):
                self.session_ok = True
                log.info("NWWS_AUTH_OK %s",json.dumps(
                    {"at":utcnow().isoformat(),"attempt":attempt,"host":HOST}))
                self.send_presence()
                try:
                    await self.plugin["xep_0045"].join_muc_wait(
                        ROOM,nickname,password=password,maxchars=0,timeout=35)
                    self.room_joined=True
                    log.info("NWWS_ROOM_JOINED %s",json.dumps({
                        "at":utcnow().isoformat(),"room":ROOM}))
                except Exception as exc:
                    log.warning("NWWS_ROOM_JOIN_FAILED %s",json.dumps({
                        "at":utcnow().isoformat(),"type":type(exc).__name__}))
                    # Fallback: NOAA's room sometimes has no separate room
                    # password despite the docs listing one.
                    try:
                        await self.plugin["xep_0045"].join_muc_wait(
                            ROOM,nickname,maxchars=0,timeout=20)
                        self.room_joined=True
                        log.info("NWWS_ROOM_JOINED %s",json.dumps({
                            "at":utcnow().isoformat(),"room":ROOM,"fallback":True}))
                    except Exception as exc2:
                        log.warning("NWWS_ROOM_JOIN_FAILED_FINAL %s",json.dumps({
                            "at":utcnow().isoformat(),"type":type(exc2).__name__}))

            def on_session_end(self,event):
                log.warning("NWWS_SESSION_ENDED %s",json.dumps({
                    "at":utcnow().isoformat(),"room_joined":self.room_joined}))

            def on_message(self,msg):
                payload = msg.xml.find("{nwws-oi}x")
                if payload is None:
                    # Some servers use a nested extension element.
                    payload = msg.xml.find(".//{nwws-oi}x")
                if payload is None:
                    return
                when = utcnow()
                attrs=payload.attrib
                # NOAA product text lives inside the proprietary x stanza;
                # <body> is just a one-line description.
                raw="".join(payload.itertext())
                record=analyze_product(attrs.get("awipsid",""),
                                       attrs.get("ttaaii",""),raw,when,
                                       attrs.get("issue",""),attrs.get("id",""))
                recorder.write(record)

        # Set a single active connection; NOAA refuses simultaneous users
        # sharing one NWWS account. Credentials never enter logs or source.
        client = NWWSClient()
        log.info("NWWS_CONNECT %s",json.dumps({
            "at":utcnow().isoformat(),"host":HOST,"port":5222,"attempt":attempt}))
        try:
            client.connect(host=HOST,port=5222)
            while not client.disconnected.done():
                await asyncio.sleep(1)
                recorder.heartbeat()
            await client.disconnected
        except Exception as exc:
            log.warning("NWWS_RECONNECT %s",json.dumps({
                "at":utcnow().isoformat(),"type":type(exc).__name__,
                "session_ok":client.session_ok,"room_joined":client.room_joined}))
        if client.auth_failed:
            # Wrong username/password should not hammer NOAA servers.
            await asyncio.sleep(240)
        else:
            await asyncio.sleep(min(90,5*(2**min(attempt-1,4))))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(race())
