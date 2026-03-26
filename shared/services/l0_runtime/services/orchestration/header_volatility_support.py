"""Helpers for low-frequency header volatility auxiliary diagnostics."""

from __future__ import annotations

import logging
import math
from datetime import date, timedelta
from typing import Any


def next_trading_day(base_day: date) -> date:
    """Return the next weekday trading day.

    The runtime currently does not have a holiday calendar at this layer.
    Weekend skipping is still better than binding 1DTE to today's expiry.
    """
    probe = base_day + timedelta(days=1)
    while probe.weekday() >= 5:
        probe += timedelta(days=1)
    return probe


def extract_chain_strike(item: Any) -> float | None:
    raw = getattr(item, "strike_price", getattr(item, "price", None))
    return to_positive_float(raw)


def to_positive_float(raw: Any) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value <= 0.0:
        return None
    return value


def normalize_decimal_ratio(raw: Any) -> float | None:
    value = to_positive_float(raw)
    if value is None:
        return None
    if value > 1.0:
        value = value / 100.0
    if value <= 0.0 or value > 5.0:
        return None
    return value


def average_valid(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None and value > 0.0]
    if not valid:
        return None
    return sum(valid) / len(valid)


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
    best_item = None
    best_distance = float("inf")
    for item in chain_info or []:
        strike = extract_chain_strike(item)
        if strike is None:
            continue
        distance = abs(strike - spot)
        if distance < best_distance:
            best_distance = distance
            best_item = item
    return best_item


def _extract_option_iv_decimal(quote: Any) -> float | None:
    if quote is None:
        return None
    primary = getattr(quote, "implied_volatility_decimal", None)
    if primary is not None:
        return normalize_decimal_ratio(primary)
    return normalize_decimal_ratio(getattr(quote, "implied_volatility", None))
