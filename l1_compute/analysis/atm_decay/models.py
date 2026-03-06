"""Shared constants and helper models for ATM decay."""

from __future__ import annotations

import math
import re
from typing import Any
from zoneinfo import ZoneInfo

ET = ZoneInfo("US/Eastern")

# OCC-style symbol regex for US equity options
_SYM_RE = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d+)\.US$")

# Restore and lock-gating thresholds
MAX_ANCHOR_DISTANCE: float = 3.0
MAX_SPOT_PARITY_STRIKE_GAP: float = 2.0
MIN_LEG_PRICE: float = 0.05
MAX_CAPTURE_CANDIDATES: int = 10
SPOT_STABILITY_MIN_SAMPLES: int = 4
SPOT_STABILITY_WINDOW: int = 8
SPOT_STABILITY_MAX_RANGE: float = 1.2


def parse_expiry(symbol: str) -> str | None:
    """Return the YYMMDD expiration string embedded in the symbol, or None."""
    m = _SYM_RE.match(symbol)
    return m.group(2) if m else None


def is_integer_strike(strike: float) -> bool:
    """SPY options are expected to be whole-dollar strikes."""
    return abs(strike - round(strike)) < 0.01


def mid_price(bid: float, ask: float, last: float) -> float:
    """Institutional mid-price waterfall. Returns 0.0 only if all inputs are 0."""
    if bid > 0 and ask > 0 and ask >= bid:
        return (bid + ask) / 2.0
    if ask > 0:
        return ask
    return last


def is_valid_spot(spot: Any) -> bool:
    return isinstance(spot, (int, float)) and math.isfinite(float(spot)) and float(spot) > 0


def spot_distance(strike: Any, spot: float) -> float | None:
    """Distance between strike and spot (None when spot or strike unavailable)."""
    if not is_valid_spot(spot):
        return None
    if not isinstance(strike, (int, float)) or not math.isfinite(float(strike)):
        return None
    return abs(float(strike) - float(spot))
