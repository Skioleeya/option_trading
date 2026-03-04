"""l2_decision.fusion.attention_fusion — Numpy-based attention-weighted signal fusion.

Implements the Attention Fusion layer described in L2_DECISION_ANALYSIS.md §5.2.
Uses numpy softmax instead of torch to eliminate heavy ML framework dependency.

Architecture:
    Layer 1: Signal Normalization   [-1.0 ~ +1.0]
    Layer 2: Regime-conditioned Attention Weights (softmax over learned scores)
    Layer 3: Weighted Sum → raw_fused_score
    Layer 4: Platt Scaling → calibrated confidence [0, 1]
    Layer 5: Direction = sign(raw_fused_score)

Training:
    AttentionWeights are initialized from the RuleFusionEngine weight tables.
    Nightly retrain via _update_weights() with T-1 day signal/PnL correlation.
    When no model is available, falls back to RuleFusionEngine.

Shadow Mode:
    Run alongside RuleFusionEngine during validation phase.
    Track mismatch_rate in Prometheus counter l2_shadow_mismatch_total.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any

import numpy as np

from l2_decision.events.decision_events import FeatureVector, FusedDecision, RawSignal
from l2_decision.fusion.normalizer import SignalNormalizer
from l2_decision.fusion.rule_fusion import RuleFusionEngine

logger = logging.getLogger(__name__)


def _softmax(x: np.ndarray) -> np.ndarray:
    """Numerically stable softmax."""
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()


class AttentionFusionEngine:
    """Numpy-based attention-weighted signal fusion engine.

    Learns signal weights per regime from historical performance.
    Falls back to RuleFusionEngine when no learned weights are available.

    Weight representation:
        _attention_weights: dict[regime → dict[signal_name → raw_attention_score]]
        Actual fusion weights = softmax(raw_attention_scores)
    """

    # Signal names in canonical order for numpy ops
    _SIGNAL_NAMES = [
        "momentum_signal",
        "trap_detector",
        "iv_regime",
        "flow_analyzer",
        "micro_flow",
    ]

    def __init__(
        self,
        fallback_engine: RuleFusionEngine | None = None,
        model_available: bool = False,
    ) -> None:
        self._fallback = fallback_engine or RuleFusionEngine()
        self._model_available = model_available
        self._normalizer = SignalNormalizer()

        # Initialize attention scores from rule weights (log-space of rule weights)
        # Regime → signal_name → raw attention logit
        self._attention_logits: dict[str, dict[str, float]] = {
            "LOW_VOL":  {n: math.log(w + 1e-9) for n, w in self._fallback._weight_table["LOW_VOL"].items()},
            "NORMAL":   {n: math.log(w + 1e-9) for n, w in self._fallback._weight_table["NORMAL"].items()},
            "HIGH_VOL": {n: math.log(w + 1e-9) for n, w in self._fallback._weight_table["HIGH_VOL"].items()},
        }

        # Platt scaling parameters (learned; initialized to identity)
        self._platt_a: float = 1.0
        self._platt_b: float = 0.0

        # Shadow mode tracking
        self._mismatch_count: int = 0
        self._total_decisions: int = 0

    def is_model_available(self) -> bool:
        return self._model_available

    def fuse(
        self,
        signals: dict[str, RawSignal],
        features: FeatureVector,
        iv_regime: str = "NORMAL",
    ) -> FusedDecision:
        """Fuse signals using attention weights.

        Falls back to rule_fusion if model_available=False.
        """
        if not self._model_available:
            logger.debug("AttentionFusion: model unavailable, falling back to rule_fusion")
            return self._fallback.fuse(signals, features, iv_regime)

        return self._attention_fuse(signals, features, iv_regime)

    def _attention_fuse(
        self,
        signals: dict[str, RawSignal],
        features: FeatureVector,
        iv_regime: str,
    ) -> FusedDecision:
        """Core attention fusion logic."""
        t0 = time.perf_counter()

        regime = iv_regime if iv_regime in self._attention_logits else "NORMAL"
        logits_map = self._attention_logits[regime]

        # Build ordered arrays from active signals
        active_names = [n for n in self._SIGNAL_NAMES if n in signals]
        if not active_names:
            return self._fallback.fuse(signals, features, iv_regime)

        normalized = self._normalizer.normalize_batch(signals)

        # Attention weights via softmax over logits
        logits = np.array([logits_map.get(n, 0.0) for n in active_names])
        attn_weights = _softmax(logits)

        # Weighted signal values
        signal_values = np.array([normalized.get(n, 0.0) for n in active_names])
        raw_score = float(np.dot(attn_weights, signal_values))
        raw_score = max(-1.0, min(1.0, raw_score))

        # Platt scaling: σ(a·score + b) → calibrated confidence
        platt_input = self._platt_a * raw_score + self._platt_b
        confidence = 1.0 / (1.0 + math.exp(-platt_input))

        direction = SignalNormalizer.float_to_direction(raw_score, threshold=0.05)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        fusion_weights = dict(zip(active_names, attn_weights.tolist()))

        return FusedDecision(
            direction=direction,
            confidence=confidence,
            raw_score=raw_score,
            fusion_weights=fusion_weights,
            signal_components=dict(signals),
            feature_vector=features,
            fusion_mode="attention",
            latency_ms=latency_ms,
        )

    def compare_with_rule(
        self,
        signals: dict[str, RawSignal],
        features: FeatureVector,
        iv_regime: str = "NORMAL",
    ) -> dict[str, Any]:
        """Run both attention and rule fusion; return comparison dict (shadow mode)."""
        self._total_decisions += 1
        attn_result = self._attention_fuse(signals, features, iv_regime)
        rule_result = self._fallback.fuse(signals, features, iv_regime)

        mismatch = attn_result.direction != rule_result.direction
        if mismatch:
            self._mismatch_count += 1

        mismatch_rate = self._mismatch_count / max(1, self._total_decisions)

        return {
            "attention_direction": attn_result.direction,
            "rule_direction": rule_result.direction,
            "mismatch": mismatch,
            "mismatch_rate": mismatch_rate,
            "total_decisions": self._total_decisions,
        }

    @property
    def mismatch_rate(self) -> float:
        """Fraction of decisions where attention ≠ rule fusion."""
        return self._mismatch_count / max(1, self._total_decisions)

    def update_weights(self, regime: str, new_logits: dict[str, float]) -> None:
        """Update attention logits for a regime (e.g., after nightly retrain)."""
        if regime not in self._attention_logits:
            self._attention_logits[regime] = {}
        self._attention_logits[regime].update(new_logits)
        logger.info("AttentionFusion: updated logits for regime '%s'", regime)

    def update_platt(self, a: float, b: float) -> None:
        """Update Platt scaling parameters after calibration."""
        self._platt_a = a
        self._platt_b = b
        logger.info("AttentionFusion: updated Platt params a=%.4f b=%.4f", a, b)

    def enable_model(self, enabled: bool = True) -> None:
        """Activate or deactivate attention fusion (for shadow mode transitions)."""
        self._model_available = enabled
        logger.info("AttentionFusion: model_available=%s", enabled)
