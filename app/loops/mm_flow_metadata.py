"""MM flow metadata extraction for L0->L1 pass-through.

This module is intentionally thin: Python only validates/sanitizes inputs
and delegates aggregation to Rust owner `shared_rust.services.mm_snapshot_metrics`.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from shared_rust import services as rust_services

logger = logging.getLogger(__name__)
_MM_SNAPSHOT_METRICS = getattr(rust_services, "mm_snapshot_metrics", None)

_NUMERIC_KEYS = (
    "net_delta_exposure_live",
    "net_gamma_exposure_live",
    "midpoint_tickrule_count",
    "condition_filtered_count",
    "complex_spread_count",
    "residual_delta_after_netting",
    "oi_participation_ratio_live",
    "flow_suppression_bias",
    "flow_dominance_ratio",
    "put_ask_side_volume",
    "call_bid_side_volume",
    "call_ask_side_volume",
    "put_bid_side_volume",
)


def _default_metrics() -> dict[str, float]:
    return {key: 0.0 for key in _NUMERIC_KEYS}


def _normalize_chain_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows = snapshot.get("chain")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    chain_arrow = snapshot.get("chain_arrow")
    if chain_arrow is not None and hasattr(chain_arrow, "to_pylist"):
        try:
            data = chain_arrow.to_pylist()
        except (AttributeError, TypeError, ValueError):
            return []
        return [row for row in data if isinstance(row, dict)]
    return []


def _coerce_numeric(raw: Any) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value):
        return 0.0
    return value


def build_mm_flow_metrics(snapshot: dict[str, Any]) -> dict[str, float]:
    rows = _normalize_chain_rows(snapshot)
    if not rows:
        return _default_metrics()
    if _MM_SNAPSHOT_METRICS is None:
        logger.warning("[MMFlow] rust mm_snapshot_metrics export missing; using zero metrics")
        return _default_metrics()

    try:
        raw_metrics = dict(_MM_SNAPSHOT_METRICS(rows))
    except (RuntimeError, TypeError, ValueError) as exc:
        logger.warning("[MMFlow] rust snapshot metrics failed: %s", exc)
        return _default_metrics()

    normalized = _default_metrics()
    for key in _NUMERIC_KEYS:
        normalized[key] = _coerce_numeric(raw_metrics.get(key))
    return normalized
