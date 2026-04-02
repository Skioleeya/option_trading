"""Neutral Active Options input surface backed by shared_rust.services."""

from shared_rust.services import (
    ActiveOptionsInputSnapshotData,
    build_active_options_input_snapshot,
)

ACTIVE_OPTIONS_INPUT_REASON_EMPTY_CHAIN = "empty_chain"
ACTIVE_OPTIONS_INPUT_REASON_INVALID_SPOT = "invalid_spot"


__all__ = [
    "ACTIVE_OPTIONS_INPUT_REASON_EMPTY_CHAIN",
    "ACTIVE_OPTIONS_INPUT_REASON_INVALID_SPOT",
    "ActiveOptionsInputSnapshotData",
    "build_active_options_input_snapshot",
]
