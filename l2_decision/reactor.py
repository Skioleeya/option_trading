"""l2_decision.reactor — L2DecisionReactor main pipeline orchestrator.

Entry point for the L2 Decision Layer refactoring.
Consumes L1 EnrichedSnapshot → produces DecisionOutput.

Pipeline (end-to-end):
    1. Feature extraction (FeatureStore.compute_all)
    2. Signal generation (6 generators in parallel concept, sequential in impl)
    3. IV regime classification (gates fusion weights)
    4. Signal normalization (SignalNormalizer)
    5. Fusion (RuleFusionEngine or AttentionFusionEngine)
    6. Guard Rail chain (P0.0 → P0.9)
    7. Audit entry construction + async write
    8. Observability metrics emission
    9. Return DecisionOutput

Shadow mode:
    Set shadow_mode=True to run alongside legacy AgentG.
    Call compare_with_legacy() to track mismatch rate.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from l2_decision.audit.audit_trail import AuditTrail
from l2_decision.events.decision_events import (
    DecisionAuditEntry,
    DecisionOutput,
    FeatureVector,
    FusedDecision,
    GuardedDecision,
    RawSignal,
)
from l2_decision.events.fused_signal_contract import classify_gex_intensity
from l2_decision.feature_store.extractors import build_default_extractors, reset_all_default_extractors
from l2_decision.feature_store.store import FeatureStore
from l2_decision.fusion.attention_fusion import AttentionFusionEngine
from l2_decision.fusion.normalizer import SignalNormalizer
from l2_decision.fusion.rule_fusion import RuleFusionEngine
from l2_decision.guards.kill_switch import ManualKillSwitch
from l2_decision.guards.rail_engine import GuardRailEngine
from l2_decision.observability.l2_instrumentation import L2Instrumentation
from l2_decision.signals.flow_analyzer import FlowAnalyzer
from l2_decision.signals.iv_regime import IVRegimeEngine
from l2_decision.signals.jump_sentinel import JumpSentinel
from l2_decision.signals.micro_flow import MicroFlowSignal
from l2_decision.signals.momentum_signal import MomentumSignal
from l2_decision.signals.trap_detector import TrapDetector

logger = logging.getLogger(__name__)

_ET = ZoneInfo("US/Eastern")


class L2DecisionReactor:
    """Main L2 Decision Layer orchestrator.

    Consumes:
        EnrichedSnapshot (from l1_compute.output.enriched_snapshot)

    Produces:
        DecisionOutput (frozen, immutable)

    Usage:
        reactor = L2DecisionReactor()
        output = await reactor.decide(enriched_snapshot)

    Shadow mode:
        reactor = L2DecisionReactor(shadow_mode=True)
        output = await reactor.decide(snapshot)
        stats = reactor.shadow_stats  # mismatch_rate, total_decisions
    """

    def __init__(
        self,
        shadow_mode: bool = False,
        use_attention_fusion: bool = False,
        enable_audit_disk: bool = True,
        enable_cache: bool = True,
    ) -> None:
        self._shadow_mode = shadow_mode
        self._instrumentation = L2Instrumentation()

        # Build feature store with all 12 extractors
        self._feature_specs = build_default_extractors()
        self._feature_store = FeatureStore(enable_cache=enable_cache)
        self._feature_store.register_bulk(self._feature_specs)

        # Signal generators
        self._signals: dict[str, Any] = {
            "momentum_signal": MomentumSignal(),
            "trap_detector":   TrapDetector(),
            "iv_regime":       IVRegimeEngine(),
            "flow_analyzer":   FlowAnalyzer(),
            "micro_flow":      MicroFlowSignal(),
            "jump_sentinel":   JumpSentinel(),
        }

        # Fusion engines
        self._rule_fusion = RuleFusionEngine()
        self._attention_fusion = AttentionFusionEngine(
            fallback_engine=self._rule_fusion,
            model_available=use_attention_fusion,
        )
        self._use_attention_fusion = use_attention_fusion

        # Guard rails
        self._kill_switch = ManualKillSwitch()
        self._guards = GuardRailEngine.build_default(
            kill_switch=self._kill_switch,
            jump_sentinel=self._signals["jump_sentinel"],
        )

        # Audit trail
        self._audit = AuditTrail(
            max_memory_entries=10_000,
            enable_disk_persistence=enable_audit_disk,
        )

        # Shadow mode tracking
        self._shadow_mismatch: int = 0
        self._shadow_total: int = 0

        logger.info(
            "L2DecisionReactor initialized: shadow=%s attention=%s",
            shadow_mode, use_attention_fusion,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def decide(self, snapshot: Any) -> DecisionOutput:
        """Full L2 pipeline: snapshot → DecisionOutput.

        Args:
            snapshot: EnrichedSnapshot from l1_compute (or duck-typed compat object).

        Returns:
            DecisionOutput (frozen).
        """
        t0 = time.perf_counter()

        # 1. Feature extraction
        with self._instrumentation.span_feature_store():
            features = self._feature_store.compute_all(snapshot)
        self._instrumentation.record_feature_latency(features.extraction_latency_ms)

        # 2. Signal generation (sequential — each generator is O(1))
        raw_signals: dict[str, RawSignal] = {}
        for name, generator in self._signals.items():
            if name == "jump_sentinel":
                continue  # JumpSentinel integrated via GuardRailEngine
            with self._instrumentation.span_signal(name):
                try:
                    sig = generator.generate(features)
                    raw_signals[name] = sig
                    self._instrumentation.record_signal_direction(name, sig.direction)
                except Exception as exc:
                    logger.exception("Signal generator '%s' raised: %s", name, exc)

        # Also run jump sentinel (for guard use)
        try:
            self._signals["jump_sentinel"].generate(features)
        except Exception:
            pass

        # 3. IV regime from IVRegimeEngine signal (used to gate fusion weights)
        iv_regime_signal = raw_signals.get("iv_regime")
        regime_direction = iv_regime_signal.direction if iv_regime_signal else "NEUTRAL"
        iv_regime_str = {
            "BULLISH": "LOW_VOL",
            "BEARISH": "HIGH_VOL",
            "NEUTRAL": "NORMAL",
        }.get(regime_direction, "NORMAL")

        # Exclude iv_regime from fusion input (it gates weights, not a direct signal)
        fusion_signals = {k: v for k, v in raw_signals.items() if k != "iv_regime"}

        # 4. Fusion
        with self._instrumentation.span_fusion():
            if self._use_attention_fusion:
                fused = self._attention_fusion.fuse(fusion_signals, features, iv_regime_str)
            else:
                fused = self._rule_fusion.fuse(fusion_signals, features, iv_regime_str)
        self._instrumentation.record_fusion_latency(fused.latency_ms)

        # 5. Guard Rails
        with self._instrumentation.span_guard_rails():
            version = getattr(snapshot, "version", 0)
            guarded = self._guards.process(fused, context={"l0_version": version})

        for action in guarded.guard_actions:
            rule_name = action.split(":")[0].strip() if ":" in action else action
            self._instrumentation.record_guard_trigger(rule_name)

        # 6. Build DecisionOutput
        total_latency_ms = (time.perf_counter() - t0) * 1000.0
        self._instrumentation.record_decision_confidence(guarded.confidence)

        raw_telemetry_dict = {}
        if hasattr(snapshot, "microstructure") and snapshot.microstructure:
            ms = snapshot.microstructure
            raw_telemetry_dict = {
                "vpin_composite": getattr(ms, "vpin_composite", 0.0),
                "bbo_imbalance_raw": getattr(ms, "bbo_imbalance_raw", 0.0),
                "vol_accel_ratio": getattr(ms, "vol_accel_ratio", 0.0),
            }

        peak_impact = features.get("peak_impact", 0.0)
        net_gex_raw = self._extract_net_gex(snapshot, features)
        gex_intensity = classify_gex_intensity(net_gex_raw)

        output = DecisionOutput(
            direction=guarded.direction,
            confidence=guarded.confidence,
            fusion_weights=dict(fused.fusion_weights),
            pre_guard_direction=guarded.pre_guard_direction,
            guard_actions=list(guarded.guard_actions),
            signal_summary={
                n: {"direction": s.direction, "confidence": s.confidence} 
                for n, s in raw_signals.items()
            },
            max_impact=peak_impact,  # Populating new institutional field
            latency_ms=total_latency_ms,
            version=version,
            computed_at=datetime.now(_ET),
            raw_telemetry=raw_telemetry_dict,
            iv_regime=iv_regime_str,
            gex_intensity=gex_intensity,
        )

        # 7. Audit trail (non-blocking append)
        audit_entry = DecisionAuditEntry(
            timestamp=output.computed_at,
            feature_vector=dict(features.features),
            signal_components={n: s.to_dict() for n, s in raw_signals.items()},
            fusion_weights=dict(fused.fusion_weights),
            fusion_mode=fused.fusion_mode,
            pre_guard_direction=guarded.pre_guard_direction,
            guard_actions=list(guarded.guard_actions),
            final_direction=output.direction,
            final_confidence=output.confidence,
            shap_top5=[],   # SHAP deferred to explainability module
            latency_ms=total_latency_ms,
            l0_version=version,
            max_impact=peak_impact,
        )
        self._audit.append(audit_entry)

        return output

    def decide_sync(self, snapshot: Any) -> DecisionOutput:
        """Synchronous wrapper — use in thread pool contexts."""
        return asyncio.get_event_loop().run_until_complete(self.decide(snapshot))

    # ── Shadow mode ───────────────────────────────────────────────────────────

    def compare_with_legacy(
        self, l2_output: DecisionOutput, legacy_direction: str
    ) -> bool:
        """Compare L2 decision with legacy AgentG output.

        Returns True if directions match.
        """
        self._shadow_total += 1
        match = l2_output.direction == legacy_direction
        if not match:
            self._shadow_mismatch += 1
            self._instrumentation.record_shadow_mismatch()
        return match

    @property
    def shadow_stats(self) -> dict[str, Any]:
        return {
            "mismatch_count": self._shadow_mismatch,
            "total_decisions": self._shadow_total,
            "mismatch_rate": self._shadow_mismatch / max(1, self._shadow_total),
        }

    # ── Session management ────────────────────────────────────────────────────

    def reset_session(self) -> None:
        """Reset all stateful components at session boundary (new trading day)."""
        for gen in self._signals.values():
            gen.reset()
        self._feature_store.clear_cache()
        reset_all_default_extractors(self._feature_specs)
        # Reset DrawdownGuard
        for rule in self._guards._rules:
            if hasattr(rule, "reset_session"):
                rule.reset_session()
        logger.info("L2DecisionReactor: session reset complete")

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def kill_switch(self) -> ManualKillSwitch:
        return self._kill_switch

    @property
    def audit(self) -> AuditTrail:
        return self._audit

    @property
    def feature_store(self) -> FeatureStore:
        return self._feature_store

    @staticmethod
    def _extract_net_gex(snapshot: Any, features: FeatureVector) -> float | None:
        """Best-effort net_gex extraction for fused-signal intensity labeling."""
        aggregates = getattr(snapshot, "aggregates", None)
        if aggregates is not None:
            value = getattr(aggregates, "net_gex", None)
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                return float(value)

        if isinstance(snapshot, dict):
            value = snapshot.get("net_gex")
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                return float(value)

        normalized = features.get("net_gex_normalized", 0.0)
        if math.isfinite(normalized):
            return float(normalized) * 1e9
        return None
