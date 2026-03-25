"""Small contract models for the L0 V2 facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

DepthCallback = Callable[[str, list[Any], list[Any]], None]
TradeCallback = Callable[[str, list[dict[str, Any]]], None]


@dataclass
class CallbackHooks:
    on_depth: DepthCallback | None = None
    on_trade: TradeCallback | None = None


@dataclass(frozen=True)
class SnapshotRequest:
    include_chain_arrow: bool = False
