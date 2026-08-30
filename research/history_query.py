"""Bounded read-only queries over Mercury's persisted JSONL research files."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional


def _dt(value: str) -> datetime:
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def query_jsonl(
    path: str,
    start_iso: str,
    end_iso: str,
    limit: int = 1000,
    city: Optional[str] = None,
    channel: Optional[str] = None,
    kind: Optional[str] = None,
    ticker: Optional[str] = None,
) -> dict:
    """Return rows in an inclusive timestamp window without mutating the file."""
    start = _dt(start_iso)
    end = _dt(end_iso)
    if end < start:
        raise ValueError("end must be >= start")

    limit = max(1, min(int(limit), 5000))
    exists = os.path.exists(path)
    if not exists:
        return {"file_exists": False, "count": 0, "truncated": False, "rows": []}

    rows = []
    matched = 0
    with open(path) as f:
        for line in f:
            try:
                row = json.loads(line)
            except Exception:
                continue

            ts = row.get("ts")
            if not ts:
                continue
            try:
                when = _dt(str(ts))
            except Exception:
                continue
            if when < start or when > end:
                continue
            if city is not None and row.get("city") != city:
                continue
            if channel is not None and row.get("channel") != channel:
                continue
            if kind is not None and row.get("kind") != kind:
                continue
            if ticker is not None:
                # Some event rows store the ticker only inside msg/detail fields.
                if ticker not in json.dumps(row, separators=(",", ":"), sort_keys=True):
                    continue

            matched += 1
            if len(rows) < limit:
                rows.append(row)

    stat = os.stat(path)
    return {
        "file_exists": True,
        "file": os.path.basename(path),
        "size_bytes": stat.st_size,
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "matched": matched,
        "count": len(rows),
        "truncated": matched > len(rows),
        "rows": rows,
    }
