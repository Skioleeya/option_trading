"""P1 — SanitizationPipeline: L0→L1A Data Cleaning Boundary.

This module is the SINGLE point where Longport raw data is parsed and validated.
All `float()` casts and `math.isfinite()` guards live here — nowhere else.

Replaces the scattered parsing logic previously baked into:
  - OptionChainBuilder._update_contract_in_memory()
  - IVBaselineSync.warm_up() / _staggered_sync()
  - Tier2Poller._fetch()
  - Tier3Poller._fetch()

Architecture:
  RawMarketEvent  ──► SanitizationPipeline.parse()  ──► CleanQuoteEvent | None
                                                           (None = silently dropped)
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from itertools import count
from typing import Any, Literal

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Sequence number provider (monotonically increasing, process-scoped)
# Used by ChainStateStore to reject out-of-order events.
# ──────────────────────────────────────────────────────────────────────────────
_seq_counter = count(1)


def _next_seq() -> int:
    return next(_seq_counter)


# ──────────────────────────────────────────────────────────────────────────────
# Event types
# ──────────────────────────────────────────────────────────────────────────────

class EventType(Enum):
    QUOTE = auto()   # WS SubType.Quote push
    DEPTH = auto()   # WS SubType.Depth push
    TRADE = auto()   # WS SubType.Trade push
    REST  = auto()   # REST calc_indexes / option_quote result


@dataclass
class RawMarketEvent:
    """Opaque container for a single market data push from Longport SDK.

    Created by MarketDataGateway from OS-thread callbacks before handing
    off to the asyncio event loop for sanitization.
    """
    event_type: EventType
    symbol: str
    payload: Any                        # raw SDK object, unchanged
    arrival_mono: float = field(default_factory=time.monotonic)


@dataclass(frozen=True)
class CleanQuoteEvent:
    """Strongly-typed, immutable, math-safe event after sanitization.

    All floats are guaranteed to satisfy math.isfinite().
    None means the field was absent in the source push (not 0.0).
    seq_no is globally monotonically increasing, used by ChainStateStore
    to prevent stale REST data from overwriting fresh WS data.
    """
    # Core Fields (Must come before fields with defaults)
    seq_no: int
    event_type: EventType
    symbol: str
    strike: float
    opt_type: Literal["CALL", "PUT"]
    arrival_mono: float

    # Price / flow
    bid: float | None = None
    ask: float | None = None
    last_price: float | None = None
    volume: int | None = None
    open_interest: int | None = None

    # Volatility (already scaled to decimal, e.g. 0.18 for 18% IV)
    implied_volatility: float | None = None
    iv_timestamp: float | None = None          # time.monotonic() at which IV arrived

    # Greeks from LongPort (rarely populated on WS pushes)
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None

    # Misc
    current_volume: float | None = None
    turnover: float | None = None

    # High-Perf Extensions (Native Rust Path)
    impact_index: float | None = 0.0
    is_sweep: bool | None = False


@dataclass(frozen=True)
class CleanDepthEvent:
    """Top-of-book bid/ask from a Depth push, post-sanitization."""
    seq_no: int
    symbol: str
    bid: float | None    # best bid price (None if no bids in event)
    ask: float | None    # best ask price (None if no asks in event)
    bid_size: int | None
    ask_size: int | None
    arrival_mono: float


@dataclass(frozen=True)
class CleanTradeEvent:
    """Single trade tick from a Trade push, post-sanitization."""
    seq_no: int
    symbol: str
    price: float
    volume: int
    direction_sign: float   # +1.0 = uptick, -1.0 = downtick, 0.0 = unknown
    arrival_mono: float


# ──────────────────────────────────────────────────────────────────────────────
# Sanitization helpers
# ──────────────────────────────────────────────────────────────────────────────

def _safe_float(val: Any) -> float | None:
    """Cast to float; return None if absent, non-finite, or unconvertible."""
    if val is None or val == "":
        return None
    try:
        f = float(val)
        return f if math.isfinite(f) else None
    except (ValueError, TypeError, AttributeError):
        return None


def _safe_positive_float(val: Any) -> float | None:
    """Like _safe_float but also requires val > 0."""
    f = _safe_float(val)
    return f if (f is not None and f > 0) else None


def _safe_int(val: Any) -> int | None:
    if val is None or val == "":
        return None
    try:
        # Handle cases where val might be a float string '123.0' or 'I'
        return int(float(val))
    except (ValueError, TypeError, AttributeError):
        return None


def _infer_opt_type(symbol: str) -> Literal["CALL", "PUT"]:
    """Infer option type from symbol string (LongPort format)."""
    # e.g. SPY260304C673000.US → C → CALL
    # Works for both LongPort format and generic single-char C/P in symbol
    upper = symbol.upper()
    return "PUT" if "P" in upper.split(".")[0][-8:] else "CALL"


# ──────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────────────────────────────────────────

class SanitizationPipeline:
    """Converts RawMarketEvents into strongly-typed Clean* events.

    Instance is stateless — safe to share across the event consumer loop.
    The strike_lookup dependency is injected via parse() to keep the pipeline
    decoupled from SubscriptionManager internals.
    """

    def parse_quote(
        self,
        raw: RawMarketEvent,
        strike: float,
    ) -> CleanQuoteEvent | None:
        """Parse a QUOTE or REST raw event into a CleanQuoteEvent.

        Args:
            raw:    The raw event from the gateway/poller.
            strike: Pre-resolved strike price (from SubscriptionManager.symbol_to_strike).

        Returns:
            CleanQuoteEvent if at least one useful field is present, else None.
        """
        q = raw.payload

        # ── Price / flow ──────────────────────────────────────────────────────
        bid       = _safe_positive_float(getattr(q, "bid", None))
        ask       = _safe_positive_float(getattr(q, "ask", None))
        last_price = _safe_positive_float(getattr(q, "last_done", None))
        volume    = _safe_int(getattr(q, "volume", None))
        cv        = _safe_float(getattr(q, "current_volume", None))
        turnover  = _safe_float(getattr(q, "turnover", None))
        opt_ext = getattr(raw.payload, "option_extend", None)
        
        logger.debug(
            "[SANITIZER] symbol=%s top_oi=%s top_iv=%s ext_oi=%s ext_iv=%s",
            raw.symbol,
            getattr(raw.payload, "open_interest", "MISSING"),
            getattr(raw.payload, "implied_volatility", "MISSING"),
            getattr(opt_ext, "open_interest", "MISSING") if opt_ext else "NO_EXT",
            getattr(opt_ext, "implied_volatility", "MISSING") if opt_ext else "NO_EXT"
        )
        
        oi = _safe_int(getattr(raw.payload, "open_interest", None))

        # ── Greeks (rarely on WS) ─────────────────────────────────────────────
        delta = _safe_float(getattr(q, "delta", None))
        gamma = _safe_float(getattr(q, "gamma", None))
        theta = _safe_float(getattr(q, "theta", None))
        vega  = _safe_float(getattr(q, "vega", None))

        # ── Implied Volatility (nested in option_extend or flat) ──────────────
        iv: float | None = None
        iv_ts: float | None = None

        # opt_ext = getattr(q, "option_extend", None) # This line is now redundant due to the earlier assignment
        iv_raw  = (
            getattr(opt_ext, "implied_volatility", None)
            if opt_ext
            else getattr(q, "implied_volatility", None)
        )
        if opt_ext and oi is None:
            oi = _safe_int(getattr(opt_ext, "open_interest", None))

        f_iv = _safe_float(iv_raw)
        if f_iv is not None and f_iv > 0:
            # Longport opt_ext.implied_volatility is a percentage string (e.g. "20.51" = 20.51%)
            # Divide by 100 to get the decimal fraction needed by BSM (0.2051)
            iv    = f_iv / 100.0
            iv_ts = time.monotonic()

        # ── BUG-6 FIX: 无套利条件检查（穿透报价，arxiv 2025） ────────────────────────
        # bid > ask 违反无套利条件，会导致 mid-price 偏高，从而括大 ATM Decay 计算误差。
        if bid is not None and ask is not None and bid > ask:
            logger.warning(
                "[SANITIZATION] %s: Crossed quote bid=%.4f > ask=%.4f, dropping prices",
                raw.symbol, bid, ask,
            )
            bid = ask = None

        # ── BUG-7 FIX: 报价时效 TTL 检测（ESMA MiFIR 2024） ────────────────────────────
        # WS 连接抑动可能导致报价延迟到达；>30s 的报价应抑制价格字段以避免 IV 时间戳偏差。
        _QUOTE_STALENESS_THRESHOLD = 30.0  # seconds
        _quote_age = time.monotonic() - raw.arrival_mono
        if _quote_age > _QUOTE_STALENESS_THRESHOLD:
            logger.warning(
                "[SANITIZATION] %s: Stale quote age=%.1fs > 30s, suppressing price fields",
                raw.symbol, _quote_age,
            )
            bid = ask = last_price = None

        # ── Guard: must carry at least one useful field ───────────────────────
        useful = any(v is not None for v in (bid, ask, last_price, volume, oi, iv))
        if not useful:
            return None

        return CleanQuoteEvent(
            seq_no             = _next_seq(),
            event_type         = raw.event_type,
            symbol             = raw.symbol,
            strike             = strike,
            opt_type           = _infer_opt_type(raw.symbol),
            bid                = bid,
            ask                = ask,
            last_price         = last_price,
            volume             = volume,
            open_interest      = oi,
            implied_volatility = iv,
            iv_timestamp       = iv_ts,
            delta              = delta,
            gamma              = gamma,
            theta              = theta,
            vega               = vega,
            current_volume     = cv,
            turnover           = turnover,
            arrival_mono       = raw.arrival_mono,
            impact_index       = 0.0,
            is_sweep           = False,
        )

    def parse_depth(self, raw: RawMarketEvent) -> CleanDepthEvent | None:
        """Parse a DEPTH push into a CleanDepthEvent (top-of-book only)."""
        event = raw.payload
        bids = getattr(event, "bids", [])
        asks = getattr(event, "asks", [])

        bid_price = bid_size = ask_price = ask_size = None

        if bids:
            bid_price = _safe_float(getattr(bids[0], "price", None))
            bid_size  = _safe_int(getattr(bids[0], "volume", None))
        if asks:
            ask_price = _safe_float(getattr(asks[0], "price", None))
            ask_size  = _safe_int(getattr(asks[0], "volume", None))

        if bid_price is None and ask_price is None:
            return None

        return CleanDepthEvent(
            seq_no       = _next_seq(),
            symbol       = raw.symbol,
            bid          = bid_price,
            ask          = ask_price,
            bid_size     = bid_size,
            ask_size     = ask_size,
            arrival_mono = raw.arrival_mono,
        )

    def parse_rest_item(
        self,
        symbol: str,
        strike: float,
        item: Any,
        tier: str = "REST",
    ) -> CleanQuoteEvent | None:
        """Parse a REST calc_indexes / option_quote result item.

        Args:
            symbol: Option contract symbol.
            strike: Pre-resolved strike.
            item:   Individual result object from SDK.
            tier:   Source tier label for logging (e.g. 'T1', 'T2', 'T3').
        """
        raw = RawMarketEvent(
            event_type    = EventType.REST,
            symbol        = symbol,
            payload       = item,
            arrival_mono  = time.monotonic(),
        )
        ev = self.parse_quote(raw, strike)
        if ev is None:
            logger.warning("[SANITIZATION] %s: REST item %s FAILED to parse", tier, symbol)
        else:
            logger.info("[SANITIZATION] %s: Filtered REST item %s | iv=%s oi=%s", tier, symbol, ev.implied_volatility, ev.open_interest)
        return ev
