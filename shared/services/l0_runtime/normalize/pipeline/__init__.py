"""Sanitization pipeline primitives for L0 V2."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from itertools import count
from pathlib import Path
from typing import Any, Literal

from shared.services.l0_runtime._native_extension_loader import load_l0_rust

logger = logging.getLogger(__name__)

_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "_native_generated"
_L0_RUST = load_l0_rust(
    candidates=[
        _PACKAGE_DIR / "wave4" / "l0_rust.pyd",
        _PACKAGE_DIR / "l0_rust.pyd",
    ],
    module_suffix="l0_rust_wave4_sanitization",
)

_seq_counter = count(1)


def _next_seq() -> int:
    return next(_seq_counter)


class EventType(Enum):
    QUOTE = auto()
    DEPTH = auto()
    TRADE = auto()
    REST = auto()


@dataclass
class RawMarketEvent:
    event_type: EventType
    symbol: str
    payload: Any
    arrival_mono: float = field(default_factory=time.monotonic)


@dataclass(frozen=True)
class CleanQuoteEvent:
    seq_no: int
    event_type: EventType
    symbol: str
    strike: float
    opt_type: Literal["CALL", "PUT"]
    arrival_mono: float
    bid: float | None = None
    ask: float | None = None
    last_price: float | None = None
    volume: int | None = None
    open_interest: int | None = None
    implied_volatility: float | None = None
    iv_timestamp: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    current_volume: float | None = None
    turnover: float | None = None
    impact_index: float | None = 0.0
    is_sweep: bool | None = False


@dataclass(frozen=True)
class CleanDepthEvent:
    seq_no: int
    symbol: str
    bid: float | None
    ask: float | None
    bid_size: int | None
    ask_size: int | None
    arrival_mono: float


@dataclass(frozen=True)
class CleanTradeEvent:
    seq_no: int
    symbol: str
    price: float
    volume: int
    direction_sign: float
    arrival_mono: float


def _infer_opt_type(symbol: str) -> Literal["CALL", "PUT"]:
    upper = symbol.upper()
    return "PUT" if "P" in upper.split(".")[0][-8:] else "CALL"


def _parse_quote_native(*, raw: RawMarketEvent, strike: float, seq_no: int) -> dict[str, Any] | None:
    out = _L0_RUST.l0_sanitize_parse_quote(
        str(raw.symbol),
        int(raw.event_type.value),
        float(strike),
        float(raw.arrival_mono),
        raw.payload,
        int(seq_no),
        float(time.monotonic()),
    )
    return None if out is None else dict(out)


def _parse_depth_native(*, raw: RawMarketEvent, seq_no: int) -> dict[str, Any] | None:
    out = _L0_RUST.l0_sanitize_parse_depth(
        str(raw.symbol),
        float(raw.arrival_mono),
        raw.payload,
        int(seq_no),
    )
    return None if out is None else dict(out)


class SanitizationPipeline:
    def parse_quote(
        self,
        raw: RawMarketEvent,
        strike: float,
    ) -> CleanQuoteEvent | None:
        native = _parse_quote_native(raw=raw, strike=strike, seq_no=_next_seq())
        if native is None:
            return None
        return CleanQuoteEvent(
            seq_no=int(native["seq_no"]),
            event_type=EventType(int(native["event_type"])),
            symbol=str(native["symbol"]),
            strike=float(native["strike"]),
            opt_type=str(native["opt_type"]),
            bid=native.get("bid"),
            ask=native.get("ask"),
            last_price=native.get("last_price"),
            volume=native.get("volume"),
            open_interest=native.get("open_interest"),
            implied_volatility=native.get("implied_volatility"),
            iv_timestamp=native.get("iv_timestamp"),
            delta=native.get("delta"),
            gamma=native.get("gamma"),
            theta=native.get("theta"),
            vega=native.get("vega"),
            current_volume=native.get("current_volume"),
            turnover=native.get("turnover"),
            arrival_mono=float(native["arrival_mono"]),
            impact_index=native.get("impact_index", 0.0),
            is_sweep=bool(native.get("is_sweep", False)),
        )

    def parse_depth(self, raw: RawMarketEvent) -> CleanDepthEvent | None:
        native = _parse_depth_native(raw=raw, seq_no=_next_seq())
        if native is None:
            return None
        return CleanDepthEvent(
            seq_no=int(native["seq_no"]),
            symbol=str(native["symbol"]),
            bid=native.get("bid"),
            ask=native.get("ask"),
            bid_size=native.get("bid_size"),
            ask_size=native.get("ask_size"),
            arrival_mono=float(native["arrival_mono"]),
        )

    def parse_rest_item(
        self,
        symbol: str,
        strike: float,
        item: Any,
        tier: str = "REST",
    ) -> CleanQuoteEvent | None:
        raw = RawMarketEvent(
            event_type=EventType.REST,
            symbol=symbol,
            payload=item,
            arrival_mono=time.monotonic(),
        )
        ev = self.parse_quote(raw, strike)
        if ev is None:
            logger.warning("[SANITIZATION] %s: REST item %s FAILED to parse", tier, symbol)
        else:
            logger.info(
                "[SANITIZATION] %s: Filtered REST item %s | iv=%s oi=%s",
                tier,
                symbol,
                ev.implied_volatility,
                ev.open_interest,
            )
        return ev


__all__ = [
    "CleanDepthEvent",
    "CleanQuoteEvent",
    "CleanTradeEvent",
    "EventType",
    "RawMarketEvent",
    "SanitizationPipeline",
    "_infer_opt_type",
]
