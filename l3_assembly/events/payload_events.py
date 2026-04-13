"""Strongly typed top-level L3 payload contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from l3_assembly.events.payload_ui_state import (
    ActiveOptionRow,
    DepthProfileRow,
    MetricCard,
    MicroStatsState,
    MTFFlowState,
    TacticalTriadState,
    UIState,
    VALID_BADGE_TOKENS,
    WallMigrationRow,
)


@dataclass(frozen=True)
class SignalData:
    """Typed wrapper around L2 DecisionOutput fields for the payload."""

    direction: str
    confidence: float
    pre_guard_direction: str
    guard_actions: tuple[str, ...]
    signal_summary: dict[str, str]
    fusion_weights: dict[str, float]
    latency_ms: float
    version: int
    computed_at: str

    def __post_init__(self) -> None:
        if self.direction not in ("BULLISH", "BEARISH", "NEUTRAL", "HALT", "NO_TRADE"):
            raise ValueError(f"SignalData.direction invalid: {self.direction!r}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"SignalData.confidence must be in [0,1], got {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "confidence": round(self.confidence, 4),
            "pre_guard_direction": self.pre_guard_direction,
            "guard_actions": list(self.guard_actions),
            "signal_summary": dict(self.signal_summary),
            "fusion_weights": {key: round(value, 4) for key, value in self.fusion_weights.items()},
            "latency_ms": round(self.latency_ms, 2),
            "version": self.version,
            "computed_at": self.computed_at,
        }

    @classmethod
    def from_decision_output(cls, decision: Any) -> "SignalData":
        direction = getattr(decision, "signal", None) or getattr(decision, "direction", "NEUTRAL")
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
        from datetime import datetime, timezone

        return cls(
            direction="NEUTRAL",
            confidence=0.0,
            pre_guard_direction="NEUTRAL",
            guard_actions=(),
            signal_summary={},
            fusion_weights={},
            latency_ms=0.0,
            version=0,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class FrozenPayload:
    """Canonical L3 output payload."""

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
    net_gex: float = 0.0
    gamma_walls: dict[str, float | None] = field(
        default_factory=lambda: {"call_wall": None, "put_wall": None}
    )
    gamma_flip_level: float | None = None
    fused_signal: dict[str, Any] | None = None
    micro_structure: dict[str, Any] | None = None
    header_volatility: dict[str, Any] | None = None
    rust_active: bool = False
    shm_stats: dict[str, Any] | None = None
    governor_telemetry: dict[str, Any] = field(default_factory=dict)
    heartbeat_timestamp: str = ""
    is_stale: bool = False
    type: str = "dashboard_update"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "version": self.version,
            "data_timestamp": self.data_timestamp,
            "broadcast_timestamp": self.broadcast_timestamp,
            "heartbeat_timestamp": self.heartbeat_timestamp,
            "timestamp": self.data_timestamp,
            "spot": round(self.spot, 2),
            "drift_ms": round(self.drift_ms, 1),
            "drift_warning": self.drift_warning,
            "is_stale": self.is_stale,
            "atm": self.atm,
            "agent_g": {
                "data": {
                    "ui_state": self.ui_state.to_dict(),
                    **self.signal.to_dict(),
                    "spy_atm_iv": round(self.atm_iv, 4),
                    "as_of": self.signal.computed_at,
                    "version": self.version,
                    "net_gex": round(self.net_gex, 2),
                    "gamma_walls": {
                        key: round(value, 2) if value is not None else None
                        for key, value in self.gamma_walls.items()
                    },
                    "gamma_flip_level": (
                        round(self.gamma_flip_level, 2)
                        if self.gamma_flip_level is not None
                        else None
                    ),
                    "fused_signal": self.fused_signal,
                    "micro_structure": self.micro_structure,
                    "header_volatility": self.header_volatility,
                },
            },
            "rust_active": self.rust_active,
            "shm_stats": self.shm_stats,
            "governor_telemetry": dict(self.governor_telemetry),
        }

    def with_broadcast_fields(
        self,
        heartbeat_timestamp: str,
        is_stale: bool,
        msg_type: str = "dashboard_update",
    ) -> "FrozenPayload":
        import dataclasses

        return dataclasses.replace(
            self,
            heartbeat_timestamp=heartbeat_timestamp,
            is_stale=is_stale,
            type=msg_type,
        )
