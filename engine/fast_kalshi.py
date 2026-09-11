"""Low-latency Kalshi market-data + order path.

This module is intentionally isolated from the current production runtime. It is
safe to run in shadow mode and becomes live only when WEATHERBOT_LIVE=yes and
Kalshi credentials are present.

Goals:
- keep the orderbook in RAM from Kalshi WebSocket deltas;
- never fetch a quote after a weather proof arrives;
- load/parse the RSA key once;
- reuse one HTTP/2 connection pool for fallback REST order entry;
- use Kalshi's current external-api host + V2 event-order endpoint.

FIX order entry should replace REST when account access is available; see
LOW_LATENCY_ARCHITECTURE.md.
"""
from __future__ import annotations

import base64
import json
import logging
import math
import os
import threading
import time
from decimal import Decimal
from pathlib import Path
from typing import Iterable

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from websockets.sync.client import connect as ws_connect

from strategy import Intent

log = logging.getLogger("fast_kalshi")

REST_ORIGIN = "https://external-api.kalshi.com"
WS_URL = "wss://external-api-ws.kalshi.com/trade-api/ws/v2"
WS_PATH = "/trade-api/ws/v2"
ORDER_PATH = "/trade-api/v2/portfolio/events/orders"


def _read_private_key():
    raw = os.environ.get("KALSHI_PRIVATE_KEY", "")
    if not raw:
        return None
    p = Path(raw)
    pem = p.read_bytes() if p.exists() else raw.encode()
    return serialization.load_pem_private_key(pem, password=None)


class KalshiSigner:
    """Loads the RSA key once; signing remains per-request because ts changes."""

    def __init__(self):
        self.key_id = os.environ.get("KALSHI_KEY_ID")
        self.private_key = _read_private_key()

    @property
    def available(self) -> bool:
        return bool(self.key_id and self.private_key)

    def headers(self, method: str, path: str) -> dict[str, str]:
        if not self.available:
            raise RuntimeError("Kalshi credentials are not configured")
        ts = str(int(time.time() * 1000))
        msg = (ts + method.upper() + path).encode()
        sig = self.private_key.sign(
            msg,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        return {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
        }


class KalshiBookCache:
    """Thread-safe in-memory YES/NO bid books from the authenticated WS stream."""

    def __init__(self, signer: KalshiSigner | None = None):
        self.signer = signer or KalshiSigner()
        self._lock = threading.RLock()
        self._books: dict[str, dict[str, dict[Decimal, Decimal]]] = {}
        self._last_exchange_ts_ms: dict[str, int] = {}
        self._tickers: set[str] = set()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.connected = False
        self.last_message_monotonic = 0.0

    def start(self, tickers: Iterable[str]) -> None:
        self._tickers = {t for t in tickers if t}
        if not self._tickers:
            raise ValueError("No tickers supplied to KalshiBookCache")
        if not self.signer.available:
            raise RuntimeError("Kalshi credentials required for WebSocket")
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="kalshi-ws-book")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def quote(self, ticker: str) -> tuple[int | None, int | None]:
        """Return conservative whole-cent (YES bid, YES ask) from RAM.

        Strategy V1 reasons in whole cents. With subpenny books, the bid is
        floored and ask is ceiled so we never make a stale price look better than
        it really is.
        """
        with self._lock:
            b = self._books.get(ticker)
            if not b:
                return None, None
            yes = b["yes"]
            no = b["no"]
            best_yes = max(yes) if yes else None
            best_no = max(no) if no else None
        bid = math.floor(float(best_yes) * 100 + 1e-9) if best_yes is not None else None
        ask = math.ceil((1.0 - float(best_no)) * 100 - 1e-9) if best_no is not None else None
        return bid, ask

    def yes_levels(self, ticker: str) -> list[tuple[float, float]]:
        """Best-first resting YES bids as (price cents, quantity)."""
        with self._lock:
            yes = dict(self._books.get(ticker, {}).get("yes", {}))
        return [(float(px) * 100.0, float(qty)) for px, qty in sorted(yes.items(), reverse=True)]

    def _apply_snapshot(self, msg: dict) -> None:
        ticker = msg.get("market_ticker")
        if not ticker:
            return
        yes = {Decimal(px): Decimal(qty) for px, qty in msg.get("yes_dollars_fp", [])}
        no = {Decimal(px): Decimal(qty) for px, qty in msg.get("no_dollars_fp", [])}
        with self._lock:
            self._books[ticker] = {"yes": yes, "no": no}

    def _apply_delta(self, msg: dict) -> None:
        ticker = msg.get("market_ticker")
        side = msg.get("side")
        if not ticker or side not in ("yes", "no"):
            return
        px = Decimal(str(msg["price_dollars"]))
        delta = Decimal(str(msg["delta_fp"]))
        with self._lock:
            book = self._books.setdefault(ticker, {"yes": {}, "no": {}})[side]
            qty = book.get(px, Decimal("0")) + delta
            if qty <= 0:
                book.pop(px, None)
            else:
                book[px] = qty
            if msg.get("ts_ms") is not None:
                self._last_exchange_ts_ms[ticker] = int(msg["ts_ms"])

    def _run(self) -> None:
        backoff = 0.25
        while not self._stop.is_set():
            try:
                headers = self.signer.headers("GET", WS_PATH)
                with ws_connect(
                    WS_URL,
                    additional_headers=headers,
                    open_timeout=5,
                    close_timeout=2,
                    ping_interval=15,
                    ping_timeout=10,
                    max_queue=4096,
                ) as ws:
                    ws.send(json.dumps({
                        "id": 1,
                        "cmd": "subscribe",
                        "params": {
                            "channels": ["orderbook_delta"],
                            "market_tickers": sorted(self._tickers),
                            # Keep the currently documented legacy orderbook scale
                            # explicit: no-side levels are NO prices. Strategy only
                            # requires YES bids, but quote() also derives YES ask.
                            "use_yes_price": False,
                        },
                    }, separators=(",", ":")))
                    self.connected = True
                    backoff = 0.25
                    for raw in ws:
                        if self._stop.is_set():
                            return
                        self.last_message_monotonic = time.monotonic()
                        obj = json.loads(raw)
                        typ = obj.get("type")
                        msg = obj.get("msg") or {}
                        if typ == "orderbook_snapshot":
                            self._apply_snapshot(msg)
                        elif typ == "orderbook_delta":
                            self._apply_delta(msg)
                        elif typ == "error":
                            log.error("Kalshi WS error: %s", msg)
            except Exception as exc:
                self.connected = False
                log.warning("Kalshi WS reconnect after error: %s", exc)
                self._stop.wait(backoff)
                backoff = min(backoff * 2, 5.0)
        self.connected = False


class FastRestExecutor:
    """Persistent fallback order path.

    This is materially faster than exec_live.py because it avoids loading the RSA
    key and establishing a fresh HTTPS connection for each proof. For the final
    race path, Kalshi FIX should be preferred when available.
    """

    def __init__(self, signer: KalshiSigner | None = None):
        self.signer = signer or KalshiSigner()
        self.client = httpx.Client(
            base_url=REST_ORIGIN,
            http2=True,
            timeout=httpx.Timeout(2.0, connect=1.0),
            limits=httpx.Limits(max_keepalive_connections=4, max_connections=8,
                                keepalive_expiry=120.0),
            headers={"User-Agent": "mercury-edge-race/1"},
        )

    @property
    def enabled(self) -> bool:
        return os.environ.get("WEATHERBOT_LIVE") == "yes" and self.signer.available

    def execute(self, intent: Intent) -> dict:
        if not self.enabled:
            return {"mode": "DISABLED", "ticker": intent.ticker}

        # V2 event-order API quotes the YES leg directly. Asking YES at min_px is
        # economically equivalent to buying NO at 1-min_px and consumes resting
        # YES bids at min_px or better.
        body = {
            "ticker": intent.ticker,
            "client_order_id": f"mercury-{time.time_ns()}",
            "side": "ask",
            "count": f"{float(intent.max_size):.2f}",
            "price": f"{intent.min_px / 100.0:.4f}",
            "time_in_force": "immediate_or_cancel",
            "self_trade_prevention_type": "taker_at_cross",
            "post_only": False,
            "cancel_order_on_pause": True,
            "reduce_only": False,
            "subaccount": 0,
        }
        t0 = time.perf_counter_ns()
        headers = {
            **self.signer.headers("POST", ORDER_PATH),
            "Content-Type": "application/json",
        }
        t_signed = time.perf_counter_ns()
        resp = self.client.post(ORDER_PATH, headers=headers, json=body)
        t_done = time.perf_counter_ns()
        resp.raise_for_status()
        out = resp.json()
        out["_mercury_latency_ms"] = {
            "sign": round((t_signed - t0) / 1e6, 3),
            "post_roundtrip": round((t_done - t_signed) / 1e6, 3),
            "total": round((t_done - t0) / 1e6, 3),
        }
        return out


SIGNER = KalshiSigner()
BOOK = KalshiBookCache(SIGNER)
EXECUTOR = FastRestExecutor(SIGNER)
