"""Minimal persistent KalshiNR FIX order transport for Mercury.

Not wired into production. Enable only after a successful FIX entitlement/demo
session test.

Mercury's ``SELL_YES`` maps to Kalshi's canonical no/ask direction. Kalshi's
order-direction docs state that sell-yes and buy-no both produce outcome_side=no
(book_side=ask), while direction does not change the order price. FIX Side<54>
uses ``2=Sell (No)``, so the hot-path IOC uses Side=2 with the same yes-leg price
that Mercury's strategy selected.
"""
from __future__ import annotations

import base64
import logging
import os
import socket
import ssl
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from fast_kalshi import KalshiSigner, kill_client_order_id
from strategy import Intent

log = logging.getLogger("kalshi_fix")
SOH = "\x01"
HOST = os.getenv("KALSHI_FIX_HOST", "mm.fix.elections.kalshi.com")
PORT = int(os.getenv("KALSHI_FIX_PORT", "8228"))
TARGET = os.getenv("KALSHI_FIX_TARGET", "KalshiNR")
TERMINAL_EXEC_TYPES = {"F", "4", "8", "C"}  # Trade, Canceled, Rejected, Expired


def utc_fix_time(now: datetime | None = None) -> str:
    dt = now or datetime.now(timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y%m%d-%H:%M:%S.") + f"{dt.microsecond // 1000:03d}"


def parse_fix(raw: bytes | str) -> dict[str, str]:
    text = raw.decode(errors="replace") if isinstance(raw, bytes) else raw
    out: dict[str, str] = {}
    for field in text.strip(SOH).split(SOH):
        if "=" not in field:
            continue
        k, v = field.split("=", 1)
        out[k] = v
    return out


def encode_fix(fields: list[tuple[int | str, str]], begin: str = "FIXT.1.1") -> bytes:
    """Build one FIX message with exact BodyLength and CheckSum."""
    body = "".join(f"{tag}={value}{SOH}" for tag, value in fields)
    head = f"8={begin}{SOH}9={len(body.encode())}{SOH}"
    partial = (head + body).encode()
    checksum = sum(partial) % 256
    return partial + f"10={checksum:03d}{SOH}".encode()


def split_fix_messages(buf: bytes) -> tuple[list[bytes], bytes]:
    """Extract complete FIX frames from a TCP byte stream."""
    out = []
    while True:
        start = buf.find(b"8=FIXT.1.1\x01")
        if start < 0:
            return out, buf[-32:]
        if start:
            buf = buf[start:]
        marker = buf.find(b"\x0110=", 12)
        if marker < 0 or len(buf) < marker + 8:
            return out, buf
        end = buf.find(b"\x01", marker + 1)
        if end < 0:
            return out, buf
        out.append(buf[:end + 1])
        buf = buf[end + 1:]


@dataclass
class FixResult:
    client_order_id: str
    status: str
    fields: dict[str, str]
    send_to_report_ms: float | None = None


class KalshiFixOrderSession:
    """One hot KalshiNR TLS/FIX session.

    Kalshi allows one active FIX connection per API key, so reconnect attempts
    are serialized inside this object rather than spawned concurrently.
    """

    def __init__(self, signer: KalshiSigner | None = None):
        self.signer = signer or KalshiSigner()
        self.sender = self.signer.key_id or ""
        self.target = TARGET
        self.host, self.port = HOST, PORT
        self.heartbeat_s = max(5, int(os.getenv("KALSHI_FIX_HEARTBEAT_S", "15")))
        self.sock: ssl.SSLSocket | None = None
        self.seq = 1
        self._lock = threading.RLock()
        self._send_lock = threading.Lock()
        self._stop = threading.Event()
        self._reader: threading.Thread | None = None
        self._logged_on = threading.Event()
        self._pending: dict[str, tuple[float, threading.Event, list[dict[str, str]]]] = {}
        self._last_rx = time.monotonic()
        self._last_tx = time.monotonic()

    @property
    def available(self) -> bool:
        return self.signer.available and bool(self.sender)

    @property
    def connected(self) -> bool:
        return bool(self.sock and self._logged_on.is_set())

    def _header(self, msg_type: str, sending_time: str | None = None) -> list[tuple[int, str]]:
        """Return Kalshi's documented standard-header ordering after tags 8/9."""
        ts = sending_time or utc_fix_time()
        with self._lock:
            seq = self.seq
            self.seq += 1
        return [
            (35, msg_type), (49, self.sender), (56, self.target),
            (34, str(seq)), (52, ts),
        ]

    def _logon_signature(self, sending_time: str, seq: int) -> str:
        if not self.signer.available:
            raise RuntimeError("Kalshi key unavailable")
        prehash = SOH.join([
            sending_time, "A", str(seq), self.sender, self.target,
        ]).encode()
        sig = self.signer.private_key.sign(
            prehash,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256(),
        )
        return base64.b64encode(sig).decode()

    def _send_fields(self, fields: list[tuple[int | str, str]]) -> None:
        raw = encode_fix(fields)
        with self._send_lock:
            if not self.sock:
                raise ConnectionError("FIX socket not connected")
            self.sock.sendall(raw)
            self._last_tx = time.monotonic()

    def connect(self, timeout_s: float = 5.0) -> None:
        if not self.available:
            raise RuntimeError("KALSHI_KEY_ID/private key required")
        self.close()
        self._stop.clear()
        self._logged_on.clear()
        self.seq = 1
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        raw = socket.create_connection((self.host, self.port), timeout=timeout_s)
        raw.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock = context.wrap_socket(raw, server_hostname=self.host)
        sock.settimeout(1.0)
        self.sock = sock

        # Build Logon manually so signature seq/time exactly match tags 34/52.
        sending_time = utc_fix_time()
        seq = self.seq
        self.seq += 1
        signature = self._logon_signature(sending_time, seq)
        fields = [
            (35, "A"), (49, self.sender), (56, self.target),
            (34, str(seq)), (52, sending_time),
            (98, "0"), (96, signature), (108, str(self.heartbeat_s)),
            (1137, "9"), (141, "Y"), (8013, "N"), (21011, "Y"),
        ]
        self._send_fields(fields)
        self._reader = threading.Thread(target=self._read_loop, daemon=True,
                                        name="kalshi-fix-reader")
        self._reader.start()
        if not self._logged_on.wait(timeout_s):
            self.close()
            raise TimeoutError("Kalshi FIX logon not acknowledged")

    def close(self) -> None:
        self._stop.set()
        self._logged_on.clear()
        s, self.sock = self.sock, None
        if s:
            try:
                s.close()
            except Exception:
                pass

    def _session_reply(self, fields: dict[str, str]) -> None:
        typ = fields.get("35")
        if typ == "0":
            return
        if typ == "1":
            hdr = self._header("0")
            req = fields.get("112")
            if req:
                hdr.append((112, req))
            self._send_fields(hdr)
        elif typ == "5":
            log.error("Kalshi FIX logout: %s", fields.get("58", ""))
            self._logged_on.clear()

    def _read_loop(self) -> None:
        buf = b""
        try:
            while not self._stop.is_set() and self.sock:
                try:
                    chunk = self.sock.recv(65536)
                except socket.timeout:
                    if time.monotonic() - self._last_tx >= self.heartbeat_s:
                        self._send_fields(self._header("0"))
                    continue
                if not chunk:
                    raise ConnectionError("FIX peer closed")
                buf += chunk
                messages, buf = split_fix_messages(buf)
                for raw in messages:
                    self._last_rx = time.monotonic()
                    f = parse_fix(raw)
                    typ = f.get("35")
                    if typ == "A":
                        self._logged_on.set()
                        continue
                    if typ in {"0", "1", "5"}:
                        self._session_reply(f)
                        continue
                    if typ == "3":
                        log.error("Kalshi FIX session reject: %s", f.get("58", ""))
                        continue
                    if typ == "8":
                        clid = f.get("11")
                        if not clid:
                            continue
                        pending = self._pending.get(clid)
                        if not pending:
                            continue
                        _sent, event, reports = pending
                        reports.append(f)
                        # Do not wake execute() on PendingNew/New. For IOC, wait
                        # until a trade or terminal cancel/reject/expiry arrives.
                        if f.get("150") in TERMINAL_EXEC_TYPES:
                            event.set()
        except Exception as exc:
            if not self._stop.is_set():
                log.warning("Kalshi FIX reader ended: %s", exc)
        finally:
            self._logged_on.clear()

    def execute(self, intent: Intent, timeout_s: float = 1.0) -> FixResult:
        if intent.action != "SELL_YES":
            raise ValueError(f"FIX hot path only supports SELL_YES, got {intent.action}")
        if not self.connected:
            raise ConnectionError("FIX session not logged on")
        clid = kill_client_order_id(intent)
        event = threading.Event()
        reports: list[dict[str, str]] = []
        sent = time.perf_counter()
        self._pending[clid] = (sent, event, reports)
        try:
            fields = self._header("D") + [
                (11, clid),
                (38, f"{float(intent.max_size):.2f}"),
                (40, "2"),             # Limit
                (54, "2"),             # SELL_YES -> no/ask outcome direction
                (55, intent.ticker),
                (44, str(int(intent.min_px))),  # price scale does not flip
                (59, "3"),             # IOC
                (2964, "1"),           # Taker-at-cross STP
                (21006, "Y"),           # Cancel on pause
            ]
            self._send_fields(fields)
            if not event.wait(timeout_s):
                return FixResult(clid, "AMBIGUOUS_TIMEOUT", {}, None)
            report = reports[-1]
            elapsed = (time.perf_counter() - sent) * 1000.0
            exec_type = report.get("150", "")
            text = report.get("58", "")
            if exec_type == "8" and text == "EXCHANGE_UNAVAILABLE":
                status = "AMBIGUOUS_EXCHANGE_UNAVAILABLE"
            else:
                status = {
                    "F": "TRADE", "4": "CANCELED", "8": "REJECTED",
                    "C": "EXPIRED",
                }.get(exec_type, f"EXEC_{exec_type or 'UNKNOWN'}")
            return FixResult(clid, status, report, round(elapsed, 3))
        finally:
            self._pending.pop(clid, None)
