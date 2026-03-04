"""l2_decision.signals.iv_regime — IV regime classification signal.

Migrated from DynamicWeightEngine.update_market_state() with enhanced logic:
- Hysteresis to prevent rapid regime switching
- IV velocity amplification
- GEX cross-check for additional confirmation

Output:
    direction: BULLISH (LOW_VOL → options buying opportunity)
              BEARISH (HIGH_VOL → hedging pressure)
              NEUTRAL (NORMAL regime)
    raw_value: continuous IV regime score [-1=LOW_VOL, +1=HIGH_VOL]
"""

from __future__ import annotations

from collections import deque
from typing import Any

from l2_decision.events.decision_events import FeatureVector, RawSignal
from l2_decision.feature_store.registry import load_signal_config
from l2_decision.signals.base import SignalGeneratorBase


class IVRegimeEngine(SignalGeneratorBase):
    """IV regime classifier producing a continuous regime score.

    HIGH_VOL → "BEARISH" direction (hedging pressure, fear spike)
    LOW_VOL  → "BULLISH" direction (complacency, gamma squeeze potential)
    NORMAL   → "NEUTRAL"

    The continuous `raw_value` in [-1, +1] is used by the FusionEngine
    to dynamically adjust signal weights in all other generators.

    Consumes:
        atm_iv              — current ATM IV level
        iv_velocity_1m      — IV rate of change direction/speed
        net_gex_normalized  — GEX regime for confirmation
    """

    name = "iv_regime"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None:
            config = load_signal_config("iv_regime")
        super().__init__(config)

        self._iv_low: float = self._param("iv_low_threshold", 0.12)
        self._iv_high: float = self._param("iv_high_threshold", 0.25)
        self._vel_weight: float = self._param("velocity_weight", 0.3)
        self._gex_amp: float = self._param("gex_amplification", 0.15)
        self._hysteresis_ticks: int = int(self._param("hysteresis_ticks", 3))

        # Hysteresis state
        self._current_regime: str = "NEUTRAL"  # LOW_VOL | NORMAL | HIGH_VOL
        self._regime_ticks: int = 0
        self._pending_regime: str = "NEUTRAL"

        # Historical IV for smoothing
        self._iv_buffer: deque[float] = deque(maxlen=60)

    def generate(self, features: FeatureVector) -> RawSignal:
        """Classify IV regime from feature vector."""
        try:
            atm_iv = features.get("atm_iv", 0.20)
            iv_vel = features.get("iv_velocity_1m", 0.0)
            net_gex = features.get("net_gex_normalized", 0.0)
        except Exception:
            return self._make_neutral()

        if not (0.0 < atm_iv < 5.0):  # sanity check
            return self._make_neutral(metadata={"atm_iv_invalid": atm_iv})

        self._iv_buffer.append(atm_iv)
        # Use 5-tick smoothed IV for regime classification
        smoothed_iv = sum(list(self._iv_buffer)[-5:]) / min(5, len(self._iv_buffer))

        # Base regime classification
        if smoothed_iv < self._iv_low:
            candidate = "LOW_VOL"
        elif smoothed_iv > self._iv_high:
            candidate = "HIGH_VOL"
        else:
            candidate = "NORMAL"

        # Hysteresis: require N consecutive ticks in new regime to switch
        if candidate != self._current_regime:
            if candidate == self._pending_regime:
                self._regime_ticks += 1
            else:
                self._pending_regime = candidate
                self._regime_ticks = 1

            if self._regime_ticks >= self._hysteresis_ticks:
                self._current_regime = candidate
                self._regime_ticks = 0

        regime = self._current_regime

        # Continuous regime score: [-1 = LOW_VOL, 0 = NORMAL, +1 = HIGH_VOL]
        # Normalized by the IV range
        iv_normalized = (smoothed_iv - self._iv_low) / max(0.01, self._iv_high - self._iv_low)
        raw_score = max(-1.0, min(1.0, -1.0 + 2.0 * iv_normalized))  # maps [low,high]→[-1,+1]

        # IV velocity amplifies the score
        raw_score += self._vel_weight * iv_vel

        # GEX cross-check: negative GEX amplifies HIGH_VOL signal
        if net_gex < -0.2:
            raw_score += self._gex_amp * abs(net_gex)

        raw_score = max(-1.0, min(1.0, raw_score))

        # Map regime to direction
        if regime == "HIGH_VOL":
            direction = "BEARISH"
            confidence = min(1.0, 0.4 + 0.6 * abs(raw_score))
        elif regime == "LOW_VOL":
            direction = "BULLISH"
            confidence = min(1.0, 0.4 + 0.6 * abs(raw_score))
        else:
            direction = "NEUTRAL"
            confidence = 0.2

        return self._make_signal(
            direction=direction,
            confidence=confidence,
            raw_value=raw_score,
            metadata={
                "smoothed_iv": smoothed_iv,
                "regime": {"LOW_VOL": -1.0, "NORMAL": 0.0, "HIGH_VOL": 1.0}.get(regime, 0.0),
                "iv_velocity_1m": iv_vel,
            },
        )

    def reset(self) -> None:
        super().reset()
        self._current_regime = "NEUTRAL"
        self._regime_ticks = 0
        self._pending_regime = "NEUTRAL"
        self._iv_buffer.clear()

    @property
    def current_regime(self) -> str:
        return self._current_regime
