"""exec_live.py — REAL order placement. DISABLED unless BOTH:
  1) env WEATHERBOT_LIVE=yes
  2) Kalshi API credentials present (see below)

Kalshi trade API v2 auth (create key at kalshi.com account settings):
  env KALSHI_KEY_ID       — API key id
  env KALSHI_PRIVATE_KEY  — path to RSA private key PEM
Headers per request: KALSHI-ACCESS-KEY, KALSHI-ACCESS-TIMESTAMP (ms),
KALSHI-ACCESS-SIGNATURE = base64(RSA-PSS-SHA256 sign of ts + METHOD + path)

The kill order = BUY NO at (100 - min_px) limit, IOC-style sizing, which is
identical to selling YES into the resting yes bids.
"""
from __future__ import annotations
import base64, json, os, time, logging, urllib.request
from strategy import Intent

log = logging.getLogger("exec_live")
BASE = "https://api.elections.kalshi.com/trade-api/v2"

def _enabled() -> bool:
    return (os.environ.get("WEATHERBOT_LIVE") == "yes"
            and os.environ.get("KALSHI_KEY_ID")
            and os.environ.get("KALSHI_PRIVATE_KEY"))

def _sign(method: str, path: str) -> dict:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    ts = str(int(time.time() * 1000))
    key = serialization.load_pem_private_key(
        open(os.environ["KALSHI_PRIVATE_KEY"], "rb").read(), password=None)
    msg = (ts + method + path).encode()
    sig = key.sign(msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                    salt_length=padding.PSS.DIGEST_LENGTH),
                   hashes.SHA256())
    return {"KALSHI-ACCESS-KEY": os.environ["KALSHI_KEY_ID"],
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode()}

def execute(intent: Intent) -> dict:
    if not _enabled():
        log.warning("LIVE DISABLED — intent for %s logged only. "
                    "Set WEATHERBOT_LIVE=yes + KALSHI_KEY_ID + KALSHI_PRIVATE_KEY.",
                    intent.ticker)
        return {"mode": "DISABLED", "ticker": intent.ticker}
    path = "/trade-api/v2/portfolio/orders"
    body = {"ticker": intent.ticker, "action": "buy", "side": "no",
            "type": "limit", "count": int(intent.max_size),
            "no_price": 100 - intent.min_px,          # cents
            "client_order_id": f"wb-{int(time.time()*1000)}",
            "time_in_force": "immediate_or_cancel"}
    req = urllib.request.Request(BASE + "/portfolio/orders",
                                 data=json.dumps(body).encode(),
                                 headers={**_sign("POST", path),
                                          "Content-Type": "application/json"},
                                 method="POST")
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    log.info("LIVE ORDER %s -> %s", intent.ticker, resp.get("order", {}).get("status"))
    return resp
