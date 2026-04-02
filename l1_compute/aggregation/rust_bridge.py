from __future__ import annotations

import logging
from typing import Any

from shared_rust.services import aggregate_greeks_full as _rust_aggregate_greeks_full  # type: ignore
from shared_rust.services import aggregate_from_greeks as _rust_aggregate_from_greeks  # type: ignore
from shared_rust.services import estimate_zero_gamma_level as _rust_estimate_zero_gamma_level  # type: ignore
from shared_rust.services import select_walls as _rust_select_walls  # type: ignore

logger = logging.getLogger(__name__)


def rust_aggregate_greeks_full(
    *,
    strikes: Any,
    call_gex: Any,
    put_gex: Any,
    vanna: Any,
    charm: Any,
) -> dict[str, Any]:
    """Rust-only aggregate path. Raises on owner failure."""
    try:
        payload = _rust_aggregate_greeks_full(strikes, call_gex, put_gex, vanna, charm)
        if not isinstance(payload, dict):
            raise TypeError("Rust aggregate_greeks_full returned non-dict payload")
        return payload
    except Exception as exc:
        logger.error("[StreamingAggregator] Rust aggregate execution failed: %s", exc)
        raise RuntimeError("Rust aggregate_greeks_full execution failed") from exc


def rust_aggregate_from_greeks(
    *,
    gamma: Any,
    vanna: Any,
    charm: Any,
    spots: Any,
    strikes: Any,
    is_call: Any,
    ivs: Any,
    t_years: float,
    ois: Any,
    mults: Any,
) -> dict[str, Any]:
    """Rust-only aggregate-from-greeks path. Raises on owner failure."""
    try:
        payload = _rust_aggregate_from_greeks(
            gamma,
            vanna,
            charm,
            spots,
            strikes,
            is_call,
            ivs,
            float(t_years),
            ois,
            mults,
        )
        if not isinstance(payload, dict):
            raise TypeError("Rust aggregate_from_greeks returned non-dict payload")
        return payload
    except Exception as exc:
        logger.error("[BSMFast] Rust aggregate_from_greeks execution failed: %s", exc)
        raise RuntimeError("Rust aggregate_from_greeks execution failed") from exc


def rust_select_walls(
    *,
    strikes: Any,
    call_gex: Any,
    put_gex: Any,
    spot_ref: float,
) -> tuple[float, float, float, float]:
    """Rust-only wall-selection path. Raises on owner failure."""
    try:
        walls = _rust_select_walls(strikes, call_gex, put_gex, float(spot_ref))
        if not isinstance(walls, tuple) or len(walls) != 4:
            raise TypeError("Rust select_walls returned invalid payload")
        return (float(walls[0]), float(walls[1]), float(walls[2]), float(walls[3]))
    except Exception as exc:
        logger.error("[StreamingAggregator] Rust wall-select execution failed: %s", exc)
        raise RuntimeError("Rust select_walls execution failed") from exc


def rust_estimate_zero_gamma_level(
    *,
    strikes: Any,
    is_call: Any,
    ivs: Any,
    ois: Any,
    mults: Any,
    t_years: float,
    spot: float,
    r: float,
    q: float,
) -> float:
    """Rust-only zero-gamma estimator. Raises on owner failure."""
    try:
        level = _rust_estimate_zero_gamma_level(
            strikes,
            is_call,
            ivs,
            ois,
            mults,
            float(t_years),
            float(spot),
            float(r),
            float(q),
        )
        return float(level)
    except Exception as exc:
        logger.error("[StreamingAggregator] Rust zero-gamma execution failed: %s", exc)
        raise RuntimeError("Rust estimate_zero_gamma_level execution failed") from exc
