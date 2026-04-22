from __future__ import annotations

import math
from typing import Any

from l1_compute.iv.iv_resolver import ResolvedIV


def build_atm_iv_context(
    *,
    spot: float,
    symbols: list[str],
    strikes: Any,
    resolved_ivs: dict[str, ResolvedIV],
    valid_mask: Any,
) -> dict[str, Any]:
    """Return the resolved nearest-ATM IV context for runtime diagnostics."""
    if spot <= 0.0 or not symbols:
        return {}

    best_idx: int | None = None
    best_dist = float("inf")
    for idx, symbol in enumerate(symbols):
        if not _mask_at(valid_mask, idx):
            continue
        strike = _to_finite_float(strikes[idx])
        resolved = resolved_ivs.get(symbol)
        if strike is None or resolved is None or not resolved.is_valid:
            continue
        dist = abs(strike - spot)
        if dist < best_dist:
            best_dist = dist
            best_idx = idx

    if best_idx is None:
        return {}

    symbol = symbols[best_idx]
    strike = _to_finite_float(strikes[best_idx])
    resolved = resolved_ivs.get(symbol)
    if strike is None or resolved is None:
        return {}

    return {
        "atm_symbol": symbol,
        "atm_strike": strike,
        "atm_distance": round(best_dist, 6),
        "atm_iv": round(float(resolved.value), 6),
        "raw_iv": round(float(resolved.raw_value), 6),
        "iv_source": str(resolved.source.value),
        "iv_confidence": round(float(resolved.confidence), 6),
        "spot": round(float(spot), 6),
    }


def _mask_at(mask: Any, idx: int) -> bool:
    try:
        return bool(mask[idx])
    except (IndexError, KeyError, TypeError):
        return False


def _to_finite_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None
