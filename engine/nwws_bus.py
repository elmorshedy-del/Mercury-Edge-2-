"""NWWS-OI push -> Mercury local proof bus.

This replaces the older source-specific parsing path. Product transport remains
XMPP, but all weather semantics are delegated to the same tested decoders used
by TGFTP/LDM:
- any DSM lines for configured stations -> ``parse_dsm_text``;
- raw METAR/SPECI lines -> ``parse_metar_proofs``.

The adapter intentionally does not depend on airport-specific AWIPS IDs. Raw
collectives and station-split products are both accepted by content, which lets
NWWS race LDM without another decoder path.

Env: NWWS_USER/NWWS_PASS (or NWWS_JID/NWWS_PASSWORD).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from dsm_decode import parse_dsm_text
from fast_sources import parse_metar_proofs
from feeds import ProofEvent
from proof_bus import send_proof

log = logging.getLogger("nwws_bus")
HERE = Path(__file__).resolve().parent
CFG = json.load(open(HERE / "config.json"))
BY_ICAO = {c["icao"]: c for c in CFG["cities"].values()}
ICAOS = set(BY_ICAO)
METAR_LINE = re.compile(r"^(?:(?:METAR|SPECI)\s+)?(K[A-Z0-9]{3})\s+\d{6}Z\b")


def parse_nwws_product(text: str, *, awipsid: str = "", ttaaii: str = "",
                       issue: str = "", seen_ts: datetime | None = None) -> list[ProofEvent]:
    """Normalize one NWWS product payload into Mercury proofs.

    Parsing is content-first because NWWS metadata differs between raw
    collectives and value-added product IDs. Duplicate proofs are expected and
    are deduped/raced downstream.
    """
    seen = seen_ts or datetime.now(timezone.utc)
    source_meta = "nwws"
    if awipsid:
        source_meta += f":{awipsid}"
    elif ttaaii:
        source_meta += f":{ttaaii}"
    if issue:
        source_meta += f" issue={issue}"

    out: list[ProofEvent] = []
    # DSM decoder safely ignores everything except configured station DS lines.
    for ev in parse_dsm_text(text, CFG["cities"], source_meta, seen):
        out.append(ev)

    for raw in text.splitlines():
        line = raw.strip()
        m = METAR_LINE.match(line)
        if not m:
            continue
        icao = m.group(1)
        city = BY_ICAO.get(icao)
        if not city:
            continue
        out.extend(parse_metar_proofs(
            line, icao, int(city["lst_offset_h"]), source_meta, seen,
        ))
    return out


def _xml_payload(x) -> str:
    """Preserve all text descendants, not just x.text.

    Some XMPP implementations expose the weather product as nested/text-tail
    nodes; using only ``x.text`` can silently drop the report body.
    """
    try:
        return "".join(x.itertext())
    except Exception:
        return x.text or ""


async def run(on_proof: Callable[[ProofEvent], None] = send_proof) -> None:
    try:
        import slixmpp
    except ImportError as exc:
        raise RuntimeError("slixmpp is required for NWWS-OI") from exc

    user = os.getenv("NWWS_USER") or os.getenv("NWWS_JID")
    password = os.getenv("NWWS_PASS") or os.getenv("NWWS_PASSWORD")
    if not user or not password:
        raise RuntimeError("NWWS credentials not configured")
    jid = user if "@" in user else f"{user}@nwws-oi.weather.gov"
    username = jid.split("@", 1)[0]
    room = "nwws@conference.nwws-oi.weather.gov"

    class Client(slixmpp.ClientXMPP):
        def __init__(self):
            super().__init__(f"{jid}/mercury", password)
            self.register_plugin("xep_0045")
            self.add_event_handler("session_start", self._session_start)
            self.add_event_handler("groupchat_message", self._message)
            self.add_event_handler("disconnected", self._disconnected)

        async def _session_start(self, _event):
            self.send_presence()
            await self.get_roster()
            self.plugin["xep_0045"].join_muc(room, username)
            log.info("NWWS-OI joined %s", room)

        def _disconnected(self, _event):
            log.warning("NWWS-OI disconnected")

        def _message(self, msg):
            # NWWS payload namespace used by the operational service.
            x = msg.xml.find("{nwws-oi}x")
            if x is None:
                # Be namespace-tolerant rather than silently losing products.
                for child in msg.xml.iter():
                    if child.tag.rsplit("}", 1)[-1].lower() == "x" and (
                        child.get("ttaaii") or child.get("awipsid")
                    ):
                        x = child
                        break
            if x is None:
                return
            text = _xml_payload(x)
            if not text.strip():
                return
            seen = datetime.now(timezone.utc)
            events = parse_nwws_product(
                text,
                awipsid=(x.get("awipsid") or "").strip(),
                ttaaii=(x.get("ttaaii") or "").strip(),
                issue=(x.get("issue") or "").strip(),
                seen_ts=seen,
            )
            for ev in events:
                try:
                    on_proof(ev)
                except Exception:
                    log.exception("NWWS proof sink failed")

    client = Client()
    # slixmpp handles XMPP stream keepalive/reconnect semantics; Mercury's proof
    # sink remains transport-independent.
    client.connect(("nwws-oi.weather.gov", 5222))
    await asyncio.Event().wait()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
