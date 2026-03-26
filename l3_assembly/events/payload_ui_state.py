"""Typed UI-state payload contracts for L3."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


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
    label: str
    badge: str
    tooltip: str = ""

    def __post_init__(self) -> None:
        if self.badge not in VALID_BADGE_TOKENS:
            raise ValueError(
                f"MetricCard.badge must be one of {VALID_BADGE_TOKENS}, got {self.badge!r}"
            )

    def to_dict(self) -> dict[str, str]:
        payload = {"label": self.label, "badge": self.badge}
        if self.tooltip:
            payload["tooltip"] = self.tooltip
        return payload


@dataclass(frozen=True)
class MicroStatsState:
    net_gex: MetricCard
    wall_dyn: MetricCard
    vanna: MetricCard
    momentum: MetricCard

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {
            "net_gex": self.net_gex.to_dict(),
            "wall_dyn": self.wall_dyn.to_dict(),
            "vanna": self.vanna.to_dict(),
            "momentum": self.momentum.to_dict(),
        }

    @classmethod
    def zero_state(cls) -> "MicroStatsState":
        card = MetricCard(label="—", badge="badge-neutral")
        return cls(net_gex=card, wall_dyn=card, vanna=card, momentum=card)


@dataclass(frozen=True)
class TacticalTriadState:
    vrp: dict[str, Any]
    charm: dict[str, Any]
    svol: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"vrp": dict(self.vrp), "charm": dict(self.charm), "svol": dict(self.svol)}

    @classmethod
    def zero_state(cls) -> "TacticalTriadState":
        return cls(vrp={}, charm={}, svol={})


@dataclass(frozen=True)
class WallMigrationRow:
    label: str
    strike: float
    state: str
    history: list[float]
    lights: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "strike": self.strike,
            "state": self.state,
            "history": list(self.history),
            "lights": dict(self.lights),
        }


@dataclass(frozen=True)
class DepthProfileRow:
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
            "strike": self.strike,
            "call_pct": round(self.call_pct, 4) if self.call_pct is not None else 0.0,
            "put_pct": round(self.put_pct, 4) if self.put_pct is not None else 0.0,
            "is_spot": self.is_spot,
            "is_flip": self.is_flip,
            "is_dominant_put": self.is_dominant_put,
            "is_dominant_call": self.is_dominant_call,
        }


@dataclass(frozen=True)
class ActiveOptionRow:
    symbol: str
    option_type: str
    strike: float
    implied_volatility: float
    volume: int
    turnover: float
    flow: float
    flow_score: float
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
    is_placeholder: bool = False
    slot_index: int = 0
    row_quality: str | None = None
    fallback_reason: str | None = None
    is_synthetic_fallback: bool = False
    flow_signal_state: str = "LIVE"
    flow_signal_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "option_type": self.option_type,
            "strike": self.strike,
            "implied_volatility": round(self.implied_volatility, 4),
            "volume": self.volume,
            "turnover": round(self.turnover, 2),
            "flow": round(self.flow, 2),
            "flow_score": round(self.flow_score, 4),
            "impact_index": round(self.impact_index, 4),
            "is_sweep": self.is_sweep,
            "flow_deg_formatted": self.flow_deg_formatted,
            "flow_volume_label": self.flow_volume_label,
            "flow_d_z": round(self.flow_d_z, 4),
            "flow_e_z": round(self.flow_e_z, 4),
            "flow_g_z": round(self.flow_g_z, 4),
            "is_placeholder": self.is_placeholder,
            "slot_index": self.slot_index,
            "row_quality": self.row_quality,
            "fallback_reason": self.fallback_reason,
            "is_synthetic_fallback": self.is_synthetic_fallback,
            "flow_signal_state": self.flow_signal_state,
            "flow_signal_reason": self.flow_signal_reason,
        }


@dataclass(frozen=True)
class MTFFlowState:
    m1: dict[str, Any]
    m5: dict[str, Any]
    m15: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"m1": dict(self.m1), "m5": dict(self.m5), "m15": dict(self.m15)}

    @classmethod
    def zero_state(cls) -> "MTFFlowState":
        neutral = {
            "state": 0,
            "relative_displacement": 0.0,
            "pressure_gradient": 0.0,
            "distance_to_vacuum": 0.0,
            "kinetic_level": 0.0,
        }
        return cls(m1=dict(neutral), m5=dict(neutral), m15=dict(neutral))


@dataclass(frozen=True)
class UIState:
    micro_stats: MicroStatsState
    tactical_triad: TacticalTriadState
    wall_migration: tuple[WallMigrationRow, ...]
    depth_profile: tuple[DepthProfileRow, ...]
    active_options: tuple[ActiveOptionRow, ...]
    mtf_flow: MTFFlowState
    skew_dynamics: dict[str, Any]
    macro_volume_map: dict[str, Any]
    iv_velocity: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "micro_stats": self.micro_stats.to_dict(),
            "tactical_triad": self.tactical_triad.to_dict(),
            "wall_migration": [row.to_dict() for row in self.wall_migration],
            "depth_profile": [row.to_dict() for row in self.depth_profile],
            "active_options": [row.to_dict() for row in self.active_options],
            "mtf_flow": self.mtf_flow.to_dict(),
            "skew_dynamics": {
                key: round(value, 4) if isinstance(value, (int, float)) else value
                for key, value in self.skew_dynamics.items()
            },
            "macro_volume_map": {
                key: round(value, 2) if isinstance(value, (int, float)) else value
                for key, value in self.macro_volume_map.items()
            },
            "iv_velocity": self.iv_velocity,
        }

    @classmethod
    def zero_state(cls) -> "UIState":
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
