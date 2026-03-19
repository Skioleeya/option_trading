"""ActiveOptions runtime support helpers.

Pure helper functions extracted from runtime_service to keep orchestration thin.
"""

from __future__ import annotations

from typing import Any

from shared.models.flow_engine import FlowEngineOutput
from .constants import (
    ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_ALL_ENGINES_INACTIVE,
    ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_MISSING_GAMMA,
    ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_MISSING_TURNOVER,
    ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_MISSING_VANNA,
    ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_DEGRADED,
    ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_LIVE,
    ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_MILLION,
    ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_THOUSAND,
    ACTIVE_OPTIONS_FLOW_ZSCORE_ROUND_DIGITS,
    ACTIVE_OPTIONS_PLACEHOLDER_SIGNATURE_PREFIX,
    ACTIVE_OPTIONS_SIGNATURE_STRIKE_ROUND_DIGITS,
)

_DIRECTION_COLOR = {
    "BULLISH": "text-accent-red",
    "BEARISH": "text-accent-green",
    "NEUTRAL": "text-text-secondary",
}

_INTENSITY_GLOW = {
    "EXTREME": "shadow-[0_0_12px_rgba(255,77,79,0.6)] animate-pulse",
    "HIGH": "shadow-[0_0_8px_rgba(255,77,79,0.35)]",
    "MODERATE": "",
    "LOW": "",
}

_OPTION_TYPE_KEYS = ("option_type", "type")
_STRIKE_KEYS = ("strike", "strike_price")
_VOLUME_KEYS = ("volume", "trade_volume", "total_volume")
_CURRENT_VOLUME_KEYS = ("current_volume", "currentVolume", "vol")
_TURNOVER_KEYS = ("turnover", "amount", "trade_amount", "total_turnover")
_OPEN_INTEREST_KEYS = ("open_interest", "openInterest", "oi")
_LAST_PRICE_KEYS = ("last_price", "last_done", "price", "mark_price")
_IV_KEYS = ("computed_iv", "implied_volatility", "iv")
_HV_KEYS = ("historical_volatility", "hv", "historical_volatility_decimal")
_DELTA_KEYS = ("computed_delta", "delta")
_GAMMA_KEYS = ("computed_gamma", "gamma")
_VANNA_KEYS = ("computed_vanna", "vanna")
_OUTPUT_FALLBACK_DEFAULT_DIRECTION = "NEUTRAL"
_OUTPUT_FALLBACK_DEFAULT_INTENSITY = "LOW"
ROW_QUALITY_REAL = "REAL"
ROW_QUALITY_FALLBACK_SYNTHETIC = "FALLBACK_SYNTHETIC"
ROW_QUALITY_PLACEHOLDER = "PLACEHOLDER"
FALLBACK_REASON_TURNOVER_OPEN_INTEREST = "turnover_open_interest"
FALLBACK_REASON_HARD_CHAIN = "hard_chain"
FALLBACK_REASON_ENGINE_EMPTY_OUTPUT = "engine_empty_output"
MAX_CHAIN_VOLUME = 1_000_000_000


def direction_from_flow_amount(flow_amount: float) -> str:
    if flow_amount > 0:
        return "BULLISH"
    if flow_amount < 0:
        return "BEARISH"
    return "NEUTRAL"


def classify_flow_signal(output: FlowEngineOutput) -> tuple[str, str | None]:
    reasons: list[str] = []
    if not bool(output.engine_d_active):
        reasons.append(ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_MISSING_GAMMA)
    if not bool(output.engine_e_active):
        reasons.append(ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_MISSING_VANNA)
    if not bool(output.engine_g_active):
        reasons.append(ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_MISSING_TURNOVER)

    if not reasons:
        return ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_LIVE, None
    if len(reasons) == 3:
        return (
            ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_DEGRADED,
            ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_ALL_ENGINES_INACTIVE,
        )
    return ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_DEGRADED, reasons[0]


def format_flow(val: float) -> str:
    abs_v = abs(val)
    sign = "" if val >= 0 else "-"
    prefix = "$"
    if abs_v >= ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_MILLION:
        return f"{sign}{prefix}{abs_v / ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_MILLION:.1f}M"
    if abs_v >= ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_THOUSAND:
        return f"{sign}{prefix}{abs_v / ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_THOUSAND:.0f}K"
    return f"{sign}{prefix}{int(abs_v)}"


def format_volume(v: int) -> str:
    if v >= ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_MILLION:
        return f"{v / ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_MILLION:.1f}M"
    if v >= ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_THOUSAND:
        return f"{v / ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_THOUSAND:.0f}K"
    return str(v)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _first_present(option_row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in option_row and not _is_missing(option_row.get(key)):
            return option_row.get(key)
    return None


def _from_option_extend(option_row: dict[str, Any], key: str) -> Any:
    option_extend = option_row.get("option_extend")
    if not isinstance(option_extend, dict):
        return None
    value = option_extend.get(key)
    return None if _is_missing(value) else value


def _normalize_option_type(option_row: dict[str, Any]) -> str:
    raw = _first_present(option_row, _OPTION_TYPE_KEYS)
    token = str(raw or "").strip().upper()
    if token in {"C", "CALL"}:
        return "CALL"
    if token in {"P", "PUT"}:
        return "PUT"
    return "CALL" if bool(option_row.get("is_call")) else "PUT"


def normalize_chain_volume_fields(option_row: dict[str, Any]) -> dict[str, Any]:
    """Normalize runtime row fields and apply volume fallback from current_volume."""
    normalized = dict(option_row)
    normalized["option_type"] = _normalize_option_type(option_row)

    strike_value = _first_present(option_row, _STRIKE_KEYS)
    if _is_missing(strike_value):
        strike_value = _from_option_extend(option_row, "strike_price")
    normalized["strike"] = max(0.0, _to_float(strike_value, 0.0))

    volume = _sanitize_chain_volume(_first_present(option_row, _VOLUME_KEYS))
    current_volume = _sanitize_chain_volume(_first_present(option_row, _CURRENT_VOLUME_KEYS))
    if volume <= 0 and current_volume > 0:
        volume = current_volume
    normalized["volume"] = volume
    normalized["current_volume"] = float(current_volume)

    turnover_value = _first_present(option_row, _TURNOVER_KEYS)
    normalized["turnover"] = max(0.0, _to_float(turnover_value, 0.0))

    open_interest_value = _first_present(option_row, _OPEN_INTEREST_KEYS)
    if _is_missing(open_interest_value):
        open_interest_value = _from_option_extend(option_row, "open_interest")
    normalized["open_interest"] = max(0, _to_int(open_interest_value, 0))

    last_price_value = _first_present(option_row, _LAST_PRICE_KEYS)
    normalized["last_price"] = max(0.0, _to_float(last_price_value, 0.0))

    implied_volatility_value = _first_present(option_row, _IV_KEYS)
    if _is_missing(implied_volatility_value):
        implied_volatility_value = _from_option_extend(option_row, "implied_volatility")
    normalized["implied_volatility"] = max(0.0, _to_float(implied_volatility_value, 0.0))

    historical_volatility_value = _first_present(option_row, _HV_KEYS)
    normalized["historical_volatility"] = max(0.0, _to_float(historical_volatility_value, 0.0))
    normalized["delta"] = _to_float(_first_present(option_row, _DELTA_KEYS), 0.0)
    normalized["gamma"] = _to_float(_first_present(option_row, _GAMMA_KEYS), 0.0)
    normalized["vanna"] = _to_float(_first_present(option_row, _VANNA_KEYS), 0.0)
    return normalized


def normalize_and_filter_chain(
    *,
    chain: list[dict[str, Any]],
    min_volume: int,
) -> list[dict[str, Any]]:
    normalized_chain = [normalize_chain_volume_fields(option_row) for option_row in chain]
    return [o for o in normalized_chain if int(o.get("volume", 0) or 0) >= min_volume]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _sanitize_chain_volume(value: Any) -> int:
    parsed = max(0, _to_int(value, 0))
    if parsed > MAX_CHAIN_VOLUME:
        return 0
    return parsed


def mark_rows_as_synthetic_fallback(
    rows: list[dict[str, Any]],
    *,
    fallback_reason: str,
) -> list[dict[str, Any]]:
    tagged: list[dict[str, Any]] = []
    for row in rows:
        updated = dict(row)
        if bool(updated.get("is_placeholder", False)):
            updated["row_quality"] = ROW_QUALITY_PLACEHOLDER
            updated["fallback_reason"] = None
            updated["is_synthetic_fallback"] = False
            updated["flow_signal_state"] = ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_DEGRADED
            updated["flow_signal_reason"] = ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_ALL_ENGINES_INACTIVE
        else:
            updated["row_quality"] = ROW_QUALITY_FALLBACK_SYNTHETIC
            updated["fallback_reason"] = fallback_reason
            updated["is_synthetic_fallback"] = True
            updated["flow_signal_state"] = ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_DEGRADED
            if _is_missing(updated.get("flow_signal_reason")):
                updated["flow_signal_reason"] = fallback_reason
        tagged.append(updated)
    return tagged


def _with_synthetic_volume_for_fallback(
    row: dict[str, Any],
    *,
    force_minimum: bool = False,
) -> dict[str, Any]:
    """Ensure fallback candidate has minimal positive volume for DEG engines."""
    out = dict(row)
    volume = _to_int(out.get("volume"), 0)
    if volume > 0:
        return out

    turnover = _to_float(out.get("turnover"), 0.0)
    if turnover <= 0.0:
        if _to_int(out.get("open_interest"), 0) > 0:
            out["volume"] = 1
        elif force_minimum:
            out["volume"] = 1
        return out

    last_price = _to_float(out.get("last_price"), 0.0)
    if last_price > 0.0:
        inferred = int(turnover / max(1e-6, last_price * 100.0))
        out["volume"] = max(1, inferred)
        return out

    out["volume"] = 1
    return out


def fallback_candidates_when_empty(
    *,
    chain: list[dict[str, Any]],
    max_candidates: int,
) -> tuple[list[dict[str, Any]], str]:
    """Build fallback candidates when min-volume filter returns empty.

    Priority: turnover desc -> open_interest desc -> stable key.
    """
    target = max(0, int(max_candidates))
    if target == 0:
        return [], "none"

    normalized = [normalize_chain_volume_fields(option_row) for option_row in chain]
    eligible = [
        row
        for row in normalized
        if _to_float(row.get("turnover"), 0.0) > 0.0 or _to_int(row.get("open_interest"), 0) > 0
    ]
    if eligible:
        ranked = sorted(
            eligible,
            key=lambda row: (
                -_to_float(row.get("turnover"), 0.0),
                -_to_int(row.get("open_interest"), 0),
                str(row.get("symbol", "")),
                _to_float(row.get("strike"), 0.0),
                str(row.get("option_type", row.get("type", ""))),
            ),
        )
        candidates = ranked[:target]
        return (
            [_with_synthetic_volume_for_fallback(row) for row in candidates],
            "turnover_open_interest",
        )

    if not normalized:
        return [], "none"

    ranked_hard = sorted(
        normalized,
        key=lambda row: (
            -_to_int(row.get("volume"), 0),
            -_to_int(row.get("open_interest"), 0),
            -_to_float(row.get("turnover"), 0.0),
            -_to_float(row.get("last_price"), 0.0),
            str(row.get("symbol", "")),
            _to_float(row.get("strike"), 0.0),
            str(row.get("option_type", row.get("type", ""))),
        ),
    )
    candidates = ranked_hard[:target]
    return (
        [_with_synthetic_volume_for_fallback(row, force_minimum=True) for row in candidates],
        "hard_chain",
    )


def rank_outputs(outputs: list[FlowEngineOutput]) -> list[FlowEngineOutput]:
    return sorted(
        outputs,
        key=lambda o: (
            -int(o.volume),
            -float(o.turnover),
            -float(o.impact_index),
            str(o.symbol),
            float(o.strike),
            str(o.option_type),
        ),
    )


def build_neutral_outputs_from_chain(
    *,
    filtered: list[dict[str, Any]],
    limit: int,
) -> list[FlowEngineOutput]:
    target = max(0, int(limit))
    if target <= 0:
        return []
    if not filtered:
        return []

    ranked = sorted(
        filtered,
        key=lambda row: (
            -_to_int(row.get("volume"), 0),
            -_to_float(row.get("turnover"), 0.0),
            -_to_int(row.get("open_interest"), 0),
            str(row.get("symbol", "")),
            _to_float(row.get("strike"), 0.0),
            str(row.get("option_type", row.get("type", ""))),
        ),
    )[:target]

    outputs: list[FlowEngineOutput] = []
    for row in ranked:
        option_type = str(row.get("option_type", "CALL")).strip().upper()
        if option_type not in {"CALL", "PUT"}:
            option_type = "CALL" if bool(row.get("is_call")) else "PUT"
        outputs.append(
            FlowEngineOutput(
                symbol=str(row.get("symbol", "SPY")),
                option_type=option_type,
                strike=float(_to_float(row.get("strike"), 0.0)),
                implied_volatility=float(_to_float(row.get("implied_volatility"), 0.0)),
                volume=max(0, _to_int(row.get("volume"), 0)),
                turnover=max(0.0, _to_float(row.get("turnover"), 0.0)),
                flow_d=0.0,
                flow_e=0.0,
                flow_g=0.0,
                flow_d_z=0.0,
                flow_e_z=0.0,
                flow_g_z=0.0,
                flow_deg=0.0,
                impact_index=0.0,
                is_sweep=False,
                flow_direction=_OUTPUT_FALLBACK_DEFAULT_DIRECTION,
                flow_intensity=_OUTPUT_FALLBACK_DEFAULT_INTENSITY,
                engine_d_active=False,
                engine_e_active=False,
                engine_g_active=False,
            )
        )
    return outputs


def format_row(o: FlowEngineOutput, *, slot_index: int = 1) -> dict[str, Any]:
    # UI semantics are amount-first: displayed FLOW sign must match direction/color.
    flow_amount = o.flow_d + o.flow_e + o.flow_g
    flow_direction = direction_from_flow_amount(flow_amount)
    flow_color = _DIRECTION_COLOR.get(flow_direction, "text-text-secondary")
    glow = _INTENSITY_GLOW.get(o.flow_intensity, "")
    flow_signal_state, flow_signal_reason = classify_flow_signal(o)

    return {
        "symbol": "SPY",
        "option_type": o.option_type,
        "strike": o.strike,
        "implied_volatility": o.implied_volatility,
        "volume": o.volume,
        "turnover": o.turnover,
        "flow": flow_amount,
        "flow_score": o.flow_deg,
        "impact_index": o.impact_index,
        "is_sweep": o.is_sweep,
        "flow_deg_formatted": format_flow(flow_amount),
        "flow_volume_label": format_volume(o.volume),
        "flow_color": flow_color,
        "flow_glow": glow if not o.is_sweep else "shadow-[0_0_15px_rgba(255,255,255,0.7)] animate-pulse",
        "flow_intensity": o.flow_intensity,
        "flow_direction": flow_direction,
        "flow_d_z": round(o.flow_d_z, ACTIVE_OPTIONS_FLOW_ZSCORE_ROUND_DIGITS),
        "flow_e_z": round(o.flow_e_z, ACTIVE_OPTIONS_FLOW_ZSCORE_ROUND_DIGITS),
        "flow_g_z": round(o.flow_g_z, ACTIVE_OPTIONS_FLOW_ZSCORE_ROUND_DIGITS),
        "is_placeholder": False,
        "row_quality": ROW_QUALITY_REAL,
        "fallback_reason": None,
        "is_synthetic_fallback": False,
        "flow_signal_state": flow_signal_state,
        "flow_signal_reason": flow_signal_reason,
        "slot_index": max(1, int(slot_index)),
    }


def placeholder_row(slot_index: int) -> dict[str, Any]:
    idx = max(1, int(slot_index))
    return {
        "symbol": "—",
        "option_type": "CALL",
        "strike": 0.0,
        "implied_volatility": 0.0,
        "volume": 0,
        "turnover": 0.0,
        "flow": 0.0,
        "flow_score": 0.0,
        "impact_index": 0.0,
        "is_sweep": False,
        "flow_deg_formatted": "—",
        "flow_volume_label": "—",
        "flow_color": "text-text-secondary",
        "flow_glow": "",
        "flow_intensity": "LOW",
        "flow_direction": "NEUTRAL",
        "flow_d_z": 0.0,
        "flow_e_z": 0.0,
        "flow_g_z": 0.0,
        "is_placeholder": True,
        "row_quality": ROW_QUALITY_PLACEHOLDER,
        "fallback_reason": None,
        "is_synthetic_fallback": False,
        "flow_signal_state": ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_DEGRADED,
        "flow_signal_reason": ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_ALL_ENGINES_INACTIVE,
        "slot_index": idx,
    }


def pad_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    target = max(0, int(limit))
    trimmed = rows[:target]
    for idx, row in enumerate(trimmed):
        is_placeholder = bool(row.get("is_placeholder", False))
        row["slot_index"] = idx + 1
        row["is_placeholder"] = is_placeholder
        if is_placeholder:
            row["row_quality"] = ROW_QUALITY_PLACEHOLDER
            row["fallback_reason"] = None
            row["is_synthetic_fallback"] = False
            row["flow_signal_state"] = ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_DEGRADED
            row["flow_signal_reason"] = ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_ALL_ENGINES_INACTIVE
        else:
            row.setdefault("row_quality", ROW_QUALITY_REAL)
            row.setdefault("fallback_reason", None)
            row.setdefault("is_synthetic_fallback", False)
            row.setdefault("flow_signal_state", ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_LIVE)
            row.setdefault("flow_signal_reason", None)
    while len(trimmed) < target:
        trimmed.append(placeholder_row(len(trimmed) + 1))
    return trimmed


def build_ranked_candidate(
    outputs: list[FlowEngineOutput],
    limit: int,
) -> tuple[list[dict[str, Any]], tuple[tuple[str, str, float], ...]]:
    target = max(0, int(limit))
    ranked = rank_outputs(outputs)[:target]
    rows = [format_row(o, slot_index=idx + 1) for idx, o in enumerate(ranked)]
    padded_rows = pad_rows(rows, target)

    signature_entries: list[tuple[str, str, float]] = [
        (str(o.symbol), str(o.option_type), round(float(o.strike), ACTIVE_OPTIONS_SIGNATURE_STRIKE_ROUND_DIGITS))
        for o in ranked
    ]
    while len(signature_entries) < target:
        signature_entries.append((f"{ACTIVE_OPTIONS_PLACEHOLDER_SIGNATURE_PREFIX}{len(signature_entries) + 1}", "CALL", 0.0))
    return padded_rows, tuple(signature_entries)


def is_placeholder_signature(signature: tuple[tuple[str, str, float], ...]) -> bool:
    if not signature:
        return False
    return all(str(entry[0]).startswith(ACTIVE_OPTIONS_PLACEHOLDER_SIGNATURE_PREFIX) for entry in signature)
