"""nwws_adapter.py — NWWS-OI push feed → ProofEvents (~10s from issuance).

STATUS: ready-to-run stub; needs credentials from the NWWS-OI application
(see NWWS_APPLICATION.md) and `pip install slixmpp`.

Env: NWWS_USER, NWWS_PASS. Run standalone (prints proofs) or import and pass
an on_proof callback wired to the KillEngine (see run.py integration note)."""
from __future__ import annotations
import os, re, logging, asyncio
from datetime import datetime, timezone
from decode import c10_to_f
from feeds import DSBODY, MAXTOK, TGRP, SIXHR, ProofEvent

log = logging.getLogger("nwws")
DSM_PILS = {"DSMNYC": "KNYC", "DSMMDW": "KMDW", "DSMAUS": "KAUS", "DSMMIA": "KMIA",
            "DSMDEN": "KDEN", "DSMPHL": "KPHL", "DSMLAX": "KLAX"}
ICAOS = set(DSM_PILS.values())
LST = {"KNYC": -5, "KPHL": -5, "KMIA": -5, "KMDW": -6, "KAUS": -6, "KDEN": -7, "KLAX": -8}

def parse_product(awipsid: str, text: str, on_proof):
    """Feed a raw NWWS product payload into ProofEvents."""
    from datetime import timedelta, date as Date
    now = datetime.now(timezone.utc)
    if awipsid in DSM_PILS:
        icao = DSM_PILS[awipsid]
        for ln in text.splitlines():
            m = DSBODY.match(ln.strip())
            if not m or m.group(1) != icao or not m.group(2):
                continue
            mt = MAXTOK.match(m.group(5).split("/")[0].strip())
            if not mt:
                continue
            try:
                cd = Date(now.year, int(m.group(4)), int(m.group(3)))
            except ValueError:
                continue
            on_proof(ProofEvent(icao, cd, int(mt.group(1)), "dsm", None, now,
                                f"nwws {awipsid} DS {m.group(2)}"))
    else:  # METAR collective — scan for our stations
        for ln in text.splitlines():
            for icao in ICAOS:
                if not ln.startswith(icao):
                    continue
                lst = LST[icao]
                dm = re.search(r'\b(\d{2})(\d{2})(\d{2})Z\b', ln)
                obs = now
                if dm:
                    obs = now.replace(day=int(dm.group(1)), hour=int(dm.group(2)),
                                      minute=int(dm.group(3)), second=0, microsecond=0)
                cd = (obs + __import__("datetime").timedelta(hours=lst)).date()
                t = TGRP.search(ln)
                if t:
                    c10 = int(t.group(2)) / 10 * (-1 if t.group(1) == "1" else 1)
                    on_proof(ProofEvent(icao, cd, c10_to_f(c10), "metar", obs, now, "nwws"))
                s = SIXHR.search(ln)
                if s and (obs.minute >= 45 and (obs.hour + 1) % 6 == 0 or obs.hour % 6 == 0):
                    c10 = int(s.group(2)) / 10 * (-1 if s.group(1) == "1" else 1)
                    on_proof(ProofEvent(icao, cd, c10_to_f(c10), "sixhr", obs, now, "nwws"))

async def run(on_proof):
    try:
        import slixmpp
    except ImportError:
        raise SystemExit("pip install slixmpp")
    user, pw = os.environ.get("NWWS_USER"), os.environ.get("NWWS_PASS")
    if not user or not pw:
        raise SystemExit("set NWWS_USER / NWWS_PASS (see NWWS_APPLICATION.md)")

    class Client(slixmpp.ClientXMPP):
        def __init__(self):
            super().__init__(f"{user}@nwws-oi.weather.gov/nwws", pw)
            self.register_plugin("xep_0045")          # MUC
            self.add_event_handler("session_start", self.start)
            self.add_event_handler("groupchat_message", self.msg)
        async def start(self, _):
            self.send_presence()
            await self.get_roster()
            self.plugin["xep_0045"].join_muc("nwws@conference.nwws-oi.weather.gov", user)
            log.info("joined NWWS room")
        def msg(self, m):
            x = m.xml.find("{nwws-oi}x")
            if x is None:
                return
            awipsid = (x.get("awipsid") or "").strip()
            if awipsid in DSM_PILS or awipsid[:3] in ("MTR",) or (x.get("ttaaii") or "").startswith(("SAUS", "SXUS")):
                parse_product(awipsid, x.text or "", on_proof)

    c = Client()
    c.connect(("nwws-oi.weather.gov", 5222))
    await asyncio.Event().wait()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run(lambda ev: print("PROOF", ev)))
