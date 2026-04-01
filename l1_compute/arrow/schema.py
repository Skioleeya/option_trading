"""Backward-compatible re-export of the neutral option-chain Arrow contract."""

from shared_rust.contracts import (
    OPTION_CHAIN_SCHEMA,
    dicts_to_record_batch,
    ensure_record_batch,
)

__all__ = [
    "OPTION_CHAIN_SCHEMA",
    "dicts_to_record_batch",
    "ensure_record_batch",
]
