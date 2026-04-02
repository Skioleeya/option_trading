"""Bridge adapters for L0 V2 normalization."""

from __future__ import annotations

import logging
from typing import Any, Callable, Iterator, Mapping

import pyarrow as pa

from shared.services.l0_runtime._native_generated import l0_rust
from shared.services.l0_runtime.normalize.pipeline import CleanQuoteEvent, EventType

logger = logging.getLogger(__name__)

DepthCallback = Callable[[str, list[dict[str, float]], list[dict[str, float]]], None]
TradeCallback = Callable[[str, list[dict[str, float | int]]], None]

_ws_event_counter = 0


def iter_arrow_batch_rows(batch: pa.RecordBatch) -> Iterator[dict[str, Any]]:
    """Yield Arrow batch rows as lightweight dict mappings for event normalization."""
    column_names = list(batch.schema.names)
    columns = [batch.column(index) for index in range(batch.num_columns)]
    for row_index in range(batch.num_rows):
        yield {
            name: column[row_index].as_py()
            for name, column in zip(column_names, columns, strict=False)
        }


def batch_id_from_batch(batch: pa.RecordBatch) -> int | None:
    """Return the batch id if present in the Arrow schema."""
    if batch.num_rows <= 0 or "batch_id" not in batch.schema.names:
        return None
    batch_id = batch.column(batch.schema.get_field_index("batch_id"))[0].as_py()
    if batch_id is None:
        return None
    return int(batch_id)


def _parse_market_event_native(
    event: Mapping[str, Any],
    *,
    symbol_to_strike: Mapping[str, float],
) -> dict[str, Any] | None:
    out = l0_rust.l0_market_parse_event(dict(event), dict(symbol_to_strike))
    return None if out is None else dict(out)


def _market_depth_levels_native(event: Any) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    out = dict(l0_rust.l0_market_depth_levels(event))
    return list(out.get("bids", [])), list(out.get("asks", []))


def _market_trade_payload_native(event: Any, previous_price: float | None) -> dict[str, Any] | None:
    out = l0_rust.l0_market_trade_payload(event, previous_price)
    return None if out is None else dict(out)


def parse_market_event(
    event: Mapping[str, Any],
    *,
    symbol_to_strike: Mapping[str, float],
) -> CleanQuoteEvent | None:
    global _ws_event_counter
    native = _parse_market_event_native(event, symbol_to_strike=symbol_to_strike)
    if native is None:
        return None
    symbol = str(native["symbol"])
    event_type = EventType(int(native["event_type"]))
    bid = native.get("bid")
    ask = native.get("ask")

    _ws_event_counter += 1
    if _ws_event_counter % 50 == 0:
        logger.debug(
            "[MarketEventBridge] Streaming %s event for %s (bid=%s ask=%s)",
            event_type.value,
            symbol,
            bid,
            ask,
        )

    return CleanQuoteEvent(
        seq_no=int(native.get("seq_no", 0) or 0),
        event_type=event_type,
        symbol=symbol,
        strike=float(native["strike"]),
        opt_type=str(native["opt_type"]),
        bid=bid,
        ask=ask,
        last_price=native.get("last_price"),
        volume=native.get("volume"),
        open_interest=native.get("open_interest"),
        implied_volatility=native.get("implied_volatility"),
        current_volume=native.get("current_volume"),
        turnover=native.get("turnover"),
        arrival_mono=float(native.get("arrival_mono", 0.0) or 0.0),
        impact_index=native.get("impact_index"),
        is_sweep=bool(native.get("is_sweep", False)),
    )


def dispatch_depth_event(
    event: CleanQuoteEvent,
    *,
    on_depth: DepthCallback | None,
) -> None:
    if on_depth is None:
        logger.debug("[MarketEventBridge] Depth callback not set")
        return

    bids, asks = _market_depth_levels_native(event)
    try:
        on_depth(event.symbol, bids, asks)
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
        logger.error(
            "[MarketEventBridge] Depth callback failed: symbol=%s error=%s",
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
        logger.debug("[MarketEventBridge] Trade callback not set")
        return

    trade = _market_trade_payload_native(event, last_trade_price.get(event.symbol))
    if trade is None:
        logger.debug(
            "[MarketEventBridge] Trade bridge skipped (non-positive volume): symbol=%s",
            event.symbol,
        )
        return
    if event.last_price is not None and event.last_price > 0.0:
        last_trade_price[event.symbol] = float(event.last_price)
    try:
        on_trade(event.symbol, [trade])
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
        logger.error(
            "[MarketEventBridge] Trade callback failed: symbol=%s error=%s",
            event.symbol,
            exc,
        )


__all__ = [
    "batch_id_from_batch",
    "dispatch_depth_event",
    "dispatch_trade_event",
    "iter_arrow_batch_rows",
    "parse_market_event",
]
