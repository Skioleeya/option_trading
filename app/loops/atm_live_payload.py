"""Helpers for ATM-only payload refresh on duplicate snapshot ticks."""

from __future__ import annotations

from dataclasses import is_dataclass, replace
from datetime import datetime, timezone
from typing import Any

from l3_assembly.events.active_options_contract import active_option_row_from_dict
from l3_assembly.events.payload_events import FrozenPayload


def _normalize_active_options_rows(
    active_options_rows: list[dict[str, Any]] | None,
) -> tuple[Any, ...] | None:
    if active_options_rows is None:
        return None
    if not isinstance(active_options_rows, list):
        return ()
    return tuple(
        active_option_row_from_dict(row)
        for row in active_options_rows
        if isinstance(row, dict)
    )


def build_duplicate_snapshot_live_refresh(
    frozen: FrozenPayload | None,
    atm_decay_payload: dict[str, Any] | None,
    *,
    active_options_rows: list[dict[str, Any]] | None = None,
) -> FrozenPayload | None:
    """Refresh ATM and async UI fields when L1/L2 are skipped on duplicate snapshots."""
    if frozen is None:
        return None
    if not is_dataclass(frozen):
        return None

    next_atm = getattr(frozen, "atm", None)
    next_ui_state = frozen.ui_state
    changed = False

    if atm_decay_payload is not None and next_atm != atm_decay_payload:
        next_atm = atm_decay_payload
        changed = True

    normalized_active_options = _normalize_active_options_rows(active_options_rows)
    if (
        normalized_active_options is not None
        and frozen.ui_state.active_options != normalized_active_options
    ):
        next_ui_state = replace(frozen.ui_state, active_options=normalized_active_options)
        changed = True

    if not changed:
        return None

    return replace(
        frozen,
        atm=next_atm,
        ui_state=next_ui_state,
        broadcast_timestamp=datetime.now(timezone.utc).isoformat(),
    )
