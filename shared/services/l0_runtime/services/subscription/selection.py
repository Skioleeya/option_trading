"""Subscription selection hysteresis for L0."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SubscriptionSelection:
    targets: set[str]
    symbol_to_strike: dict[str, float]
    priority_by_symbol: dict[str, int]
    diagnostics: dict[str, Any]


class SubscriptionRebalanceGate:
    def __init__(self, *, confirmations: int, min_shift_steps: int, interval_sec: float) -> None:
        self._confirmations = max(1, confirmations)
        self._min_shift_steps = max(0, min_shift_steps)
        self._interval_sec = max(1.0, interval_sec)
        self._last_core_signature: tuple[tuple[float, float] | None, tuple[float, float] | None] | None = None
        self._pending_core_signature: tuple[tuple[float, float] | None, tuple[float, float] | None] | None = None
        self._pending_confirmations = 0
        self._last_rebalance_mono = 0.0
        self._last_reason = "not_started"
        self.selection_diagnostics: dict[str, Any] = {
            "phase": "initial",
            "last_rebalance_reason": self._last_reason,
        }

    @staticmethod
    def merge_diagnostics(existing: dict[str, Any], native: dict[str, Any]) -> dict[str, Any]:
        phase = "dynamic" if native.get("phase") == "dynamic" or existing.get("phase") == "dynamic" else "initial"
        out = dict(existing)
        out["phase"] = phase
        for key in (
            "call_phase",
            "put_phase",
            "call_core_range",
            "put_core_range",
            "call_core_step_range",
            "put_core_step_range",
            "call_raw_range",
            "put_raw_range",
        ):
            if native.get(key) is not None:
                out[key] = str(native[key]) if key.endswith("_phase") else tuple(native[key])
        out["sentinel_count"] = int(out.get("sentinel_count", 0)) + len(native.get("sentinel_targets", set()))
        out["core_count"] = int(out.get("core_count", 0)) + len(native.get("core_targets", set()))
        return out

    def should_rebalance(self, diagnostics: dict[str, Any], now_mono: float, *, has_target_symbols: bool) -> bool:
        signature = self._core_signature(diagnostics)
        if not has_target_symbols:
            self._accept(signature, now_mono, "initial_subscribe")
            return True
        if diagnostics.get("phase") != "dynamic":
            self._accept(signature, now_mono, "initial_phase_refresh")
            return True
        if (now_mono - self._last_rebalance_mono) < self._interval_sec:
            self._last_reason = "interval_hold"
            return False
        if self._last_core_signature is None:
            self._accept(signature, now_mono, "dynamic_first_lock")
            return True
        if self._core_shift_steps(self._last_core_signature, signature) > self._min_shift_steps:
            self._accept(signature, now_mono, "dynamic_shift")
            return True
        if signature == self._pending_core_signature:
            self._pending_confirmations += 1
        else:
            self._pending_core_signature = signature
            self._pending_confirmations = 1
        if self._pending_confirmations >= self._confirmations:
            self._accept(signature, now_mono, "dynamic_confirmed")
            return True
        self._last_reason = "confirmation_hold"
        return False

    def record(self, diagnostics: dict[str, Any], *, target_count: int, subscribed_count: int, rebalanced: bool) -> None:
        self.selection_diagnostics = {
            **diagnostics,
            "target_count": target_count,
            "subscribed_count": subscribed_count,
            "last_rebalance_reason": self._last_reason,
            "rebalanced": rebalanced,
            "pending_confirmations": self._pending_confirmations,
        }

    def _accept(
        self,
        signature: tuple[tuple[float, float] | None, tuple[float, float] | None],
        now_mono: float,
        reason: str,
    ) -> None:
        self._last_core_signature = signature
        self._pending_core_signature = None
        self._pending_confirmations = 0
        self._last_rebalance_mono = now_mono
        self._last_reason = reason

    @staticmethod
    def _core_signature(diagnostics: dict[str, Any]) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
        return (
            SubscriptionRebalanceGate._required_step_tuple(diagnostics, "call_core_step_range"),
            SubscriptionRebalanceGate._required_step_tuple(diagnostics, "put_core_step_range"),
        )

    @staticmethod
    def _required_step_tuple(diagnostics: dict[str, Any], key: str) -> tuple[float, float] | None:
        raw = diagnostics.get(key)
        if not isinstance(raw, (tuple, list)) or len(raw) != 2:
            raise RuntimeError(f"subscription_rebalance_missing_step_range: {key}")
        try:
            return (float(raw[0]), float(raw[1]))
        except (TypeError, ValueError):
            raise RuntimeError(f"subscription_rebalance_invalid_step_range: {key}")

    @staticmethod
    def _core_shift_steps(
        old: tuple[tuple[float, float] | None, tuple[float, float] | None],
        new: tuple[tuple[float, float] | None, tuple[float, float] | None],
    ) -> int:
        values: list[int] = []
        for old_range, new_range in zip(old, new):
            if old_range is None or new_range is None:
                values.append(0 if old_range == new_range else 999)
                continue
            values.extend([round(abs(new_range[0] - old_range[0])), round(abs(new_range[1] - old_range[1]))])
        return max(values or [0])
