"""Helpers for ATM-only payload refresh on duplicate snapshot ticks."""

from __future__ import annotations

from dataclasses import is_dataclass, replace
from datetime import datetime, timezone
from typing import Any

from l3_assembly.events.payload_events import FrozenPayload


def build_duplicate_snapshot_atm_refresh(
    frozen: FrozenPayload | None,
    atm_decay_payload: dict[str, Any] | None,
) -> FrozenPayload | None:
    """Refresh only ATM fields when L1/L2 are skipped on duplicate snapshots."""
    if frozen is None or atm_decay_payload is None:
        return None
    if not is_dataclass(frozen):
        return None
    if getattr(frozen, "atm", None) == atm_decay_payload:
        return None
    return replace(
        frozen,
        atm=atm_decay_payload,
        broadcast_timestamp=datetime.now(timezone.utc).isoformat(),
    )
