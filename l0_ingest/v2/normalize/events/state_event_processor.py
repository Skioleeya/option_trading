"""Event pipeline that updates L0 state and forwards normalized callbacks."""

from __future__ import annotations

import time
from typing import Any

from longport.openapi import TradeDirection

from l0_ingest.v2.normalize.pipeline import EventType


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
        if raw_event.symbol != "SPY.US" or raw_event.event_type != EventType.QUOTE:
            return False
        try:
            price = float(getattr(raw_event.payload, "last_done", 0.0) or 0.0)
        except (TypeError, ValueError):
            price = 0.0
        if price > 0.0:
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
        on_trade(raw_event.symbol, [self._normalize_trade(trade) for trade in trades])

    def _normalize_trade(self, trade: Any) -> dict[str, Any]:
        raw_dir = getattr(trade, "direction", 0)
        if raw_dir == TradeDirection.Up or str(raw_dir) in {"2", "TradeDirection.Up"} or raw_dir == 2:
            direction = 1
        elif raw_dir == TradeDirection.Down or str(raw_dir) in {"1", "TradeDirection.Down"} or raw_dir == 1:
            direction = -1
        else:
            direction = 0
        return {
            "price": self._safe_float(getattr(trade, "price", 0.0)),
            "vol": self._safe_float(getattr(trade, "volume", 0.0)),
            "volume": self._safe_float(getattr(trade, "volume", 0.0)),
            "timestamp": self._to_ts_int(getattr(trade, "timestamp", 0)),
            "dir": direction,
            "direction": direction,
            "trade_type": self._safe_int(getattr(trade, "trade_type", 0)),
        }

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _to_ts_int(value: Any) -> int:
        if hasattr(value, "timestamp"):
            return int(value.timestamp())
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return int(time.time())
