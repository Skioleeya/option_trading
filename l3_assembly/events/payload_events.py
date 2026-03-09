"""l3_assembly.events.payload_events — Strongly-typed L3 payload contracts.

All types are frozen dataclasses (immutable). They form the canonical
L3 → broadcast / storage interface.

Hierarchy:
    FrozenPayload
    └── UIState
        ├── MicroStatsState (4× MetricCard)
        ├── TacticalTriadState (vrp / charm / svol)
        ├── list[WallMigrationRow]
        ├── list[DepthProfileRow]
        ├── list[ActiveOptionRow]
        ├── MTFFlowState
        └── skew_dynamics: dict  (pass-through until Phase 2.7)
    SignalData (from L2 DecisionOutput)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Leaf / atom types
# ─────────────────────────────────────────────────────────────────────────────

# Canonical badge tokens accepted by L3 payload contracts.
# Must remain aligned with frontend classes in l4_ui/src/index.css.
VALID_BADGE_TOKENS = {
    "badge-neutral",
    "badge-amber",
    "badge-red",
    "badge-green",
    "badge-purple",
    "badge-cyan",
    "badge-hollow-purple",
    "badge-hollow-amber",
    "badge-hollow-cyan",
    "badge-hollow-green",
    "badge-red-dim",
}

@dataclass(frozen=True)
class MetricCard:
    """Atomic UI display card: a single labelled metric with badge colour.

    Attributes:
        label:   Primary display string (e.g. "GEX", "482.1B").
        badge:   CSS/design-token class.  Always one of the canonical set:
                 "badge-neutral" | "badge-amber" | "badge-red"
                 | "badge-green" | "badge-purple" | "badge-cyan"
                 | "badge-hollow-purple" | "badge-hollow-amber"
                 | "badge-hollow-cyan" | "badge-hollow-green" | "badge-red-dim"
        tooltip: Optional hover explanation (empty string = no tooltip).
    """
    label: str
    badge: str
    tooltip: str = ""

    def __post_init__(self) -> None:
        if self.badge not in VALID_BADGE_TOKENS:
            raise ValueError(
                f"MetricCard.badge must be one of {VALID_BADGE_TOKENS}, got {self.badge!r}"
            )

    def to_dict(self) -> dict[str, str]:
        d = {"label": self.label, "badge": self.badge}
        if self.tooltip:
            d["tooltip"] = self.tooltip
        return d


# ─────────────────────────────────────────────────────────────────────────────
# MicroStats
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MicroStatsState:
    """Four-card MicroStats block.

    Legacy schema (dict output) maps:
        net_gex  → {"label": ..., "badge": ...}
        wall_dyn → {"label": ..., "badge": ...}
        vanna    → {"label": ..., "badge": ...}
        momentum → {"label": ..., "badge": ...}
    """
    net_gex: MetricCard
    wall_dyn: MetricCard
    vanna: MetricCard
    momentum: MetricCard

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {
            "net_gex":  self.net_gex.to_dict(),
            "wall_dyn": self.wall_dyn.to_dict(),
            "vanna":    self.vanna.to_dict(),
            "momentum": self.momentum.to_dict(),
        }

    @classmethod
    def zero_state(cls) -> "MicroStatsState":
        """Return safe neutral placeholder (used during cold-start)."""
        card = MetricCard(label="—", badge="badge-neutral")
        return cls(net_gex=card, wall_dyn=card, vanna=card, momentum=card)


# ─────────────────────────────────────────────────────────────────────────────
# TacticalTriad
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TacticalTriadState:
    """VRP / CHARM / SVOL triad.

    The inner dicts intentionally remain untyped for now — the legacy
    Presenter produces a deeply-nested structure with many sub-keys.
    A full typed migration is deferred to Phase 2.2.
    """
    vrp: dict[str, Any]
    charm: dict[str, Any]
    svol: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"vrp": dict(self.vrp), "charm": dict(self.charm), "svol": dict(self.svol)}

    @classmethod
    def zero_state(cls) -> "TacticalTriadState":
        empty: dict[str, Any] = {}
        return cls(vrp=empty, charm=empty, svol=empty)


# ─────────────────────────────────────────────────────────────────────────────
# WallMigration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class WallMigrationRow:
    """One row in the WallMigration display table.

    Fields mirror the shape emitted by WallMigrationPresenter.build().
    Lighting dicts contain CSS token strings produced by the 5-scenario
    lighting table in the legacy presenter.
    """
    label: str                          # e.g. "CALL WALL", "PUT WALL"
    strike: float
    state: str                          # e.g. "REINFORCED", "BREACHED"
    history: list[float]               # last-N strike positions
    lights: dict[str, str]             # CSS lighting tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "label":   self.label,
            "strike":  self.strike,
            "state":   self.state,
            "history": list(self.history),
            "lights":  dict(self.lights),
        }


# ─────────────────────────────────────────────────────────────────────────────
# DepthProfile
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DepthProfileRow:
    """One strike row in the DepthProfile bar chart.

    Includes EMA-smoothed call/put GEX values and render-hint booleans.
    """
    strike: float
    call_pct: float
    put_pct: float
    is_spot: bool
    is_flip: bool
    is_dominant_put: bool
    is_dominant_call: bool

    def __post_init__(self) -> None:
        if not math.isfinite(self.call_pct):
            raise ValueError(f"DepthProfileRow.call_pct must be finite, got {self.call_pct}")
        if not math.isfinite(self.put_pct):
            raise ValueError(f"DepthProfileRow.put_pct must be finite, got {self.put_pct}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "strike":           self.strike,
            "call_pct":         round(self.call_pct, 4) if self.call_pct is not None else 0.0,
            "put_pct":          round(self.put_pct, 4) if self.put_pct is not None else 0.0,
            "is_spot":          self.is_spot,
            "is_flip":          self.is_flip,
            "is_dominant_put":  self.is_dominant_put,
            "is_dominant_call": self.is_dominant_call,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Active Options
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ActiveOptionRow:
    """One row in the Active Options panel.

    Represents a single option contract ranked by DEG composite flow.
    """
    symbol: str
    option_type: str            # "CALL" | "PUT"
    strike: float
    implied_volatility: float
    volume: int
    turnover: float
    flow: float
    impact_index: float
    is_sweep: bool
    flow_deg_formatted: str
    flow_volume_label: str
    flow_color: str
    flow_glow: str
    flow_intensity: str
    flow_direction: str
    flow_d_z: float
    flow_e_z: float
    flow_g_z: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol":             self.symbol,
            "option_type":        self.option_type,
            "strike":             self.strike,
            "implied_volatility": round(self.implied_volatility, 4),
            "volume":             self.volume,
            "turnover":           round(self.turnover, 2),
            "flow":               round(self.flow, 2),
            "impact_index":       round(self.impact_index, 4),
            "is_sweep":           self.is_sweep,
            "flow_deg_formatted": self.flow_deg_formatted,
            "flow_volume_label":  self.flow_volume_label,
            "flow_color":         self.flow_color,
            "flow_glow":          self.flow_glow,
            "flow_intensity":     self.flow_intensity,
            "flow_direction":     self.flow_direction,
            "flow_d_z":           round(self.flow_d_z, 4),
            "flow_e_z":           round(self.flow_e_z, 4),
            "flow_g_z":           round(self.flow_g_z, 4),
        }


# ─────────────────────────────────────────────────────────────────────────────
# MTF Flow
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MTFFlowState:
    """Multi-timeframe IV flow signal state."""
    m1: dict[str, Any]
    m5: dict[str, Any]
    m15: dict[str, Any]
    consensus: str          # "BULLISH" | "BEARISH" | "NEUTRAL"
    strength: float
    alignment: float
    align_label: str        # "ALIGNED" | "SPLIT" | "DIVERGE"
    align_color: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "m1":          dict(self.m1),
            "m5":          dict(self.m5),
            "m15":         dict(self.m15),
            "consensus":   self.consensus,
            "strength":    self.strength,
            "alignment":   self.alignment,
            "align_label": self.align_label,
            "align_color": self.align_color,
        }

    @classmethod
    def zero_state(cls) -> "MTFFlowState":
        empty: dict[str, Any] = {}
        return cls(
            m1=empty, m5=empty, m15=empty,
            consensus="NEUTRAL", strength=0.0, alignment=0.0,
            align_label="SPLIT", align_color="text-text-secondary",
        )


# ─────────────────────────────────────────────────────────────────────────────
# UIState (composite)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class UIState:
    """Full immutable UI state block.

    Assembles all Presenter outputs into a single frozen object.
    Replaces the `ui_state: dict[str, Any]` in legacy SnapshotBuilder.
    """
    micro_stats:      MicroStatsState
    tactical_triad:   TacticalTriadState
    wall_migration:   tuple[WallMigrationRow, ...]   # frozen — tuple, not list
    depth_profile:    tuple[DepthProfileRow, ...]
    active_options:   tuple[ActiveOptionRow, ...]
    mtf_flow:         MTFFlowState
    skew_dynamics:    dict[str, Any]       # pass-through (fully typed in Phase 2.7)
    macro_volume_map: dict[str, Any]
    iv_velocity:      dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "micro_stats":      self.micro_stats.to_dict(),
            "tactical_triad":   self.tactical_triad.to_dict(),
            "wall_migration":   [r.to_dict() for r in self.wall_migration],
            "depth_profile":    [r.to_dict() for r in self.depth_profile],
            "active_options":   [r.to_dict() for r in self.active_options],
            "mtf_flow":         self.mtf_flow.to_dict(),
            "skew_dynamics":    {k: round(v, 4) if isinstance(v, (int, float)) else v for k, v in self.skew_dynamics.items()},
            "macro_volume_map": {k: round(v, 2) if isinstance(v, (int, float)) else v for k, v in self.macro_volume_map.items()},
            "iv_velocity":      self.iv_velocity,
        }

    @classmethod
    def zero_state(cls) -> "UIState":
        """Return safe neutral placeholder for cold-start / error paths."""
        return cls(
            micro_stats=MicroStatsState.zero_state(),
            tactical_triad=TacticalTriadState.zero_state(),
            wall_migration=(),
            depth_profile=(),
            active_options=(),
            mtf_flow=MTFFlowState.zero_state(),
            skew_dynamics={},
            macro_volume_map={},
            iv_velocity=None,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Signal summary (from L2 DecisionOutput)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SignalData:
    """Typed wrapper around L2 DecisionOutput fields for the payload."""
    direction: str              # "BULLISH" | "BEARISH" | "NEUTRAL" | "HALT"
    confidence: float           # [0.0, 1.0]
    pre_guard_direction: str
    guard_actions: tuple[str, ...]
    signal_summary: dict[str, str]  # name → direction
    fusion_weights: dict[str, float]
    latency_ms: float
    version: int
    computed_at: str            # ISO-format string

    def __post_init__(self) -> None:
        if self.direction not in ("BULLISH", "BEARISH", "NEUTRAL", "HALT", "NO_TRADE"):
            raise ValueError(f"SignalData.direction invalid: {self.direction!r}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"SignalData.confidence must be in [0,1], got {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction":           self.direction,
            "confidence":          round(self.confidence, 4),
            "pre_guard_direction": self.pre_guard_direction,
            "guard_actions":       list(self.guard_actions),
            "signal_summary":      dict(self.signal_summary),
            "fusion_weights":      {k: round(v, 4) for k, v in self.fusion_weights.items()},
            "latency_ms":          round(self.latency_ms, 2),
            "version":             self.version,
            "computed_at":         self.computed_at,
        }

    @classmethod
    def from_decision_output(cls, decision: Any) -> "SignalData":
        """Construct from L2 DecisionOutput (duck-typed for testability)."""
        # Note: AgentResult (L2) uses 'signal' vs legacy 'direction'.
        direction = getattr(decision, "signal", None) or getattr(decision, "direction", "NEUTRAL")
        
        # Safe confidence extraction
        confidence = getattr(decision, "confidence", 0.0)
        if not confidence and "confidence" in getattr(decision, "data", {}):
            confidence = decision.data["confidence"]

        return cls(
            direction=direction,
            confidence=float(confidence or 0.0),
            pre_guard_direction=getattr(decision, "pre_guard_direction", "NEUTRAL"),
            guard_actions=tuple(getattr(decision, "guard_actions", ())),
            signal_summary=dict(getattr(decision, "signal_summary", {})),
            fusion_weights=dict(getattr(decision, "fusion_weights", {})),
            latency_ms=getattr(decision, "latency_ms", 0.0),
            version=getattr(decision, "version", 0),
            computed_at=decision.computed_at.isoformat()
            if hasattr(decision, "computed_at") and hasattr(decision.computed_at, "isoformat")
            else str(getattr(decision, "computed_at", "")),
        )

    @classmethod
    def neutral(cls) -> "SignalData":
        """Return neutral placeholder for cold-start."""
        from datetime import datetime, timezone
        return cls(
            direction="NEUTRAL", confidence=0.0,
            pre_guard_direction="NEUTRAL",
            guard_actions=(), signal_summary={}, fusion_weights={},
            latency_ms=0.0, version=0,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# FrozenPayload — top-level broadcast contract
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FrozenPayload:
    """Canonical L3 output payload — immutable, serialization-ready.

    This is the single object passed to BroadcastGovernor, TimeSeriesStore,
    and FieldDeltaEncoder. It replaces the `dict[str, Any]` produced by
    legacy SnapshotBuilder.build().

    Attributes:
        data_timestamp:       ISO timestamp of L0 source market data time (UTC).
        broadcast_timestamp:  ISO timestamp of when the broadcast fires.
        spot:                 SPY spot price.
        version:              L0 MVCC snapshot version (for cache validation).
        drift_ms:             L0 snapshot age relative to L2 compute time.
        drift_warning:        True when drift > 800ms.
        signal:               L2 decision output (typed SignalData).
        ui_state:             Full assembled UI state (typed UIState).
        atm:                  ATM decay payload dict (pass-through, None when unavailable).
        heartbeat_timestamp:  Updated on every broadcast tick.
        is_stale:             True when payload age > 2.5× compute interval.
        type:                 Message type tag ("dashboard_update" | "dashboard_init").
    """
    data_timestamp: str
    broadcast_timestamp: str
    spot: float
    version: int
    drift_ms: float
    drift_warning: bool
    signal: SignalData
    ui_state: UIState
    atm: dict[str, Any] | None
    atm_iv: float = 0.0

    # GEX aggregates (Phase 3: GexStatusBar sync)
    net_gex: float = 0.0
    gamma_walls: dict[str, float | None] = field(default_factory=lambda: {"call_wall": None, "put_wall": None})
    gamma_flip_level: float = 0.0

    # Decision Engine: full fused_signal dict from AgentG (Phase 4: DecisionEngine sync)
    fused_signal: dict[str, Any] | None = None
    
    # Microstructure: Consolidated state from AgentB via AgentG (Phase 1 Refactor compatibility)
    micro_structure: dict[str, Any] | None = None

    # Rust Ingest Gateway Diagnostics
    rust_active: bool = False
    shm_stats: dict[str, Any] | None = None

    # Broadcast-layer fields (set by BroadcastGovernor, not PayloadAssembler)
    heartbeat_timestamp: str = ""
    is_stale: bool = False
    type: str = "dashboard_update"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the exact schema expected by the React frontend.

        The output is backward-compatible with the dict produced by
        legacy SnapshotBuilder.build() → validated by test_reactor.py parity tests.
        """
        return {
            "type":                self.type,
            "data_timestamp":      self.data_timestamp,
            "broadcast_timestamp": self.broadcast_timestamp,
            "heartbeat_timestamp": self.heartbeat_timestamp,
            "timestamp":           self.data_timestamp,   # legacy alias
            "spot":                round(self.spot, 2),
            "drift_ms":            round(self.drift_ms, 1),
            "drift_warning":       self.drift_warning,
            "is_stale":            self.is_stale,
            "atm":                 self.atm,
            # Legacy: frontend reads agent_g.data.* paths
            "agent_g": {
                "data": {
                    "ui_state":    self.ui_state.to_dict(),
                    **self.signal.to_dict(),
                    # ⚠️ BUG-5 NOTE: L1 使用 atm_iv，前端期望 spy_atm_iv，此处显式重命名。
                    # 若 L1 字段名变更未同步更新此处，前端将静默收到 null。
                    "spy_atm_iv":  round(self.atm_iv, 4),
                    "as_of":       self.signal.computed_at,
                    "version":     self.version,
                    # GexStatusBar fields
                    "net_gex":          round(self.net_gex, 2),
                    "gamma_walls":      {k: round(v, 2) if v is not None else None for k, v in self.gamma_walls.items()},
                    "gamma_flip_level": round(self.gamma_flip_level, 2),
                    # DecisionEngine: fused_signal from AgentG.data (Phase 4)
                    "fused_signal":     self.fused_signal,
                    # Microstructure: Phase 1 Refactor support
                    "micro_structure":  self.micro_structure,
                },
            },
            # Top-level Diagnostics
            "rust_active": self.rust_active,
            "shm_stats":   self.shm_stats,
        }

    def with_broadcast_fields(
        self,
        heartbeat_timestamp: str,
        is_stale: bool,
        msg_type: str = "dashboard_update",
    ) -> "FrozenPayload":
        """Return a new FrozenPayload with broadcast-layer fields replaced.

        Uses object.__setattr__ to work around frozen=True.
        This is the only sanctioned mutation pattern for FrozenPayload.
        """
        import dataclasses
        return dataclasses.replace(
            self,
            heartbeat_timestamp=heartbeat_timestamp,
            is_stale=is_stale,
            type=msg_type,
        )
