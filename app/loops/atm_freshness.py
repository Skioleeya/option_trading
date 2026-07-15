"""ATM decay source freshness context builder."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from app.loops.shared_state import SharedLoopState

ATM_SOURCE_STALE_MS = 10_000.0
MILLISECONDS_PER_SECOND = 1_000.0


def build_atm_source_freshness(
    *,
    snapshot: dict[str, Any],
    state: SharedLoopState,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Build source-freshness metadata for one ATM decay update."""
    quote_lane = _select_quote_lane(snapshot, state)
    source_ts = _select_source_timestamp(snapshot, quote_lane)
    source_gap_ms = _finite_float(quote_lane.get("last_source_gap_ms"))
    source_dt = _parse_utc(source_ts)
    age_ms = _age_ms(source_dt, now_utc or datetime.now(timezone.utc))

    stale_reason = _stale_reason(source_ts=source_ts, age_ms=age_ms)
    source_stale = stale_reason is not None
    stale_recovery = False
    if source_stale:
        state.atm_source_was_stale = True
    else:
        stale_recovery = bool(state.atm_source_was_stale) or (
            source_gap_ms is not None and source_gap_ms > ATM_SOURCE_STALE_MS
        )
        state.atm_source_was_stale = False

    return {
        "source_timestamp": source_ts,
        "source_gap_ms": source_gap_ms,
        "source_age_ms": age_ms,
        "source_stale": source_stale,
        "stale_recovery": stale_recovery,
        "reason": stale_reason,
    }


def _select_quote_lane(snapshot: dict[str, Any], state: SharedLoopState) -> dict[str, Any]:
    telemetry = snapshot.get("governor_telemetry")
    if isinstance(telemetry, dict) and isinstance(telemetry.get("quote_lane"), dict):
        return dict(telemetry["quote_lane"])
    if isinstance(state.latest_quote_lane_telemetry, dict):
        return dict(state.latest_quote_lane_telemetry)
    return {}


def _select_source_timestamp(snapshot: dict[str, Any], quote_lane: dict[str, Any]) -> str | None:
    for raw in (
        quote_lane.get("source_data_timestamp_utc"),
        quote_lane.get("last_source_timestamp_utc"),
        snapshot.get("as_of_utc"),
        snapshot.get("data_timestamp"),
        snapshot.get("timestamp"),
    ):
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def _finite_float(raw: Any) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _parse_utc(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_ms(source_dt: datetime | None, now_utc: datetime) -> float | None:
    if source_dt is None:
        return None
    current = now_utc.astimezone(timezone.utc)
    return max(0.0, (current - source_dt).total_seconds() * MILLISECONDS_PER_SECOND)


def _stale_reason(*, source_ts: str | None, age_ms: float | None) -> str | None:
    if not source_ts:
        return "missing_source_timestamp"
    if age_ms is None:
        return "invalid_source_timestamp"
    if age_ms > ATM_SOURCE_STALE_MS:
        return "source_age_stale"
    return None
