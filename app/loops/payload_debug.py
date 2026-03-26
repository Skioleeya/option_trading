"""Structured debug helpers for live payload observability."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

ET = ZoneInfo("US/Eastern")
PAYLOAD_DEBUG_DUPLICATE_EVERY_TICKS = 30


def should_log_duplicate_payload_debug(tick_id: int) -> bool:
    return tick_id % PAYLOAD_DEBUG_DUPLICATE_EVERY_TICKS == 0


def emit_payload_debug(
    logger: Any,
    *,
    frozen: Any,
    tick_id: int,
    snapshot_version: int,
    duplicate_snapshot: bool,
) -> None:
    if frozen is None:
        logger.info(
            "[L3-PAYLOAD] tick_id=%s snapshot_version=%s duplicate=%s payload=missing",
            tick_id,
            snapshot_version,
            duplicate_snapshot,
        )
        return

    depth_rows = tuple(getattr(getattr(frozen, "ui_state", None), "depth_profile", ()) or ())
    depth_count = len(depth_rows)
    put_peak = max(depth_rows, key=lambda row: float(getattr(row, "put_pct", 0.0) or 0.0), default=None)
    call_peak = max(depth_rows, key=lambda row: float(getattr(row, "call_pct", 0.0) or 0.0), default=None)
    spot_row = next((row for row in depth_rows if bool(getattr(row, "is_spot", False))), None)
    flip_row = next((row for row in depth_rows if bool(getattr(row, "is_flip", False))), None)

    atm = getattr(frozen, "atm", None)
    now_et = datetime.now(ET)
    in_regular_hours = (
        (now_et.hour > 9 or (now_et.hour == 9 and now_et.minute >= 30))
        and (now_et.hour < 16 or (now_et.hour == 16 and now_et.minute == 0 and now_et.second == 0))
    )
    atm_status = "LIVE" if isinstance(atm, dict) else ("MISSING_OUTSIDE_RTH" if not in_regular_hours else "MISSING")

    logger.info(
        "[L3-PAYLOAD] tick_id=%s snapshot_version=%s duplicate=%s "
        "depth_rows=%s depth_spot=%s depth_flip=%s depth_put_peak=%s depth_put_pct=%s "
        "depth_call_peak=%s depth_call_pct=%s atm_status=%s atm_ts=%s atm_straddle=%s atm_call=%s atm_put=%s",
        tick_id,
        snapshot_version,
        duplicate_snapshot,
        depth_count,
        _row_strike(spot_row),
        _row_strike(flip_row),
        _row_strike(put_peak),
        _row_pct(put_peak, "put_pct"),
        _row_strike(call_peak),
        _row_pct(call_peak, "call_pct"),
        atm_status,
        _atm_value(atm, "timestamp"),
        _atm_value(atm, "straddle_pct"),
        _atm_value(atm, "call_pct"),
        _atm_value(atm, "put_pct"),
    )


def _row_strike(row: Any) -> str:
    if row is None:
        return "NA"
    strike = getattr(row, "strike", None)
    try:
        return f"{float(strike):.2f}"
    except (TypeError, ValueError):
        return "NA"


def _row_pct(row: Any, field: str) -> str:
    if row is None:
        return "NA"
    value = getattr(row, field, None)
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return "NA"


def _atm_value(atm: Any, field: str) -> str:
    if not isinstance(atm, dict):
        return "NA"
    value = atm.get(field)
    if value is None:
        return "NA"
    return str(value)
