"""Wall context builder — pure-computation helpers for GEX wall analysis.

Responsibilities:
    - Wall gamma regime classification (SHORT_GAMMA / LONG_GAMMA / NEUTRAL)
    - Near-wall liquidity estimation from chain snapshot
    - Wall context dict assembly for L3 contract consumption

No mutable state — all functions are stateless.

Layer:  L1
Deps:   pyarrow, shared/config, shared_rust.services
"""

from __future__ import annotations

from typing import Union

import pyarrow as pa

from shared.config import settings
from shared_rust.services import classify_wall_gamma_regime as rust_classify_wall_gamma_regime  # type: ignore
from shared_rust.services import compute_wall_context_metrics as rust_compute_wall_context_metrics  # type: ignore
from shared_rust.services import estimate_near_wall_liquidity as rust_estimate_near_wall_liquidity  # type: ignore


def classify_wall_gamma_regime(net_gex: float) -> str:
    """Classify GEX as SHORT_GAMMA / LONG_GAMMA / NEUTRAL.

    Uses settings.wall_gamma_neutral_abs_threshold.
    """
    neutral_abs = getattr(settings, "wall_gamma_neutral_abs_threshold", 20_000.0)
    try:
        return str(rust_classify_wall_gamma_regime(net_gex, neutral_abs))
    except Exception as exc:
        raise RuntimeError("Rust classify_wall_gamma_regime execution failed") from exc


def estimate_near_wall_liquidity(
    chain_snapshot: Union[list[dict], pa.RecordBatch],
    *,
    call_wall: float,
    put_wall: float,
) -> float:
    """Return total volume within the liquidity bandwidth around each wall.

    Rust owner handles extraction, fallback, and lower-bound clamping.
    """
    band = getattr(settings, "wall_liquidity_bandwidth", 1.0)
    try:
        near_liq = rust_estimate_near_wall_liquidity(
            chain_snapshot,
            call_wall,
            put_wall,
            band,
        )
    except Exception as exc:
        raise RuntimeError("Rust estimate_near_wall_liquidity execution failed") from exc
    return float(near_liq)


def build_wall_context(
    chain_snapshot: Union[list[dict], pa.RecordBatch],
    *,
    net_gex: float,
    call_wall: float,
    put_wall: float,
    call_wall_gex: float,
    put_wall_gex: float,
) -> dict[str, float | str]:
    """Assemble the wall_context payload for downstream L3 consumers.

    Returns:
        {
            "gamma_regime":                   str,
            "hedge_flow_intensity":           float,
            "counterfactual_vol_impact_bps":  float,
            "near_wall_hedge_notional_m":     float,
            "near_wall_liquidity":            float,
        }
    """
    neutral_abs = getattr(settings, "wall_gamma_neutral_abs_threshold", 20_000.0)
    band = getattr(settings, "wall_liquidity_bandwidth", 1.0)
    cap_bps = getattr(settings, "wall_counterfactual_impact_cap_bps", 2_000.0)
    try:
        (
            gamma_regime,
            hedge_flow_intensity,
            counterfactual_vol_impact_bps,
            near_wall_hedge_notional_m,
            near_wall_liquidity,
        ) = rust_compute_wall_context_metrics(
            chain_snapshot,
            net_gex,
            call_wall,
            put_wall,
            call_wall_gex,
            put_wall_gex,
            band,
            neutral_abs,
            cap_bps,
        )
    except Exception as exc:
        raise RuntimeError("Rust compute_wall_context_metrics execution failed") from exc

    return {
        "gamma_regime":                  str(gamma_regime),
        "hedge_flow_intensity":          float(hedge_flow_intensity),
        "counterfactual_vol_impact_bps": float(counterfactual_vol_impact_bps),
        "near_wall_hedge_notional_m":    float(near_wall_hedge_notional_m),
        "near_wall_liquidity":           float(near_wall_liquidity),
    }
