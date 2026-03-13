"""Tests for Phase 1: decision events, feature store, and extractors.

Covers:
    - RawSignal immutability and validation
    - FeatureVector access methods
    - DecisionOutput serialization
    - FeatureStore registration, compute_all, cache
    - All 12 default feature extractors (synthetic snapshot)
    - DecisionAuditEntry serialization
"""

from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import pyarrow as pa
import pytest

sys.path.insert(0, "e:\\US.market\\Option_v3")

from l2_decision.events.decision_events import (
    DecisionAuditEntry,
    DecisionOutput,
    FeatureVector,
    FusedDecision,
    GuardedDecision,
    RawSignal,
)
from l2_decision.feature_store.extractors import build_default_extractors, reset_all_default_extractors
from l2_decision.feature_store.store import FeatureSpec, FeatureStore

_ET = ZoneInfo("US/Eastern")


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic EnrichedSnapshot (duck-typed, no l1_compute import needed)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _FakeAggregates:
    net_gex: float = 1_500.0  # MMUSD, i.e. $1.5B
    net_vanna_raw_sum: float = 0.0
    net_vanna: float = 0.0
    net_charm_raw_sum: float = 0.0
    net_charm: float = 0.0
    call_wall: float = 565.0
    put_wall: float = 555.0
    flip_level: float = 560.0
    atm_iv: float = 0.18
    total_call_gex: float = 2_000.0
    total_put_gex: float = 1_000.0
    num_contracts: int = 200

@dataclass
class _FakeMicro:
    vpin_1m: float = 0.30
    vpin_5m: float = 0.28
    vpin_15m: float = 0.25
    vpin_composite: float = 0.28
    vpin_regime: str = "NORMAL"
    bbo_imbalance_raw: float = 0.40
    bbo_ewma_fast: float = 0.35
    bbo_ewma_slow: float = 0.20
    bbo_persistence: float = 0.5
    vol_accel_ratio: float = 1.3
    vol_accel_threshold: float = 2.0
    vol_accel_elevated: bool = False
    vol_entropy: float = 0.6
    session_phase: str = "mid"

@dataclass
class _FakeSnapshot:
    spot: float = 560.0
    aggregates: _FakeAggregates = None
    microstructure: _FakeMicro = None
    version: int = 42
    chain: object = None

    def __post_init__(self):
        if self.aggregates is None:
            self.aggregates = _FakeAggregates()
        if self.microstructure is None:
            self.microstructure = _FakeMicro()


def _make_snap(**kwargs) -> _FakeSnapshot:
    return _FakeSnapshot(**kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Tests: RawSignal
# ─────────────────────────────────────────────────────────────────────────────

class TestRawSignal:

    def _now(self):
        return datetime.now(_ET)

    def test_frozen(self):
        sig = RawSignal("test", "BULLISH", 0.7, 0.5, self._now())
        with pytest.raises((AttributeError, TypeError)):
            sig.direction = "BEARISH"  # type: ignore

    def test_valid_directions(self):
        now = self._now()
        for d in ("BULLISH", "BEARISH", "NEUTRAL"):
            sig = RawSignal("x", d, 0.5, 0.0, now)
            assert sig.direction == d

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError):
            RawSignal("x", "STRONG_BUY", 0.5, 0.0, self._now())

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValueError):
            RawSignal("x", "NEUTRAL", 1.5, 0.0, self._now())

    def test_raw_value_out_of_range_raises(self):
        with pytest.raises(ValueError):
            RawSignal("x", "NEUTRAL", 0.5, 1.5, self._now())

    def test_is_directional(self):
        now = self._now()
        assert RawSignal("x", "BULLISH", 0.5, 0.5, now).is_directional()
        assert not RawSignal("x", "NEUTRAL", 0.0, 0.0, now).is_directional()

    def test_to_dict_keys(self):
        sig = RawSignal("test", "BEARISH", 0.6, -0.4, self._now(), {"k": 1.0})
        d = sig.to_dict()
        assert all(k in d for k in ("name", "direction", "confidence", "raw_value", "computed_at"))
        assert d["direction"] == "BEARISH"
        assert d["metadata"]["k"] == 1.0

    def test_nan_raw_value_raises(self):
        with pytest.raises(ValueError):
            RawSignal("x", "NEUTRAL", 0.0, float("nan"), self._now())


# ─────────────────────────────────────────────────────────────────────────────
# Tests: FeatureVector
# ─────────────────────────────────────────────────────────────────────────────

class TestFeatureVector:

    def _make_fv(self, **features) -> FeatureVector:
        return FeatureVector(features=features, timestamp=datetime.now(_ET))

    def test_get_existing(self):
        fv = self._make_fv(atm_iv=0.20)
        assert fv.get("atm_iv") == pytest.approx(0.20)

    def test_get_missing_returns_default(self):
        fv = self._make_fv()
        assert fv.get("nonexistent", 99.0) == 99.0

    def test_get_nan_returns_default(self):
        fv = self._make_fv(bad_feature=float("nan"))
        assert fv.get("bad_feature", -1.0) == -1.0

    def test_is_valid_true(self):
        fv = self._make_fv(spot_roc_1m=0.001)
        assert fv.is_valid("spot_roc_1m")

    def test_is_valid_false_missing(self):
        fv = self._make_fv()
        assert not fv.is_valid("missing_feature")

    def test_to_array_ordered(self):
        fv = self._make_fv(a=1.0, b=2.0, c=3.0)
        arr = fv.to_array(["c", "a", "b"])
        assert arr == [3.0, 1.0, 2.0]

    def test_len(self):
        fv = self._make_fv(x=1.0, y=2.0)
        assert len(fv) == 2

    def test_frozen(self):
        fv = self._make_fv(a=1.0)
        with pytest.raises((AttributeError, TypeError)):
            fv.features = {}  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# Tests: FeatureStore
# ─────────────────────────────────────────────────────────────────────────────

class TestFeatureStore:

    def test_register_and_compute(self):
        store = FeatureStore()
        store.register(FeatureSpec("test_feat", lambda s: s.spot * 2.0))
        snap = _make_snap(spot=100.0)
        fv = store.compute_all(snap)
        assert fv.get("test_feat") == pytest.approx(200.0)

    def test_missing_count_on_extractor_error(self):
        store = FeatureStore(enable_cache=False)
        store.register(FeatureSpec("bad_feat", lambda s: 1 / 0))  # raises ZeroDivisionError
        snap = _make_snap()
        fv = store.compute_all(snap)
        assert fv.missing_count == 1
        assert fv.get("bad_feat") == 0.0

    def test_none_returns_zero(self):
        store = FeatureStore(enable_cache=False)
        store.register(FeatureSpec("none_feat", lambda s: None))  # type: ignore
        snap = _make_snap()
        fv = store.compute_all(snap)
        assert fv.get("none_feat") == 0.0

    def test_cache_hit(self):
        call_count = [0]
        def extractor(s):
            call_count[0] += 1
            return 1.0
        store = FeatureStore(enable_cache=True)
        store.register(FeatureSpec("cached", extractor, ttl_seconds=10.0))
        snap = _make_snap()
        store.compute_all(snap)
        store.compute_all(snap)
        assert call_count[0] == 1  # second call used cache

    def test_cache_invalidated_when_snapshot_version_changes(self):
        call_count = [0]

        def extractor(s):
            call_count[0] += 1
            return float(s.spot)

        store = FeatureStore(enable_cache=True)
        store.register(FeatureSpec("versioned", extractor, ttl_seconds=10.0))

        snap_v1 = _make_snap(spot=100.0, version=1)
        snap_v2 = _make_snap(spot=200.0, version=2)

        first = store.compute_all(snap_v1)
        second = store.compute_all(snap_v2)

        assert first.get("versioned") == pytest.approx(100.0)
        assert second.get("versioned") == pytest.approx(200.0)
        assert call_count[0] == 2

    def test_atm_iv_updates_immediately_on_version_change(self):
        store = FeatureStore(enable_cache=True)
        store.register(FeatureSpec("atm_iv", lambda s: s.aggregates.atm_iv, ttl_seconds=30.0))

        snap_v1 = _make_snap(version=100)
        snap_v1.aggregates.atm_iv = 0.15
        snap_v2 = _make_snap(version=101)
        snap_v2.aggregates.atm_iv = 0.45

        first = store.compute_all(snap_v1)
        second = store.compute_all(snap_v2)

        assert first.get("atm_iv") == pytest.approx(0.15)
        assert second.get("atm_iv") == pytest.approx(0.45)

    def test_cache_clear(self):
        store = FeatureStore(enable_cache=True)
        store.register(FeatureSpec("f", lambda s: 1.0, ttl_seconds=100.0))
        snap = _make_snap()
        store.compute_all(snap)
        store.clear_cache()
        assert store.get_feature("f") is None

    def test_deregister(self):
        store = FeatureStore()
        store.register(FeatureSpec("to_remove", lambda s: 1.0))
        assert store.deregister("to_remove")
        assert "to_remove" not in store.registered_names

    def test_registered_names_sorted(self):
        store = FeatureStore()
        store.register(FeatureSpec("z_feat", lambda s: 0.0))
        store.register(FeatureSpec("a_feat", lambda s: 0.0))
        names = store.registered_names
        assert names == sorted(names)

    def test_len(self):
        store = FeatureStore()
        store.register(FeatureSpec("f1", lambda s: 0.0))
        store.register(FeatureSpec("f2", lambda s: 0.0))
        assert len(store) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Default 12 Feature Extractors
# ─────────────────────────────────────────────────────────────────────────────

class TestDefaultExtractors:

    def setup_method(self):
        self._specs = build_default_extractors()
        self._store = FeatureStore(enable_cache=False)
        self._store.register_bulk(self._specs)

    def test_all_default_features_registered(self):
        expected = {
            "spot_roc_1m", "atm_iv", "net_gex_normalized", "vpin_composite",
            "bbo_imbalance_ewma", "call_wall_distance", "iv_velocity_1m",
            "wall_migration_speed", "svol_correlation_15m", "vol_accel_ratio",
            "skew_25d_normalized", "rr25_call_minus_put", "skew_25d_valid", "mtf_consensus_score",
            "realized_volatility_15m", "vol_risk_premium", "vrp_realized_based",
            "net_vanna_raw_sum", "net_vanna", "net_charm_raw_sum", "net_charm",
        }
        assert expected.issubset(set(self._store.registered_names))

    def test_compute_all_no_nan(self):
        snap = _make_snap()
        fv = self._store.compute_all(snap)
        for name, value in fv.features.items():
            assert math.isfinite(value), f"Feature '{name}' is not finite: {value}"

    def test_atm_iv_reads_snapshot(self):
        snap = _make_snap()
        snap.aggregates.atm_iv = 0.25
        fv = self._store.compute_all(snap)
        assert fv.get("atm_iv") == pytest.approx(0.25)

    def test_gex_normalized_clamped(self):
        snap = _make_snap()
        snap.aggregates.net_gex = 1e12  # very large
        fv = self._store.compute_all(snap)
        assert fv.get("net_gex_normalized") <= 1.0

    def test_gex_normalized_uses_mmusd_to_1b_scale(self):
        snap = _make_snap()
        snap.aggregates.net_gex = 500.0  # MMUSD = $0.5B
        fv = self._store.compute_all(snap)
        assert fv.get("net_gex_normalized") == pytest.approx(0.5)

    def test_vpin_in_unit_interval(self):
        snap = _make_snap()
        fv = self._store.compute_all(snap)
        v = fv.get("vpin_composite")
        assert 0.0 <= v <= 1.0

    def test_bbo_imbalance_clamped(self):
        snap = _make_snap()
        snap.microstructure.bbo_ewma_fast = 0.9
        fv = self._store.compute_all(snap)
        assert fv.get("bbo_imbalance_ewma") <= 1.0

    def test_call_wall_distance_positive_when_above_spot(self):
        snap = _make_snap()
        snap.spot = 560.0
        snap.aggregates.call_wall = 570.0
        fv = self._store.compute_all(snap)
        dist = fv.get("call_wall_distance")
        assert dist > 0  # wall is above spot

    def test_vol_risk_premium_uses_percent_point_contract(self):
        snap = _make_snap()
        snap.aggregates.atm_iv = 0.18
        fv = self._store.compute_all(snap)
        assert fv.get("vol_risk_premium") == pytest.approx(3.0)

    def test_vrp_realized_based_uses_rolling_realized_vol_baseline(self):
        snap = _make_snap()
        snap.aggregates.atm_iv = 0.18

        prices = [100.0, 100.4, 99.8, 100.7, 101.0, 100.6]
        result = None
        original_monotonic = time.monotonic
        clock = {"now": 0.0}

        def _fake_monotonic() -> float:
            return clock["now"]

        time.monotonic = _fake_monotonic
        try:
            for idx, price in enumerate(prices):
                clock["now"] = float(idx * 180.0)
                snap.spot = price
                result = self._store.compute_all(snap)
        finally:
            time.monotonic = original_monotonic

        assert result is not None
        realized_vol = result.get("realized_volatility_15m")
        assert realized_vol > 0.0
        assert result.get("vrp_realized_based") == pytest.approx((0.18 * 100.0) - (realized_vol * 100.0))

    def test_reset_clears_stateful_extractors(self):
        """After reset, ROC-based features should return 0."""
        snap = _make_snap(spot=560.0)
        self._store.compute_all(snap)
        reset_all_default_extractors(self._specs)
        fv = self._store.compute_all(snap)
        assert fv.get("spot_roc_1m") == 0.0  # not enough history after reset

    def test_skew_25d_uses_recordbatch_computed_delta_and_iv(self):
        snap = _make_snap(spot=100.0)
        snap.aggregates.atm_iv = 0.25
        snap.chain = pa.RecordBatch.from_arrays(
            [
                pa.array(["C1", "P1"], type=pa.string()),
                pa.array([102.5, 97.5], type=pa.float64()),
                pa.array([True, False], type=pa.bool_()),
                pa.array([0.22, 0.31], type=pa.float64()),
                pa.array([0.27, -0.23], type=pa.float64()),
            ],
            names=["symbol", "strike", "is_call", "computed_iv", "computed_delta"],
        )

        fv = self._store.compute_all(snap)
        assert fv.get("skew_25d_valid") == pytest.approx(1.0)
        assert fv.get("skew_25d_normalized") == pytest.approx((0.31 - 0.22) / 0.25)
        assert fv.get("rr25_call_minus_put") == pytest.approx(0.22 - 0.31)

    def test_skew_25d_marks_invalid_when_delta_outside_tolerance(self):
        snap = _make_snap(spot=100.0)
        snap.aggregates.atm_iv = 0.25
        snap.chain = pa.RecordBatch.from_arrays(
            [
                pa.array(["C1", "P1"], type=pa.string()),
                pa.array([102.5, 97.5], type=pa.float64()),
                pa.array([True, False], type=pa.bool_()),
                pa.array([0.22, 0.31], type=pa.float64()),
                pa.array([0.45, -0.45], type=pa.float64()),
            ],
            names=["symbol", "strike", "is_call", "computed_iv", "computed_delta"],
        )

        fv = self._store.compute_all(snap)
        assert fv.get("skew_25d_valid") == pytest.approx(0.0)
        assert fv.get("skew_25d_normalized") == pytest.approx(0.0)
        assert fv.get("rr25_call_minus_put") == pytest.approx(0.0)

    def test_raw_sum_features_prefer_canonical_aggregate_fields(self):
        snap = _make_snap()
        snap.aggregates.net_vanna_raw_sum = 12.5
        snap.aggregates.net_vanna = -99.0
        snap.aggregates.net_charm_raw_sum = -4.0
        snap.aggregates.net_charm = 88.0

        fv = self._store.compute_all(snap)
        assert fv.get("net_vanna_raw_sum") == pytest.approx(12.5)
        assert fv.get("net_vanna") == pytest.approx(12.5)
        assert fv.get("net_charm_raw_sum") == pytest.approx(-4.0)
        assert fv.get("net_charm") == pytest.approx(-4.0)


# ─────────────────────────────────────────────────────────────────────────────
# Tests: DecisionOutput + DecisionAuditEntry
# ─────────────────────────────────────────────────────────────────────────────

class TestDecisionOutput:

    def _make_output(self, direction="BULLISH", confidence=0.75) -> DecisionOutput:
        return DecisionOutput(
            direction=direction,
            confidence=confidence,
            fusion_weights={"momentum_signal": 0.5, "trap_detector": 0.5},
            pre_guard_direction="BULLISH",
            guard_actions=[],
            signal_summary={"momentum_signal": "BULLISH"},
            latency_ms=4.5,
            version=42,
            computed_at=datetime.now(_ET),
        )

    def test_frozen(self):
        out = self._make_output()
        with pytest.raises((AttributeError, TypeError)):
            out.direction = "BEARISH"  # type: ignore

    def test_is_actionable_true(self):
        out = self._make_output("BULLISH", 0.75)
        assert out.is_actionable()

    def test_is_actionable_false_low_confidence(self):
        out = self._make_output("BULLISH", 0.3)
        assert not out.is_actionable()

    def test_is_actionable_false_neutral(self):
        out = self._make_output("NEUTRAL", 0.9)
        assert not out.is_actionable()

    def test_to_dict_complete(self):
        out = self._make_output()
        d = out.to_dict()
        for key in ("direction", "confidence", "fusion_weights", "guard_actions",
                    "signal_summary", "latency_ms", "version", "computed_at"):
            assert key in d, f"Missing key: {key}"

    def test_audit_entry_serialization(self):
        entry = DecisionAuditEntry(
            timestamp=datetime.now(_ET),
            feature_vector={"atm_iv": 0.18},
            signal_components={},
            fusion_weights={"momentum_signal": 1.0},
            fusion_mode="rule",
            pre_guard_direction="BULLISH",
            guard_actions=[],
            final_direction="BULLISH",
            final_confidence=0.75,
            shap_top5=[("atm_iv", 0.3)],
            latency_ms=3.5,
            l0_version=42,
        )
        d = entry.to_dict()
        assert d["final_direction"] == "BULLISH"
        assert d["l0_version"] == 42
        # shap_top5 is stored as-is (list of tuples) — compare elements
        assert d["shap_top5"][0][0] == "atm_iv"
        assert d["shap_top5"][0][1] == pytest.approx(0.3)
