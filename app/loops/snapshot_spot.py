from __future__ import annotations

import math
from dataclasses import is_dataclass, replace
from typing import Any


def positive_finite_spot(value: Any) -> float | None:
    try:
        spot = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(spot) or spot <= 0.0:
        return None
    return spot


def reconcile_l1_snapshot_spot(l1_snapshot: Any, source_spot: Any) -> Any:
    fallback_spot = positive_finite_spot(source_spot)
    if fallback_spot is None:
        return l1_snapshot
    if positive_finite_spot(getattr(l1_snapshot, "spot", None)) is not None:
        return l1_snapshot
    if is_dataclass(l1_snapshot):
        try:
            return replace(l1_snapshot, spot=fallback_spot)
        except TypeError:
            return l1_snapshot
    if isinstance(l1_snapshot, dict):
        patched = dict(l1_snapshot)
        patched["spot"] = fallback_spot
        return patched
    try:
        setattr(l1_snapshot, "spot", fallback_spot)
    except (AttributeError, TypeError):
        return l1_snapshot
    return l1_snapshot
