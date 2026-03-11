"""l2_decision.events.decision_events — Strongly-typed L2 decision event models.

All models are frozen dataclasses to ensure immutability across the pipeline.
This module defines the canonical data contracts between L2 sub-components.

Design principles:
    - Frozen (immutable) — no accidental mutation across pipeline stages
    - No circular imports — only depends on stdlib + typing
    - Serialization-ready via to_dict() methods
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from l2_decision.events.fused_signal_contract import (
    normalize_signal_components,
    resolve_iv_regime,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Core Signal Models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RawSignal:
    """Output of a single SignalGenerator.

    Attributes:
        name:        Signal identifier (e.g., "momentum", "trap_detector").
        direction:   Directional classification: BULLISH | BEARISH | NEUTRAL.
        confidence:  Calibrated confidence in [0.0, 1.0].
        raw_value:   Pre-normalization value in [-1.0, +1.0].
        computed_at: Wall-clock UTC timestamp of computation.
        metadata:    Optional diagnostics for XAI/SHAP attribution.
    """
    name: str
    direction: str          # "BULLISH" | "BEARISH" | "NEUTRAL"
    confidence: float       # [0.0, 1.0]
    raw_value: float        # [-1.0, +1.0] normalized
    computed_at: datetime
    metadata: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.direction not in ("BULLISH", "BEARISH", "NEUTRAL"):
            raise ValueError(f"Invalid direction: {self.direction!r}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")
        raw = self.raw_value
        if not math.isfinite(raw) or not (-1.0 <= raw <= 1.0):
            raise ValueError(f"raw_value must be finite in [-1,1], got {raw}")

    def is_directional(self) -> bool:
        """Returns True if signal has a non-neutral direction."""
        return self.direction != "NEUTRAL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "direction": self.direction,
            "confidence": self.confidence,
            "raw_value": self.raw_value,
            "computed_at": self.computed_at.isoformat(),
            "metadata": dict(self.metadata),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Feature Vector
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FeatureVector:
    """Snapshot of all extracted features at a single timestep.

    Produced by FeatureStore.compute_all() and consumed by all SignalGenerators.
    Immutability guarantees that generators cannot corrupt shared state.
    """
    features: dict[str, float]          # name → float value
    timestamp: datetime
    missing_count: int = 0              # features that could not be computed
    extraction_latency_ms: float = 0.0

    def get(self, name: str, default: float = 0.0) -> float:
        """Retrieve feature value with fallback default."""
        v = self.features.get(name, default)
        if v is None or not math.isfinite(v):
            return default
        return v

    def is_valid(self, name: str) -> bool:
        """Returns True if feature exists and is finite."""
        v = self.features.get(name)
        return v is not None and math.isfinite(v)

    def to_array(self, names: list[str]) -> list[float]:
        """Extract ordered float array for ML inference."""
        return [self.get(n, 0.0) for n in names]

    def __len__(self) -> int:
        return len(self.features)


# ─────────────────────────────────────────────────────────────────────────────
# Fusion Intermediates
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FusedDecision:
    """Output of the FusionEngine — before Guard Rails processing.

    Not exposed externally; consumed by GuardRailEngine.
    """
    direction: str          # "BULLISH" | "BEARISH" | "NEUTRAL"
    confidence: float       # [0.0, 1.0]
    raw_score: float        # weighted sum, can exceed [-1, +1] before norm
    fusion_weights: dict[str, float]    # signal_name → weight
    signal_components: dict[str, RawSignal]
    feature_vector: FeatureVector
    fusion_mode: str = "rule"           # "rule" | "attention"
    latency_ms: float = 0.0


@dataclass(frozen=True)
class GuardedDecision:
    """Output of the GuardRailEngine — final pre-output decision.

    Wraps FusedDecision and adds guard audit trail.
    """
    direction: str              # "BULLISH" | "BEARISH" | "NEUTRAL" | "HALT"
    confidence: float           # guard-adjusted confidence
    pre_guard_direction: str    # direction before guard processing
    pre_guard_confidence: float
    guard_actions: list[str]    # e.g., ["SessionGuard: -30%", "DrawdownGuard: COOL_DOWN"]
    fused: FusedDecision
    guard_latency_ms: float = 0.0

    def was_modified_by_guards(self) -> bool:
        return bool(self.guard_actions)

    def is_halted(self) -> bool:
        return self.direction == "HALT"


# ─────────────────────────────────────────────────────────────────────────────
# Final Output Contract
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DecisionOutput:
    """Canonical L2 → downstream output contract.

    Immutable. Contains everything needed for trading decisions,
    real-time dashboard display, and audit/compliance logging.
    """
    direction: str                          # "BULLISH" | "BEARISH" | "NEUTRAL" | "HALT"
    confidence: float                       # final calibrated confidence [0, 1]
    fusion_weights: dict[str, float]        # signal_name → weight used in fusion
    pre_guard_direction: str
    guard_actions: list[str]
    signal_summary: dict[str, Any]         # name → dict with direction/confidence
    latency_ms: float
    version: int                            # L0 MVCC version propagated from L1
    computed_at: datetime
    max_impact: float = 0.0                 # Peak OFII across the entire chain
    raw_telemetry: dict[str, float] = field(default_factory=dict)
    iv_regime: str | None = None
    gex_intensity: str | None = None
    # L3 UIStateTracker consumes this for skew_dynamics classification.
    feature_vector: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "confidence": round(self.confidence, 4),
            "fusion_weights": {k: round(v, 4) for k, v in self.fusion_weights.items()},
            "pre_guard_direction": self.pre_guard_direction,
            "guard_actions": list(self.guard_actions),
            "signal_summary": dict(self.signal_summary),
            "latency_ms": round(self.latency_ms, 2),
            "version": self.version,
            "computed_at": self.computed_at.isoformat(),
            "max_impact": round(self.max_impact, 4),
        }

    @property
    def data(self) -> dict[str, Any]:
        """Expose fused_signal dict for PayloadAssemblerV2.assemble() extraction.

        PayloadAssemblerV2 reads `getattr(decision, 'data', {}).get('fused_signal')`.
        This property satisfies that contract without requiring changes in the assembler.
        The schema matches what the frontend `selectFused` selector expects:
          { direction, confidence, weights, components, regime, gex_intensity, explanation }
        """
        components = normalize_signal_components(self.signal_summary)
        component_iv_regime = resolve_iv_regime(
            components.get("iv_regime", {}).get("direction", "NORMAL")
        )
        iv_regime = resolve_iv_regime(self.iv_regime) if self.iv_regime else component_iv_regime
        gex_intensity = str(self.gex_intensity or "NEUTRAL").strip().upper() or "NEUTRAL"

        return {
            "fused_signal": {
                "direction":    self.direction,
                "confidence":   round(self.confidence, 4),
                "weights":      {k: round(v, 4) for k, v in self.fusion_weights.items()},
                "components":   components,
                "regime":          iv_regime,
                "iv_regime":       iv_regime,
                "gex_intensity":   gex_intensity,
                "explanation":     f"Guard: {self.guard_actions[0]}" if self.guard_actions else "",
                "raw_vpin":        self.raw_telemetry.get("vpin_composite", 0.0),
                "raw_bbo_imb":     self.raw_telemetry.get("bbo_imbalance_raw", 0.0),
                "raw_vol_accel":   self.raw_telemetry.get("vol_accel_ratio", 0.0),
            }
        }

    def is_actionable(self) -> bool:
        """Returns True if signal is directional, confident, and not halted."""
        return (
            self.direction in ("BULLISH", "BEARISH")
            and self.confidence >= 0.5
            and self.direction != "HALT"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Audit Trail Entry
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DecisionAuditEntry:
    """Immutable audit log entry for compliance and postmortem analysis.

    Written on every reactor.decide() call. Persisted to Parquet nightly.
    """
    timestamp: datetime
    feature_vector: dict[str, float]            # full feature snapshot
    signal_components: dict[str, dict[str, Any]] # name → RawSignal.to_dict()
    fusion_weights: dict[str, float]
    fusion_mode: str                             # "rule" | "attention"
    pre_guard_direction: str
    guard_actions: list[str]
    final_direction: str
    final_confidence: float
    shap_top5: list[tuple[str, float]]          # [(feature_name, shap_value), ...]
    latency_ms: float
    l0_version: int
    max_impact: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "feature_vector": dict(self.feature_vector),
            "signal_components": dict(self.signal_components),
            "fusion_weights": dict(self.fusion_weights),
            "fusion_mode": self.fusion_mode,
            "pre_guard_direction": self.pre_guard_direction,
            "guard_actions": list(self.guard_actions),
            "final_direction": self.final_direction,
            "final_confidence": self.final_confidence,
            "shap_top5": list(self.shap_top5),
            "latency_ms": self.latency_ms,
            "l0_version": self.l0_version,
            "max_impact": self.max_impact,
        }
