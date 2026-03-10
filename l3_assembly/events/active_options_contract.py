"""Shared ActiveOptions row contract helpers for L3 adapters."""

from __future__ import annotations

from typing import Any

from l3_assembly.events.payload_events import ActiveOptionRow


def active_option_row_from_dict(raw: dict[str, Any]) -> ActiveOptionRow:
    """Normalize a legacy active-options dict row into ActiveOptionRow."""
    option_type_raw = str(raw.get("option_type", "CALL")).upper()
    option_type = "CALL" if option_type_raw in ("CALL", "C") else "PUT"
    return ActiveOptionRow(
        symbol=str(raw.get("symbol", "SPY")),
        option_type=option_type,
        strike=float(raw.get("strike", 0.0) or 0.0),
        implied_volatility=float(raw.get("implied_volatility", 0.0) or 0.0),
        volume=int(raw.get("volume", 0) or 0),
        turnover=float(raw.get("turnover", 0.0) or 0.0),
        flow=float(raw.get("flow", 0.0) or 0.0),
        flow_score=float(raw.get("flow_score", 0.0) or 0.0),
        impact_index=float(raw.get("impact_index", 0.0) or 0.0),
        is_sweep=bool(raw.get("is_sweep", False)),
        flow_deg_formatted=str(raw.get("flow_deg_formatted", "$0")),
        flow_volume_label=str(raw.get("flow_volume_label", "0")),
        flow_color=str(raw.get("flow_color", "text-text-secondary")),
        flow_glow=str(raw.get("flow_glow", "")),
        flow_intensity=str(raw.get("flow_intensity", "LOW")),
        flow_direction=str(raw.get("flow_direction", "NEUTRAL")),
        flow_d_z=float(raw.get("flow_d_z", 0.0) or 0.0),
        flow_e_z=float(raw.get("flow_e_z", 0.0) or 0.0),
        flow_g_z=float(raw.get("flow_g_z", 0.0) or 0.0),
        is_placeholder=bool(raw.get("is_placeholder", False)),
        slot_index=int(raw.get("slot_index", 0) or 0),
    )
