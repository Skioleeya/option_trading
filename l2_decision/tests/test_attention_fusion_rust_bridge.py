from __future__ import annotations

import asyncio
import math
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

import l2_decision.fusion.attention_fusion as attn_mod
from l2_decision.events.decision_events import FeatureVector, GuardedDecision, RawSignal
from l2_decision.fusion.attention_fusion import AttentionFusionEngine
from l2_decision.reactor import L2DecisionReactor


_ET = ZoneInfo("US/Eastern")


def _softmax(values: list[float]) -> list[float]:
    max_v = max(values)
    exp_values = [math.exp(v - max_v) for v in values]
    denom = sum(exp_values)
    return [v / denom for v in exp_values]


def test_attention_fusion_rust_parity_for_score_confidence_and_weights() -> None:
    now = datetime.now(_ET)
    features = FeatureVector(features={}, timestamp=now)
    signals = {
        "momentum_signal": RawSignal("momentum_signal", "BULLISH", 0.80, 0.50, now),
        "trap_detector": RawSignal("trap_detector", "BEARISH", 0.65, -0.20, now),
        "flow_analyzer": RawSignal("flow_analyzer", "BULLISH", 0.60, 0.30, now),
        "micro_flow": RawSignal("micro_flow", "NEUTRAL", 0.55, 0.10, now),
    }

    engine = AttentionFusionEngine(model_available=True)
    engine._attention_logits["NORMAL"] = {
        "momentum_signal": 1.1,
        "trap_detector": -0.2,
        "iv_regime": 0.0,
        "flow_analyzer": 0.4,
        "micro_flow": -0.8,
    }
    engine._platt_a = 1.3
    engine._platt_b = -0.15

    fused = engine.fuse(signals, features, "NORMAL")
    normalized = engine._normalizer.normalize_batch(signals)
    active_names = [name for name in engine._SIGNAL_NAMES if name in signals]
    logits = [engine._attention_logits["NORMAL"].get(name, 0.0) for name in active_names]
    signal_values = [normalized.get(name, 0.0) for name in active_names]
    expected_weights = _softmax(logits)
    expected_raw = sum(w * v for w, v in zip(expected_weights, signal_values, strict=True))
    expected_raw = max(-1.0, min(1.0, expected_raw))
    expected_conf = 1.0 / (1.0 + math.exp(-(engine._platt_a * expected_raw + engine._platt_b)))

    assert fused.raw_score == pytest.approx(expected_raw, abs=1e-10)
    assert fused.confidence == pytest.approx(expected_conf, abs=1e-10)
    assert set(fused.fusion_weights.keys()) == set(active_names)
    for idx, name in enumerate(active_names):
        assert fused.fusion_weights[name] == pytest.approx(expected_weights[idx], abs=1e-10)


def test_attention_fusion_rust_failure_is_not_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(_ET)
    features = FeatureVector(features={}, timestamp=now)
    signals = {
        "momentum_signal": RawSignal("momentum_signal", "BULLISH", 0.80, 0.50, now),
    }

    engine = AttentionFusionEngine(model_available=True)
    monkeypatch.setattr(
        attn_mod,
        "rust_compute_attention_fused",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("forced-attn-rust-fail")),
    )

    with pytest.raises(RuntimeError, match="Rust compute_attention_fused execution failed"):
        engine.fuse(signals, features, "NORMAL")


def test_reactor_keeps_fusion_weights_populated_in_attention_mode() -> None:
    now = datetime.now(_ET)
    reactor = L2DecisionReactor(
        shadow_mode=False,
        use_attention_fusion=True,
        enable_audit_disk=False,
        enable_cache=False,
    )

    class _Snapshot:
        version = 7
        microstructure = None
        aggregates = None

    class _StaticSignal:
        def __init__(self, name: str, direction: str, raw: float) -> None:
            self._name = name
            self._direction = direction
            self._raw = raw

        def generate(self, _features: FeatureVector) -> RawSignal:
            return RawSignal(
                name=self._name,
                direction=self._direction,
                confidence=0.6,
                raw_value=self._raw,
                computed_at=now,
            )

        def reset(self) -> None:
            return None

    reactor._feature_store.compute_all = lambda _snapshot: FeatureVector(  # type: ignore[method-assign]
        features={"peak_impact": 0.0, "net_gex_normalized": -0.2},
        timestamp=now,
    )
    reactor._signals = {
        "momentum_signal": _StaticSignal("momentum_signal", "BULLISH", 0.55),
        "trap_detector": _StaticSignal("trap_detector", "BEARISH", -0.25),
        "iv_regime": _StaticSignal("iv_regime", "NEUTRAL", 0.0),
        "flow_analyzer": _StaticSignal("flow_analyzer", "BULLISH", 0.15),
        "micro_flow": _StaticSignal("micro_flow", "NEUTRAL", 0.05),
        "jump_sentinel": _StaticSignal("jump_sentinel", "NEUTRAL", 0.0),
    }
    reactor._guards.process = lambda fused, context=None: GuardedDecision(  # type: ignore[method-assign]
        direction=fused.direction,
        confidence=fused.confidence,
        pre_guard_direction=fused.direction,
        pre_guard_confidence=fused.confidence,
        guard_actions=[],
        fused=fused,
        guard_latency_ms=0.0,
    )

    output = asyncio.run(reactor.decide(_Snapshot()))
    recent_entry = reactor.audit.recent(1)[0]
    fused_payload = output.data.get("fused_signal", {})

    assert output.fusion_weights
    assert recent_entry.fusion_weights
    assert output.fusion_weights == recent_entry.fusion_weights
    assert fused_payload
    assert fused_payload.get("direction") == output.direction
    assert fused_payload.get("confidence") == pytest.approx(round(output.confidence, 4), abs=1e-12)
    assert fused_payload.get("weights") == {
        name: round(weight, 4) for name, weight in output.fusion_weights.items()
    }
