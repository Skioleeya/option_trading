"""Rust-owner BSM compatibility surface for legacy callers."""

from __future__ import annotations

import logging
from typing import Any

from shared_rust.services import aggregate_from_greeks as _rust_aggregate_from_greeks  # type: ignore

from l1_compute.analysis.bsm_rust_bridge import rust_bsm_batch_numpy_tier

logger = logging.getLogger(__name__)


def _bsm_batch_numpy(
    spots: Any,
    strikes: Any,
    ivs: Any,
    t_years: float,
    is_call: Any,
    r: float,
    q: float,
) -> dict[str, Any]:
    """Legacy helper retained for parity tests and diagnostics."""
    return rust_bsm_batch_numpy_tier(
        spots=spots,
        strikes=strikes,
        ivs=ivs,
        t_years=float(t_years),
        is_call=is_call,
        r=float(r),
        q=float(q),
    )


def compute_greeks_batch(
    spots: Any,
    strikes: Any,
    ivs: Any,
    t_years: float,
    is_call: Any,
    r: float = 0.05,
    q: float = 0.0,
    ois: Any | None = None,
    mults: Any | None = None,
) -> tuple[dict[str, Any], dict[str, float] | None]:
    """Return per-contract Greeks and optional aggregate payload from Rust owners."""
    greeks = _bsm_batch_numpy(spots, strikes, ivs, t_years, is_call, r, q)

    if ois is None or mults is None:
        return greeks, None

    agg = _rust_aggregate_from_greeks(
        gamma=greeks["gamma"],
        vanna=greeks["vanna"],
        charm=greeks["charm"],
        spots=spots,
        strikes=strikes,
        is_call=is_call,
        ivs=ivs,
        t_years=float(t_years),
        ois=ois,
        mults=mults,
    )
    if not isinstance(agg, dict):
        raise TypeError("Rust aggregate_from_greeks returned non-dict payload")
    return greeks, {k: float(v) if isinstance(v, (int, float)) else v for k, v in agg.items()}


def warmup() -> None:
    """Compatibility no-op; Rust owners warm up at import/runtime level."""
    logger.info("[bsm_fast.warmup] Rust owner active; explicit warmup no-op.")
