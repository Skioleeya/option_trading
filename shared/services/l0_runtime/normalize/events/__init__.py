"""Event processors for L0 V2 normalization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from shared.services.l0_runtime.native_loader import load_l0_rust
from shared.services.l0_runtime.normalize.pipeline import EventType

_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "_native_generated"
_L0_RUST = load_l0_rust(
    candidates=[
        _PACKAGE_DIR / "wave4" / "l0_rust.pyd",
        _PACKAGE_DIR / "l0_rust.pyd",
    ],
    module_suffix="l0_rust_wave4_events",
)

DepthCallback = Callable[[str, list[Any], list[Any]], None]
TradeCallback = Callable[[str, list[dict[str, Any]]], None]


def _extract_spy_spot_price(raw_event: Any) -> float | None:
    return _L0_RUST.l0_event_extract_spy_spot_price(raw_event)


def _normalize_trade_entries(trades: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in _L0_RUST.l0_event_normalize_trade_entries(trades)]


@dataclass
class ChainEventProcessor:
    store: Any
    sanitizer: Any
    entropy_filter: Any
    depth_engine: Any
    sub_mgr: Any

    def process_event(
        self,
        raw_event: Any,
        *,
        on_depth: DepthCallback | None = None,
        on_trade: TradeCallback | None = None,
    ) -> None:
        if self._handle_spy_spot_quote(raw_event):
            return
        if raw_event.event_type == EventType.QUOTE:
            self._handle_option_quote(raw_event)
            return
        if raw_event.event_type == EventType.DEPTH:
            self._handle_depth(raw_event, on_depth=on_depth)
            return
        if raw_event.event_type == EventType.TRADE:
            self._handle_trade(raw_event, on_trade=on_trade)

    def _handle_spy_spot_quote(self, raw_event: Any) -> bool:
        price = _extract_spy_spot_price(raw_event)
        if price is None:
            return False
        self.store.update_spot(price)
        return True

    def _handle_option_quote(self, raw_event: Any) -> None:
        strike = self.sub_mgr.symbol_to_strike.get(raw_event.symbol)
        if strike is None:
            return
        clean = self.sanitizer.parse_quote(raw_event, strike)
        if clean and self.entropy_filter.accept(clean.symbol, clean):
            self.store.apply_event(clean)
            if clean.open_interest is not None:
                self.store.apply_oi_smooth(clean.symbol, clean.open_interest)

    def _handle_depth(
        self,
        raw_event: Any,
        *,
        on_depth: DepthCallback | None = None,
    ) -> None:
        clean_depth = self.sanitizer.parse_depth(raw_event)
        if not clean_depth:
            return
        bids = getattr(raw_event.payload, "bids", [])
        asks = getattr(raw_event.payload, "asks", [])
        self.depth_engine.update_depth(clean_depth.symbol, bids, asks)
        self.store.apply_depth(clean_depth)
        if on_depth is not None:
            on_depth(clean_depth.symbol, bids, asks)

    def _handle_trade(
        self,
        raw_event: Any,
        *,
        on_trade: TradeCallback | None = None,
    ) -> None:
        trades = getattr(raw_event.payload, "trades", [])
        if not trades:
            return
        trade_dicts = _normalize_trade_entries(trades)
        self.depth_engine.update_trades(raw_event.symbol, trade_dicts)
        if on_trade is not None:
            on_trade(raw_event.symbol, trade_dicts)


class StateEventProcessor:
    def __init__(self, *, state: Any, sub_mgr: Any) -> None:
        self._state = state
        self._sub_mgr = sub_mgr

    def process(self, raw_event: Any, *, on_depth: Any = None, on_trade: Any = None) -> None:
        if self._handle_spy_spot_quote(raw_event):
            return
        if raw_event.event_type == EventType.QUOTE:
            self._handle_option_quote(raw_event)
            return
        if raw_event.event_type == EventType.DEPTH:
            self._handle_depth(raw_event, on_depth=on_depth)
            return
        if raw_event.event_type == EventType.TRADE:
            self._handle_trade(raw_event, on_trade=on_trade)

    def _handle_spy_spot_quote(self, raw_event: Any) -> bool:
        price = _extract_spy_spot_price(raw_event)
        if price is None:
            return False
        self._state.store.update_spot(price)
        return True

    def _handle_option_quote(self, raw_event: Any) -> None:
        strike = self._sub_mgr.resolve_strike(raw_event.symbol)
        if strike is None:
            return
        clean = self._state.sanitizer.parse_quote(raw_event, strike)
        if clean is None:
            return
        self._state.store.apply_event(clean)
        if clean.open_interest is not None:
            self._state.store.apply_oi_smooth(clean.symbol, clean.open_interest)

    def _handle_depth(self, raw_event: Any, *, on_depth: Any = None) -> None:
        clean_depth = self._state.sanitizer.parse_depth(raw_event)
        if clean_depth is None:
            return
        self._state.store.apply_depth(clean_depth)
        if on_depth is not None:
            on_depth(clean_depth.symbol, getattr(raw_event.payload, "bids", []), getattr(raw_event.payload, "asks", []))

    def _handle_trade(self, raw_event: Any, *, on_trade: Any = None) -> None:
        if on_trade is None:
            return
        trades = getattr(raw_event.payload, "trades", [])
        if not trades:
            return
        on_trade(raw_event.symbol, _normalize_trade_entries(trades))


__all__ = ["ChainEventProcessor", "StateEventProcessor"]
