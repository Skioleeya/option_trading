"""Rust-backed ATM raw pct computation with leg freshness validation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from shared_rust.services import atm_decay_raw_pct

from .models import mid_price

LEG_MAX_AGE_MS = 10_000.0
LEG_MAX_SKEW_MS = 2_000.0
MILLISECONDS_PER_SECOND = 1_000.0


@dataclass(frozen=True)
class RawPctResult:
    raw_pcts: tuple[float, float, float] | None
    leg_freshness: dict[str, Any]
    failure_kind: str | None = None


def calculate_raw_pct(
    anchor: dict[str, Any] | None,
    chain: list[dict[str, Any]],
    *,
    source_timestamp: str | None = None,
    require_freshness: bool = False,
) -> tuple[float, float, float] | None:
    return calculate_raw_pct_result(
        anchor,
        chain,
        source_timestamp=source_timestamp,
        require_freshness=require_freshness,
    ).raw_pcts


def calculate_raw_pct_result(
    anchor: dict[str, Any] | None,
    chain: list[dict[str, Any]],
    *,
    source_timestamp: str | None,
    require_freshness: bool,
) -> RawPctResult:
    empty = _empty_leg_freshness(anchor)
    if not anchor:
        return RawPctResult(None, empty, "price")

    call_symbol = str(anchor.get("call_symbol") or "")
    put_symbol = str(anchor.get("put_symbol") or "")
    call_leg = _find_leg(chain, call_symbol)
    put_leg = _find_leg(chain, put_symbol)
    leg_freshness = build_leg_freshness(
        call_leg=call_leg,
        put_leg=put_leg,
        call_symbol=call_symbol,
        put_symbol=put_symbol,
        source_timestamp=source_timestamp,
    )
    if require_freshness and leg_freshness.get("status") != "fresh":
        return RawPctResult(None, leg_freshness, "freshness")

    current_call = _leg_mid(call_leg)
    current_put = _leg_mid(put_leg)
    if current_call <= 0.0 or current_put <= 0.0:
        leg_freshness["status"] = "missing"
        leg_freshness["reason"] = "non_positive_mid"
        return RawPctResult(None, leg_freshness, "price")

    try:
        raw = atm_decay_raw_pct(
            float(anchor.get("call_price")),
            float(anchor.get("put_price")),
            current_call,
            current_put,
        )
    except (TypeError, ValueError) as exc:
        leg_freshness["status"] = "missing"
        leg_freshness["reason"] = f"rust_raw_pct_error:{exc}"
        return RawPctResult(None, leg_freshness, "price")
    raw_call, raw_put, raw_straddle = raw
    return RawPctResult((float(raw_call), float(raw_put), float(raw_straddle)), leg_freshness)


def build_leg_freshness(
    *,
    call_leg: dict[str, Any] | None,
    put_leg: dict[str, Any] | None,
    call_symbol: str,
    put_symbol: str,
    source_timestamp: str | None,
) -> dict[str, Any]:
    source_dt = _parse_utc(source_timestamp)
    call_dt = _leg_update_time(call_leg)
    put_dt = _leg_update_time(put_leg)
    call_age = _age_ms(call_dt, source_dt)
    put_age = _age_ms(put_dt, source_dt)
    skew = _skew_ms(call_dt, put_dt)
    status, reason = _classify_leg_freshness(
        call_leg=call_leg,
        put_leg=put_leg,
        source_dt=source_dt,
        call_age=call_age,
        put_age=put_age,
        skew=skew,
    )
    return {
        "status": status,
        "reason": reason,
        "call_symbol": call_symbol or None,
        "put_symbol": put_symbol or None,
        "call_age_ms": call_age,
        "put_age_ms": put_age,
        "call_put_skew_ms": skew,
    }


def _classify_leg_freshness(
    *,
    call_leg: dict[str, Any] | None,
    put_leg: dict[str, Any] | None,
    source_dt: datetime | None,
    call_age: float | None,
    put_age: float | None,
    skew: float | None,
) -> tuple[str, str | None]:
    if call_leg is None or put_leg is None:
        return "missing", "missing_leg"
    if source_dt is None:
        return "unknown", "missing_source_timestamp"
    if call_age is None or put_age is None or skew is None:
        return "unknown", "missing_leg_timestamp"
    if call_age > LEG_MAX_AGE_MS or put_age > LEG_MAX_AGE_MS:
        return "stale", "leg_age_stale"
    if skew > LEG_MAX_SKEW_MS:
        return "stale", "call_put_skew_stale"
    return "fresh", None


def _empty_leg_freshness(anchor: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "status": "missing",
        "reason": "missing_anchor",
        "call_symbol": (anchor or {}).get("call_symbol"),
        "put_symbol": (anchor or {}).get("put_symbol"),
        "call_age_ms": None,
        "put_age_ms": None,
        "call_put_skew_ms": None,
    }


def _find_leg(chain: list[dict[str, Any]], symbol: str) -> dict[str, Any] | None:
    return next((row for row in chain if row.get("symbol") == symbol), None)


def _leg_mid(row: dict[str, Any] | None) -> float:
    if row is None:
        return 0.0
    return mid_price(
        _positive_or_zero(row.get("bid")),
        _positive_or_zero(row.get("ask")),
        _positive_or_zero(row.get("last_price")),
    )


def _positive_or_zero(raw: Any) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0
    return value if math.isfinite(value) else 0.0


def _leg_update_time(row: dict[str, Any] | None) -> datetime | None:
    if not isinstance(row, dict):
        return None
    return _parse_utc(row.get("last_update_utc")) or _parse_utc(row.get("last_update"))


def _parse_utc(raw: Any) -> datetime | None:
    if isinstance(raw, datetime):
        parsed = raw
    elif isinstance(raw, str) and raw.strip():
        text = raw.strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_ms(leg_dt: datetime | None, source_dt: datetime | None) -> float | None:
    if leg_dt is None or source_dt is None:
        return None
    return max(0.0, (source_dt - leg_dt).total_seconds() * MILLISECONDS_PER_SECOND)


def _skew_ms(call_dt: datetime | None, put_dt: datetime | None) -> float | None:
    if call_dt is None or put_dt is None:
        return None
    return abs((call_dt - put_dt).total_seconds() * MILLISECONDS_PER_SECOND)
