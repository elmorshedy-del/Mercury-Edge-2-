"""Signed one-way NWWS -> Mercury source-agnostic proof delivery.

NWWS credentials remain solely on the research Railway service. No direct
engine imports or trading actions; the receiver verifies and queues proof.
Signed HTTPS delivery is only enabled when URL and secret are provisioned.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

log=logging.getLogger("nwws-race")


def build_event(decoded):
    """Convert a validated NOAA bulletin to one station-day max proof."""
    if decoded.get("reason")!="ok" or not decoded.get("report_key"):
        return None
    values=decoded.get("evidence")
    if not isinstance(values,list) or len(values)!=1:
        return None
    proof=values[0]
    if proof.get("kind") not in ("DSM","CLI"):
        return None
    if not isinstance(proof.get("max_f"),int):
        return None
    return {
        "source":"nwws-oi","kind":proof["kind"],"station":proof["station"],
        "awipsid":decoded["awipsid"],"report_key":decoded["report_key"],
        "climate_date":proof["climate_date"],"max_f":proof["max_f"],
        "max_time_lst":proof.get("max_time_lst"),
        "first_seen_utc":decoded["first_seen_utc"],
        "issue_utc":decoded.get("issue_utc"),
    }


def post_once(url,secret,event):
    raw=json.dumps(event,sort_keys=True,separators=(",",":")).encode("utf-8")
    stamp=str(int(time.time()))
    mac=hmac.new(secret.encode("utf-8"),stamp.encode("ascii")+b"."+raw,
                 hashlib.sha256).hexdigest()
    req=urllib.request.Request(url,data=raw,method="POST",headers={
        "Content-Type":"application/json",
        "X-NWWS-Time":stamp,
        "X-NWWS-Signature":mac,
        "User-Agent":"Mercury-Edge-Research-Climate-Relay/1.0",
    })
    try:
        with urllib.request.urlopen(req,timeout=6) as response:
            return response.status,None
    except urllib.error.HTTPError as exc:
        return exc.code,"http_error"
    except Exception as exc:
        return 0,type(exc).__name__


class NWWSBridgeSender:
    def __init__(self, url=None, secret=None):
        self.url=url or os.environ.get("NWWS_BRIDGE_URL","")
        self.secret=secret or os.environ.get("NWWS_BRIDGE_SECRET","")
        self.enabled=self.url.startswith("https://") and len(self.secret)>=32
        self.queue=asyncio.Queue(maxsize=200)
        self.sent=0
        self.rejected=0
        self.failed=0
        self.queue_full=0
        self.last_success=None

    def enqueue(self,decoded):
        event=build_event(decoded)
        if event is None or not self.enabled:
            return
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            self.queue_full+=1
            log.error("NWWS_BRIDGE_QUEUE_FULL station=%s",event["station"])

    async def run(self):
        if not self.enabled:
            log.info("NWWS_BRIDGE_OFF no configured HTTPS URL/shared token")
            return
        log.info("NWWS_BRIDGE_READY signed-HTTPS-only")
        while True:
            event=await self.queue.get()
            # Real-time only; never allow backfilling past days to create
            # new trade intents when the bot was disconnected.
            try:
                issued=datetime.fromisoformat(event["first_seen_utc"])
                if (datetime.now(timezone.utc)-issued).total_seconds()>180:
                    self.rejected+=1
                    continue
            except (ValueError,TypeError):
                self.rejected+=1
                continue
            start=time.monotonic()
            while time.monotonic()-start<120:
                status,error=await asyncio.to_thread(
                    post_once,self.url,self.secret,event)
                if status==200:
                    self.sent+=1
                    self.last_success=datetime.now(timezone.utc).isoformat()
                    log.info("NWWS_BRIDGE_DELIVERED %s",json.dumps({
                        "station":event["station"],
                        "kind":event["kind"],
                        "report_key":event["report_key"],
                        "seen":event["first_seen_utc"],
                        "delivered_utc":self.last_success,
                    },separators=(",",":")))
                    break
                if status in (400,401,403,409,422):
                    self.rejected+=1
                    log.warning("NWWS_BRIDGE_REJECTED station=%s status=%s",
                                event["station"],status)
                    break
                await asyncio.sleep(4)
            else:
                self.failed+=1
                log.warning("NWWS_BRIDGE_DELIVERY_FAILED station=%s",event["station"])
