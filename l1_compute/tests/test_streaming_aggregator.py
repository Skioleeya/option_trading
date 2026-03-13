"""Tests for StreamingAggregator.

Validates:
    1. Incremental result matches full_recompute baseline (drift < 1e-10)
    2. Wall identification (call_wall = highest call GEX strike)
    3. Flip level detection
    4. Drift protection counter triggers dirty_walls
    5. Empty chain resets cleanly
"""

from __future__ import annotations

import sys

import numpy as np
import pytest

sys.path.insert(0, "e:\\US.market\\Option_v3")

from l1_compute.aggregation.streaming_aggregator import StreamingAggregator, AggregateGreeks
from l1_compute.compute.gpu_greeks_kernel import GreeksMatrix, _compute_numpy


def _make_matrix(n: int, spot: float = 560.0, t: float = 0.002):
    rng = np.random.default_rng(7)
    strikes = np.linspace(spot * 0.95, spot * 1.05, n)
    ivs     = rng.uniform(0.15, 0.35, n)
    is_call = np.array([i % 2 == 0 for i in range(n)])
    spots   = np.full(n, spot)
    ois     = rng.integers(500, 10000, n).astype(np.float64)
    mults   = np.full(n, 100.0)
    matrix = _compute_numpy(spots, strikes, ivs, t, is_call, r=0.05, q=0.0, ois=ois, mults=mults)
    return matrix, strikes, is_call


class TestStreamingAggregator:

    def test_full_recompute_sets_net_gex(self):
        agg = StreamingAggregator()
        matrix, strikes, is_call = _make_matrix(100)
        agg.full_recompute(matrix, strikes, is_call)
        snap = agg.snapshot()
        expected_net = float(np.sum(matrix.call_gex) - np.sum(matrix.put_gex))
        assert abs(snap.net_gex - expected_net) < 1e-10, f"net_gex mismatch: {snap.net_gex} vs {expected_net}"

    def test_call_wall_is_highest_call_gex_strike(self):
        agg = StreamingAggregator()
        matrix, strikes, is_call = _make_matrix(100)
        agg.full_recompute(matrix, strikes, is_call)
        snap = agg.snapshot()

        # Manual: find strike with highest sum of call_gex
        per_strike = {}
        for i in range(len(strikes)):
            k = float(strikes[i])
            per_strike.setdefault(k, 0.0)
            per_strike[k] += float(matrix.call_gex[i])
        expected_wall = max(per_strike, key=per_strike.get)
        assert abs(snap.call_wall - expected_wall) < 0.01, f"Call wall mismatch: {snap.call_wall} vs {expected_wall}"

    def test_incremental_matches_full(self):
        """Single update_contract should yield same result as fresh full_recompute."""
        agg = StreamingAggregator()
        matrix, strikes, is_call = _make_matrix(50)
        symbols = [f"SYM{i:03d}" for i in range(50)]
        agg.full_recompute(matrix, strikes, is_call, symbols=symbols)
        snap_full = agg.snapshot()

        # Simulate a no-change update for the first symbol
        sym = symbols[0]
        st = agg._per_symbol.get(sym, {})
        agg.update_contract(
            symbol=sym,
            new_call_gex=st.get("call_gex", 0.0),
            new_put_gex=st.get("put_gex", 0.0),
            new_vanna=st.get("vanna", 0.0),
            new_charm=st.get("charm", 0.0),
            strike=float(strikes[0]),
            is_call=bool(is_call[0]),
        )
        snap_inc = agg.snapshot()
        # No-change update must not drift
        assert abs(snap_inc.net_gex - snap_full.net_gex) < 1e-10

    def test_empty_chain_resets(self):
        agg = StreamingAggregator()
        matrix, strikes, is_call = _make_matrix(20)
        agg.full_recompute(matrix, strikes, is_call)
        # Reset with empty
        empty = _compute_numpy(np.array([]), np.array([]), np.array([]), 0.002,
                               np.array([], dtype=np.bool_), r=0.05, q=0.0,
                               ois=np.array([]), mults=np.array([]))
        agg.full_recompute(empty, np.array([]), np.array([], dtype=np.bool_))
        snap = agg.snapshot()
        assert snap.net_gex == 0.0
        assert snap.call_wall == 0.0
        assert snap.put_wall == 0.0

    def test_snapshot_is_frozen(self):
        """AggregateGreeks snapshot must be immutable (frozen dataclass)."""
        agg = StreamingAggregator()
        matrix, strikes, is_call = _make_matrix(10)
        agg.full_recompute(matrix, strikes, is_call)
        snap = agg.snapshot()
        with pytest.raises((AttributeError, TypeError)):
            snap.net_gex = 999.0  # type: ignore

    def test_incremental_counter_triggers_dirty_walls(self):
        """After DRIFT_GUARD_INTERVAL increments, _dirty_walls must be True."""
        from l1_compute.aggregation.streaming_aggregator import _DRIFT_GUARD_INTERVAL
        agg = StreamingAggregator()
        matrix, strikes, is_call = _make_matrix(10)
        symbols = [f"S{i}" for i in range(10)]
        agg.full_recompute(matrix, strikes, is_call, symbols=symbols)

        for _ in range(_DRIFT_GUARD_INTERVAL):
            agg.update_contract("S0", 0.0, 0.0, 0.0, 0.0, float(strikes[0]), bool(is_call[0]))

        assert agg._dirty_walls is True

    def test_flip_level_exact_zero_on_cumulative_path(self):
        agg = StreamingAggregator()
        flip = agg._find_flip_level([(100.0, -5.0), (101.0, 5.0), (102.0, 1.0)])
        assert flip == pytest.approx(101.0)

    def test_flip_level_interpolates_when_cumulative_crosses_between_strikes(self):
        agg = StreamingAggregator()
        flip = agg._find_flip_level([(100.0, -5.0), (101.0, 10.0)])
        assert flip == pytest.approx(100.5)

    def test_flip_level_returns_zero_when_no_cumulative_cross(self):
        agg = StreamingAggregator()
        flip = agg._find_flip_level([(100.0, 3.0), (101.0, 2.0), (102.0, 1.0)])
        assert flip == 0.0

    def test_walls_prefer_spot_side_with_global_fallback(self):
        agg = StreamingAggregator()
        n = 4
        strikes = np.array([95.0, 100.0, 105.0, 110.0], dtype=np.float64)
        is_call = np.array([True, False, True, False], dtype=np.bool_)
        call_gex = np.array([200.0, 0.0, 100.0, 0.0], dtype=np.float64)
        put_gex = np.array([0.0, 300.0, 0.0, 500.0], dtype=np.float64)
        matrix = GreeksMatrix(
            delta=np.zeros(n, dtype=np.float64),
            gamma=np.zeros(n, dtype=np.float64),
            vega=np.zeros(n, dtype=np.float64),
            vanna=np.zeros(n, dtype=np.float64),
            charm=np.zeros(n, dtype=np.float64),
            theta=np.zeros(n, dtype=np.float64),
            gex_per_contract=call_gex + put_gex,
            call_gex=call_gex,
            put_gex=put_gex,
            iv_used=np.full(n, 0.2, dtype=np.float64),
        )
        agg.full_recompute(matrix, strikes, is_call, spot=102.0)
        snap = agg.snapshot()
        assert snap.call_wall == pytest.approx(105.0)  # prefer strike >= spot
        assert snap.put_wall == pytest.approx(100.0)   # prefer strike <= spot

    def test_zero_gamma_level_differs_from_cumulative_flip(self):
        agg = StreamingAggregator()
        spot = 100.0
        strikes = np.array([90.0, 100.0, 110.0], dtype=np.float64)
        is_call = np.array([False, False, True], dtype=np.bool_)
        ivs = np.array([0.18, 0.20, 0.22], dtype=np.float64)
        ois = np.array([8000.0, 3000.0, 6000.0], dtype=np.float64)
        mults = np.array([100.0, 100.0, 100.0], dtype=np.float64)
        t_years = 0.01
        matrix = _compute_numpy(
            np.full(strikes.size, spot, dtype=np.float64),
            strikes,
            ivs,
            t_years,
            is_call,
            r=0.05,
            q=0.0,
            ois=ois,
            mults=mults,
        )
        agg.full_recompute(
            matrix,
            strikes,
            is_call,
            spot=spot,
            ivs=ivs,
            ois=ois,
            mults=mults,
            t_years=t_years,
            r=0.05,
            q=0.0,
        )
        snap = agg.snapshot()
        assert snap.flip_level_cumulative == pytest.approx(0.0)
        assert snap.zero_gamma_level > 0.0
        assert snap.zero_gamma_level != pytest.approx(snap.flip_level_cumulative)
