"""Backward-compatible re-export of the neutral Rust SHM bridge."""

from shared.system.rust_shm_bridge import EventLayout, EventLayoutRegistry, RustBridge, RUST_EVENT_ARROW_SCHEMA

__all__ = [
    "EventLayout",
    "EventLayoutRegistry",
    "RustBridge",
    "RUST_EVENT_ARROW_SCHEMA",
]
