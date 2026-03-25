"""Deprecated compatibility wrapper for the old rust_event_bridge module."""

from __future__ import annotations

import warnings
from typing import Any, Mapping

from .market_event_bridge import dispatch_depth_event, dispatch_trade_event, parse_market_event

_DEPRECATION_MESSAGE = (
    "shared.services.l0_runtime.normalize.bridges.rust_event_bridge is deprecated; "
    "use shared.services.l0_runtime.normalize.bridges.market_event_bridge instead."
)


def _warn_once() -> None:
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)


def parse_rust_event(
    event: Mapping[str, Any],
    *,
    symbol_to_strike: Mapping[str, float],
) -> Any:
    _warn_once()
    return parse_market_event(event, symbol_to_strike=symbol_to_strike)


__all__ = [
    "dispatch_depth_event",
    "dispatch_trade_event",
    "parse_rust_event",
]

