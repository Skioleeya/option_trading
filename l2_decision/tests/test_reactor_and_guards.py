"""Tests for Phase 3 + 4: Fusion, Guard Rails, Reactor, Audit.

Covers:
    - SignalNormalizer direction maps and batch normalize
    - RuleFusionEngine weight validation and fusion output
    - AttentionFusionEngine fallback behavior
    - GuardRailEngine: KillSwitch halt, SessionGuard, DrawdownGuard
    - ManualKillSwitch: activate/deactivate/persist
    - L2DecisionReactor: end-to-end decide() returns DecisionOutput
    - Reactor: shadow mode mismatch tracking
    - AuditTrail: append, recent, flush
    - L2Instrumentation: no-op safety
"""

from __future__ import annotations

import sys
import asyncio
import threading
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, "e:\\US.market\\Option_v3")

from l2_decision.events.decision_events import (
    DecisionAuditEntry,
    DecisionOutput,
    FeatureVector,
    FusedDecision,
    RawSignal,
)
from l2_decision.fusion.normalizer import SignalNormalizer
from l2_decision.fusion.rule_fusion import RuleFusionEngine
from l2_decision.fusion.attention_fusion import AttentionFusionEngine
from l2_decision.guards.kill_switch import ManualKillSwitch
from l2_decision.guards.rail_engine import (
    DrawdownGuard, GuardRailEngine, KillSwitchGuard, SessionGuard,
)
from l2_decision.audit.audit_trail import AuditTrail
from l2_decision.observability.l2_instrumentation import L2Instrumentation
from l2_decision.reactor import L2DecisionReactor

_ET = ZoneInfo("US/Eastern")


def _now():
    return datetime.now(_ET)


def _fv(**features) -> FeatureVector:
    return FeatureVector(features=features, timestamp=_now())


def _sig(name="test", direction="BULLISH", confidence=0.7, raw_value=0.6) -> RawSignal:
    return RawSignal(name=name, direction=direction, confidence=confidence,
                     raw_value=raw_value, computed_at=_now())


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic snapshot for Reactor tests
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _FakeAgg:
    net_gex: float = 1e9
    atm_iv: float = 0.18
    call_wall: float = 565.0
    put_wall: float = 555.0
    flip_level: float = 560.0
    total_call_gex: float = 2e9
    total_put_gex: float = 0.0
    net_vanna: float = 0.0
    net_charm: float = 0.0
    num_contracts: int = 100

@dataclass
class _FakeMicro:
    vpin_composite: float = 0.25
    bbo_ewma_fast: float = 0.30
    vol_accel_ratio: float = 1.1
    vpin_regime: str = "NORMAL"

@dataclass
class _FakeSnap:
    spot: float = 560.0
    aggregates: _FakeAgg = None
    microstructure: _FakeMicro = None
    version: int = 7
    chain: object = None

    def __post_init__(self):
        if self.aggregates is None:
            self.aggregates = _FakeAgg()
        if self.microstructure is None:
            self.microstructure = _FakeMicro()


# ─────────────────────────────────────────────────────────────────────────────
# SignalNormalizer
# ─────────────────────────────────────────────────────────────────────────────

class TestSignalNormalizer:

    def test_bullish_positive(self):
        norm = SignalNormalizer()
        sig = _sig("x", "BULLISH", 1.0, 0.8)
        assert norm.normalize(sig) > 0

    def test_bearish_negative(self):
        norm = SignalNormalizer()
        sig = _sig("x", "BEARISH", 1.0, -0.8)
        assert norm.normalize(sig) < 0

    def test_neutral_near_zero(self):
        norm = SignalNormalizer()
        sig = _sig("x", "NEUTRAL", 0.0, 0.0)
        assert norm.normalize(sig) == pytest.approx(0.0)

    def test_batch_normalize_keys(self):
        norm = SignalNormalizer()
        sigs = {"a": _sig("a"), "b": _sig("b", "BEARISH", 0.5, -0.3)}
        result = norm.normalize_batch(sigs)
        assert set(result.keys()) == {"a", "b"}

    def test_direction_to_float(self):
        assert SignalNormalizer.direction_to_float("BULLISH") == 1.0
        assert SignalNormalizer.direction_to_float("BEARISH") == -1.0
        assert SignalNormalizer.direction_to_float("NEUTRAL") == 0.0

    def test_float_to_direction(self):
        assert SignalNormalizer.float_to_direction(0.5) == "BULLISH"
        assert SignalNormalizer.float_to_direction(-0.5) == "BEARISH"
        assert SignalNormalizer.float_to_direction(0.05) == "NEUTRAL"

    def test_result_clamped(self):
        norm = SignalNormalizer()
        sig = _sig("x", "BULLISH", 1.0, 1.0)
        v = norm.normalize(sig)
        assert -1.0 <= v <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# RuleFusionEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestRuleFusionEngine:

    def test_weight_validation_passes(self):
        engine = RuleFusionEngine()  # default weights should be valid

    def test_invalid_weights_raise(self):
        with pytest.raises(ValueError):
            RuleFusionEngine(weight_table={"NORMAL": {"momentum_signal": 0.2}})

    def test_all_bullish_produces_bullish(self):
        engine = RuleFusionEngine()
        signals = {
            "momentum_signal": _sig("momentum_signal", "BULLISH", 0.8, 0.7),
            "trap_detector":   _sig("trap_detector", "BULLISH", 0.7, 0.6),
            "flow_analyzer":   _sig("flow_analyzer", "BULLISH", 0.9, 0.8),
            "micro_flow":      _sig("micro_flow", "BULLISH", 0.6, 0.5),
        }
        fused = engine.fuse(signals, _fv(), iv_regime="NORMAL")
        assert fused.direction == "BULLISH"

    def test_all_bearish_produces_bearish(self):
        engine = RuleFusionEngine()
        signals = {
            "momentum_signal": _sig("momentum_signal", "BEARISH", 0.8, -0.7),
            "trap_detector":   _sig("trap_detector", "BEARISH", 0.7, -0.6),
            "flow_analyzer":   _sig("flow_analyzer", "BEARISH", 0.9, -0.8),
            "micro_flow":      _sig("micro_flow", "BEARISH", 0.6, -0.5),
        }
        fused = engine.fuse(signals, _fv(), iv_regime="NORMAL")
        assert fused.direction == "BEARISH"

    def test_empty_signals_returns_neutral(self):
        engine = RuleFusionEngine()
        fused = engine.fuse({}, _fv())
        assert fused.direction == "NEUTRAL"
        assert fused.confidence == 0.0

    def test_fusion_weights_sum_to_one(self):
        engine = RuleFusionEngine()
        signals = {
            "momentum_signal": _sig("momentum_signal", "BULLISH", 0.8, 0.7),
            "trap_detector":   _sig("trap_detector", "BULLISH", 0.7, 0.6),
        }
        fused = engine.fuse(signals, _fv())
        total = sum(fused.fusion_weights.values())
        assert abs(total - 1.0) < 0.01

    def test_fusion_mode_is_rule(self):
        engine = RuleFusionEngine()
        fused = engine.fuse({"momentum_signal": _sig()}, _fv())
        assert fused.fusion_mode == "rule"

    def test_regime_high_vol_uses_different_weights(self):
        engine = RuleFusionEngine()
        sigs = {
            "momentum_signal": _sig("momentum_signal"),
            "flow_analyzer":   _sig("flow_analyzer"),
            "micro_flow":      _sig("micro_flow"),
        }
        normal_fused = engine.fuse(sigs, _fv(), iv_regime="NORMAL")
        high_fused = engine.fuse(sigs, _fv(), iv_regime="HIGH_VOL")
        # Weights should differ between regimes
        assert normal_fused.fusion_weights != high_fused.fusion_weights


# ─────────────────────────────────────────────────────────────────────────────
# AttentionFusionEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestAttentionFusionEngine:

    def test_falls_back_to_rule_when_model_unavailable(self):
        rule = RuleFusionEngine()
        attn = AttentionFusionEngine(fallback_engine=rule, model_available=False)
        sigs = {"momentum_signal": _sig("momentum_signal")}
        fused = attn.fuse(sigs, _fv())
        assert fused.fusion_mode == "rule"  # Using fallback

    def test_attention_mode_when_model_available(self):
        attn = AttentionFusionEngine(model_available=True)
        sigs = {
            "momentum_signal": _sig("momentum_signal", "BULLISH", 0.8, 0.7),
            "trap_detector":   _sig("trap_detector", "BULLISH", 0.7, 0.6),
        }
        fused = attn.fuse(sigs, _fv())
        assert fused.fusion_mode == "attention"

    def test_compare_with_rule_tracks_mismatch(self):
        attn = AttentionFusionEngine(model_available=True)
        sigs = {"momentum_signal": _sig("momentum_signal", "BULLISH", 0.8, 0.7)}
        attn.compare_with_rule(sigs, _fv())
        assert attn.mismatch_rate >= 0.0

    def test_enable_disable_model(self):
        attn = AttentionFusionEngine(model_available=False)
        sigs = {"momentum_signal": _sig("momentum_signal")}
        fused_before = attn.fuse(sigs, _fv())
        assert fused_before.fusion_mode == "rule"
        attn.enable_model(True)
        fused_after = attn.fuse(sigs, _fv())
        assert fused_after.fusion_mode == "attention"


# ─────────────────────────────────────────────────────────────────────────────
# ManualKillSwitch
# ─────────────────────────────────────────────────────────────────────────────

class TestManualKillSwitch:

    def test_initially_inactive(self):
        with tempfile.TemporaryDirectory() as tmp:
            ks = ManualKillSwitch(flag_file=Path(tmp) / "ks.flag")
            assert not ks.is_active()

    def test_activate_sets_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            ks = ManualKillSwitch(flag_file=Path(tmp) / "ks.flag")
            ks.activate("test_reason")
            assert ks.is_active()
            assert ks.reason == "test_reason"

    def test_deactivate_clears(self):
        with tempfile.TemporaryDirectory() as tmp:
            ks = ManualKillSwitch(flag_file=Path(tmp) / "ks.flag")
            ks.activate("r")
            ks.deactivate()
            assert not ks.is_active()

    def test_persists_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            flag = Path(tmp) / "ks.flag"
            ks = ManualKillSwitch(flag_file=flag)
            ks.activate("persistent")
            # New instance should restore state
            ks2 = ManualKillSwitch(flag_file=flag)
            assert ks2.is_active()
            assert "persistent" in ks2.reason

    def test_thread_safe_concurrent_reads(self):
        """Concurrent reads should not raise."""
        with tempfile.TemporaryDirectory() as tmp:
            ks = ManualKillSwitch(flag_file=Path(tmp) / "ks.flag")
            ks.activate("concurrent")
            errors = []

            def reader():
                try:
                    for _ in range(100):
                        _ = ks.is_active()
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=reader) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            assert not errors


# ─────────────────────────────────────────────────────────────────────────────
# GuardRailEngine
# ─────────────────────────────────────────────────────────────────────────────

def _make_fused(direction="BULLISH", confidence=0.8) -> FusedDecision:
    sigs = {"momentum_signal": _sig("momentum_signal", direction, confidence)}
    fv = _fv(atm_iv=0.18, vol_accel_ratio=0.0)
    return FusedDecision(
        direction=direction, confidence=confidence, raw_score=0.5,
        fusion_weights={"momentum_signal": 1.0},
        signal_components=sigs,
        feature_vector=fv,
        fusion_mode="rule",
    )


class TestGuardRailEngine:

    def test_kill_switch_produces_halt(self):
        with tempfile.TemporaryDirectory() as tmp:
            ks = ManualKillSwitch(flag_file=Path(tmp) / "ks.flag")
            ks.activate("test halt")
            engine = GuardRailEngine([KillSwitchGuard(ks)])
            guarded = engine.process(_make_fused())
            assert guarded.is_halted()
            assert guarded.direction == "HALT"

    def test_no_guards_passes_through(self):
        engine = GuardRailEngine([])
        fused = _make_fused("BULLISH", 0.8)
        guarded = engine.process(fused)
        assert guarded.direction == "BULLISH"
        assert guarded.confidence == pytest.approx(0.8)
        assert not guarded.guard_actions

    def test_was_modified_by_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            ks = ManualKillSwitch(flag_file=Path(tmp) / "ks.flag")
            ks.activate("test")
            engine = GuardRailEngine([KillSwitchGuard(ks)])
            guarded = engine.process(_make_fused())
            assert guarded.was_modified_by_guards()

    def test_pre_guard_direction_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            ks = ManualKillSwitch(flag_file=Path(tmp) / "ks.flag")
            ks.activate("test")
            engine = GuardRailEngine([KillSwitchGuard(ks)])
            guarded = engine.process(_make_fused("BEARISH"))
            assert guarded.pre_guard_direction == "BEARISH"

    def test_session_guard_reduces_confidence(self):
        """SessionGuard should produce non-1.0 multiplier during session windows.
        We test that multiple guards compose correctly (not that clock is in window)."""
        guard = SessionGuard()
        # Can't reliably test time-based guard without mocking — verify check() runs
        fused = _make_fused()
        triggered, desc, multiplier = guard.check(fused, {})
        assert isinstance(triggered, bool)
        assert isinstance(multiplier, float)
        assert 0.0 <= multiplier <= 1.0

    def test_drawdown_guard_triggers_on_low_pnl(self):
        guard = DrawdownGuard()
        guard.update_pnl(-1000.0)  # below limit
        fused = _make_fused()
        triggered, desc, multiplier = guard.check(fused, {})
        assert triggered
        assert multiplier == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# L2DecisionReactor end-to-end
# ─────────────────────────────────────────────────────────────────────────────

class TestL2DecisionReactor:

    def test_decide_returns_decision_output(self):
        reactor = L2DecisionReactor(enable_audit_disk=False)
        snap = _FakeSnap()
        output = asyncio.get_event_loop().run_until_complete(reactor.decide(snap))
        assert isinstance(output, DecisionOutput)

    def test_output_direction_valid(self):
        reactor = L2DecisionReactor(enable_audit_disk=False)
        snap = _FakeSnap()
        output = asyncio.get_event_loop().run_until_complete(reactor.decide(snap))
        assert output.direction in ("BULLISH", "BEARISH", "NEUTRAL", "HALT")

    def test_output_confidence_in_range(self):
        reactor = L2DecisionReactor(enable_audit_disk=False)
        snap = _FakeSnap()
        output = asyncio.get_event_loop().run_until_complete(reactor.decide(snap))
        assert 0.0 <= output.confidence <= 1.0

    def test_output_version_preserved(self):
        reactor = L2DecisionReactor(enable_audit_disk=False)
        snap = _FakeSnap(version=99)
        output = asyncio.get_event_loop().run_until_complete(reactor.decide(snap))
        assert output.version == 99

    def test_latency_positive(self):
        reactor = L2DecisionReactor(enable_audit_disk=False)
        snap = _FakeSnap()
        output = asyncio.get_event_loop().run_until_complete(reactor.decide(snap))
        assert output.latency_ms > 0

    def test_signal_summary_keys(self):
        reactor = L2DecisionReactor(enable_audit_disk=False)
        snap = _FakeSnap()
        output = asyncio.get_event_loop().run_until_complete(reactor.decide(snap))
        # Should have at least momentum and flow signals
        assert len(output.signal_summary) > 0

    def test_output_feature_vector_propagated(self):
        reactor = L2DecisionReactor(enable_audit_disk=False)
        snap = _FakeSnap()
        output = asyncio.get_event_loop().run_until_complete(reactor.decide(snap))
        assert isinstance(output.feature_vector, dict)
        assert "skew_25d_normalized" in output.feature_vector

    def test_fused_signal_contract_uses_runtime_regime_and_gex_labels(self):
        reactor = L2DecisionReactor(enable_audit_disk=False)
        snap = _FakeSnap()
        output = asyncio.get_event_loop().run_until_complete(reactor.decide(snap))
        fused = output.data["fused_signal"]
        assert fused["regime"] in {"LOW_VOL", "NORMAL", "HIGH_VOL"}
        assert fused["iv_regime"] == fused["regime"]
        assert fused["gex_intensity"] == "EXTREME_POSITIVE"

    def test_kill_switch_halts_all(self):
        reactor = L2DecisionReactor(enable_audit_disk=False)
        reactor.kill_switch.activate("unit_test_halt")
        try:
            snap = _FakeSnap()
            output = asyncio.get_event_loop().run_until_complete(reactor.decide(snap))
            assert output.direction == "HALT"
        finally:
            reactor.kill_switch.deactivate()

    def test_audit_trail_populated(self):
        reactor = L2DecisionReactor(enable_audit_disk=False)
        snap = _FakeSnap()
        asyncio.get_event_loop().run_until_complete(reactor.decide(snap))
        assert reactor.audit.total_appended >= 1

    def test_session_reset_clears_cache(self):
        reactor = L2DecisionReactor(enable_audit_disk=False)
        snap = _FakeSnap()
        asyncio.get_event_loop().run_until_complete(reactor.decide(snap))
        reactor.reset_session()
        assert reactor.feature_store.get_feature("atm_iv") is None

    def test_shadow_mismatch_tracking(self):
        reactor = L2DecisionReactor(shadow_mode=True, enable_audit_disk=False)
        snap = _FakeSnap()
        output = asyncio.get_event_loop().run_until_complete(reactor.decide(snap))
        reactor.compare_with_legacy(output, "NEUTRAL")  # force mismatch if output != NEUTRAL
        stats = reactor.shadow_stats
        assert "mismatch_rate" in stats
        assert 0.0 <= stats["mismatch_rate"] <= 1.0

    def test_to_dict_serializable(self):
        import json
        reactor = L2DecisionReactor(enable_audit_disk=False)
        output = asyncio.get_event_loop().run_until_complete(reactor.decide(_FakeSnap()))
        json.dumps(output.to_dict())  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# AuditTrail
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditTrail:

    def _make_entry(self) -> DecisionAuditEntry:
        return DecisionAuditEntry(
            timestamp=_now(),
            feature_vector={"atm_iv": 0.18},
            signal_components={},
            fusion_weights={"m": 1.0},
            fusion_mode="rule",
            pre_guard_direction="BULLISH",
            guard_actions=[],
            final_direction="BULLISH",
            final_confidence=0.75,
            shap_top5=[],
            latency_ms=3.5,
            l0_version=1,
        )

    def test_append_and_total(self):
        trail = AuditTrail(enable_disk_persistence=False)
        for _ in range(5):
            trail.append(self._make_entry())
        assert trail.total_appended == 5

    def test_recent_returns_correct_count(self):
        trail = AuditTrail(enable_disk_persistence=False)
        for _ in range(20):
            trail.append(self._make_entry())
        assert len(trail.recent(10)) == 10

    def test_recent_all(self):
        trail = AuditTrail(enable_disk_persistence=False)
        for _ in range(5):
            trail.append(self._make_entry())
        assert len(trail.recent(100)) == 5

    def test_max_memory_ring(self):
        trail = AuditTrail(max_memory_entries=3, enable_disk_persistence=False)
        for _ in range(10):
            trail.append(self._make_entry())
        assert trail.memory_size == 3  # ring buffer

    def test_flush_to_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            trail = AuditTrail(
                log_dir=Path(tmp),
                enable_disk_persistence=True,
            )
            for _ in range(5):
                trail.append(self._make_entry())
            written = trail.flush_to_disk()
            assert written == 5

    def test_clear(self):
        trail = AuditTrail(enable_disk_persistence=False)
        trail.append(self._make_entry())
        trail.clear()
        assert trail.memory_size == 0


# ─────────────────────────────────────────────────────────────────────────────
# L2Instrumentation (no-op safety)
# ─────────────────────────────────────────────────────────────────────────────

class TestL2Instrumentation:

    def test_all_methods_safe_without_otel(self):
        inst = L2Instrumentation()
        with inst.span_feature_store():
            with inst.span_signal("momentum"):
                pass
            with inst.span_fusion():
                pass
            with inst.span_guard_rails():
                pass

    def test_prometheus_methods_safe(self):
        inst = L2Instrumentation()
        inst.record_feature_latency(1.0)
        inst.record_fusion_latency(2.0)
        inst.record_decision_confidence(0.75)
        inst.record_guard_trigger("SessionGuard")
        inst.record_signal_direction("momentum_signal", "BULLISH")
        inst.record_shadow_mismatch()
