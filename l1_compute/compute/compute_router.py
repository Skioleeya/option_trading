"""Compute Router — Adaptive GPU/CPU tier selection.

Routing decision rules (evaluated in order):
    1. chain_size ≥ 100  → GPU (CuPy CUDA)       — amortise kernel launch cost
    2. chain_size < 100  → NumPy vectorized        — lower latency for small chains
    3. GPU unavailable   → Numba JIT (if present)  — CPU-parallel
    4. Numba unavailable → NumPy vectorized         — guaranteed fallback

Tier override: set `force_tier` to bypass auto-routing (useful for testing).

All tiers return the same `GreeksMatrix` schema.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np

from l1_compute.compute.gpu_greeks_kernel import GPUGreeksKernel, GreeksMatrix, _compute_numpy

logger = logging.getLogger(__name__)

# ── Numba availability probe ───────────────────────────────────────────────────
try:
    from l1_compute.analysis.bsm_fast import compute_greeks_batch as _numba_batch  # type: ignore
    _NUMBA_AVAILABLE = True
    logger.info("[ComputeRouter] Numba JIT tier available via bsm_fast.compute_greeks_batch.")
except ImportError:
    _NUMBA_AVAILABLE = False
    logger.info("[ComputeRouter] Numba tier unavailable. NumPy fallback active.")

# ── GPU routing threshold ─────────────────────────────────────────────────────
_GPU_CHAIN_THRESHOLD: int = 100


class ComputeTier(str, Enum):
    GPU    = "gpu"
    NUMBA  = "numba"
    NUMPY  = "numpy"


@dataclass
class ComputeDecision:
    """Records the routing decision for observability / logging."""
    tier: ComputeTier
    reason: str
    chain_size: int


from shared.config import settings

class ComputeRouter:
    """Adaptive compute tier router for BSM Greeks batch computation.

    Usage::

        router = ComputeRouter()
        matrix, decision = router.compute(
            spots, strikes, ivs, t_years, is_call,
            r=0.05, q=0.0, ois=ois_arr, mults=mults_arr
        )
        print(decision.tier)  # ComputeTier.GPU / NUMBA / NUMPY
    """

    def __init__(self, force_tier: Optional[ComputeTier] = None) -> None:
        self._kernel = GPUGreeksKernel()
        self._force = force_tier

    @property
    def gpu_available(self) -> bool:
        return self._kernel.gpu_available

    def compute(
        self,
        spots: np.ndarray,
        strikes: np.ndarray,
        ivs: np.ndarray,
        t_years: float,
        is_call: np.ndarray,
        r: float = 0.05,
        q: float = 0.0,
        ois: Optional[np.ndarray] = None,
        mults: Optional[np.ndarray] = None,
    ) -> tuple[GreeksMatrix, ComputeDecision]:
        """Route and execute BSM batch computation.

        Returns:
            (GreeksMatrix, ComputeDecision) — Greeks arrays and routing metadata.
        """
        n = len(spots)
        tier, reason = self._decide(n)

        decision = ComputeDecision(tier=tier, reason=reason, chain_size=n)

        matrix = self._execute(tier, spots, strikes, ivs, t_years, is_call, r, q, ois, mults)

        logger.debug(
            "[ComputeRouter] tier=%s chain=%d reason=%s",
            tier.value, n, reason,
        )
        return matrix, decision

    # ── Private ───────────────────────────────────────────────────────────────

    def _decide(self, chain_size: int) -> tuple[ComputeTier, str]:
        """Pure routing logic — returns (tier, reason_string)."""
        if self._force is not None:
            return self._force, f"forced:{self._force.value}"

        if chain_size >= settings.gpu_offload_threshold:
            if self._kernel.gpu_available:
                return ComputeTier.GPU, f"chain_size={chain_size} >= {settings.gpu_offload_threshold} (offload threshold)"
            # GPU needed but unavailable
            if _NUMBA_AVAILABLE:
                return ComputeTier.NUMBA, f"gpu_unavailable, chain_size={chain_size} >= {settings.gpu_offload_threshold}"
            return ComputeTier.NUMPY, "gpu_unavailable+numba_unavailable"
        else:
            # Small chain — CPU is faster (no kernel launch overhead)
            if _NUMBA_AVAILABLE:
                return ComputeTier.NUMBA, f"chain_size={chain_size} < {settings.gpu_offload_threshold}"
            return ComputeTier.NUMPY, f"chain_size={chain_size} < {settings.gpu_offload_threshold}, numba_unavailable"

    def _execute(
        self,
        tier: ComputeTier,
        spots: np.ndarray,
        strikes: np.ndarray,
        ivs: np.ndarray,
        t_years: float,
        is_call: np.ndarray,
        r: float,
        q: float,
        ois: Optional[np.ndarray],
        mults: Optional[np.ndarray],
    ) -> GreeksMatrix:
        n = len(spots)
        _ois   = ois   if ois   is not None else np.zeros(n, dtype=np.float64)
        _mults = mults if mults is not None else np.full(n, 100.0, dtype=np.float64)

        if tier == ComputeTier.GPU:
            return self._kernel.compute_batch(
                spots, strikes, ivs, t_years, is_call, r, q, _ois, _mults, prefer_gpu=True
            )

        if tier == ComputeTier.NUMBA:
            try:
                # Bridge to existing bsm_fast.compute_greeks_batch
                batch, batch_agg = _numba_batch(
                    spots, strikes, ivs, t_years, is_call, r=r, q=q,
                    ois=_ois, mults=_mults,
                )
                gex_raw = (batch["gamma"] * _ois * _mults * spots ** 2 / 1_000_000.0)
                return GreeksMatrix(
                    delta=batch["delta"],
                    gamma=batch["gamma"],
                    vega=batch["vega"],
                    vanna=batch["vanna"],
                    charm=batch["charm"],
                    theta=batch["theta"],
                    gex_per_contract=gex_raw,
                    call_gex=np.where(is_call, gex_raw, 0.0),
                    put_gex=np.where(~is_call, gex_raw, 0.0),
                    iv_used=ivs,
                )
            except Exception as exc:
                logger.warning("[ComputeRouter] Numba tier failed (%s). Falling back to NumPy.", exc)

        # NumPy fallback (always available)
        return _compute_numpy(spots, strikes, ivs, t_years, is_call, r, q, _ois, _mults)
