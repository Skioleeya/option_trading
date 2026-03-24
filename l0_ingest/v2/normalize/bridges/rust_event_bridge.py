"""Rust event adapter/dispatch helpers for OptionChainBuilder."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Mapping

from l0_ingest.v2.normalize.pipeline.sanitization import CleanQuoteEvent, EventType, _infer_opt_type

logger = logging.getLogger(__name__)

DepthCallback = Callable[[str, list[dict[str, float]], list[dict[str, float]]], None]
TradeCallback = Callable[[str, list[dict[str, float | int]]], None]

ARRIVAL_MONO_NS_PER_SECOND = 1_000_000_000.0
MIN_BOOK_VOLUME = 1.0
DEPTH_IMPACT_SIDE_RATIO = 0.3


def parse_rust_event(
    event: Mapping[str, Any],
    *,
    symbol_to_strike: Mapping[str, float],
) -> CleanQuoteEvent | None:
    symbol = str(event.get("symbol", "") or "")
    strike = symbol_to_strike.get(symbol)
    if strike is None:
        logger.debug("[RustEventBridge] Rust event dropped (unknown symbol): %s", symbol)
        return None

    raw_event_type = event.get("event_type")
    try:
        event_type = EventType(raw_event_type)
    except (TypeError, ValueError):
        logger.warning(
            "[RustEventBridge] Rust event dropped (invalid event_type): symbol=%s event_type=%s",
            symbol,
            raw_event_type,
        )
        return None

    return CleanQuoteEvent(
        seq_no=int(event.get("seq_no", 0) or 0),
        event_type=event_type,
        symbol=symbol,
        strike=strike,
        opt_type=_infer_opt_type(symbol),
        bid=_positive_or_none(event.get("bid")),
        ask=_positive_or_none(event.get("ask")),
        last_price=_positive_or_none(event.get("last_price")),
        volume=_safe_int_or_none(event.get("volume")),
        open_interest=None,
        implied_volatility=None,
        current_volume=_safe_float_or_none(event.get("current_volume")),
        turnover=_safe_float_or_none(event.get("turnover")),
        arrival_mono=float(event.get("arrival_mono_ns", 0) or 0) / ARRIVAL_MONO_NS_PER_SECOND,
        impact_index=_safe_float_or_none(event.get("impact_index")),
        is_sweep=bool(event.get("is_sweep", False)),
    )


def dispatch_depth_event(
    event: CleanQuoteEvent,
    *,
    on_depth: DepthCallback | None,
) -> None:
    if on_depth is None:
        logger.debug("[RustEventBridge] Rust depth bridge: on_depth callback not set")
        return

    bids, asks = _rust_depth_levels(event)
    try:
        on_depth(event.symbol, bids, asks)
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
        logger.error(
            "[RustEventBridge] Rust depth bridge callback failed: symbol=%s error=%s",
            event.symbol,
            exc,
        )


def dispatch_trade_event(
    event: CleanQuoteEvent,
    *,
    on_trade: TradeCallback | None,
    last_trade_price: dict[str, float],
) -> None:
    if on_trade is None:
        logger.debug("[RustEventBridge] Rust trade bridge: on_trade callback not set")
        return

    volume = float(event.volume or 0.0)
    if volume <= 0.0:
        logger.debug(
            "[RustEventBridge] Rust trade bridge skipped (non-positive volume): symbol=%s",
            event.symbol,
        )
        return

    direction = _infer_rust_trade_direction(
        last_trade_price,
        symbol=event.symbol,
        last_price=event.last_price,
        impact_index=event.impact_index,
    )
    trade = {
        "price": float(event.last_price or 0.0),
        "vol": volume,
        "volume": volume,
        "timestamp": int(time.time()),
        "dir": direction,
        "direction": direction,
        "trade_type": 0,
    }
    try:
        on_trade(event.symbol, [trade])
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
        logger.error(
            "[RustEventBridge] Rust trade bridge callback failed: symbol=%s error=%s",
            event.symbol,
            exc,
        )


def _positive_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0.0 else None


def _safe_int_or_none(value: Any) -> int | None:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _safe_float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _impact_sign(value: float | None) -> int:
    impact = float(value or 0.0)
    if impact > 0.0:
        return 1
    if impact < 0.0:
        return -1
    return 0


def _infer_rust_trade_direction(
    cache: dict[str, float],
    *,
    symbol: str,
    last_price: float | None,
    impact_index: float | None,
) -> int:
    if last_price is None or last_price <= 0.0:
        return _impact_sign(impact_index)

    prev = cache.get(symbol)
    cache[symbol] = last_price
    if prev is None:
        return _impact_sign(impact_index)
    if last_price > prev:
        return 1
    if last_price < prev:
        return -1
    return _impact_sign(impact_index)


def _rust_depth_levels(event: CleanQuoteEvent) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    base_volume = max(float(event.volume or 0.0), MIN_BOOK_VOLUME)
    bid_volume, ask_volume = _depth_side_volumes(base_volume, float(event.impact_index or 0.0))
    bids = _build_book_side(event.bid, bid_volume)
    asks = _build_book_side(event.ask, ask_volume)
    return bids, asks


def _depth_side_volumes(volume: float, impact: float) -> tuple[float, float]:
    if impact > 0.0:
        return volume, max(MIN_BOOK_VOLUME, volume * DEPTH_IMPACT_SIDE_RATIO)
    if impact < 0.0:
        return max(MIN_BOOK_VOLUME, volume * DEPTH_IMPACT_SIDE_RATIO), volume
    return volume, volume


def _build_book_side(price: float | None, volume: float) -> list[dict[str, float]]:
    if (price or 0.0) <= 0.0:
        return []
    return [{"price": float(price), "volume": volume}]
