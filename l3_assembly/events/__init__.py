"""l3_assembly.events — Strongly-typed L3 output event models.

All models are frozen dataclasses to guarantee immutability across
the L3 assembly pipeline. These are the canonical contracts between
L3 sub-components and downstream consumers (broadcast, storage).

Design principles:
    - Frozen (immutable) — no accidental mutation across pipeline stages
    - No circular imports — only depends on stdlib + typing
    - Serialization-ready via to_dict() methods
    - Direct alignment with L3_OUTPUT_ASSEMBLY.md spec
"""

from l3_assembly.events.payload_events import (
    MetricCard,
    MicroStatsState,
    TacticalTriadState,
    WallMigrationRow,
    DepthProfileRow,
    MTFFlowState,
    ActiveOptionRow,
    UIState,
    SignalData,
    FrozenPayload,
)
from l3_assembly.events.delta_events import (
    DeltaType,
    DeltaPayload,
)

__all__ = [
    # Payload contracts
    "MetricCard",
    "MicroStatsState",
    "TacticalTriadState",
    "WallMigrationRow",
    "DepthProfileRow",
    "MTFFlowState",
    "ActiveOptionRow",
    "UIState",
    "SignalData",
    "FrozenPayload",
    # Delta contracts
    "DeltaType",
    "DeltaPayload",
]
