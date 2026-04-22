"""Canonical GEX regime contract parser for L3 UI assembly."""

from __future__ import annotations

from typing import Any

_VALID_GEX_REGIMES: set[str] = {
    "SUPER_PIN",
    "DAMPING",
    "ACCELERATION",
    "NEUTRAL",
}


def parse_gex_regime(raw: Any) -> str:
    """Parse and validate gex_regime from enum-like/object/string payloads.

    Accepted input shapes:
    - Enum-like object with `.value`
    - Plain string (`ACCELERATION`, `GexRegime.ACCELERATION`)
    """
    value = raw
    if hasattr(value, "value"):
        value = getattr(value, "value")
    if value is None:
        raise ValueError("gex_regime is required")
    normalized = str(value).strip()
    if "." in normalized:
        normalized = normalized.split(".")[-1]
    normalized = normalized.upper()
    if normalized not in _VALID_GEX_REGIMES:
        raise ValueError(f"Invalid gex_regime: {normalized!r}")
    return normalized
