"""l2_refactor.signals.micro_flow — VPIN + BBO + VolAccel composite microstructure signal.

Combines the three primary microstructure signals from L1 (already computed
by VPINv2, BBOv2, VolAccelV2 in l1_refactor) into a unified directional
micro-flow signal for L2 decision making.

Signal semantics:
    BULLISH: strong bid-side pressure + low toxicity + accelerating buy volume
    BEARISH: strong ask-side pressure + high toxicity + accelerating sell volume
"""

from __future__ import annotations

from typing import Any

from l2_refactor.events.decision_events import FeatureVector, RawSignal
from l2_refactor.feature_store.registry import load_signal_config
from l2_refactor.signals.base import SignalGeneratorBase


class MicroFlowSignal(SignalGeneratorBase):
    """VPIN + BBO + VolumeAcceleration composite microstructure signal.

    Consumes:
        vpin_composite       — composite VPIN toxicity [0, 1]
        bbo_imbalance_ewma   — BBO fast EWMA [-1, +1]
        vol_accel_ratio      — volume acceleration [-1, +1] (centered)
    """

    name = "micro_flow"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None:
            config = load_signal_config("micro_flow")
        super().__init__(config)

        self._w_vpin: float = self._param("weight_vpin", 0.40)
        self._w_bbo: float = self._param("weight_bbo", 0.40)
        self._w_vol: float = self._param("weight_vol_accel", 0.20)
        self._vpin_toxicity_threshold: float = self._param("vpin_toxicity_threshold", 0.25)
        self._dir_threshold: float = self._param("directional_threshold", 0.15)

    def generate(self, features: FeatureVector) -> RawSignal:
        """Compute composite microstructure signal."""
        try:
            vpin = features.get("vpin_composite", 0.0)
            bbo = features.get("bbo_imbalance_ewma", 0.0)
            vol_accel = features.get("vol_accel_ratio", 0.0)
        except Exception:
            return self._make_neutral()

        # High VPIN toxicity → market makers stepping back → adverse move likely
        # vpin=0.0 is the default/missing value → treat as neutral (no data)
        if vpin > 0.0:
            vpin_centered = -(vpin - 0.5) * 2.0
        else:
            vpin_centered = 0.0

        # VPIN toxicity gate: if toxicity is very high, suppress signal
        # (informed trading is too aggressive; both sides are dangerous)
        if vpin > self._vpin_toxicity_threshold * 2:
            return self._make_neutral(metadata={"vpin_toxicity_gate": vpin})

        # Composite score
        raw_score = (
            self._w_vpin * vpin_centered
            + self._w_bbo * bbo
            + self._w_vol * vol_accel
        )
        raw_score = max(-1.0, min(1.0, raw_score))

        if raw_score > self._dir_threshold:
            direction = "BULLISH"
        elif raw_score < -self._dir_threshold:
            direction = "BEARISH"
        else:
            return self._make_neutral(metadata={"raw_score": raw_score})

        confidence = self._scale_confidence(raw_score, reference=0.5, floor=0.3)

        return self._make_signal(
            direction=direction,
            confidence=confidence,
            raw_value=raw_score,
            metadata={"vpin": vpin, "bbo": bbo, "vol_accel": vol_accel},
        )

    def reset(self) -> None:
        super().reset()
