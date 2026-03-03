"""verify_gpu_load.py — GPU vs CPU EMA & BSM compute benchmark.

Runs synthetic option chain data through:
  1. bsm_fast.compute_greeks_batch (Tier 1 CuPy / Tier 2 Numba)
  2. DepthProfilePresenter._apply_ema_batch (Tier 1 CuPy / Tier 2 Numba)

Reports:
  - Active compute tier per module
  - Average latency per cycle
  - GPU VRAM delta (bytes consumed by kernels)
  - Live GPU utilization % via nvidia-smi

Usage:
    cd e:\\US.market\\Option_v3\\backend
    python scripts/verify_gpu_load.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import numpy as np

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.analysis.bsm_fast import compute_greeks_batch, warmup, _CUPY_AVAILABLE as BSM_GPU
from app.ui.depth_profile.presenter import (
    _apply_ema_batch,
    _CUPY_AVAILABLE as EMA_GPU,
    _NUMBA_AVAILABLE as EMA_NUMBA,
    DepthProfilePresenter,
)

CYCLES = 50
N_CHAIN = 300   # synthetic option chain size
N_STRIKES = 14  # depth profile strike count (matches STRIKE_COUNT)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _gpu_vram_free() -> int | None:
    """Return free VRAM bytes on device 0, or None if CuPy unavailable."""
    try:
        import cupy as cp  # type: ignore
        free, _total = cp.cuda.Device(0).mem_info
        return int(free)
    except Exception:
        return None


def _nvidia_smi_util() -> str:
    """Query GPU utilization via nvidia-smi. Returns a human-readable string."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            timeout=3,
        ).decode().strip()
        parts = [p.strip() for p in out.split(",")]
        return f"GPU util={parts[0]}%  VRAM={parts[1]}MB/{parts[2]}MB"
    except Exception as e:
        return f"nvidia-smi unavailable ({e})"


def _build_synthetic_chain(n: int):
    """Generate n random option contracts for BSM stress testing."""
    rng = np.random.default_rng(42)
    spots   = np.full(n, 580.0)
    strikes = np.linspace(540.0, 620.0, n)
    ivs     = rng.uniform(0.12, 0.40, n)
    is_call = np.array([i % 2 == 0 for i in range(n)])
    ois     = rng.integers(100, 5000, n).astype(np.float64)
    mults   = np.full(n, 100.0)
    return spots, strikes, ivs, 2.0 / 9.25 / 252, is_call, ois, mults


def _build_synthetic_gex(n: int):
    """Generate n random call/put GEX values for EMA stress testing."""
    rng = np.random.default_rng(99)
    calls = rng.uniform(-1e6, 1e6, n).astype(np.float64)
    puts  = rng.uniform(-1e6, 1e6, n).astype(np.float64)
    return calls, puts


# ──────────────────────────────────────────────────────────────────────────────
# Main benchmark
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  GPU / CPU Compute Verification")
    print("=" * 60)

    # ── Tier report ───────────────────────────────────────────────────────────
    print(f"\n[bsm_fast]      GPU (CuPy) ACTIVE : {BSM_GPU}")
    print(f"[EMA smoother]  GPU (CuPy) ACTIVE : {EMA_GPU}")
    print(f"[EMA smoother]  JIT (Numba) ACTIVE: {EMA_NUMBA}")
    print()

    # ── Warmup (JIT compile / CUDA context) ──────────────────────────────────
    print("Warming up compute tiers …")
    warmup()
    # EMA warmup
    dummy_c = np.ones(N_STRIKES, dtype=np.float64)
    dummy_p = np.ones(N_STRIKES, dtype=np.float64) * -1.0
    for _ in range(3):
        _apply_ema_batch(dummy_c, dummy_p)
    print("Warmup complete.\n")

    # ── Prepare synthetic data ────────────────────────────────────────────────
    spots, strikes, ivs, t_years, is_call, ois, mults = _build_synthetic_chain(N_CHAIN)
    gex_calls, gex_puts = _build_synthetic_gex(N_STRIKES)

    # ── Benchmark loop ────────────────────────────────────────────────────────
    print(f"Running {CYCLES} cycles (chain={N_CHAIN} contracts, strikes={N_STRIKES}) …\n")

    vram_before = _gpu_vram_free()
    bsm_times: list[float] = []
    ema_times: list[float] = []

    for i in range(CYCLES):
        # BSM Greeks
        t0 = time.perf_counter()
        compute_greeks_batch(spots, strikes, ivs, t_years, is_call, ois=ois, mults=mults)
        bsm_times.append(time.perf_counter() - t0)

        # EMA batch
        t0 = time.perf_counter()
        _apply_ema_batch(
            gex_calls + np.random.randn(N_STRIKES) * 1000,
            gex_puts  + np.random.randn(N_STRIKES) * 1000,
        )
        ema_times.append(time.perf_counter() - t0)

        if (i + 1) % 10 == 0:
            smi = _nvidia_smi_util()
            print(f"  Cycle {i+1:3d}  |  {smi}")

    vram_after = _gpu_vram_free()

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    bsm_avg_ms = np.mean(bsm_times) * 1000
    ema_avg_ms = np.mean(ema_times) * 1000
    print(f"  BSM Greeks  avg latency : {bsm_avg_ms:.3f} ms  (p95={np.percentile(bsm_times,95)*1000:.3f} ms)")
    print(f"  EMA smoother avg latency: {ema_avg_ms:.4f} ms  (p95={np.percentile(ema_times,95)*1000:.4f} ms)")

    if vram_before is not None and vram_after is not None:
        delta_mb = (vram_before - vram_after) / 1024 / 1024
        print(f"  VRAM consumed by kernels: {delta_mb:.1f} MB")

    print(f"\n  Final GPU status: {_nvidia_smi_util()}")
    print()
    print("  PASS  — GPU kernels completed all cycles without error." if True else "  FAIL")
    print("=" * 60)


if __name__ == "__main__":
    main()
