"""Helpers for building stable L2->L4 fused_signal contract fields.

This module keeps fused-signal serialization logic out of the DecisionOutput
dataclass so it can be unit-tested independently.
"""

from __future__ import annotations

import math
from typing import Any

from shared.config import settings


_IV_DIRECTION_TO_REGIME: dict[str, str] = {
    "BULLISH": "LOW_VOL",
    "BEARISH": "HIGH_VOL",
    "NEUTRAL": "NORMAL",
    "LOW_VOL": "LOW_VOL",
    "HIGH_VOL": "HIGH_VOL",
    "NORMAL": "NORMAL",
}


def resolve_iv_regime(direction: Any) -> str:
    """Map raw IV signal direction into canonical fused-signal regime labels."""
    key = str(direction or "").strip().upper()
    return _IV_DIRECTION_TO_REGIME.get(key, "NORMAL")


def classify_gex_intensity(net_gex: Any) -> str:
    """Classify raw net_gex into the canonical GEX intensity buckets."""
    if not isinstance(net_gex, (int, float)) or not math.isfinite(float(net_gex)):
        return "NEUTRAL"

    gex = float(net_gex)
    abs_gex = abs(gex)

    if gex >= settings.gex_super_pin_threshold:
        return "EXTREME_POSITIVE"
    if gex >= settings.gex_strong_positive:
        return "STRONG_POSITIVE"
    if gex <= settings.gex_strong_negative:
        return "EXTREME_NEGATIVE"
    if gex < 0:
        return "STRONG_NEGATIVE"
    if abs_gex >= settings.gex_moderate_threshold:
        return "MODERATE"
    return "NEUTRAL"


def normalize_signal_components(signal_summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Normalize DecisionOutput.signal_summary into fused_signal.components schema."""
    components: dict[str, dict[str, Any]] = {}
    for name, value in signal_summary.items():
        if isinstance(value, dict):
            direction = value.get("direction", "NEUTRAL")
            if name == "iv_regime":
                direction = resolve_iv_regime(direction)

            components[name] = {
                "direction": direction,
                "confidence": value.get("confidence", 0.0),
            }
        else:
            direction = value
            if name == "iv_regime":
                direction = resolve_iv_regime(direction)
            components[name] = {"direction": direction, "confidence": 0.0}
    return components
