"""l2_decision.fusion.normalizer — Signal normalization to [-1.0, +1.0].

Normalizes all RawSignal values before fusion to ensure fair weighting
regardless of each signal generator's internal scaling.

Normalization contract:
    raw_value is already in [-1.0, +1.0] (enforced by RawSignal.__post_init__)
    direction maps BULLISH→+1.0, BEARISH→-1.0, NEUTRAL→0.0
    confidence scales the final value: normalized = raw_value * confidence

This module also provides batch normalization for the full signal set.
"""

from __future__ import annotations

import math
from typing import Any

from l2_decision.events.decision_events import FeatureVector, RawSignal

_DIRECTION_MAP = {
    "BULLISH": 1.0,
    "BEARISH": -1.0,
    "NEUTRAL": 0.0,
    "HALT": 0.0,
}


class SignalNormalizer:
    """Normalizes RawSignal values for fusion engine input.

    All signals are mapped to a standardized float in [-1.0, +1.0].
    This decouples signal generation (which may use arbitrary scales)
    from fusion (which needs comparable units).
    """

    def normalize(self, signal: RawSignal) -> float:
        """Normalize a single signal to a signed float.

        Uses the signal's raw_value (already in [-1,1]) scaled by confidence.
        Direction provides the sign; confidence scales magnitude.

        Returns:
            Float in [-1.0, +1.0].
        """
        raw = signal.raw_value
        confidence = signal.confidence

        # Use raw_value × confidence for nuanced scaling
        normalized = raw * confidence

        # Cross-check with direction: ensure sign consistency
        d = _DIRECTION_MAP.get(signal.direction, 0.0)
        if d != 0.0:
            # If direction and raw_value sign differ, trust direction
            if (d > 0 and normalized < 0) or (d < 0 and normalized > 0):
                normalized = -normalized

        return max(-1.0, min(1.0, normalized))

    def normalize_batch(self, signals: dict[str, RawSignal]) -> dict[str, float]:
        """Normalize all signals in a batch.

        Args:
            signals: dict of signal_name → RawSignal.

        Returns:
            dict of signal_name → normalized float in [-1.0, +1.0].
        """
        return {name: self.normalize(sig) for name, sig in signals.items()}

    @staticmethod
    def direction_to_float(direction: str) -> float:
        """Map direction string to sign float."""
        return _DIRECTION_MAP.get(direction, 0.0)

    @staticmethod
    def float_to_direction(value: float, threshold: float = 0.1) -> str:
        """Map normalized float back to direction string."""
        if value > threshold:
            return "BULLISH"
        if value < -threshold:
            return "BEARISH"
        return "NEUTRAL"
