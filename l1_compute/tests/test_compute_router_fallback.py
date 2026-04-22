from __future__ import annotations

import numpy as np

from l1_compute.compute.compute_router import ComputeRouter, ComputeTier
from l1_compute.compute.gpu_greeks_kernel import GPUComputationUnavailableError


def _sample_inputs() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    spots = np.asarray([709.0, 709.0], dtype=np.float64)
    strikes = np.asarray([709.0, 710.0], dtype=np.float64)
    ivs = np.asarray([0.12, 0.13], dtype=np.float64)
    is_call = np.asarray([True, False], dtype=np.bool_)
    return spots, strikes, ivs, is_call


def test_router_uses_rust_cpu_tier_when_gpu_unavailable() -> None:
    router = ComputeRouter()
    router._kernel._gpu_ok = False  # noqa: SLF001 - test forces fallback path
    spots, strikes, ivs, is_call = _sample_inputs()

    matrix, decision = router.compute(
        spots=spots,
        strikes=strikes,
        ivs=ivs,
        t_years=0.01,
        is_call=is_call,
    )

    assert decision.tier == ComputeTier.NUMPY
    assert decision.reason == "gpu_unavailable_rust_cpu_fallback"
    assert np.any(np.asarray(matrix.gamma) > 0.0)


def test_router_falls_back_to_rust_cpu_when_gpu_runtime_fails() -> None:
    router = ComputeRouter()
    router._kernel._gpu_ok = True  # noqa: SLF001 - test controls routing
    spots, strikes, ivs, is_call = _sample_inputs()

    execute_batch = router._execute_batch

    def _execute_batch_with_gpu_failure(*args, **kwargs):  # type: ignore[no-untyped-def]
        if bool(kwargs.get("prefer_gpu")):
            raise GPUComputationUnavailableError("simulated_gpu_failure")
        return execute_batch(*args, **kwargs)

    router._execute_batch = _execute_batch_with_gpu_failure  # type: ignore[method-assign]
    matrix, decision = router.compute(
        spots=spots,
        strikes=strikes,
        ivs=ivs,
        t_years=0.01,
        is_call=is_call,
    )

    assert decision.tier == ComputeTier.NUMPY
    assert decision.reason.startswith("gpu_runtime_failed_rust_cpu_fallback:")
    assert np.any(np.asarray(matrix.gamma) > 0.0)
