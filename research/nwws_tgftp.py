"""Independent NOAA TGFTP climate polling for first-seen comparisons.

Runs alongside the authenticated NWWS push stream on the same *research*
worker. No trading imports, secrets, or extra NWWS logins. The first HTTP
snapshot is marked BOOTSTRAP and not allowed to win a live race.
"""
from __future__ import annotations

import asyncio
import logging
import re
import urllib.request
from datetime import datetime,timezone
from nwws_extract import CONFIG, extract_evidence, tgftp_url

log=logging.getLogger("nwws-race")
_REPORTED_FAILURES=set()
AWIPS_IDS=[f"{kind}{suffix}" for suffix in CONFIG for kind in ("DSM","CLI")]
WMO_HEADER=re.compile(
    r"(?m)^\s*(?:CXUS|CDUS)\d{2}\s+K[A-Z]{3}\s+(\d{2})(\d{2})(\d{2})\s*$")


def infer_issue_stamp(text: str, now: datetime):
    m=WMO_HEADER.search(text)
    if not m:
        return None
    day, hour, minute=(int(v) for v in m.groups())
    if hour>23 or minute>59:
        return None
    choices=[]
    monthindex=now.year*12+now.month-1
    for offset in (-1,0,1):
        year,month0=divmod(monthindex+offset,12)
        try:
            date=datetime(year,month0+1,day,hour,minute,tzinfo=timezone.utc)
        except ValueError:
            continue
        if -600<=(now-date).total_seconds()<=7*24*3600:
            choices.append(date)
    return min(choices,key=lambda d:abs((now-d).total_seconds())) if choices else None


def read_tgftp(awips: str):
    target=tgftp_url(awips)
    if target is None:
        return None
    try:
        with urllib.request.urlopen(urllib.request.Request(
            target,headers={"User-Agent":"Mercury-Edge-Research-NWWS-Race/1.0"}),
            timeout=6) as response:
            return response.read(50000).decode("utf-8",errors="replace")
    except Exception as exc:
        signature=(awips,type(exc).__name__,getattr(exc,"code",None))
        if signature not in _REPORTED_FAILURES:
            _REPORTED_FAILURES.add(signature)
            log.warning("TGFTP_HTTP_FAILURE product=%s type=%s http_code=%s",
                        awips,type(exc).__name__,getattr(exc,"code",None))
        return None


class TGFTPRacer:
    def __init__(self, recorder, interval=20.0):
        self.recorder=recorder
        self.interval=interval
        self.hashes={}
        self.checks=0
        self.updates=0
        self.unavailable=0
        self.first_scan=set()

    async def poll_one(self, awips: str):
        raw=await asyncio.to_thread(read_tgftp,awips)
        self.checks+=1
        if not raw:
            self.unavailable+=1
            return
        import hashlib
        digest=hashlib.sha256(raw.encode()).hexdigest()
        if digest==self.hashes.get(awips):
            return
        bootstrapping=awips not in self.first_scan
        self.first_scan.add(awips)
        self.hashes[awips]=digest
        observed=datetime.now(timezone.utc)
        issued=infer_issue_stamp(raw,observed)
        ptype=awips[:3]
        result=extract_evidence({
            "awipsid":awips,"ttaaii":("CXUS" if ptype=="DSM" else "CDUS")+CONFIG[awips[3:]][2],
            "raw":raw,"issue_utc":issued.isoformat() if issued else None,
            "first_seen_utc":observed.isoformat(),"product_type":ptype,
        })
        if not result["evidence"]:
            return
        self.updates+=1
        self.recorder.observe_race("TGFTP",result,bootstrap=bootstrapping)

    async def run(self):
        limiter=asyncio.Semaphore(4)
        async def guarded(awips):
            async with limiter:
                await self.poll_one(awips)
        while True:
            try:
                await asyncio.gather(*(guarded(a) for a in AWIPS_IDS))
            except Exception as exc:
                log.warning("TGFTP_RACE_LOOP_FAILURE %s",type(exc).__name__)
            await asyncio.sleep(self.interval)
