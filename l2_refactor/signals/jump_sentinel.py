"""l2_refactor.signals.jump_sentinel — Price jump detection signal.

Detects abnormal spot price jumps using rolling volatility.
When a jump is detected, the signal enters HOLD state for N ticks,
which can be used by the GuardRailEngine to gate all other signals.

Inspired by L0 StatisticalBreaker (5σ tick jump detection) but operates
at the L2 feature level rather than raw tick validation.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Any

from l2_refactor.events.decision_events import FeatureVector, RawSignal
from l2_refactor.feature_store.registry import load_signal_config
from l2_refactor.signals.base import SignalGeneratorBase


class JumpSentinel(SignalGeneratorBase):
    """Spot price jump detector.

    Uses rolling standard deviation of spot_roc_1m to identify
    statistically significant moves (N-sigma threshold).

    Output:
        NEUTRAL:  no jump detected (safe to act)
        BEARISH:  downward jump detected (signals suppressed for hold_ticks)
        BULLISH:  upward jump detected   (signals suppressed for hold_ticks)

    Jump confidence encodes the sigma multiple (clipped to [0.5, 1.0]).
    The GuardRailEngine uses is_jump() to gate other signals.
    """

    name = "jump_sentinel"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None:
            config = load_signal_config("jump_sentinel")
        super().__init__(config)

        self._sigma_threshold: float = self._param("jump_sigma_threshold", 3.0)
        self._window_ticks: int = int(self._param("rolling_window_ticks", 60))
        self._hold_ticks: int = int(self._param("jump_hold_ticks", 5))
        self._min_jump_roc: float = self._param("min_jump_roc", 0.004)

        # Rolling window for ROC values
        self._roc_buffer: deque[float] = deque(maxlen=self._window_ticks)

        # Jump hold state
        self._hold_remaining: int = 0
        self._last_jump_direction: str = "NEUTRAL"
        self._last_jump_sigma: float = 0.0

    def generate(self, features: FeatureVector) -> RawSignal:
        """Detect jump from spot_roc_1m feature."""
        try:
            roc = features.get("spot_roc_1m", 0.0)
        except Exception:
            return self._make_neutral()

        self._roc_buffer.append(roc)
        self._tick_count += 1

        # Decrement hold counter
        if self._hold_remaining > 0:
            self._hold_remaining -= 1
            # During hold, continue emitting jump signal
            raw = 1.0 if self._last_jump_direction == "BULLISH" else -1.0
            confidence = min(1.0, 0.5 + self._last_jump_sigma / (2 * self._sigma_threshold))
            return self._make_signal(
                direction=self._last_jump_direction,
                confidence=confidence,
                raw_value=raw,
                metadata={"hold_remaining": float(self._hold_remaining), "sigma": self._last_jump_sigma},
            )

        # Need enough samples for meaningful std
        if len(self._roc_buffer) < max(10, self._window_ticks // 4):
            return self._make_neutral()

        buf = list(self._roc_buffer)
        n = len(buf)
        mean = sum(buf) / n
        variance = sum((v - mean) ** 2 for v in buf) / n
        std = math.sqrt(variance) if variance > 0 else 0.0

        if std < 1e-9:
            return self._make_neutral()

        sigma = abs(roc - mean) / std

        # Jump condition: must exceed sigma threshold AND absolute ROC threshold
        if sigma >= self._sigma_threshold and abs(roc) >= self._min_jump_roc:
            self._hold_remaining = self._hold_ticks
            self._last_jump_sigma = sigma
            direction = "BULLISH" if roc > 0 else "BEARISH"
            self._last_jump_direction = direction
            raw = 1.0 if direction == "BULLISH" else -1.0
            confidence = min(1.0, 0.5 + sigma / (2 * self._sigma_threshold))

            return self._make_signal(
                direction=direction,
                confidence=confidence,
                raw_value=raw,
                metadata={"sigma": sigma, "roc": roc, "rolling_std": std},
            )

        return self._make_neutral(metadata={"sigma": sigma, "roc": roc})

    def is_active_jump(self) -> bool:
        """Returns True if currently in a jump hold period."""
        return self._hold_remaining > 0

    def reset(self) -> None:
        super().reset()
        self._roc_buffer.clear()
        self._hold_remaining = 0
        self._last_jump_direction = "NEUTRAL"
        self._last_jump_sigma = 0.0
