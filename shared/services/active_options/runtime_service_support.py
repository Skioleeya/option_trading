"""ActiveOptions runtime support helpers.

Pure helper functions extracted from runtime_service to keep orchestration thin.
"""

from __future__ import annotations

from typing import Any

from shared.models.flow_engine import FlowEngineOutput
from .constants import (
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


def direction_from_flow_amount(flow_amount: float) -> str:
    if flow_amount > 0:
        return "BULLISH"
    if flow_amount < 0:
        return "BEARISH"
    return "NEUTRAL"


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


def normalize_chain_volume_fields(option_row: dict[str, Any]) -> dict[str, Any]:
    """Normalize runtime volume fields using `current_volume` as fallback."""
    normalized = dict(option_row)
    volume = int(normalized.get("volume", 0) or 0)
    if volume > 0:
        return normalized

    current_volume = int(float(normalized.get("current_volume", 0) or 0.0))
    if current_volume > 0:
        normalized["volume"] = current_volume
    return normalized


def normalize_and_filter_chain(
    *,
    chain: list[dict[str, Any]],
    min_volume: int,
) -> list[dict[str, Any]]:
    normalized_chain = [normalize_chain_volume_fields(option_row) for option_row in chain]
    return [o for o in normalized_chain if int(o.get("volume", 0) or 0) >= min_volume]


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


def format_row(o: FlowEngineOutput, *, slot_index: int = 1) -> dict[str, Any]:
    # UI semantics are amount-first: displayed FLOW sign must match direction/color.
    flow_amount = o.flow_d + o.flow_e + o.flow_g
    flow_direction = direction_from_flow_amount(flow_amount)
    flow_color = _DIRECTION_COLOR.get(flow_direction, "text-text-secondary")
    glow = _INTENSITY_GLOW.get(o.flow_intensity, "")

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
        "slot_index": idx,
    }


def pad_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    target = max(0, int(limit))
    trimmed = rows[:target]
    for idx, row in enumerate(trimmed):
        row["slot_index"] = idx + 1
        row["is_placeholder"] = bool(row.get("is_placeholder", False))
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
