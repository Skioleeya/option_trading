"""Rust-backed helpers for ChainStateStore semantics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.services.l0_runtime._native_extension_loader import load_l0_rust

_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "_native_generated"
_L0_RUST = load_l0_rust(
    candidates=[
        _PACKAGE_DIR / "wave5" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave4" / "l0_rust.pyd",
        _PACKAGE_DIR / "l0_rust.pyd",
    ],
    module_suffix="l0_rust_wave5_state",
)


def default_entry(*, symbol: str, strike: float, opt_type: str) -> dict[str, Any]:
    return dict(_L0_RUST.l0_state_default_entry(symbol, float(strike), str(opt_type)))


def apply_quote_patch(
    *,
    entry: dict[str, Any],
    event: Any,
    is_rest: bool,
    ws_price_seen: bool,
    ws_volume_seen: bool,
    ws_current_volume_seen: bool,
    ws_turnover_seen: bool,
    max_ws_flow_volume: float,
) -> dict[str, Any]:
    return dict(
        _L0_RUST.l0_state_apply_quote(
            entry,
            event,
            bool(is_rest),
            bool(ws_price_seen),
            bool(ws_volume_seen),
            bool(ws_current_volume_seen),
            bool(ws_turnover_seen),
            float(max_ws_flow_volume),
        )
    )


def apply_depth_patch(*, entry: dict[str, Any], event: Any) -> dict[str, Any]:
    return dict(_L0_RUST.l0_state_apply_depth(entry, event))
