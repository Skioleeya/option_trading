"""Utility helpers for the research feature store."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

_ET = ZoneInfo("US/Eastern")
_UTC = timezone.utc


def coerce_timestamp(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        dt = raw
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_UTC)
    return dt.astimezone(_UTC)


def extract_as_of_utc(snapshot: Any, payload: Any, ts: datetime) -> str:
    extra = getattr(snapshot, "extra_metadata", None)
    if isinstance(extra, dict):
        raw = extra.get("source_data_timestamp_utc")
        dt = coerce_timestamp(raw)
        if dt is not None:
            return dt.isoformat()
    payload_ts = coerce_timestamp(getattr(payload, "data_timestamp", None))
    if payload_ts is not None:
        return payload_ts.isoformat()
    return ts.isoformat()


def iter_trade_dates(start_dt: datetime, end_dt: datetime) -> list[str]:
    cur = start_dt.astimezone(_ET).date()
    end = end_dt.astimezone(_ET).date()
    out: list[str] = []
    while cur <= end:
        out.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)
    return out


def in_range(ts: datetime | None, start_dt: datetime, end_dt: datetime) -> bool:
    if ts is None:
        return False
    return start_dt <= ts <= end_dt


def coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def to_float(value: Any, default: float | None = None) -> float | None:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(num):
        return default
    return num


def coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean_v = sum(values) / len(values)
    var = sum((x - mean_v) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(max(var, 0.0))


def f32(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
