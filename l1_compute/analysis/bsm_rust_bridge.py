from __future__ import annotations

import logging
from typing import Any

from shared_rust.services import bsm_batch_numpy_tier as _rust_bsm_batch_numpy_tier  # type: ignore

logger = logging.getLogger(__name__)

_REQUIRED_BSM_KEYS = ("delta", "gamma", "vega", "vanna", "charm", "theta")


def rust_bsm_batch_numpy_tier(
    spots: Any,
    strikes: Any,
    ivs: Any,
    t_years: float,
    is_call: Any,
    r: float,
    q: float,
) -> dict[str, Any]:
    """Rust-only BSM tier. Raises on owner failure or malformed payload."""
    try:
        raw = _rust_bsm_batch_numpy_tier(spots, strikes, ivs, float(t_years), is_call, float(r), float(q))
        if not isinstance(raw, dict):
            raise TypeError("Rust bsm_batch_numpy_tier returned non-dict payload")
        for key in _REQUIRED_BSM_KEYS:
            if key not in raw:
                raise KeyError(f"Missing Rust BSM output key: {key}")
        return raw
    except Exception as exc:
        logger.error("[bsm_fast] Rust numpy-tier execution failed: %s", exc)
        raise RuntimeError("Rust BSM tier execution failed") from exc
