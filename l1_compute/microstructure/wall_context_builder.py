"""Wall context builder — pure-computation helpers for GEX wall analysis.

Responsibilities:
    - Wall gamma regime classification (SHORT_GAMMA / LONG_GAMMA / NEUTRAL)
    - Near-wall liquidity estimation from chain snapshot
    - Wall context dict assembly for L3 contract consumption

No mutable state — all functions are stateless.

Layer:  L1
Deps:   numpy, pyarrow, shared/config
"""

from __future__ import annotations

from typing import Union

import numpy as np
import pyarrow as pa

from shared.config import settings


def classify_wall_gamma_regime(net_gex: float) -> str:
    """Classify GEX as SHORT_GAMMA / LONG_GAMMA / NEUTRAL.

    Uses settings.wall_gamma_neutral_abs_threshold.
    """
    neutral_abs = float(getattr(settings, "wall_gamma_neutral_abs_threshold", 20_000.0))
    if abs(float(net_gex)) <= neutral_abs:
        return "NEUTRAL"
    return "SHORT_GAMMA" if float(net_gex) < 0.0 else "LONG_GAMMA"


def estimate_near_wall_liquidity(
    chain_snapshot: Union[list[dict], pa.RecordBatch],
    *,
    call_wall: float,
    put_wall: float,
) -> float:
    """Return total volume within the liquidity bandwidth around each wall.

    Vectorised path for RecordBatch; scalar iteration for list-of-dicts.
    Falls back to total chain volume when no entries are in-band.

    Returns at least 1.0 to avoid division-by-zero downstream.
    """
    band = float(getattr(settings, "wall_liquidity_bandwidth", 1.0))
    if band <= 0:
        band = 1.0

    if isinstance(chain_snapshot, pa.RecordBatch):
        strikes = chain_snapshot.column("strike").to_numpy()
        volumes = chain_snapshot.column("volume").to_numpy()
        mask    = np.zeros(len(strikes), dtype=np.bool_)
        if call_wall > 0.0:
            mask = mask | (np.abs(strikes - call_wall) <= band)
        if put_wall > 0.0:
            mask = mask | (np.abs(strikes - put_wall) <= band)
        near_liq = float(np.sum(volumes[mask])) if np.any(mask) else float(np.sum(volumes))
        return max(near_liq, 1.0)

    near_liq  = 0.0
    total_vol = 0.0
    for row in chain_snapshot:
        if not isinstance(row, dict):
            continue
        strike  = float(row.get("strike", 0.0) or 0.0)
        volume  = float(row.get("volume", 0.0) or 0.0)
        total_vol += volume
        if strike <= 0.0:
            continue
        if call_wall > 0.0 and abs(strike - call_wall) <= band:
            near_liq += volume
            continue
        if put_wall > 0.0 and abs(strike - put_wall) <= band:
            near_liq += volume

    if near_liq <= 0.0:
        near_liq = total_vol
    return max(near_liq, 1.0)


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
    gamma_regime              = classify_wall_gamma_regime(net_gex)
    near_wall_hedge_notional_m = (
        abs(float(call_wall_gex or 0.0)) + abs(float(put_wall_gex or 0.0))
    )
    near_wall_liquidity = estimate_near_wall_liquidity(
        chain_snapshot,
        call_wall=float(call_wall or 0.0),
        put_wall=float(put_wall or 0.0),
    )
    hedge_flow_intensity = near_wall_hedge_notional_m / max(near_wall_liquidity, 1.0)

    cap_bps = float(getattr(settings, "wall_counterfactual_impact_cap_bps", 2_000.0))
    if gamma_regime == "SHORT_GAMMA":
        direction = 1.0
    elif gamma_regime == "LONG_GAMMA":
        direction = -0.5
    else:
        direction = 0.0
    counterfactual_vol_impact_bps = direction * min(cap_bps, hedge_flow_intensity * 100.0)

    return {
        "gamma_regime":                  gamma_regime,
        "hedge_flow_intensity":          float(hedge_flow_intensity),
        "counterfactual_vol_impact_bps": float(counterfactual_vol_impact_bps),
        "near_wall_hedge_notional_m":    float(near_wall_hedge_notional_m),
        "near_wall_liquidity":           float(near_wall_liquidity),
    }
