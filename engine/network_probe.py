"""Credential-free network-path measurements for Mercury's race worker.

This does not authenticate, subscribe, or trade. It measures DNS, TCP connect,
and TLS handshake time from the actual deployment region to the endpoints that
matter. Results let us choose Railway/AWS placement empirically before enabling
Kalshi FIX or FAA push feeds.
"""
from __future__ import annotations

import json
import os
import socket
import ssl
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

TARGETS = [
    ("kalshi-rest", "external-api.kalshi.com", 443),
    ("kalshi-wss", "external-api-ws.kalshi.com", 443),
    ("kalshi-fix-order", "mm.fix.elections.kalshi.com", 8228),
    ("kalshi-fix-marketdata", "marketdata.fix.elections.kalshi.com", 8233),
    ("nws-tgftp", "tgftp.nws.noaa.gov", 443),
    ("aviationweather", "aviationweather.gov", 443),
    ("madis", "madis-data.ncep.noaa.gov", 443),
    ("iem", "mesonet.agron.iastate.edu", 443),
]


def probe_tls(name: str, host: str, port: int, timeout: float = 3.0) -> dict:
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "name": name,
        "host": host,
        "port": port,
        "ok": False,
    }
    t0 = time.perf_counter_ns()
    try:
        info = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        t_dns = time.perf_counter_ns()
        if not info:
            raise OSError("no addresses")
        family, socktype, proto, _, sockaddr = info[0]
        raw = socket.socket(family, socktype, proto)
        raw.settimeout(timeout)
        try:
            t1 = time.perf_counter_ns()
            raw.connect(sockaddr)
            t_tcp = time.perf_counter_ns()
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(raw, server_hostname=host) as tls:
                t_tls = time.perf_counter_ns()
                row.update(
                    ok=True,
                    ip=sockaddr[0],
                    tls_version=tls.version(),
                    dns_ms=round((t_dns - t0) / 1e6, 3),
                    tcp_ms=round((t_tcp - t1) / 1e6, 3),
                    tls_ms=round((t_tls - t_tcp) / 1e6, 3),
                    total_ms=round((t_tls - t0) / 1e6, 3),
                )
        finally:
            try:
                raw.close()
            except Exception:
                pass
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
        row["total_ms"] = round((time.perf_counter_ns() - t0) / 1e6, 3)
    return row


class NetworkProbeWorker:
    def __init__(self, stop: threading.Event, data_dir: str | Path | None = None):
        self.stop = stop
        self.interval_s = float(os.getenv("MERCURY_NETWORK_PROBE_S", "60"))
        root = Path(data_dir or os.getenv("WEATHERBOT_DATA_DIR", "/data"))
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "network_race.jsonl"

    def run(self) -> None:
        while not self.stop.is_set():
            for target in TARGETS:
                if self.stop.is_set():
                    return
                row = probe_tls(*target)
                try:
                    with self.path.open("a") as f:
                        f.write(json.dumps(row, separators=(",", ":")) + "\n")
                except Exception:
                    pass
                print(json.dumps({"network_probe": row}, separators=(",", ":")), flush=True)
            self.stop.wait(self.interval_s)
