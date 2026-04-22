"""Compute Router — GPU-first routing with Rust CPU fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from l1_compute.compute.gpu_greeks_kernel import GPUGreeksKernel, GPUComputationUnavailableError, GreeksMatrix

logger = logging.getLogger(__name__)


class ComputeTier(str, Enum):
    GPU = "gpu"
    GPU_ONLY_BLOCKED = "gpu_only_blocked"
    NUMBA = "numba"
    NUMPY = "numpy"


@dataclass
class ComputeDecision:
    tier: ComputeTier
    reason: str
    chain_size: int


class ComputeRouter:
    """Adaptive compute router with deterministic Rust fallback when GPU is unavailable."""

    def __init__(self, force_tier: Optional[ComputeTier] = None) -> None:
        self._kernel = GPUGreeksKernel()
        self._force = force_tier
        self._cpu_fallback_logged = False

    @property
    def gpu_available(self) -> bool:
        return self._kernel.gpu_available

    def compute(
        self,
        spots: Any,
        strikes: Any,
        ivs: Any,
        t_years: float,
        is_call: Any,
        r: float = 0.05,
        q: float = 0.0,
        ois: Any | None = None,
        mults: Any | None = None,
    ) -> tuple[GreeksMatrix, ComputeDecision]:
        n = len(spots)
        tier, reason = self._decide(n)
        decision = ComputeDecision(tier=tier, reason=reason, chain_size=n)

        if tier == ComputeTier.NUMPY:
            matrix = self._execute_cpu_fallback(
                spots=spots, strikes=strikes, ivs=ivs, t_years=t_years, is_call=is_call, r=r, q=q, ois=ois, mults=mults
            )
            return matrix, decision

        try:
            matrix = self._execute_batch(
                spots=spots,
                strikes=strikes,
                ivs=ivs,
                t_years=t_years,
                is_call=is_call,
                r=r,
                q=q,
                ois=ois,
                mults=mults,
                prefer_gpu=True,
                allow_cpu_fallback=False,
            )
            return matrix, decision
        except GPUComputationUnavailableError as exc:
            matrix = self._execute_cpu_fallback(
                spots=spots, strikes=strikes, ivs=ivs, t_years=t_years, is_call=is_call, r=r, q=q, ois=ois, mults=mults
            )
            self._log_cpu_fallback_once(str(exc))
            fallback_decision = ComputeDecision(
                tier=ComputeTier.NUMPY,
                reason=f"gpu_runtime_failed_rust_cpu_fallback:{exc}",
                chain_size=n,
            )
            return matrix, fallback_decision

    def _decide(self, _: int) -> tuple[ComputeTier, str]:
        if self._force is not None:
            return self._force, f"forced:{self._force.value}"
        if self._kernel.gpu_available:
            return ComputeTier.GPU, "gpu_mandate_active"
        return ComputeTier.NUMPY, "gpu_unavailable_rust_cpu_fallback"

    @staticmethod
    def _zero_like(values: Any) -> Any:
        try:
            return values * 0.0
        except (TypeError, AttributeError, ValueError):
            return [0.0 for _ in range(len(values))]

    @classmethod
    def _constant_like(cls, values: Any, constant: float) -> Any:
        base = cls._zero_like(values)
        try:
            return base + constant
        except (TypeError, AttributeError, ValueError):
            return [constant for _ in range(len(values))]

    def _execute_batch(
        self,
        spots: Any,
        strikes: Any,
        ivs: Any,
        t_years: float,
        is_call: Any,
        r: float,
        q: float,
        ois: Any | None,
        mults: Any | None,
        *,
        prefer_gpu: bool,
        allow_cpu_fallback: bool,
    ) -> GreeksMatrix:
        _ois = ois if ois is not None else self._zero_like(spots)
        _mults = mults if mults is not None else self._constant_like(spots, 100.0)
        return self._kernel.compute_batch(
            spots,
            strikes,
            ivs,
            float(t_years),
            is_call,
            float(r),
            float(q),
            _ois,
            _mults,
            prefer_gpu=prefer_gpu,
            allow_cpu_fallback=allow_cpu_fallback,
        )

    def _execute_cpu_fallback(
        self,
        *,
        spots: Any,
        strikes: Any,
        ivs: Any,
        t_years: float,
        is_call: Any,
        r: float,
        q: float,
        ois: Any | None,
        mults: Any | None,
    ) -> GreeksMatrix:
        return self._execute_batch(
            spots=spots,
            strikes=strikes,
            ivs=ivs,
            t_years=t_years,
            is_call=is_call,
            r=r,
            q=q,
            ois=ois,
            mults=mults,
            prefer_gpu=False,
            allow_cpu_fallback=True,
        )

    def _log_cpu_fallback_once(self, reason: str) -> None:
        if not self._cpu_fallback_logged:
            logger.warning("[ComputeRouter] GPU failed, switched to Rust CPU fallback: %s", reason)
            self._cpu_fallback_logged = True
