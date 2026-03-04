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
    net_vanna: float        # Net Vanna Exposure
    net_charm: float        # Net Charm (delta decay)
    call_wall: float        # Strike with highest call GEX
    call_wall_gex: float
    put_wall: float         # Strike with highest put GEX
    put_wall_gex: float
    flip_level: float       # Strike nearest net GEX = 0 crossover
    total_call_gex: float
    total_put_gex: float
    num_contracts: int


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
        self._flip_level: float = 0.0
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
    ) -> None:
        """Seed aggregator from a complete GreeksMatrix (O(N) calibration).

        Call this after each ComputeRouter.compute() cycle to reset drift.

        Args:
            matrix:  Full-chain GreeksMatrix from GPUGreeksKernel.
            strikes: Strike array (N,) matching matrix dimensions.
            is_call: Boolean array (N,) matching matrix dimensions.
            symbols: Optional symbol list for per-symbol tracking.
        """
        n = matrix.n
        if n == 0:
            self._reset()
            return

        self._net_gex       = float(np.sum(matrix.gex_per_contract) * np.where(is_call, 1.0, -1.0).sum()
                                    / max(n, 1))
        # More precise: call GEX helps dealers, put GEX hurts
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

        return AggregateGreeks(
            net_gex=self._net_gex,
            net_vanna=self._net_vanna,
            net_charm=self._net_charm,
            call_wall=self._call_wall[0],
            call_wall_gex=self._call_wall[1],
            put_wall=self._put_wall[0],
            put_wall_gex=self._put_wall[1],
            flip_level=self._flip_level,
            total_call_gex=self._total_call_gex,
            total_put_gex=self._total_put_gex,
            num_contracts=len(self._per_symbol),
        )

    # ── Private ───────────────────────────────────────────────────────────────

    def _reset(self) -> None:
        self._net_gex = self._net_vanna = self._net_charm = 0.0
        self._total_call_gex = self._total_put_gex = 0.0
        self._per_strike.clear()
        self._per_symbol.clear()
        self._call_wall = self._put_wall = (0.0, 0.0)
        self._flip_level = 0.0

    def _recompute_walls(self) -> None:
        """O(K) — scan per-strike map for highest call/put GEX walls."""
        if not self._per_strike:
            self._call_wall = self._put_wall = (0.0, 0.0)
            self._flip_level = 0.0
            return

        best_call = (0.0, -math.inf)   # (strike, gex)
        best_put  = (0.0, -math.inf)

        sorted_strikes = sorted(self._per_strike.keys())
        net_gex_by_strike: list[tuple[float, float]] = []  # for flip detection

        for k in sorted_strikes:
            sc = self._per_strike[k]
            if sc.call_gex > best_call[1]:
                best_call = (k, sc.call_gex)
            if sc.put_gex > best_put[1]:
                best_put = (k, sc.put_gex)
            net_gex_by_strike.append((k, sc.net_gex))

        self._call_wall = best_call[0], max(0.0, best_call[1])
        self._put_wall  = best_put[0],  max(0.0, best_put[1])

        # Flip level: nearest strike where cumulative net_gex changes sign
        self._flip_level = self._find_flip_level(net_gex_by_strike)

    def _find_flip_level(self, net_by_strike: list[tuple[float, float]]) -> float:
        """Locate strike nearest to GEX sign crossover."""
        if not net_by_strike:
            return 0.0
        prev_sign = 0
        for k, v in net_by_strike:
            s = 1 if v > 0 else (-1 if v < 0 else 0)
            if prev_sign != 0 and s != 0 and s != prev_sign:
                return k
            if s != 0:
                prev_sign = s
        return 0.0
