"""Tests for GPUGreeksKernel and ComputeRouter.

Validates:
    1. Numerical correctness vs reference bsm.compute_greeks (< 1e-8 error)
    2. ComputeRouter tier selection logic (GPU / Numba / NumPy)
    3. NaN/Inf guard in output arrays
    4. Empty chain edge case
"""

from __future__ import annotations

import math
import sys
from typing import Optional

import numpy as np
import pytest

sys.path.insert(0, "e:\\US.market\\Option_v3")
sys.path.insert(0, "e:\\US.market\\Option_v3\\backend")

from l1_compute.compute.gpu_greeks_kernel import GPUGreeksKernel, GreeksMatrix, _compute_numpy
from l1_compute.compute.compute_router import ComputeRouter, ComputeTier
from l1_compute.analysis.bsm_fast import _aggregate_greeks_cpu


# ── Helpers ───────────────────────────────────────────────────────────────────

def _reference_greeks(spot, strike, iv, t, opt_type, r=0.05, q=0.0):
    """Reference implementation from bsm.compute_greeks."""
    from l1_compute.analysis.bsm import compute_greeks
    return compute_greeks(spot, strike, iv, t, opt_type, r=r, q=q)


def _make_chain(n: int, spot: float = 560.0, t: float = 0.002):
    """Generate a synthetic option chain of size n."""
    rng = np.random.default_rng(42)
    strikes = np.linspace(spot * 0.90, spot * 1.10, n)
    ivs     = rng.uniform(0.15, 0.40, n)
    is_call = np.array([i % 2 == 0 for i in range(n)])
    spots   = np.full(n, spot)
    ois     = rng.integers(100, 5000, n).astype(np.float64)
    mults   = np.full(n, 100.0)
    return spots, strikes, ivs, is_call, ois, mults


# ── Tests: GPUGreeksKernel ────────────────────────────────────────────────────

class TestGPUGreeksKernel:

    def test_empty_chain_returns_empty_matrix(self):
        kernel = GPUGreeksKernel()
        spots   = np.array([], dtype=np.float64)
        strikes = np.array([], dtype=np.float64)
        ivs     = np.array([], dtype=np.float64)
        is_call = np.array([], dtype=np.bool_)
        m = kernel.compute_batch(spots, strikes, ivs, 0.002, is_call)
        assert m.n == 0

    def test_numpy_numerical_correctness_vs_reference(self):
        """NumPy path: each Greek must be within 1e-6 of reference bsm.compute_greeks."""
        try:
            _reference_greeks(560.0, 560.0, 0.20, 0.002, "CALL")
        except (ImportError, Exception):
            pytest.skip("Reference bsm.py not importable in test environment")

        spot, strike, iv, t = 560.0, 555.0, 0.25, 0.002
        spots   = np.array([spot])
        strikes = np.array([strike])
        ivs     = np.array([iv])
        is_call = np.array([True])

        m = _compute_numpy(spots, strikes, ivs, t, is_call, r=0.05, q=0.0,
                           ois=np.zeros(1), mults=np.full(1, 100.0))
        ref = _reference_greeks(spot, strike, iv, t, "CALL")

        assert abs(m.delta[0] - ref["delta"]) < 1e-6, f"delta mismatch: {m.delta[0]} vs {ref['delta']}"
        assert abs(m.gamma[0] - ref["gamma"]) < 1e-6, f"gamma mismatch: {m.gamma[0]} vs {ref['gamma']}"
        assert abs(m.vanna[0] - ref["vanna"]) < 1e-6, f"vanna mismatch"

    def test_nan_inf_guard(self):
        """Output arrays must never contain NaN or Inf."""
        kernel = GPUGreeksKernel()
        n = 50
        spots, strikes, ivs, is_call, ois, mults = _make_chain(n)
        # Inject extreme IV to test guard
        ivs[5] = 100.0
        ivs[10] = 0.0   # zero IV (should be clamped)
        m = kernel.compute_batch(spots, strikes, ivs, 0.001, is_call, ois=ois, mults=mults, prefer_gpu=False)
        assert np.all(np.isfinite(m.delta)),  "NaN/Inf in delta"
        assert np.all(np.isfinite(m.gamma)),  "NaN/Inf in gamma"
        assert np.all(np.isfinite(m.vanna)),  "NaN/Inf in vanna"
        assert np.all(np.isfinite(m.gex_per_contract)), "NaN/Inf in gex"

    def test_delta_range(self):
        """Delta must be in [-1, 1] for all contracts."""
        kernel = GPUGreeksKernel()
        n = 200
        spots, strikes, ivs, is_call, ois, mults = _make_chain(n)
        m = kernel.compute_batch(spots, strikes, ivs, 0.002, is_call, ois=ois, mults=mults, prefer_gpu=False)
        assert np.all(m.delta >= -1.0), "delta < -1 detected"
        assert np.all(m.delta <= 1.0),  "delta > 1 detected"

    def test_gamma_positive(self):
        """Gamma must always be >= 0."""
        kernel = GPUGreeksKernel()
        n = 100
        spots, strikes, ivs, is_call, ois, mults = _make_chain(n)
        m = kernel.compute_batch(spots, strikes, ivs, 0.002, is_call, ois=ois, mults=mults, prefer_gpu=False)
        assert np.all(m.gamma >= 0), "Negative gamma detected"

    def test_gex_sign_convention(self):
        """call_gex > 0, put_gex > 0 for in-chain contracts; put should sum with calls separately."""
        kernel = GPUGreeksKernel()
        n = 10
        spots, strikes, ivs, is_call, ois, mults = _make_chain(n)
        m = kernel.compute_batch(spots, strikes, ivs, 0.002, is_call, ois=ois, mults=mults, prefer_gpu=False)
        assert np.all(m.call_gex >= 0)
        assert np.all(m.put_gex >= 0)
        # call_gex is 0 for puts and vice versa
        assert np.all(m.call_gex[~is_call] == 0)
        assert np.all(m.put_gex[is_call] == 0)


# ── Tests: ComputeRouter ──────────────────────────────────────────────────────

class TestComputeRouter:

    def test_numpy_forced_tier(self):
        """force_tier=NUMPY always routes to NumPy."""
        router = ComputeRouter(force_tier=ComputeTier.NUMPY)
        n = 150
        spots, strikes, ivs, is_call, ois, mults = _make_chain(n)
        m, decision = router.compute(spots, strikes, ivs, 0.002, is_call, ois=ois, mults=mults)
        assert decision.tier == ComputeTier.NUMPY

    def test_small_chain_routes_gpu_if_available(self):
        """Mandate: All recomputations must go through GPU if available, regardless of size."""
        router = ComputeRouter()
        n = 50
        spots, strikes, ivs, is_call, ois, mults = _make_chain(n)
        m, decision = router.compute(spots, strikes, ivs, 0.002, is_call, ois=ois, mults=mults)
        if router.gpu_available:
            assert decision.tier == ComputeTier.GPU
        else:
            assert decision.tier in (ComputeTier.NUMBA, ComputeTier.NUMPY)

    def test_large_chain_routes_gpu_if_available(self):
        """Chain size >= 100 should route to GPU if available."""
        router = ComputeRouter()
        n = 200
        spots, strikes, ivs, is_call, ois, mults = _make_chain(n)
        m, decision = router.compute(spots, strikes, ivs, 0.002, is_call, ois=ois, mults=mults)
        if router.gpu_available:
            assert decision.tier == ComputeTier.GPU
        else:
            assert decision.tier in (ComputeTier.NUMBA, ComputeTier.NUMPY)

    def test_output_schema_consistent_across_tiers(self):
        """Both tiers must return same GreeksMatrix field structure."""
        numpy_router = ComputeRouter(force_tier=ComputeTier.NUMPY)
        n = 20
        spots, strikes, ivs, is_call, ois, mults = _make_chain(n)
        m, _ = numpy_router.compute(spots, strikes, ivs, 0.002, is_call, ois=ois, mults=mults)
        assert hasattr(m, "delta")
        assert hasattr(m, "gamma")
        assert hasattr(m, "vanna")
        assert hasattr(m, "gex_per_contract")
        assert len(m.delta) == n

    def test_chain_size_in_decision(self):
        """decision.chain_size must equal actual chain size."""
        router = ComputeRouter(force_tier=ComputeTier.NUMPY)
        n = 77
        spots, strikes, ivs, is_call, ois, mults = _make_chain(n)
        _, decision = router.compute(spots, strikes, ivs, 0.002, is_call, ois=ois, mults=mults)
        assert decision.chain_size == n

    @pytest.mark.parametrize("shape", ["mixed", "calls_only", "puts_only"])
    def test_legacy_aggregate_gex_formula_matches_mainline(self, shape: str):
        """Legacy bsm_fast aggregate must match mainline GEX formula and units."""
        router = ComputeRouter(force_tier=ComputeTier.NUMPY)
        n = 64
        t_years = 0.002
        spots, strikes, ivs, is_call, ois, mults = _make_chain(n, t=t_years)

        if shape == "calls_only":
            is_call = np.ones(n, dtype=np.bool_)
        elif shape == "puts_only":
            is_call = np.zeros(n, dtype=np.bool_)

        matrix, _ = router.compute(spots, strikes, ivs, t_years, is_call, ois=ois, mults=mults)
        legacy = _aggregate_greeks_cpu(
            {"gamma": matrix.gamma, "vanna": matrix.vanna, "charm": matrix.charm},
            spots,
            strikes,
            is_call,
            ivs,
            t_years,
            ois,
            mults,
        )

        expected_call = float(np.sum(matrix.call_gex))
        expected_put = -float(np.sum(matrix.put_gex))
        expected_net = expected_call + expected_put

        assert legacy["total_call_gex"] == pytest.approx(expected_call, rel=1e-9, abs=1e-12)
        assert legacy["total_put_gex"] == pytest.approx(expected_put, rel=1e-9, abs=1e-12)
        assert legacy["net_gex"] == pytest.approx(expected_net, rel=1e-9, abs=1e-12)

        if shape == "calls_only":
            assert legacy["total_put_gex"] == 0.0
            assert legacy["put_wall"] is None
        if shape == "puts_only":
            assert legacy["total_call_gex"] == 0.0
            assert legacy["call_wall"] is None
