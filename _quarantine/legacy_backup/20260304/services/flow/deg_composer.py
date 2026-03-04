"""DEGComposer — Z-Score normalisation and weighted composition.

Combines per-strike output from FlowEngine_D, FlowEngine_E and FlowEngine_G
into a single DEG-FLOW score using Z-Score standardisation followed by a
regime-adaptive weighted sum.

Weight schedule (from config — all three must sum to 1.0):
    Normal session    → w_D=0.40, w_E=0.35, w_G=0.25
    Charm Surge zone  → w_D=0.50, w_E=0.30, w_G=0.20  (last 2h, 0DTE)
    NEUTRAL GEX       → w_D=0.30, w_E=0.40, w_G=0.30

Intensity labels
    |z_deg| >= EXTREME_THRESHOLD → EXTREME
    |z_deg| >= HIGH_THRESHOLD    → HIGH
    |z_deg| >= 0.5               → MODERATE
    else                         → LOW
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from typing import Literal

from app.config import settings
from app.models.flow_engine import FlowComponentResult, FlowEngineOutput

logger = logging.getLogger(__name__)


def _z_score(values: list[float]) -> list[float]:
    """Return Z-Score normalised list.  Returns zeros if std ≈ 0."""
    if not values:
        return []
    mu = sum(values) / len(values)
    variance = sum((v - mu) ** 2 for v in values) / len(values)
    std = math.sqrt(variance) if variance > 0 else 0.0
    if std < 1e-9:
        return [0.0] * len(values)
    return [(v - mu) / std for v in values]


def _direction(z: float) -> Literal["BULLISH", "BEARISH", "NEUTRAL"]:
    if z > 0.1:
        return "BULLISH"
    if z < -0.1:
        return "BEARISH"
    return "NEUTRAL"


def _intensity(z: float, extreme_th: float, high_th: float) -> Literal["EXTREME", "HIGH", "MODERATE", "LOW"]:
    az = abs(z)
    if az >= extreme_th:
        return "EXTREME"
    if az >= high_th:
        return "HIGH"
    if az >= 0.5:
        return "MODERATE"
    return "LOW"


class DEGComposer:
    """Compose DEG-FLOW from the three engine component results."""

    def compose(
        self,
        d_results: list[FlowComponentResult],
        e_results: list[FlowComponentResult],
        g_results: list[FlowComponentResult],
        inputs_by_symbol: dict[str, object],
        *,
        is_charm_surge: bool = False,
        gex_regime: str = "NEUTRAL",
    ) -> list[FlowEngineOutput]:
        """Build final FlowEngineOutput list.

        Args:
            d_results:          FlowEngine_D output list.
            e_results:          FlowEngine_E output list.
            g_results:          FlowEngine_G output list.
            inputs_by_symbol:   Map of symbol → FlowEngineInput (for metadata).
            is_charm_surge:     True if within last 2 hours (adjusts weights).
            gex_regime:         Current GEX regime for adaptive weighting.

        Returns:
            List of fully composed FlowEngineOutput, one per common symbol.
        """
        # --- build lookup maps ---
        def _index(results: list[FlowComponentResult]) -> dict[str, float]:
            return {r.symbol: r.flow_value for r in results if r.is_valid}

        map_d = _index(d_results)
        map_e = _index(e_results)
        map_g = _index(g_results)

        # Active engines (for fallback weight redistribution)
        g_active = any(r.is_valid for r in g_results)

        # Union of all valid symbols
        all_symbols = set(map_d) | set(map_e) | set(map_g)

        if not all_symbols:
            return []

        # --- Z-Score per component ---
        symbols = sorted(all_symbols)
        vals_d = [map_d.get(s, 0.0) for s in symbols]
        vals_e = [map_e.get(s, 0.0) for s in symbols]
        vals_g = [map_g.get(s, 0.0) for s in symbols]

        z_d = _z_score(vals_d)
        z_e = _z_score(vals_e)
        z_g = _z_score(vals_g)

        # --- Adaptive weights ---
        if is_charm_surge:
            w_d = settings.flow_charm_surge_weight_d
            w_e = settings.flow_charm_surge_weight_e
            w_g = settings.flow_charm_surge_weight_g
        elif gex_regime == "NEUTRAL":
            w_d = settings.flow_neutral_gex_weight_d
            w_e = settings.flow_neutral_gex_weight_e
            w_g = settings.flow_neutral_gex_weight_g
        else:
            w_d = settings.flow_weight_d
            w_e = settings.flow_weight_e
            w_g = settings.flow_weight_g

        # If G engine was degraded, redistribute its weight proportionally
        if not g_active:
            total = w_d + w_e
            if total > 0:
                w_d, w_e = w_d / total, w_e / total
            w_g = 0.0

        extreme_th = settings.flow_zscore_extreme_threshold
        high_th = settings.flow_intensity_high_threshold

        # --- Build outputs ---
        outputs: list[FlowEngineOutput] = []
        for i, sym in enumerate(symbols):
            inp = inputs_by_symbol.get(sym)
            if inp is None:
                continue

            deg = w_d * z_d[i] + w_e * z_e[i] + w_g * z_g[i]

            outputs.append(FlowEngineOutput(
                symbol=sym,
                option_type=inp.option_type,
                strike=inp.strike,
                implied_volatility=inp.implied_volatility,
                volume=inp.volume,
                turnover=inp.turnover,
                flow_d=map_d.get(sym, 0.0),
                flow_e=map_e.get(sym, 0.0),
                flow_g=map_g.get(sym, 0.0),
                flow_d_z=z_d[i],
                flow_e_z=z_e[i],
                flow_g_z=z_g[i],
                flow_deg=deg,
                flow_direction=_direction(deg),
                flow_intensity=_intensity(deg, extreme_th, high_th),
                engine_d_active=sym in map_d,
                engine_e_active=sym in map_e,
                engine_g_active=g_active,
            ))

        return outputs
