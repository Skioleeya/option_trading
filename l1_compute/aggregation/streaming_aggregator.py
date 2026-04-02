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

from l1_compute.aggregation.rust_bridge import (
    rust_aggregate_greeks_full,
    rust_estimate_zero_gamma_level,
    rust_select_walls,
)
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
    call_wall: float        # Trading-practice proxy: strike with highest call-side GEX proxy
    call_wall_gex: float
    put_wall: float         # Trading-practice proxy: strike with highest put-side GEX proxy
    put_wall_gex: float
    flip_level: float       # Legacy alias of flip_level_cumulative (for compatibility)
    flip_level_cumulative: float  # Trading-practice cumulative flip proxy
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

        rust_payload = rust_aggregate_greeks_full(
            strikes=np.asarray(strikes, dtype=np.float64),
            call_gex=np.asarray(matrix.call_gex, dtype=np.float64),
            put_gex=np.asarray(matrix.put_gex, dtype=np.float64),
            vanna=np.asarray(matrix.vanna, dtype=np.float64),
            charm=np.asarray(matrix.charm, dtype=np.float64),
        )
        self._net_gex = float(rust_payload.get("net_gex", 0.0))
        self._total_call_gex = float(rust_payload.get("total_call_gex", 0.0))
        self._total_put_gex = float(rust_payload.get("total_put_gex", 0.0))
        self._net_vanna = float(rust_payload.get("net_vanna", 0.0))
        self._net_charm = float(rust_payload.get("net_charm", 0.0))

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
        self._zero_gamma_level = rust_estimate_zero_gamma_level(
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

        sorted_strikes = sorted(self._per_strike.keys())
        strikes_arr = np.asarray(sorted_strikes, dtype=np.float64)
        call_gex_arr = np.asarray(
            [self._per_strike[strike].call_gex for strike in sorted_strikes],
            dtype=np.float64,
        )
        put_gex_arr = np.asarray(
            [self._per_strike[strike].put_gex for strike in sorted_strikes],
            dtype=np.float64,
        )

        call_wall, put_wall, max_call_gex, max_put_gex = rust_select_walls(
            strikes=strikes_arr,
            call_gex=call_gex_arr,
            put_gex=put_gex_arr,
            spot_ref=self._spot,
        )

        self._call_wall = call_wall, max(0.0, max_call_gex)
        self._put_wall = put_wall, max(0.0, max_put_gex)

        net_gex_by_strike = list(
            zip(strikes_arr.tolist(), (call_gex_arr - put_gex_arr).tolist())
        )
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


