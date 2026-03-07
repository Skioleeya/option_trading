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

from shared.config import settings
from shared.models.flow_engine import FlowComponentResult, FlowEngineOutput

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


class InstitutionalSweepDetector:
    """Identifies multi-strike orders (sweeps) based on spatial clustering."""

    def detect(self, symbols: list[str], z_scores: list[float]) -> dict[str, bool]:
        """Identify strikes part of a sweep cluster (±2 strikes).
        
        A sweep is defined as a strike with at least 2 neighbors within ±2 strikes 
        that also have |Z| > 1.5.
        """
        is_sweep = {s: False for s in symbols}
        if len(symbols) < 3:
            return is_sweep

        # We assume symbols are sorted in strike order (e.g. SPY260305C00500000)
        # For SPX, symbols usually contain the strike price.
        # However, it's safer to extract strike from symbols or use the sorted order.
        # Given DEGComposer already has 'symbols' sorted.
        
        n = len(symbols)
        high_activity = [abs(z) > 1.5 for z in z_scores]

        for i in range(n):
            if not high_activity[i]:
                continue
            
            # Count active neighbors within ±2 index range
            # Note: This assumes 'symbols' contains a contiguous or near-contiguous chain.
            neighbor_indices = [j for j in range(max(0, i - 2), min(n, i + 3)) if i != j]
            active_neighbors = sum(1 for j in neighbor_indices if high_activity[j])
            
            if active_neighbors >= 2:
                is_sweep[symbols[i]] = True
                # Propagate to neighbors to ensure the whole cluster is marked
                for j in neighbor_indices:
                    if high_activity[j]:
                        is_sweep[symbols[j]] = True

        return is_sweep


class DEGComposer:
    """Compose DEG-FLOW from the three engine component results."""

    def __init__(self) -> None:
        self._sweep_detector = InstitutionalSweepDetector()

    def compose(
        self,
        d_results: list[FlowComponentResult],
        e_results: list[FlowComponentResult],
        g_results: list[FlowComponentResult],
        inputs_by_symbol: dict[str, FlowEngineInput],
        *,
        is_charm_surge: bool = False,
        gex_regime: str = "NEUTRAL",
        ttm_seconds: float | None = None,
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

        # --- Base Weights from Configuration (Adaptive to Regime) ---
        if gex_regime == "ACCELERATION" or is_charm_surge:
            # High intensity regime
            w_d, w_e, w_g = settings.flow_charm_surge_weight_d, settings.flow_charm_surge_weight_e, settings.flow_charm_surge_weight_g
        else:
            # Defensive/Neutral regime
            w_d, w_e, w_g = settings.flow_neutral_gex_weight_d, settings.flow_neutral_gex_weight_e, settings.flow_neutral_gex_weight_g

        # Fallback redistribution if G is inactive
        if not g_active:
            total_de = w_d + w_e
            w_d /= total_de
            w_e /= total_de
            w_g = 0.0

        # --- Initial DEG Score (before boost) ---
        initial_degs = [
            w_d * z_d[i] + w_e * z_e[i] + w_g * z_g[i]
            for i in range(len(symbols))
        ]

        # --- Sweep Detection ---
        is_sweep_map = self._sweep_detector.detect(symbols, initial_degs)

        # --- OFII Time Decay Factor (tau) ---
        # Assume 0DTE logic or use provided TTM. If weekend or closed, tau=1.0 (no decay boost)
        # design: e^-tau. tau = t_to_close / t_day.
        DAY_SECONDS = 23400.0  # 6.5h
        tau = (ttm_seconds / DAY_SECONDS) if ttm_seconds and ttm_seconds > 0 else 1.0
        time_factor = math.exp(-tau)

        sweep_mult = settings.flow_sweep_multiplier
        market_depth = settings.flow_market_depth_baseline
        extreme_th = settings.flow_zscore_extreme_threshold
        high_th = settings.flow_intensity_high_threshold

        # --- Build outputs ---
        outputs: list[FlowEngineOutput] = []
        for i, sym in enumerate(symbols):
            inp = inputs_by_symbol.get(sym)
            if inp is None:
                continue

            deg = initial_degs[i]
            is_sweep = is_sweep_map.get(sym, False)

            # Apply Sweep Boost
            if is_sweep:
                deg *= sweep_mult

            # OFII Calculation: (|Flow_D| + |Flow_E| + |Flow_G|) * |Gamma| * e^-tau / Depth
            abs_flow_total = abs(map_d.get(sym, 0.0)) + abs(map_e.get(sym, 0.0)) + abs(map_g.get(sym, 0.0))
            ofii = (abs_flow_total * abs(inp.gamma) * time_factor) / market_depth

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
                impact_index=ofii,
                is_sweep=is_sweep,
                flow_direction=_direction(deg),
                flow_intensity=_intensity(deg, extreme_th, high_th),
                engine_d_active=sym in map_d,
                engine_e_active=sym in map_e,
                engine_g_active=g_active,
            ))

        return outputs
