"""Pure helpers for ATM decay stitching math."""

from __future__ import annotations

import math
from typing import Mapping

_KEYS = ("c", "p", "s")


def _safe_factor_from_pct(pct: float) -> float:
    """Convert return pct to multiplicative factor, bounded at zero."""
    if not math.isfinite(pct):
        return 1.0
    return max(0.0, 1.0 + float(pct))


def _safe_pct_from_factor(factor: float) -> float:
    """Convert multiplicative factor to return pct with -100% hard floor."""
    if not math.isfinite(factor):
        return 0.0
    return max(-1.0, float(factor) - 1.0)


def default_stitch_factor() -> dict[str, float]:
    """Neutral factor state (no stitched offset)."""
    return {"c": 1.0, "p": 1.0, "s": 1.0}


def legacy_offset_to_factor(offset: Mapping[str, float] | None) -> dict[str, float]:
    """Backfill multiplicative factors from legacy additive offsets."""
    out = default_stitch_factor()
    if not isinstance(offset, Mapping):
        return out
    for key in _KEYS:
        raw = offset.get(key, 0.0)
        try:
            out[key] = _safe_factor_from_pct(float(raw))
        except (TypeError, ValueError):
            out[key] = 1.0
    return out


def factor_to_legacy_offset(factor: Mapping[str, float] | None) -> dict[str, float]:
    """Provide compatibility view for legacy readers expecting offsets."""
    out = {"c": 0.0, "p": 0.0, "s": 0.0}
    if not isinstance(factor, Mapping):
        return out
    for key in _KEYS:
        raw = factor.get(key, 1.0)
        try:
            out[key] = _safe_pct_from_factor(float(raw))
        except (TypeError, ValueError):
            out[key] = 0.0
    return out


def stitch_with_factor(raw_pct: float, stitched_factor: float) -> float:
    """Compose stitched return using multiplicative factors."""
    raw_factor = _safe_factor_from_pct(raw_pct)
    factor = max(0.0, float(stitched_factor)) * raw_factor
    return _safe_pct_from_factor(factor)


def advance_factor(stitched_factor: float, raw_pct: float) -> float:
    """Advance stitched factor when rolling anchor to next strike."""
    return max(0.0, float(stitched_factor)) * _safe_factor_from_pct(raw_pct)
