"""Arrow event handling for L0 runtime."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from shared.services.l0_runtime.normalize.bridges import (
    dispatch_depth_event,
    dispatch_trade_event,
    parse_market_event,
)
from shared.services.l0_runtime.normalize.pipeline import EventType


def _extract_midpoint(*, bid: Any, ask: Any) -> float | None:
    try:
        bid_px = float(bid)
        ask_px = float(ask)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(bid_px) or not math.isfinite(ask_px):
        return None
    if bid_px <= 0.0 or ask_px <= 0.0 or ask_px < bid_px:
        return None
    return (bid_px + ask_px) * 0.5


def extract_spy_spot_from_arrow_event(event: Mapping[str, Any]) -> float | None:
    symbol = str(event.get("symbol") or "").strip()
    if symbol != "SPY.US":
        return None
    try:
        event_type = int(event.get("event_type"))
    except (TypeError, ValueError):
        return None
    if event_type != EventType.DEPTH.value:
        return None
    return _extract_midpoint(bid=event.get("bid"), ask=event.get("ask"))


def handle_arrow_event(
    event: Mapping[str, Any],
    *,
    store: Any,
    symbol_to_strike: Mapping[str, float],
    on_depth: Any,
    on_trade: Any,
    last_trade_price: dict[str, float],
    last_trade_direction: dict[str, int],
    top_of_book: dict[str, tuple[float | None, float | None]],
) -> None:
    spot = extract_spy_spot_from_arrow_event(event)
    if spot is not None:
        store.update_spot_from_source(spot)
        return

    clean = parse_market_event(event, symbol_to_strike=symbol_to_strike)
    if clean is None:
        return

    store.apply_event(clean)
    if clean.event_type == EventType.DEPTH:
        top_of_book[clean.symbol] = (clean.bid, clean.ask)
        dispatch_depth_event(clean, on_depth=on_depth)
        return
    if clean.event_type == EventType.TRADE:
        dispatch_trade_event(
            clean,
            on_trade=on_trade,
            last_trade_price=last_trade_price,
            last_trade_direction=last_trade_direction,
            top_of_book=top_of_book,
        )


__all__ = ["extract_spy_spot_from_arrow_event", "handle_arrow_event"]
