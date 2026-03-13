"""Streaming Aggregator — O(ΔN) incremental GEX/Vanna/Charm aggregation.

Key design: instead of traversing all N contracts every tick, only update
the contribution of the small subset ΔN contracts whose quotes changed.

Performance: O(N) per tick → O(ΔN) per tick (ΔN ≈ 10–20% of chain).

Features:
    - update_contract()  : O(1) incremental adjustment — add/remove delta
    - full_recompute()   : O(N) calibration from a fresh GreeksMatrix
    - snapshot()         : O(1) read current aggregate state
    - drift_protection   : auto full-recompute every N incremental updates
    - wall_tracking      : lazy O(K) max recompute (K = distinct strikes)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from l1_compute.compute.gpu_greeks_kernel import GreeksMatrix

logger = logging.getLogger(__name__)

# Drift protection: full_recompute triggered every N incremental updates
_DRIFT_GUARD_INTERVAL: int = 200


@dataclass
class StrikeContribution:
    """Per-strike GEX contributions for wall tracking."""
    call_gex: float = 0.0
    put_gex: float = 0.0

    @property
    def net_gex(self) -> float:
        return self.call_gex - self.put_gex


@dataclass(frozen=True)
class AggregateGreeks:
    """Immutable snapshot of the current aggregated risk exposure."""
    net_gex: float          # Net Gamma Exposure (USD millions)
    net_vanna_raw_sum: float  # Canonical raw chain sum of vanna sensitivities
    net_vanna: float        # Legacy alias for net_vanna_raw_sum
    net_charm_raw_sum: float  # Canonical raw chain sum of charm sensitivities
    net_charm: float        # Legacy alias for net_charm_raw_sum
    call_wall: float        # Strike with highest call GEX
    call_wall_gex: float
    put_wall: float         # Strike with highest put GEX
    put_wall_gex: float
    flip_level: float       # Legacy alias of flip_level_cumulative (for compatibility)
    flip_level_cumulative: float
    zero_gamma_level: float
    total_call_gex: float
    total_put_gex: float
    num_contracts: int
    per_strike_gex: list[dict] = field(default_factory=list)


class StreamingAggregator:
    """Incremental GEX/Vanna/Charm aggregator for the option chain.

    Usage::

        agg = StreamingAggregator()
        # Full seed from Greeks matrix after each compute cycle
        agg.full_recompute(matrix, strikes, is_call, ois, mults, spots)
        # Incremental per-contract update on price tick
        agg.update_contract(symbol, old_greeks, new_greeks)
        result = agg.snapshot()
    """

    def __init__(self) -> None:
        self._net_gex: float = 0.0
        self._net_vanna: float = 0.0
        self._net_charm: float = 0.0
        self._total_call_gex: float = 0.0
        self._total_put_gex: float = 0.0
        # Per-strike contribution map for wall tracking
        self._per_strike: dict[float, StrikeContribution] = {}
        # Per-symbol numerical contributions for incremental update
        self._per_symbol: dict[str, dict[str, float]] = {}
        # Wall cache
        self._call_wall: tuple[float, float] = (0.0, 0.0)   # (strike, gex)
        self._put_wall:  tuple[float, float] = (0.0, 0.0)
        self._flip_level_cumulative: float = 0.0
        self._zero_gamma_level: float = 0.0
        self._spot: float = 0.0
        # Drift protection counter
        self._incremental_count: int = 0
        self._dirty_walls: bool = False

    # ── Public API ─────────────────────────────────────────────────────────────

    def full_recompute(
        self,
        matrix: GreeksMatrix,
        strikes: np.ndarray,
        is_call: np.ndarray,
        symbols: Optional[list[str]] = None,
        *,
        spot: float | None = None,
        ivs: np.ndarray | None = None,
        ois: np.ndarray | None = None,
        mults: np.ndarray | None = None,
        t_years: float | None = None,
        r: float = 0.05,
        q: float = 0.0,
    ) -> None:
        """Seed aggregator from a complete GreeksMatrix (O(N) calibration).

        Call this after each ComputeRouter.compute() cycle to reset drift.

        Args:
            matrix:  Full-chain GreeksMatrix from GPUGreeksKernel.
            strikes: Strike array (N,) matching matrix dimensions.
            is_call: Boolean array (N,) matching matrix dimensions.
            symbols: Optional symbol list for per-symbol tracking.
            spot: Underlying spot used for side-aware walls and zero-gamma search.
            ivs/ois/mults/t_years/r/q: Optional inputs for zero-gamma grid recompute.
        """
        n = matrix.n
        if n == 0:
            self._reset()
            return

        if spot is not None:
            try:
                self._spot = float(spot)
            except (TypeError, ValueError):
                self._spot = 0.0

        # Net GEX in MMUSD: call gross minus put gross.
        self._net_gex       = float(np.sum(matrix.call_gex) - np.sum(matrix.put_gex))
        self._total_call_gex = float(np.sum(matrix.call_gex))
        self._total_put_gex  = float(np.sum(matrix.put_gex))
        self._net_vanna     = float(np.sum(matrix.vanna))
        self._net_charm     = float(np.sum(matrix.charm))

        # Rebuild per-strike map
        self._per_strike.clear()
        for i in range(n):
            k = float(strikes[i])
            if k not in self._per_strike:
                self._per_strike[k] = StrikeContribution()
            self._per_strike[k].call_gex += float(matrix.call_gex[i])
            self._per_strike[k].put_gex  += float(matrix.put_gex[i])

        # Rebuild per-symbol map
        self._per_symbol.clear()
        if symbols:
            for i, sym in enumerate(symbols):
                self._per_symbol[sym] = {
                    "gex":   float(matrix.gex_per_contract[i]),
                    "call_gex": float(matrix.call_gex[i]),
                    "put_gex":  float(matrix.put_gex[i]),
                    "vanna":    float(matrix.vanna[i]),
                    "charm":    float(matrix.charm[i]),
                    "is_call":  bool(is_call[i]),
                }

        self._recompute_walls()
        self._zero_gamma_level = self._estimate_zero_gamma_level(
            strikes=strikes,
            is_call=is_call,
            ivs=ivs,
            ois=ois,
            mults=mults,
            t_years=t_years,
            spot=self._spot,
            r=r,
            q=q,
        )
        self._incremental_count = 0
        self._dirty_walls = False
        logger.debug("[StreamingAggregator] full_recompute n=%d net_gex=%.2f", n, self._net_gex)

    def update_contract(
        self,
        symbol: str,
        new_call_gex: float,
        new_put_gex: float,
        new_vanna: float,
        new_charm: float,
        strike: float,
        is_call: bool,
    ) -> None:
        """O(1) incremental update for a single contract quote change.

        Subtracts old contribution and adds new contribution.

        Args:
            symbol:      Option symbol (e.g. 'SPY250303C00560000').
            new_call_gex: Updated call GEX value (0 for puts).
            new_put_gex:  Updated put GEX value (0 for calls).
            new_vanna:   Updated vanna.
            new_charm:   Updated charm.
            strike:      Contract strike price.
            is_call:     True = Call, False = Put.
        """
        old = self._per_symbol.get(symbol, {})

        old_call_gex = old.get("call_gex", 0.0)
        old_put_gex  = old.get("put_gex", 0.0)
        old_vanna    = old.get("vanna",    0.0)
        old_charm    = old.get("charm",    0.0)

        # Incremental aggregator adjustments
        self._net_gex       += (new_call_gex - old_call_gex) - (new_put_gex - old_put_gex)
        self._total_call_gex += (new_call_gex - old_call_gex)
        self._total_put_gex  += (new_put_gex  - old_put_gex)
        self._net_vanna     += (new_vanna  - old_vanna)
        self._net_charm     += (new_charm  - old_charm)

        # Per-strike update for wall tracking
        if strike not in self._per_strike:
            self._per_strike[strike] = StrikeContribution()
        sc = self._per_strike[strike]
        sc.call_gex += (new_call_gex - old_call_gex)
        sc.put_gex  += (new_put_gex  - old_put_gex)

        # Update per-symbol record
        self._per_symbol[symbol] = {
            "gex":      new_call_gex + new_put_gex,
            "call_gex": new_call_gex,
            "put_gex":  new_put_gex,
            "vanna":    new_vanna,
            "charm":    new_charm,
            "is_call":  is_call,
        }

        # Wall may have changed if this strike touched the wall
        if (strike == self._call_wall[0] or new_call_gex > self._call_wall[1] or
                strike == self._put_wall[0]  or new_put_gex  > self._put_wall[1]):
            self._dirty_walls = True

        self._incremental_count += 1
        if self._incremental_count >= _DRIFT_GUARD_INTERVAL:
            # Cannot full_recompute here (no GreeksMatrix available);
            # mark walls dirty and reset counter — reactor will call full_recompute.
            self._dirty_walls = True
            self._incremental_count = 0
            logger.debug(
                "[StreamingAggregator] drift guard triggered after %d increments",
                _DRIFT_GUARD_INTERVAL,
            )

    def snapshot(self) -> AggregateGreeks:
        """O(1) — return current aggregate state.

        If walls are dirty (e.g. after incremental drift), lazy-recompute them.
        """
        if self._dirty_walls:
            self._recompute_walls()
            self._dirty_walls = False

        # Build per_strike_gex list
        per_strike_list = [
            {
                "strike": k,
                "call_gex": v.call_gex,
                "put_gex": v.put_gex,
                "net_gex": v.net_gex
            }
            for k, v in self._per_strike.items()
        ]

        return AggregateGreeks(
            net_gex=self._net_gex,
            net_vanna_raw_sum=self._net_vanna,
            net_vanna=self._net_vanna,
            net_charm_raw_sum=self._net_charm,
            net_charm=self._net_charm,
            call_wall=self._call_wall[0],
            call_wall_gex=self._call_wall[1],
            put_wall=self._put_wall[0],
            put_wall_gex=self._put_wall[1],
            flip_level=self._flip_level_cumulative,
            flip_level_cumulative=self._flip_level_cumulative,
            zero_gamma_level=self._zero_gamma_level,
            total_call_gex=self._total_call_gex,
            total_put_gex=self._total_put_gex,
            num_contracts=len(self._per_symbol),
            per_strike_gex=per_strike_list,
        )

    # ── Private ───────────────────────────────────────────────────────────────

    def _reset(self) -> None:
        self._net_gex = self._net_vanna = self._net_charm = 0.0
        self._total_call_gex = self._total_put_gex = 0.0
        self._per_strike.clear()
        self._per_symbol.clear()
        self._call_wall = self._put_wall = (0.0, 0.0)
        self._flip_level_cumulative = 0.0
        self._zero_gamma_level = 0.0
        self._spot = 0.0

    def _recompute_walls(self) -> None:
        """O(K) — scan per-strike map for highest call/put GEX walls."""
        if not self._per_strike:
            self._call_wall = self._put_wall = (0.0, 0.0)
            self._flip_level_cumulative = 0.0
            return

        best_call_global = (0.0, -math.inf)   # (strike, gex)
        best_put_global  = (0.0, -math.inf)
        best_call_side = (0.0, -math.inf)
        best_put_side = (0.0, -math.inf)

        sorted_strikes = sorted(self._per_strike.keys())
        net_gex_by_strike: list[tuple[float, float]] = []  # for flip detection

        for k in sorted_strikes:
            sc = self._per_strike[k]
            if sc.call_gex > best_call_global[1]:
                best_call_global = (k, sc.call_gex)
            if sc.put_gex > best_put_global[1]:
                best_put_global = (k, sc.put_gex)
            if self._spot > 0.0:
                if k >= self._spot and sc.call_gex > best_call_side[1]:
                    best_call_side = (k, sc.call_gex)
                if k <= self._spot and sc.put_gex > best_put_side[1]:
                    best_put_side = (k, sc.put_gex)
            net_gex_by_strike.append((k, sc.net_gex))

        call_choice = best_call_side if best_call_side[1] > -math.inf else best_call_global
        put_choice = best_put_side if best_put_side[1] > -math.inf else best_put_global
        self._call_wall = call_choice[0], max(0.0, call_choice[1])
        self._put_wall  = put_choice[0],  max(0.0, put_choice[1])

        # Flip level: first cumulative net_gex zero-crossing along sorted strikes.
        self._flip_level_cumulative = self._find_flip_level(net_gex_by_strike)

    def _find_flip_level(self, net_by_strike: list[tuple[float, float]]) -> float:
        """Locate first cumulative net-GEX zero crossing along sorted strikes."""
        if not net_by_strike:
            return 0.0

        eps = 1e-12
        cumulative = 0.0
        prev_strike: float | None = None
        prev_cumulative: float | None = None

        for strike, net in net_by_strike:
            cumulative += float(net)
            if abs(cumulative) <= eps:
                return float(strike)

            if prev_strike is not None and prev_cumulative is not None:
                cross_up = prev_cumulative < -eps and cumulative > eps
                cross_down = prev_cumulative > eps and cumulative < -eps
                if cross_up or cross_down:
                    denom = cumulative - prev_cumulative
                    if abs(denom) <= eps:
                        return float(strike)
                    weight = -prev_cumulative / denom
                    weight = min(1.0, max(0.0, weight))
                    return float(prev_strike + (float(strike) - prev_strike) * weight)

            prev_strike = float(strike)
            prev_cumulative = float(cumulative)

        return 0.0

    def _estimate_zero_gamma_level(
        self,
        *,
        strikes: np.ndarray,
        is_call: np.ndarray,
        ivs: np.ndarray | None,
        ois: np.ndarray | None,
        mults: np.ndarray | None,
        t_years: float | None,
        spot: float,
        r: float,
        q: float,
    ) -> float:
        """Estimate zero-gamma by recomputing net GEX across a spot grid."""
        if (
            ivs is None
            or ois is None
            or mults is None
            or t_years is None
            or t_years <= 0.0
            or len(strikes) == 0
        ):
            return 0.0

        strikes_arr = np.asarray(strikes, dtype=np.float64)
        is_call_arr = np.asarray(is_call, dtype=np.bool_)
        ivs_arr = np.asarray(ivs, dtype=np.float64)
        ois_arr = np.asarray(ois, dtype=np.float64)
        mults_arr = np.asarray(mults, dtype=np.float64)

        valid = (
            np.isfinite(strikes_arr)
            & np.isfinite(ivs_arr)
            & np.isfinite(ois_arr)
            & np.isfinite(mults_arr)
            & (strikes_arr > 0.0)
            & (ivs_arr > 0.0)
            & (ois_arr >= 0.0)
            & (mults_arr > 0.0)
        )
        if not np.any(valid):
            return 0.0

        strikes_v = strikes_arr[valid]
        is_call_v = is_call_arr[valid]
        ivs_v = ivs_arr[valid]
        ois_v = ois_arr[valid]
        mults_v = mults_arr[valid]

        spot_ref = float(spot) if spot > 0.0 and math.isfinite(spot) else float(np.median(strikes_v))
        low = max(1e-6, min(float(np.min(strikes_v)), spot_ref) * 0.90)
        high = max(low + 1e-6, max(float(np.max(strikes_v)), spot_ref) * 1.10)
        if not math.isfinite(low) or not math.isfinite(high) or high <= low:
            return 0.0

        grid = np.linspace(low, high, 161, dtype=np.float64)
        sqrt_t = math.sqrt(float(t_years))
        eq_t = math.exp(-q * float(t_years))
        sqrt_2pi = math.sqrt(2.0 * math.pi)

        S = grid[:, None]
        K = strikes_v[None, :]
        IV = ivs_v[None, :]
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            d1 = (np.log(np.maximum(S, 1e-12) / K) + (r - q + 0.5 * IV**2) * float(t_years)) / (IV * sqrt_t)
            nd1 = np.exp(-0.5 * d1**2) / sqrt_2pi
            gamma = eq_t * nd1 / np.maximum(S * IV * sqrt_t, 1e-12)
            gex = gamma * ois_v[None, :] * mults_v[None, :] * (S**2) * 0.01 / 1_000_000.0
            signed = np.where(is_call_v[None, :], gex, -gex)
            net_curve = np.sum(signed, axis=1)

        net_curve = np.where(np.isfinite(net_curve), net_curve, 0.0)
        return self._interpolate_zero_crossing(grid, net_curve, spot_ref)

    @staticmethod
    def _interpolate_zero_crossing(
        grid: np.ndarray,
        curve: np.ndarray,
        spot_ref: float,
    ) -> float:
        """Interpolate zero crossing on a 1D grid; pick crossing nearest spot."""
        if grid.size == 0 or curve.size == 0 or grid.size != curve.size:
            return 0.0

        eps = 1e-12
        candidates: list[float] = []
        for i in range(grid.size - 1):
            y0 = float(curve[i])
            y1 = float(curve[i + 1])
            x0 = float(grid[i])
            x1 = float(grid[i + 1])
            if abs(y0) <= eps:
                candidates.append(x0)
                continue
            if abs(y1) <= eps:
                candidates.append(x1)
                continue
            if y0 * y1 < 0.0:
                denom = y1 - y0
                if abs(denom) <= eps:
                    candidates.append(x1)
                else:
                    w = -y0 / denom
                    w = min(1.0, max(0.0, w))
                    candidates.append(x0 + (x1 - x0) * w)

        if not candidates:
            return 0.0

        if math.isfinite(spot_ref) and spot_ref > 0.0:
            return float(min(candidates, key=lambda x: abs(x - spot_ref)))
        return float(candidates[0])
