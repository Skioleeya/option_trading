"""Orchestration service namespace for L0 V2."""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Callable, Mapping

from shared.services.l0_runtime.normalize.pipeline import CleanQuoteEvent, EventType, _infer_opt_type
from shared.services.l0_runtime.services._native_helpers import (
    average_valid_native,
    extract_option_iv_decimal_native,
    infer_strike_from_symbol_native,
    next_trading_day_native,
    normalize_decimal_ratio_native,
    read_u64_native,
    select_nearest_chain_item_native,
    to_positive_float_native,
)

logger = logging.getLogger(__name__)


def _infer_strike_from_symbol(symbol: str) -> float | None:
    return infer_strike_from_symbol_native(symbol)


def _resolve_strike_for_symbol(symbol: str, resolve_strike: Callable[[str], float | None]) -> float | None:
    strike = resolve_strike(symbol)
    if strike is not None:
        return strike
    return _infer_strike_from_symbol(symbol)


def apply_preloaded_oi_events(
    *,
    oi_cache: Mapping[str, int],
    resolve_strike: Callable[[str], float | None],
    store: Any,
) -> int:
    """Write preloaded OI cache into chain state as REST-style events."""
    applied = 0
    for symbol, oi in oi_cache.items():
        strike = _resolve_strike_for_symbol(symbol, resolve_strike)
        if strike is None:
            logger.warning("[IVBaselineSync] HOT-START OI skipped: strike unresolved for %s", symbol)
            continue
        clean = CleanQuoteEvent(
            seq_no=0,
            event_type=EventType.REST,
            symbol=symbol,
            strike=strike,
            opt_type=_infer_opt_type(symbol),
            bid=None,
            ask=None,
            last_price=None,
            volume=None,
            open_interest=oi,
            implied_volatility=None,
            iv_timestamp=None,
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            current_volume=None,
            turnover=None,
            arrival_mono=time.monotonic(),
        )
        store.apply_event(clean)
        if clean.open_interest is not None:
            store.apply_oi_smooth(clean.symbol, clean.open_interest)
        applied += 1
    return applied


def apply_rest_update(
    *,
    symbol: str,
    item: Any,
    resolve_strike: Callable[[str], float | None],
    sanitizer: Any,
    store: Any,
) -> None:
    """Sanitize and apply a single REST update item into store."""
    strike = _resolve_strike_for_symbol(symbol, resolve_strike)
    if strike is None:
        logger.warning("[OptionChainBuilder] REST update dropped: strike unresolved for %s", symbol)
        return
    clean = sanitizer.parse_rest_item(symbol, strike, item)
    if clean:
        store.apply_event(clean)
        if clean.open_interest is not None:
            store.apply_oi_smooth(clean.symbol, clean.open_interest)
        return
    logger.warning("[OptionChainBuilder] REST update sanitize failed for %s", symbol)


def read_shm_u64(mm: Any | None, ptr: int) -> int:
    """Read uint64 value from SHM pointer; returns 0 when SHM is unavailable."""
    if mm is None:
        return 0
    return read_u64_native(bytes(mm), ptr)


def next_trading_day(base_day: date) -> date:
    return next_trading_day_native(base_day)


def extract_chain_strike(item: Any) -> float | None:
    raw = getattr(item, "strike_price", getattr(item, "price", None))
    return to_positive_float(raw)


def to_positive_float(raw: Any) -> float | None:
    return to_positive_float_native(raw)


def normalize_decimal_ratio(raw: Any) -> float | None:
    return normalize_decimal_ratio_native(raw)


def average_valid(values: list[float | None]) -> float | None:
    return average_valid_native(values)


async def build_header_volatility_aux(
    *,
    quote_runtime: Any,
    limiter: Any,
    spot: float,
    trade_day: date,
    logger: logging.Logger,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    payload.update(
        await _fetch_vix_aux(
            quote_runtime=quote_runtime,
            limiter=limiter,
            logger=logger,
        )
    )
    payload.update(
        await _fetch_1dte_aux(
            quote_runtime=quote_runtime,
            limiter=limiter,
            spot=spot,
            trade_day=trade_day,
            logger=logger,
        )
    )
    return payload


async def _fetch_vix_aux(
    *,
    quote_runtime: Any,
    limiter: Any,
    logger: logging.Logger,
) -> dict[str, Any]:
    try:
        async with limiter.acquire(weight=1):
            quotes = await quote_runtime.quote([".VIX.US"])
    except Exception as exc:
        logger.warning("[FeedOrchestrator] header VIX quote failed: %s", exc)
        return {"vix_symbol": ".VIX.US", "vix_iv_decimal": None}
    quote = quotes[0] if quotes else None
    raw_last_done = getattr(quote, "last_done", None) if quote is not None else None
    return {
        "vix_symbol": ".VIX.US",
        "vix_last_done": raw_last_done,
        "vix_iv_decimal": normalize_decimal_ratio(raw_last_done),
    }


async def _fetch_1dte_aux(
    *,
    quote_runtime: Any,
    limiter: Any,
    spot: float,
    trade_day: date,
    logger: logging.Logger,
) -> dict[str, Any]:
    expiry = next_trading_day(trade_day)
    try:
        async with limiter.acquire(weight=1):
            chain_info = await quote_runtime.option_chain_info_by_date("SPY.US", expiry)
    except Exception as exc:
        logger.warning("[FeedOrchestrator] header 1DTE chain lookup failed: %s", exc)
        return {"next_expiry": expiry.isoformat(), "atm_iv_1dte": None}
    nearest = _select_nearest_chain_item(chain_info, spot)
    if nearest is None:
        return {"next_expiry": expiry.isoformat(), "atm_iv_1dte": None}
    symbols = [
        symbol
        for symbol in (getattr(nearest, "call_symbol", None), getattr(nearest, "put_symbol", None))
        if isinstance(symbol, str) and symbol
    ]
    if not symbols:
        return {"next_expiry": expiry.isoformat(), "atm_iv_1dte": None}
    try:
        async with limiter.acquire(weight=len(symbols)):
            quotes = await quote_runtime.option_quote(symbols)
    except Exception as exc:
        logger.warning("[FeedOrchestrator] header 1DTE option quote failed: %s", exc)
        return {"next_expiry": expiry.isoformat(), "atm_iv_1dte": None}
    quote_by_symbol = {getattr(quote, "symbol", ""): quote for quote in quotes or []}
    call_symbol = getattr(nearest, "call_symbol", None)
    put_symbol = getattr(nearest, "put_symbol", None)
    call_iv = _extract_option_iv_decimal(quote_by_symbol.get(call_symbol))
    put_iv = _extract_option_iv_decimal(quote_by_symbol.get(put_symbol))
    return {
        "next_expiry": expiry.isoformat(),
        "atm_iv_1dte": average_valid([call_iv, put_iv]),
        "atm_iv_1dte_call": call_iv,
        "atm_iv_1dte_put": put_iv,
        "atm_iv_1dte_strike": extract_chain_strike(nearest),
    }


def _select_nearest_chain_item(chain_info: list[Any], spot: float) -> Any | None:
    return select_nearest_chain_item_native(chain_info, spot)


def _extract_option_iv_decimal(quote: Any) -> float | None:
    if quote is None:
        return None
    return extract_option_iv_decimal_native(quote)


from .feed_orchestrator import FeedOrchestrator

__all__ = [
    "FeedOrchestrator",
    "apply_preloaded_oi_events",
    "apply_rest_update",
    "average_valid",
    "build_header_volatility_aux",
    "extract_chain_strike",
    "next_trading_day",
    "normalize_decimal_ratio",
    "read_shm_u64",
    "to_positive_float",
]
