"""IEM AFOS DSM source lane for the same-station NWWS race.

Use the exact station DSM PIL and optionally regional AFOS collectives.
Only a full WMO+AWIPS identity qualifies for same-bulletin comparison.
Station-row-only collective data qualifies for same-observation comparisons.
A first HTTP snapshot is always BOOTSTRAP, never a live winning arrival.
All requests are serialized and throttled; 429/503 cause global backoff.
This research worker never places trades.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from nwws_extract import CONFIG, DSM_ROW, DSM_HIGH, extract_evidence, _year_from_issue

log=logging.getLogger("nwws-race")
IEM_URL="https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py"
WMO=re.compile(r"(?m)^[ \t]*(CXUS\d{2}|CDUS\d{2})[ \t]+(K[A-Z]{3})[ \t]+(\d{6})[ \t]*$")
AWIPS_LINE=re.compile(r"(?m)^[ \t]*((?:DSM|CLI)[A-Z0-9]{3})[ \t]*$")
TARGETS=tuple(f"DSM{s}" for s in CONFIG)
# These region-wide bulletins were seen in the independent IEM shadow:
REGIONAL=("DSMZNY","DSMZAU","DSMZHU")
_ALL=TARGETS+REGIONAL


def fetch(pil: str):
    url=IEM_URL+"?"+urllib.parse.urlencode({"pil":pil,"fmt":"text","limit":3})
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mercury-Weather-Source-Race/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=9) as resp:
            return resp.read(180000).decode("utf-8","replace"),None
    except urllib.error.HTTPError as exc:
        return None,"http_"+str(exc.code)
    except Exception as exc:
        return None,type(exc).__name__


def _issue_time(ddhhmm,now):
    day,hour,minute=int(ddhhmm[:2]),int(ddhhmm[2:4]),int(ddhhmm[4:6])
    ym=now.year*12+now.month-1
    possible=[]
    for offset in (-1,0,1):
        y,m=divmod(ym+offset,12)
        try:
            t=datetime(y,m+1,day,hour,minute,tzinfo=timezone.utc)
            if -600 <= (now-t).total_seconds() <= 72*3600:
                possible.append(t)
        except ValueError:
            pass
    return min(possible,key=lambda t:abs((now-t).total_seconds())) if possible else None


def parse_response(raw: str, requested_pil: str, seen: datetime):
    """Return verified bulletin reports + station-only regional evidence.

    Never invent an AWIPS identity for a region-wide DSM product. The WMO
    header must be inside this product chunk, never copied from a prior chunk.
    """
    results=[]
    headers=list(WMO.finditer(raw))
    for i,header in enumerate(headers):
        chunk=raw[header.start():headers[i+1].start() if i+1<len(headers) else len(raw)]
        pil_line=AWIPS_LINE.search(chunk)
        if pil_line is None or pil_line.group(1)!=requested_pil:
            continue
        issue=_issue_time(header.group(3),seen)
        if issue is None:
            continue
        pil=pil_line.group(1)
        if pil[3:] in CONFIG:
            report=extract_evidence({
                "awipsid":pil,"ttaaii":header.group(1),
                "raw":chunk,"issue_utc":issue.isoformat(),
                "first_seen_utc":seen.isoformat(),"product_type":pil[:3],
            })
            if report["evidence"]:
                report["wire_identity_verified"]=True
                results.append(report)
        elif requested_pil in REGIONAL:
            results+=_regional_evidence(chunk,requested_pil,seen,issue)
    return results


def _regional_evidence(chunk, pil, seen, issued):
    rows=[]
    for m in DSM_ROW.finditer(chunk):
        station=m.group(1)
        if station not in {v[0] for v in CONFIG.values()}:
            continue
        try:
            day=_year_from_issue(int(m.group(3)),int(m.group(2)),issued)
            code=DSM_HIGH.fullmatch(m.group(4))
            if day is None or code is None:
                continue
            hi=int(code.group(1))
            stamp=code.group(2)
            if not (-40<=hi<=135 and int(stamp[:2])<24 and int(stamp[2:])<60):
                continue
        except ValueError:
            continue
        rows.append({
            "awipsid":pil,"product_type":"DSM","station":station,
            "first_seen_utc":seen.isoformat(),
            "issue_utc":issued.isoformat(),
            "report_key":None,"wire_identity_verified":False,
            "reason":"regional_collective_station_evidence",
            "evidence":[{
                "station":station,"kind":"DSM",
                "climate_date":day.isoformat(),"max_f":hi,
                "max_time_lst":stamp,
            }],
        })
    return rows


class IEMRacer:
    """A dedicated throttled worker; no IEM parallelism or startup wins."""
    def __init__(self, recorder, min_spacing_s=1.8, cycle_s=95):
        self.recorder=recorder
        self.min_spacing_s=min_spacing_s
        self.cycle_s=cycle_s
        self.previous={}
        self.bootstrapped=set()
        self.checks=0
        self.updates=0
        self.errors=0
        self.rate_limits=0
        self.verified=0
        self.last_error=None

    async def run(self):
        cooldown=30.0
        while True:
            began=time.monotonic()
            throttled=False
            for pil in _ALL:
                raw,error=await asyncio.to_thread(fetch,pil)
                self.checks+=1
                if error:
                    self.errors+=1
                    self.last_error=error
                    if error in ("http_429","http_503"):
                        self.rate_limits+=1
                        throttled=True
                        log.warning("IEM_RACE_RATE_LIMIT %s",{
                            "pil":pil,"code":error,"cooldown_s":cooldown})
                        break
                    if self.errors < 6:
                        log.warning("IEM_RACE_FETCH_ERROR %s",{"pil":pil,"code":error})
                elif raw is not None:
                    import hashlib
                    # Keep unchanged responses from appearing as new races.
                    digest=hashlib.sha256(raw.encode("utf-8")).hexdigest()
                    old=self.previous.get(pil)
                    first=pil not in self.bootstrapped
                    self.bootstrapped.add(pil)
                    self.previous[pil]=digest
                    if old != digest:
                        now=datetime.now(timezone.utc)
                        reports=parse_response(raw,pil,now)
                        # First snapshot or products already published before
                        # startup cannot claim a live discovery race.
                        for report in reports:
                            issued=report.get("issue_utc")
                            age=(now-datetime.fromisoformat(issued)).total_seconds() if issued else None
                            bootstrap=first or age is None or age>1800
                            self.recorder.observe_race("IEM",report,bootstrap=bootstrap)
                            self.verified+=1
                        self.updates+=1
                await asyncio.sleep(self.min_spacing_s)
            if throttled:
                await asyncio.sleep(cooldown)
                cooldown=min(cooldown*2,600)
            else:
                cooldown=30.0
                await asyncio.sleep(max(8.0,self.cycle_s-(time.monotonic()-began)))
