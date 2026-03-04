"""Tests for Phase 2: Signal Generators.

Covers:
    - SignalGenerator Protocol compliance
    - Each generator returns NEUTRAL on empty/zero features
    - Directional logic correctness
    - State machine (TrapDetector reset)
    - IV regime hysteresis
    - JumpSentinel sigma detection
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, "e:\\US.market\\Option_v3")

from l2_refactor.events.decision_events import FeatureVector
from l2_refactor.signals.base import SignalGenerator, SignalGeneratorBase
from l2_refactor.signals.momentum_signal import MomentumSignal
from l2_refactor.signals.trap_detector import TrapDetector
from l2_refactor.signals.iv_regime import IVRegimeEngine
from l2_refactor.signals.flow_analyzer import FlowAnalyzer
from l2_refactor.signals.micro_flow import MicroFlowSignal
from l2_refactor.signals.jump_sentinel import JumpSentinel

_ET = ZoneInfo("US/Eastern")


def _fv(**features) -> FeatureVector:
    return FeatureVector(features=features, timestamp=datetime.now(_ET))


def _zero_fv() -> FeatureVector:
    return _fv(
        spot_roc_1m=0.0, atm_iv=0.18, net_gex_normalized=0.0,
        vpin_composite=0.0, bbo_imbalance_ewma=0.0, call_wall_distance=0.02,
        iv_velocity_1m=0.0, wall_migration_speed=0.0, svol_correlation_15m=0.0,
        vol_accel_ratio=0.0, skew_25d_normalized=0.0, mtf_consensus_score=0.0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Protocol compliance
# ─────────────────────────────────────────────────────────────────────────────

class TestProtocolCompliance:

    @pytest.mark.parametrize("gen_class", [
        MomentumSignal, TrapDetector, IVRegimeEngine,
        FlowAnalyzer, MicroFlowSignal, JumpSentinel,
    ])
    def test_implements_protocol(self, gen_class):
        gen = gen_class()
        assert isinstance(gen, SignalGenerator), f"{gen_class.__name__} does not implement SignalGenerator"

    @pytest.mark.parametrize("gen_class", [
        MomentumSignal, TrapDetector, IVRegimeEngine,
        FlowAnalyzer, MicroFlowSignal, JumpSentinel,
    ])
    def test_has_name_attribute(self, gen_class):
        gen = gen_class()
        assert isinstance(gen.name, str) and len(gen.name) > 0

    @pytest.mark.parametrize("gen_class", [
        MomentumSignal, TrapDetector, IVRegimeEngine,
        FlowAnalyzer, MicroFlowSignal, JumpSentinel,
    ])
    def test_reset_does_not_raise(self, gen_class):
        gen = gen_class()
        gen.reset()  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# NEUTRAL on zero features
# ─────────────────────────────────────────────────────────────────────────────

class TestNeutralOnZeroFeatures:

    @pytest.mark.parametrize("gen_class", [
        MomentumSignal, FlowAnalyzer, MicroFlowSignal,
    ])
    def test_neutral_on_zero(self, gen_class):
        gen = gen_class()
        sig = gen.generate(_zero_fv())
        assert sig.direction == "NEUTRAL"
        assert sig.confidence == 0.0

    def test_trap_detector_idle_on_zero(self):
        gen = TrapDetector()
        sig = gen.generate(_zero_fv())
        assert sig.direction == "NEUTRAL"

    def test_iv_regime_neutral_normal_iv(self):
        gen = IVRegimeEngine()
        # ATM IV of 0.18 is in the NORMAL range [0.12, 0.25]
        fv = _fv(atm_iv=0.18, iv_velocity_1m=0.0, net_gex_normalized=0.0)
        sig = gen.generate(fv)
        assert sig.direction == "NEUTRAL"


# ─────────────────────────────────────────────────────────────────────────────
# MomentumSignal directional logic
# ─────────────────────────────────────────────────────────────────────────────

class TestMomentumSignal:

    def test_bullish_with_positive_roc_and_bbo(self):
        gen = MomentumSignal()
        fv = _fv(spot_roc_1m=0.003, bbo_imbalance_ewma=0.5)
        sig = gen.generate(fv)
        assert sig.direction == "BULLISH"
        assert sig.confidence > 0.3

    def test_bearish_with_negative_roc_and_bbo(self):
        gen = MomentumSignal()
        fv = _fv(spot_roc_1m=-0.003, bbo_imbalance_ewma=-0.5)
        sig = gen.generate(fv)
        assert sig.direction == "BEARISH"

    def test_raw_value_sign_consistent_with_direction(self):
        gen = MomentumSignal()
        fv = _fv(spot_roc_1m=0.004, bbo_imbalance_ewma=0.6)
        sig = gen.generate(fv)
        assert sig.raw_value > 0  # BULLISH → positive

    def test_confidence_scales_with_magnitude(self):
        gen = MomentumSignal()
        sig_small = gen.generate(_fv(spot_roc_1m=0.0016, bbo_imbalance_ewma=0.2))
        gen2 = MomentumSignal()
        sig_large = gen2.generate(_fv(spot_roc_1m=0.0050, bbo_imbalance_ewma=0.8))
        if sig_small.direction != "NEUTRAL" and sig_large.direction != "NEUTRAL":
            assert sig_large.confidence >= sig_small.confidence


# ─────────────────────────────────────────────────────────────────────────────
# TrapDetector state machine
# ─────────────────────────────────────────────────────────────────────────────

class TestTrapDetector:

    def test_enter_bull_trap_after_k_entry(self):
        gen = TrapDetector(config={"parameters": {
            "spot_entry_threshold": 0.001, "opt_fade_threshold": -0.0005,
            "k_entry": 3, "k_exit": 2, "rocket_exit_pct": 0.05,
            "iv_chaos_threshold": 0.60, "confidence_base": 0.70,
            "confidence_decay_per_tick": 0.05,
        }})
        # spot_roc > 0 and bbo > 0 → opt_fade_proxy = -bbo < opt_fade_threshold
        # This simulates: spot rising (+0.003) but option sellers (BBO asks win)
        # opt_fade_proxy = -bbo = -0.4 < -0.0005 → triggers bull trap entry
        fv = _fv(spot_roc_1m=0.003, bbo_imbalance_ewma=0.4, atm_iv=0.18)
        for _ in range(3):
            sig = gen.generate(fv)
        assert sig.direction == "BEARISH"   # BULL TRAP → BEARISH output

    def test_reset_clears_state(self):
        gen = TrapDetector()
        fv = _fv(spot_roc_1m=0.003, bbo_imbalance_ewma=-0.3, atm_iv=0.18)
        for _ in range(5):
            gen.generate(fv)
        gen.reset()
        assert gen.current_state == "IDLE"

    def test_iv_chaos_gate_suppresses(self):
        gen = TrapDetector()
        # Very high IV → should suppress and return NEUTRAL
        fv = _fv(spot_roc_1m=0.003, bbo_imbalance_ewma=-0.3, atm_iv=0.80)
        sig = gen.generate(fv)
        assert sig.direction == "NEUTRAL"


# ─────────────────────────────────────────────────────────────────────────────
# IVRegimeEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestIVRegimeEngine:

    def test_high_vol_returns_bearish(self):
        gen = IVRegimeEngine()
        # Feed enough ticks with high IV to pass hysteresis
        high_iv_fv = _fv(atm_iv=0.40, iv_velocity_1m=0.3, net_gex_normalized=-0.5)
        for _ in range(5):
            sig = gen.generate(high_iv_fv)
        assert sig.direction == "BEARISH"

    def test_low_vol_returns_bullish(self):
        gen = IVRegimeEngine()
        low_iv_fv = _fv(atm_iv=0.08, iv_velocity_1m=-0.2, net_gex_normalized=0.2)
        for _ in range(5):
            sig = gen.generate(low_iv_fv)
        assert sig.direction == "BULLISH"

    def test_raw_value_positive_for_high_vol(self):
        gen = IVRegimeEngine()
        fv = _fv(atm_iv=0.40, iv_velocity_1m=0.0, net_gex_normalized=0.0)
        for _ in range(5):
            sig = gen.generate(fv)
        assert sig.raw_value > 0  # HIGH_VOL = positive score


# ─────────────────────────────────────────────────────────────────────────────
# FlowAnalyzer
# ─────────────────────────────────────────────────────────────────────────────

class TestFlowAnalyzer:

    def test_bullish_when_gex_and_bbo_aligned(self):
        gen = FlowAnalyzer()
        fv = _fv(net_gex_normalized=-0.8, vol_accel_ratio=0.5,
                 vpin_composite=0.1, bbo_imbalance_ewma=0.7)
        sig = gen.generate(fv)
        assert sig.direction == "BULLISH"

    def test_bearish_when_gex_bearish(self):
        gen = FlowAnalyzer()
        # Positive GEX (dealer long gamma = selling pressure) + high VPIN toxicity
        # + negative vol_accel + negative BBO → strong bearish composite
        fv = _fv(net_gex_normalized=0.9, vol_accel_ratio=-0.8,
                 vpin_composite=0.9, bbo_imbalance_ewma=-0.8)
        sig = gen.generate(fv)
        assert sig.direction == "BEARISH"


# ─────────────────────────────────────────────────────────────────────────────
# JumpSentinel
# ─────────────────────────────────────────────────────────────────────────────

class TestJumpSentinel:

    def test_neutral_on_normal_roc(self):
        gen = JumpSentinel(config={"parameters": {
            "jump_sigma_threshold": 3.0, "rolling_window_ticks": 20,
            "jump_hold_ticks": 5, "min_jump_roc": 0.004,
        }})
        # Feed normal low-variance ROC values
        for _ in range(20):
            sig = gen.generate(_fv(spot_roc_1m=0.001))
        assert sig.direction == "NEUTRAL"

    def test_jump_detected_on_large_roc(self):
        gen = JumpSentinel(config={"parameters": {
            "jump_sigma_threshold": 2.0, "rolling_window_ticks": 30,
            "jump_hold_ticks": 5, "min_jump_roc": 0.002,
        }})
        # Build normal baseline
        for _ in range(30):
            gen.generate(_fv(spot_roc_1m=0.0001))
        # Inject large spike
        sig = gen.generate(_fv(spot_roc_1m=0.02))  # large positive jump
        assert sig.direction in ("BULLISH", "BEARISH")  # jump detected

    def test_hold_state_after_jump(self):
        gen = JumpSentinel(config={"parameters": {
            "jump_sigma_threshold": 2.0, "rolling_window_ticks": 30,
            "jump_hold_ticks": 5, "min_jump_roc": 0.002,
        }})
        for _ in range(30):
            gen.generate(_fv(spot_roc_1m=0.0001))
        gen.generate(_fv(spot_roc_1m=0.05))  # trigger jump
        assert gen.is_active_jump()

    def test_reset_clears_jump_state(self):
        gen = JumpSentinel()
        for _ in range(30):
            gen.generate(_fv(spot_roc_1m=0.0001))
        gen.generate(_fv(spot_roc_1m=0.05))
        gen.reset()
        assert not gen.is_active_jump()
