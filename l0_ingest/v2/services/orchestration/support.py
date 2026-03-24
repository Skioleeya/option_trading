"""Support helpers for OptionChainBuilder orchestration paths."""

from __future__ import annotations

import logging
import re
import struct
import time
from typing import Any, Callable, Mapping

from l0_ingest.v2.normalize.pipeline.sanitization import CleanQuoteEvent, EventType, _infer_opt_type

logger = logging.getLogger(__name__)

U64_BYTE_WIDTH = 8
_OPTION_SYMBOL_RE = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d+)(?:\.[A-Z]+)?$")


def _infer_strike_from_symbol(symbol: str) -> float | None:
    """Best-effort strike inference for LongPort option symbols.

    This is used as a startup-safe fallback when subscription metadata has not
    populated `symbol_to_strike` yet. The encoding differs across symbol forms,
    so we infer the price scale from the strike digit width.
    """
    normalized = (symbol or "").strip().upper()
    match = _OPTION_SYMBOL_RE.match(normalized)
    if not match:
        return None

    strike_digits = match.group(4)
    try:
        raw = int(strike_digits)
    except ValueError:
        return None

    strike = raw / 1000.0
    return strike if strike > 0.0 else None


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
            logger.warning(
                "[IVBaselineSync] HOT-START OI skipped: strike unresolved for %s",
                symbol,
            )
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
    return struct.unpack("Q", mm[ptr : ptr + U64_BYTE_WIDTH])[0]
