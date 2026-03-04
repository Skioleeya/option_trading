"""l2_refactor.signals.flow_analyzer — DEG-FLOW composite flow signal.

Wraps the Z-score normalized DEG (Delta/Entropy/Gamma) flow composition
from deg_composer.py into a unified SignalGenerator interface.

Since the full per-strike chain processing is already done by DEGComposer
at a lower level, this signal consumes the aggregate summary features
from FeatureVector (net_gex, vol_accel, vpin) to produce a composite
directional bias reflecting the overall option flow pressure.
"""

from __future__ import annotations

import math
from typing import Any

from l2_refactor.events.decision_events import FeatureVector, RawSignal
from l2_refactor.feature_store.registry import load_signal_config
from l2_refactor.signals.base import SignalGeneratorBase


class FlowAnalyzer(SignalGeneratorBase):
    """DEG-FLOW composite option flow signal.

    Combines net_gex_normalized, vol_accel_ratio, and vpin_composite
    into a single directional flow signal using configurable weights.

    Consumes:
        net_gex_normalized   — dealer gamma position direction
        vol_accel_ratio      — volume acceleration vs baseline
        vpin_composite       — order toxicity / informed flow proxy
        bbo_imbalance_ewma   — live orderbook pressure
    """

    name = "flow_analyzer"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None:
            config = load_signal_config("flow_analyzer")
        super().__init__(config)

        self._w_gex: float = self._param("weight_d", 0.40)
        self._w_vol: float = self._param("weight_e", 0.35)
        self._w_vpin: float = self._param("weight_g", 0.25)
        self._dir_threshold: float = self._param("directional_threshold", 0.1)

    def generate(self, features: FeatureVector) -> RawSignal:
        """Compute composite DEG-FLOW signal from feature vector."""
        try:
            gex = features.get("net_gex_normalized", 0.0)
            vol_accel = features.get("vol_accel_ratio", 0.0)
            vpin = features.get("vpin_composite", 0.0)
            bbo = features.get("bbo_imbalance_ewma", 0.0)
        except Exception:
            return self._make_neutral()

        # VPIN is [0,1] — only meaningful when non-zero (informed flow detected)
        # vpin=0.0 is the "not-yet-computed" default → treat as NEUTRAL (0.0)
        # vpin=0.5 baseline → 0.0; vpin=1.0 (max toxicity) → -1.0 (bearish)
        if vpin > 0.0:
            vpin_centered = -(vpin - 0.5) * 2.0   # [0,1] → [-1,+1] inverted
        else:
            vpin_centered = 0.0  # no data → neutral

        # Composite weighted score
        # GEX: positive = dealers long gamma = BEARISH flow (sell pressure)
        # Vol accel: already scaled to [-1,+1]
        # VPIN: high toxicity usually precedes adverse move
        raw_score = (
            self._w_gex * gex
            + self._w_vol * vol_accel
            + self._w_vpin * vpin_centered
        )

        # BBO adds a small confirming boost (not in base weights)
        raw_score += 0.1 * bbo

        raw_score = max(-1.0, min(1.0, raw_score))

        if raw_score > self._dir_threshold:
            direction = "BULLISH"
        elif raw_score < -self._dir_threshold:
            direction = "BEARISH"
        else:
            return self._make_neutral(metadata={"raw_score": raw_score})

        # Confidence from score magnitude
        confidence = self._scale_confidence(raw_score, reference=0.5, floor=0.3)

        return self._make_signal(
            direction=direction,
            confidence=confidence,
            raw_value=raw_score,
            metadata={
                "gex": gex,
                "vol_accel": vol_accel,
                "vpin": vpin,
                "bbo": bbo,
            },
        )

    def reset(self) -> None:
        super().reset()
