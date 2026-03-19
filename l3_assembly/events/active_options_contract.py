"""Shared ActiveOptions row contract helpers for L3 adapters."""

from __future__ import annotations

from typing import Any

from l3_assembly.events.payload_events import ActiveOptionRow


def _to_str(raw: dict[str, Any], key: str, default: str) -> str:
    return str(raw.get(key, default))


def _to_float(raw: dict[str, Any], key: str, default: float = 0.0) -> float:
    return float(raw.get(key, default) or default)


def _to_int(raw: dict[str, Any], key: str, default: int = 0) -> int:
    return int(raw.get(key, default) or default)


def _optional_clean_str(raw: dict[str, Any], key: str, *, upper: bool = False) -> str | None:
    value = raw.get(key)
    if value in (None, ""):
        return None
    cleaned = str(value).strip()
    if cleaned == "":
        return None
    return cleaned.upper() if upper else cleaned


def _normalize_option_type(raw: dict[str, Any]) -> str:
    option_type_raw = _to_str(raw, "option_type", "CALL").upper()
    return "CALL" if option_type_raw in ("CALL", "C") else "PUT"


def active_option_row_from_dict(raw: dict[str, Any]) -> ActiveOptionRow:
    """Normalize a legacy active-options dict row into ActiveOptionRow."""
    return ActiveOptionRow(
        symbol=_to_str(raw, "symbol", "SPY"),
        option_type=_normalize_option_type(raw),
        strike=_to_float(raw, "strike", 0.0),
        implied_volatility=_to_float(raw, "implied_volatility", 0.0),
        volume=_to_int(raw, "volume", 0),
        turnover=_to_float(raw, "turnover", 0.0),
        flow=_to_float(raw, "flow", 0.0),
        flow_score=_to_float(raw, "flow_score", 0.0),
        impact_index=_to_float(raw, "impact_index", 0.0),
        is_sweep=bool(raw.get("is_sweep", False)),
        flow_deg_formatted=_to_str(raw, "flow_deg_formatted", "$0"),
        flow_volume_label=_to_str(raw, "flow_volume_label", "0"),
        flow_color=_to_str(raw, "flow_color", "text-text-secondary"),
        flow_glow=_to_str(raw, "flow_glow", ""),
        flow_intensity=_to_str(raw, "flow_intensity", "LOW"),
        flow_direction=_to_str(raw, "flow_direction", "NEUTRAL"),
        flow_d_z=_to_float(raw, "flow_d_z", 0.0),
        flow_e_z=_to_float(raw, "flow_e_z", 0.0),
        flow_g_z=_to_float(raw, "flow_g_z", 0.0),
        is_placeholder=bool(raw.get("is_placeholder", False)),
        slot_index=_to_int(raw, "slot_index", 0),
        row_quality=_optional_clean_str(raw, "row_quality", upper=True),
        fallback_reason=_optional_clean_str(raw, "fallback_reason", upper=False),
        is_synthetic_fallback=bool(raw.get("is_synthetic_fallback", False)),
        flow_signal_state=_optional_clean_str(raw, "flow_signal_state", upper=True) or "LIVE",
        flow_signal_reason=_optional_clean_str(raw, "flow_signal_reason", upper=False),
    )
