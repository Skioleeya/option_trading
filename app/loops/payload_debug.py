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
    header_volatility = getattr(frozen, "header_volatility", None)
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
    if isinstance(header_volatility, dict):
        logger.info(
            "[L3-PAYLOAD] tick_id=%s header_volatility lookback=%s effective_days=%s "
            "ivr=%s ivp=%s term_1d_ratio=%s term_1d_state=%s term_vx_ratio=%s "
            "relation_state=%s relation_beta=%s",
            tick_id,
            header_volatility.get("lookback_days"),
            header_volatility.get("lookback_effective_days"),
            _header_scalar(header_volatility.get("ivr")),
            _header_scalar(header_volatility.get("ivp")),
            _header_ratio(header_volatility, ("term_structure", "primary", "ratio")),
            _header_text(header_volatility, ("term_structure", "primary", "state")),
            _header_ratio(header_volatility, ("term_structure", "secondary", "ratio")),
            _header_text(header_volatility, ("iv_price_relation", "state")),
            _header_scalar(_nested_get(header_volatility, ("iv_price_relation", "beta_pp_per_pct"))),
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


def _nested_get(payload: Any, path: tuple[str, ...]) -> Any:
    current = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _header_ratio(payload: dict[str, Any], path: tuple[str, ...]) -> str:
    return _header_scalar(_nested_get(payload, path))


def _header_text(payload: dict[str, Any], path: tuple[str, ...]) -> str:
    value = _nested_get(payload, path)
    if value is None:
        return "NA"
    return str(value)


def _header_scalar(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "NA"
    return f"{numeric:.4f}"
