"""Tests for fused-signal contract normalization helpers."""

from __future__ import annotations

import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, "e:\\US.market\\Option_v3")

from l2_decision.events.decision_events import DecisionOutput
from l2_decision.events.fused_signal_contract import (
    classify_gex_intensity,
    normalize_signal_components,
    resolve_iv_regime,
)
from shared.config import settings

_ET = ZoneInfo("US/Eastern")


def _now() -> datetime:
    return datetime.now(_ET)


def test_resolve_iv_regime_maps_direction_aliases():
    assert resolve_iv_regime("BULLISH") == "LOW_VOL"
    assert resolve_iv_regime("BEARISH") == "HIGH_VOL"
    assert resolve_iv_regime("NEUTRAL") == "NORMAL"
    assert resolve_iv_regime("unknown") == "NORMAL"


def test_classify_gex_intensity_uses_config_thresholds():
    assert classify_gex_intensity(settings.gex_super_pin_threshold + 1) == "EXTREME_POSITIVE"
    assert classify_gex_intensity(settings.gex_strong_positive + 1) == "STRONG_POSITIVE"
    assert classify_gex_intensity(settings.gex_strong_negative - 1) == "EXTREME_NEGATIVE"
    assert classify_gex_intensity(-1.0) == "STRONG_NEGATIVE"
    assert classify_gex_intensity(settings.gex_moderate_threshold + 1) == "MODERATE"
    assert classify_gex_intensity(0.0) == "NEUTRAL"


def test_normalize_signal_components_translates_iv_regime_direction():
    components = normalize_signal_components(
        {
            "iv_regime": {"direction": "BEARISH", "confidence": 0.8},
            "momentum_signal": {"direction": "BULLISH", "confidence": 0.6},
        }
    )
    assert components["iv_regime"]["direction"] == "HIGH_VOL"
    assert components["momentum_signal"]["direction"] == "BULLISH"


def test_decision_output_data_uses_runtime_regime_and_gex_intensity():
    output = DecisionOutput(
        direction="NEUTRAL",
        confidence=0.31,
        fusion_weights={"momentum_signal": 0.5, "trap_detector": 0.5},
        pre_guard_direction="NEUTRAL",
        guard_actions=[],
        signal_summary={
            "iv_regime": {"direction": "BEARISH", "confidence": 0.8},
            "momentum_signal": {"direction": "BULLISH", "confidence": 0.6},
        },
        latency_ms=1.2,
        version=1,
        computed_at=_now(),
        iv_regime="HIGH_VOL",
        gex_intensity="STRONG_NEGATIVE",
    )

    fused = output.data["fused_signal"]
    assert fused["regime"] == "HIGH_VOL"
    assert fused["iv_regime"] == "HIGH_VOL"
    assert fused["gex_intensity"] == "STRONG_NEGATIVE"
