"""l2_decision.fusion.rule_fusion — Backward-compatible rule-based signal fusion.

Migrated from backend/app/services/fusion/dynamic_weight_engine.py.
Preserves the IV-regime adaptive weight table for backward compatibility.
Used as the primary fusion path and as fallback when attention fusion
model is unavailable.

Weight schedule:
    LOW_VOL (IV < 12%):   momentum↑, trap↑, gex↓
    NORMAL  (12%–25%):    balanced weights from config
    HIGH_VOL (IV > 25%):  flow↑, micro↑, momentum↓
"""

from __future__ import annotations

import logging
import time
from typing import Any

from l2_decision.events.decision_events import (
    FeatureVector,
    FusedDecision,
    RawSignal,
)
from l2_decision.fusion.normalizer import SignalNormalizer

logger = logging.getLogger(__name__)


# Default weight table by IV regime
# Keys must match SignalGenerator.name values
_WEIGHT_TABLE: dict[str, dict[str, float]] = {
    "LOW_VOL": {
        "momentum_signal": 0.30,
        "trap_detector":   0.30,
        "iv_regime":       0.10,
        "flow_analyzer":   0.15,
        "micro_flow":      0.15,
    },
    "NORMAL": {
        "momentum_signal": 0.20,
        "trap_detector":   0.25,
        "iv_regime":       0.15,
        "flow_analyzer":   0.25,
        "micro_flow":      0.15,
    },
    "HIGH_VOL": {
        "momentum_signal": 0.10,
        "trap_detector":   0.15,
        "iv_regime":       0.20,
        "flow_analyzer":   0.30,
        "micro_flow":      0.25,
    },
}


class RuleFusionEngine:
    """IV-regime adaptive rule-based signal fusion.

    Fuses multiple RawSignals using fixed weight tables keyed by IV regime.
    Equivalent to DynamicWeightEngine.calculate_weights() but operating on
    the new FeatureVector → RawSignal pipeline.

    Backward compatibility:
        Produces FusedDecision objects identical in semantics to the
        old FusedSignalResult / direction+confidence dict pattern.
    """

    def __init__(
        self,
        weight_table: dict[str, dict[str, float]] | None = None,
    ) -> None:
        self._weight_table = weight_table or _WEIGHT_TABLE
        self._normalizer = SignalNormalizer()
        self._validate_weights()

    def _validate_weights(self) -> None:
        """Assert weight tables sum to 1.0 (±0.01 tolerance)."""
        for regime, weights in self._weight_table.items():
            total = sum(weights.values())
            if abs(total - 1.0) > 0.01:
                raise ValueError(
                    f"Weights for regime '{regime}' sum to {total:.3f}, expected 1.0"
                )

    def fuse(
        self,
        signals: dict[str, RawSignal],
        features: FeatureVector,
        iv_regime: str = "NORMAL",
    ) -> FusedDecision:
        """Fuse signals using regime-adaptive weights.

        Args:
            signals:   dict of signal_name → RawSignal.
            features:  current FeatureVector (used for audit metadata).
            iv_regime: "LOW_VOL" | "NORMAL" | "HIGH_VOL" from IVRegimeEngine.

        Returns:
            FusedDecision with direction, confidence, weights, and components.
        """
        t0 = time.perf_counter()

        regime = iv_regime if iv_regime in self._weight_table else "NORMAL"
        weights = self._weight_table[regime]

        # Normalize all signals to [-1, +1]
        normalized = self._normalizer.normalize_batch(signals)

        # Redistribute weights for missing signals
        active_names = [n for n in weights if n in signals]
        if not active_names:
            return self._empty_decision(signals, features, weights)

        # Scale weights to sum=1.0 over active signals only
        active_weight_sum = sum(weights.get(n, 0.0) for n in active_names)
        if active_weight_sum < 1e-9:
            return self._empty_decision(signals, features, weights)

        scaled_weights: dict[str, float] = {
            n: weights.get(n, 0.0) / active_weight_sum
            for n in active_names
        }

        # Weighted sum
        raw_score = sum(
            scaled_weights[n] * normalized.get(n, 0.0)
            for n in active_names
        )

        # Confidence = weighted average of individual signal confidences
        confidence = sum(
            scaled_weights[n] * signals[n].confidence
            for n in active_names
        )
        confidence = max(0.0, min(1.0, confidence))

        direction = SignalNormalizer.float_to_direction(raw_score, threshold=0.05)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        return FusedDecision(
            direction=direction,
            confidence=confidence,
            raw_score=raw_score,
            fusion_weights={**scaled_weights},  # copy
            signal_components=dict(signals),
            feature_vector=features,
            fusion_mode="rule",
            latency_ms=latency_ms,
        )

    def _empty_decision(
        self,
        signals: dict[str, RawSignal],
        features: FeatureVector,
        weights: dict[str, float],
    ) -> FusedDecision:
        """Return a NEUTRAL FusedDecision when no signals are available."""
        return FusedDecision(
            direction="NEUTRAL",
            confidence=0.0,
            raw_score=0.0,
            fusion_weights=dict(weights),
            signal_components=dict(signals),
            feature_vector=features,
            fusion_mode="rule",
            latency_ms=0.0,
        )

    def update_weight_table(self, regime: str, weights: dict[str, float]) -> None:
        """Hot-update weights for a regime. Validates sum = 1.0."""
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")
        self._weight_table[regime] = dict(weights)
        logger.info("RuleFusionEngine: updated weights for regime '%s'", regime)
