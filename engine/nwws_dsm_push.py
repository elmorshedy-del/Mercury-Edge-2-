"""Optional NWWS-OI XMPP DSM push adapter.

Runs only with NWS-issued NWWS credentials. It does not assume every configured
DSM is present on NWWS; it records/forwards only products actually observed.
The IEM-LDM and AFOS-HTTP paths remain redundant competitors.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from nwws_receiver import WxWire, WxWireConfig

HERE = Path(__file__).resolve().parent
CFG = json.load(open(HERE / "config.json"))

from dsm_decode import parse_dsm_text  # noqa: E402
from proof_bus import send_proof  # noqa: E402


def handle_message(message) -> None:
    content = getattr(message, "content", "") or ""
    awipsid = (getattr(message, "awipsid", "") or "").upper()
    configured_pils = {c["dsm_pil"].upper() for c in CFG["cities"].values()}

    # The raw content check is intentionally retained even if awipsid is not an
    # exact configured PIL; NWWS product identifiers can differ by office/format.
    if awipsid and awipsid not in configured_pils and " DS " not in content:
        return
    now = datetime.now(timezone.utc)
    for ev in parse_dsm_text(content, CFG["cities"], "nwws-oi", now):
        send_proof(ev)


async def main() -> None:
    username = os.environ.get("NWWS_USERNAME")
    password = os.environ.get("NWWS_PASSWORD")
    if not username or not password:
        raise SystemExit("NWWS_USERNAME and NWWS_PASSWORD are required")

    cfg = WxWireConfig(
        username=username,
        password=password,
        server=os.environ.get("NWWS_SERVER", "nwws-oi.weather.gov"),
        port=int(os.environ.get("NWWS_PORT", "5222")),
        room=os.environ.get("NWWS_ROOM", "nwws-oi@conference.weather.gov"),
        history=0,
        use_tls=True,
        validate_certificates=True,
    )
    client = WxWire(cfg)
    client.subscribe(handle_message)
    ok = await client.start()
    if not ok:
        raise RuntimeError("NWWS-OI connection failed")
    try:
        await asyncio.Event().wait()
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
