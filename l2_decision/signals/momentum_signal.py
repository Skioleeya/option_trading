"""l2_decision.signals.momentum_signal — VWAP-anchored spot momentum signal.

Extracted from backend/app/agents/agent_a.py (AgentA.run()).
No longer reads directly from snapshot dict — consumes FeatureVector.spot_roc_1m
and FeatureVector.bbo_imbalance_ewma, which are computed by the FeatureStore.

Changes vs legacy AgentA:
    - No snapshot dict dependency
    - BBO confirmation gate (new)
    - Confidence scaled by ROC magnitude
    - Pure function of FeatureVector (testable without live data)
"""

from __future__ import annotations

import math
from typing import Any

from l2_decision.events.decision_events import FeatureVector, RawSignal
from l2_decision.feature_store.registry import load_signal_config, get_param
from l2_decision.signals.base import SignalGeneratorBase


class MomentumSignal(SignalGeneratorBase):
    """VWAP-based spot momentum signal generator.

    Consumes:
        spot_roc_1m      — 1-minute rate-of-change (fractional)
        bbo_imbalance_ewma — BBO imbalance for direction confirmation

    Signal logic:
        BULLISH: roc > bull_threshold AND bbo > bbo_min
        BEARISH: roc < bear_threshold AND bbo < -bbo_min
        NEUTRAL: otherwise
    """

    name = "momentum_signal"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None:
            config = load_signal_config("momentum_signal")
        super().__init__(config)

        self._bull_threshold: float = self._param("roc_bull_threshold", 0.0015)
        self._bear_threshold: float = self._param("roc_bear_threshold", -0.0015)
        self._bbo_min: float = self._param("bbo_confirmation_min", 0.1)
        self._max_roc_ref: float = self._param("max_roc_reference", 0.005)
        self._conf_floor: float = self._param("confidence_floor", 0.3)

    def generate(self, features: FeatureVector) -> RawSignal:
        """Generate momentum signal from feature vector."""
        try:
            roc = features.get("spot_roc_1m", 0.0)
            bbo = features.get("bbo_imbalance_ewma", 0.0)
        except Exception:
            return self._make_neutral()

        # Directional classification with BBO confirmation
        if roc > self._bull_threshold and bbo > self._bbo_min:
            direction = "BULLISH"
            raw_value = min(1.0, roc / self._max_roc_ref)
        elif roc < self._bear_threshold and bbo < -self._bbo_min:
            direction = "BEARISH"
            raw_value = max(-1.0, roc / self._max_roc_ref)
        elif roc > self._bull_threshold:
            # ROC bullish but BBO not confirming — weakly bullish
            direction = "BULLISH"
            raw_value = min(0.5, roc / self._max_roc_ref)
        elif roc < self._bear_threshold:
            direction = "BEARISH"
            raw_value = max(-0.5, roc / self._max_roc_ref)
        else:
            return self._make_neutral(metadata={"roc": roc, "bbo": bbo})

        confidence = self._scale_confidence(roc, self._max_roc_ref, self._conf_floor)

        return self._make_signal(
            direction=direction,
            confidence=confidence,
            raw_value=raw_value,
            metadata={"spot_roc_1m": roc, "bbo_imbalance_ewma": bbo},
        )

    def reset(self) -> None:
        """Reset state (no internal state beyond base class)."""
        super().reset()
