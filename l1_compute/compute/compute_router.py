"""Compute Router — GPU-first routing with explicit blocked fallback."""

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
    """Adaptive compute router with institutional GPU-only discipline."""

    def __init__(self, force_tier: Optional[ComputeTier] = None) -> None:
        self._kernel = GPUGreeksKernel()
        self._force = force_tier
        self._gpu_only_blocked_logged = False

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

        if tier == ComputeTier.GPU_ONLY_BLOCKED:
            matrix = self._blocked_matrix(ivs)
            self._log_gpu_only_blocked_once("gpu_unavailable_cpu_recompute_forbidden")
            return matrix, decision

        try:
            matrix = self._execute_gpu(spots, strikes, ivs, t_years, is_call, r, q, ois, mults)
            return matrix, decision
        except GPUComputationUnavailableError as exc:
            blocked = self._blocked_matrix(ivs)
            blocked_decision = ComputeDecision(
                tier=ComputeTier.GPU_ONLY_BLOCKED,
                reason=f"gpu_runtime_failed:{exc}",
                chain_size=n,
            )
            self._log_gpu_only_blocked_once(str(exc))
            return blocked, blocked_decision

    def _decide(self, _: int) -> tuple[ComputeTier, str]:
        if self._force is not None:
            return self._force, f"forced:{self._force.value}"
        if self._kernel.gpu_available:
            return ComputeTier.GPU, "gpu_mandate_active"
        return ComputeTier.GPU_ONLY_BLOCKED, "gpu_unavailable_cpu_recompute_forbidden"

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

    def _execute_gpu(
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
            prefer_gpu=True,
            allow_cpu_fallback=False,
        )

    def _blocked_matrix(self, ivs: Any) -> GreeksMatrix:
        zeros = self._zero_like(ivs)
        return GreeksMatrix(
            delta=zeros,
            gamma=zeros,
            vega=zeros,
            vanna=zeros,
            charm=zeros,
            theta=zeros,
            gex_per_contract=zeros,
            call_gex=zeros,
            put_gex=zeros,
            iv_used=ivs * 1.0,
        )

    def _log_gpu_only_blocked_once(self, reason: str) -> None:
        if not self._gpu_only_blocked_logged:
            logger.error("[ComputeRouter] GPU-only mode blocked CPU recomputation: %s", reason)
            self._gpu_only_blocked_logged = True
