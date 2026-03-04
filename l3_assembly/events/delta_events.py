"""l3_assembly.events.delta_events — Delta encoding contracts.

DeltaPayload represents the wire message sent to WebSocket clients.
Either a full snapshot (type=DeltaType.FULL) or an incremental field
diff (type=DeltaType.DELTA).

The FieldDeltaEncoder in assembly/delta_encoder.py produces these.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class DeltaType(str, Enum):
    """Message type discriminator for WebSocket clients."""
    FULL  = "dashboard_update"        # Initial / periodic full snapshot
    DELTA = "dashboard_delta"         # Incremental field changes
    INIT  = "dashboard_init"          # First message on WS connect
    KEEPALIVE = "keepalive"           # Heartbeat (no data)


@dataclass(frozen=True)
class DeltaPayload:
    """Wire-format message sent to WebSocket clients.

    Attributes:
        type:         DeltaType discriminator.
        version:      Current payload version (L0 MVCC version).
        prev_version: Previous version this delta was calculated against.
                      None for FULL messages.
        data:         Full serialized payload dict (FULL type only).
        patch:        JSON Patch document list (DELTA type only, legacy compat).
        changes:      Field-level changes dict (DELTA type, preferred).
        timestamp:    ISO timestamp string.
        heartbeat_timestamp: Broadcast-layer timestamp.
    """
    type: DeltaType
    version: int
    timestamp: str
    heartbeat_timestamp: str

    prev_version: int | None = None
    data: dict[str, Any] | None = None          # FULL messages
    patch: list[dict[str, Any]] | None = None   # DELTA (legacy jsonpatch compat)
    changes: dict[str, Any] | None = None       # DELTA (field-level diff, preferred)

    def __post_init__(self) -> None:
        if self.type == DeltaType.FULL and self.data is None:
            raise ValueError("DeltaPayload of type FULL must have data")
        if self.type == DeltaType.DELTA and self.changes is None and self.patch is None:
            raise ValueError("DeltaPayload of type DELTA must have changes or patch")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the exact wire format expected by the React frontend."""
        base: dict[str, Any] = {
            "type":                self.type.value,
            "timestamp":           self.timestamp,
            "heartbeat_timestamp": self.heartbeat_timestamp,
        }
        if self.type == DeltaType.FULL or self.type == DeltaType.INIT:
            assert self.data is not None
            base.update(self.data)
            base["type"] = self.type.value
        elif self.type == DeltaType.DELTA:
            if self.patch is not None:
                # Legacy jsonpatch format (backward compat with existing frontend)
                base["patch"] = self.patch
            if self.changes is not None:
                # New field-level change format (smaller, no jsonpatch lib needed)
                base["changes"] = self.changes
        return base
