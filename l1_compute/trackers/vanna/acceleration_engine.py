"""IV Rate-of-Change (ROC) and Acceleration engine for Vanna Flow.

Responsibilities:
    - Track last-seen IV and timestamp
    - Compute IV ROC (pp per 5-min)
    - Compute IV acceleration
    - Classify acceleration into VannaAccelerationState

Layer:  L1
Deps:   stdlib, shared/models
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from shared_rust.models import VannaAccelerationState


# ── Constants ─────────────────────────────────────────────────────────────────

_ROC_ACCEL_THRESHOLD = 2.0   # pp/5min² — significant acceleration
_ROC_HIGH_THRESHOLD  = 5.0   # pp/5min  — high fear level
_ROC_LOW_THRESHOLD   = -5.0  # pp/5min  — vol crush level
_MIN_ACCEL_DT        = 30.0  # seconds  — min spacing between ROC readings


class IVAccelerationEngine:
    """Tracks IV ROC and acceleration state.

    Args:
        history_maxlen: Maximum number of IV-ROC samples kept (default 10).
    """

    def __init__(self, history_maxlen: int = 10) -> None:
        self._iv_roc_history: deque[tuple[float, float]] = deque(maxlen=history_maxlen)
        self._last_iv: float | None = None
        self._last_iv_time: float | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def update(
        self,
        iv: float,
        now_mono: float,
    ) -> tuple[float | None, float | None, float | None, VannaAccelerationState]:
        """Update with new IV sample and return (iv_roc, iv_roc_prev, iv_accel, state).

        Args:
            iv:        Current ATM IV.
            now_mono:  Monotonic timestamp of this observation.

        Returns:
            (iv_roc, iv_roc_prev, iv_acceleration, acceleration_state)
        """
        iv_roc: Optional[float] = None
        iv_roc_prev: Optional[float] = None
        iv_accel: Optional[float] = None
        accel_state = VannaAccelerationState.UNAVAILABLE

        if self._last_iv is not None and self._last_iv_time is not None:
            dt = now_mono - self._last_iv_time
            if dt > 0:
                # Scale to pp per 5-min for readability
                iv_roc = (iv - self._last_iv) / dt * 60 * 5
                self._iv_roc_history.append((now_mono, iv_roc))

                if len(self._iv_roc_history) >= 2:
                    for ts, roc in reversed(list(self._iv_roc_history)[:-1]):
                        iv_roc_prev = roc
                        if (now_mono - ts) > _MIN_ACCEL_DT:
                            iv_accel = iv_roc - iv_roc_prev
                            break

                accel_state = self._classify(iv_roc, iv_roc_prev, iv_accel)

        # Advance state
        self._last_iv      = iv
        self._last_iv_time = now_mono

        return iv_roc, iv_roc_prev, iv_accel, accel_state

    def reset(self) -> None:
        """Clear all accumulated state (call on day change)."""
        self._iv_roc_history.clear()
        self._last_iv      = None
        self._last_iv_time = None

    # ── Snapshot for persistence ──────────────────────────────────────────────

    @property
    def last_iv(self) -> float | None:
        return self._last_iv

    @last_iv.setter
    def last_iv(self, value: float | None) -> None:
        self._last_iv = value

    @property
    def last_iv_time(self) -> float | None:
        return self._last_iv_time

    @last_iv_time.setter
    def last_iv_time(self, value: float | None) -> None:
        self._last_iv_time = value

    # ── Classification (pure, testable) ──────────────────────────────────────

    @staticmethod
    def _classify(
        iv_roc: float | None,
        iv_roc_prev: float | None,
        iv_accel: float | None,
    ) -> VannaAccelerationState:
        """Classify acceleration state — pure function, no side-effects."""
        if iv_roc is None:
            return VannaAccelerationState.UNAVAILABLE

        if iv_accel is None or iv_roc_prev is None:
            if iv_roc > _ROC_HIGH_THRESHOLD:
                return VannaAccelerationState.ACCELERATING_FEAR
            if iv_roc < _ROC_LOW_THRESHOLD:
                return VannaAccelerationState.ACCELERATING_CALM
            return VannaAccelerationState.STABLE

        if iv_roc > 0 and iv_roc_prev > 0:
            if iv_accel > _ROC_ACCEL_THRESHOLD:
                return VannaAccelerationState.ACCELERATING_FEAR
            if iv_accel < -_ROC_ACCEL_THRESHOLD:
                return VannaAccelerationState.DECELERATING_FEAR
            return VannaAccelerationState.STABLE

        if iv_roc < 0 and iv_roc_prev < 0:
            if iv_accel < -_ROC_ACCEL_THRESHOLD:
                return VannaAccelerationState.ACCELERATING_CALM
            if iv_accel > _ROC_ACCEL_THRESHOLD:
                return VannaAccelerationState.DECELERATING_CALM
            return VannaAccelerationState.STABLE

        if iv_roc > 0 and iv_roc_prev < 0:
            return VannaAccelerationState.REVERSING_UP
        if iv_roc < 0 and iv_roc_prev > 0:
            return VannaAccelerationState.REVERSING_DOWN

        return VannaAccelerationState.STABLE
