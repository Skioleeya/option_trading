"""Unit tests for VannaFlowAnalyzer and its new sub-modules.

Tests cover:
    1. VannaStateClassifier — state classification (original test parity)
    2. PearsonEngine        — correlation calculation
    3. IVAccelerationEngine — acceleration state classification
    4. classify_gex_regime  — GEX regime pure function
    5. VannaFlowAnalyzer    — thin orchestrator smoke tests
"""

from __future__ import annotations

from collections import deque

from l1_compute.trackers.vanna_flow_analyzer import VannaFlowAnalyzer
from l1_compute.trackers.vanna.gex_classifier import (
    VannaStateClassifier,
    classify_gex_regime,
    calculate_confidence,
)
from l1_compute.trackers.vanna.pearson_engine import PearsonEngine, SpotIVPoint
from l1_compute.trackers.vanna.acceleration_engine import IVAccelerationEngine
from shared.models.microstructure import (
    GexRegime,
    VannaAccelerationState,
    VannaFlowState,
)


# ── VannaStateClassifier (original tests — now via VannaStateClassifier directly) ──

def test_small_positive_correlation_stays_normal() -> None:
    clf = VannaStateClassifier()
    assert clf.classify(0.10, is_flip=False) == VannaFlowState.NORMAL
    assert clf.classify(0.00, is_flip=False) == VannaFlowState.NORMAL


def test_negative_correlation_enters_grind_stable() -> None:
    clf = VannaStateClassifier()
    assert clf.classify(-0.30, is_flip=False) == VannaFlowState.GRIND_STABLE


def test_danger_zone_still_takes_priority() -> None:
    clf = VannaStateClassifier()
    assert clf.classify(0.90, is_flip=False) == VannaFlowState.DANGER_ZONE


def test_flip_overrides_all_zones() -> None:
    clf = VannaStateClassifier()
    # Even if correlation is in grind-stable range, is_flip takes priority
    assert clf.classify(-0.80, is_flip=True) == VannaFlowState.VANNA_FLIP


def test_none_correlation_returns_normal() -> None:
    clf = VannaStateClassifier()
    assert clf.classify(None, is_flip=False) == VannaFlowState.NORMAL


# ── PearsonEngine ──────────────────────────────────────────────────────────────

def test_pearson_engine_perfect_positive() -> None:
    history: deque[SpotIVPoint] = deque(maxlen=500)
    engine = PearsonEngine(history)
    # Perfect positive correlation: iv = 0.1 + 0.001 * spot
    for i in range(20):
        spot = 550.0 + i
        history.append(SpotIVPoint(float(i), spot, 0.10 + 0.001 * spot))
    corr = engine.calculate()
    assert corr is not None
    assert corr > 0.99


def test_pearson_engine_insufficient_history() -> None:
    history: deque[SpotIVPoint] = deque(maxlen=500)
    engine = PearsonEngine(history)
    assert engine.calculate() is None
    history.append(SpotIVPoint(1.0, 550.0, 0.20))
    assert engine.calculate() is None


def test_pearson_engine_no_flip_on_stable_corr() -> None:
    history: deque[SpotIVPoint] = deque(maxlen=500)
    engine = PearsonEngine(history)
    # Push 20 correlation samples all near -0.5
    for i in range(20):
        engine.push_correlation(float(i * 10), -0.5)
    # Current corr also near -0.5 → no flip
    assert engine.detect_flip(200.0, -0.5) is False


# ── IVAccelerationEngine ───────────────────────────────────────────────────────

def test_iv_accel_unavailable_on_first_call() -> None:
    engine = IVAccelerationEngine()
    _, _, _, state = engine.update(0.20, 1000.0)
    assert state == VannaAccelerationState.UNAVAILABLE


def test_iv_accel_stable_when_roc_small() -> None:
    engine = IVAccelerationEngine()
    engine.update(0.20, 1000.0)
    _, _, _, state = engine.update(0.20, 1060.0)   # 60s later, same IV → ROC ≈ 0
    assert state == VannaAccelerationState.STABLE


def test_iv_accel_accelerating_fear_high_roc() -> None:
    engine = IVAccelerationEngine()
    engine.update(0.20, 1000.0)
    # Large IV spike in 10s → ROC in pp/5min very high
    _, _, _, state = engine.update(0.40, 1010.0)
    assert state == VannaAccelerationState.ACCELERATING_FEAR


def test_iv_accel_reset_clears_state() -> None:
    engine = IVAccelerationEngine()
    engine.update(0.20, 1000.0)
    engine.reset()
    _, _, _, state = engine.update(0.20, 2000.0)
    assert state == VannaAccelerationState.UNAVAILABLE


# ── classify_gex_regime ────────────────────────────────────────────────────────

def test_gex_regime_negative_is_acceleration() -> None:
    assert classify_gex_regime(-1.0) == GexRegime.ACCELERATION
    assert classify_gex_regime(-9999.0) == GexRegime.ACCELERATION


def test_gex_regime_none_is_neutral() -> None:
    assert classify_gex_regime(None) == GexRegime.NEUTRAL


def test_gex_regime_zero_is_neutral() -> None:
    assert classify_gex_regime(0.0) == GexRegime.NEUTRAL


# ── VannaFlowAnalyzer orchestrator smoke test ──────────────────────────────────

def test_analyzer_unavailable_before_warmup() -> None:
    analyzer = VannaFlowAnalyzer()
    result = analyzer.update(spot=560.0, atm_iv=0.20, net_gex=50.0)
    assert result.state == VannaFlowState.UNAVAILABLE


def test_analyzer_produces_result_after_warmup() -> None:
    analyzer = VannaFlowAnalyzer()
    for i in range(25):
        result = analyzer.update(
            spot=560.0 + i * 0.1,
            atm_iv=0.20 + i * 0.001,
            net_gex=100.0,
            sim_clock_mono=float(i),
        )
    assert result is not None
    assert result.state != VannaFlowState.UNAVAILABLE
    assert result.correlation is not None


def test_analyzer_reset_clears_data() -> None:
    analyzer = VannaFlowAnalyzer()
    for i in range(10):
        analyzer.update(spot=560.0, atm_iv=0.20, net_gex=10.0, sim_clock_mono=float(i))
    analyzer.reset()
    assert analyzer.data_points == 0
    result = analyzer.update(spot=560.0, atm_iv=0.20, net_gex=10.0, sim_clock_mono=100.0)
    assert result.state == VannaFlowState.UNAVAILABLE
