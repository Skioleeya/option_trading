"""L0 chain event processor.

Owns quote/depth/trade event normalization so OptionChainBuilder can stay focused on
runtime lifecycle and orchestration wiring.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from longport.openapi import TradeDirection

from l0_ingest.feeds.sanitization import EventType

DepthCallback = Callable[[str, list[Any], list[Any]], None]
TradeCallback = Callable[[str, list[dict[str, Any]]], None]


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
        if raw_event.symbol != "SPY.US" or raw_event.event_type != EventType.QUOTE:
            return False
        price = self._safe_float(getattr(raw_event.payload, "last_done", 0.0), default=0.0)
        if price > 0.0:
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

        trade_dicts = [self._normalize_trade_entry(trade) for trade in trades]
        self.depth_engine.update_trades(raw_event.symbol, trade_dicts)
        if on_trade is not None:
            on_trade(raw_event.symbol, trade_dicts)

    @staticmethod
    def _normalize_trade_entry(trade: Any) -> dict[str, Any]:
        raw_dir = (
            getattr(trade, "direction", 0)
            if not isinstance(trade, dict)
            else trade.get("dir", trade.get("direction", 0))
        )
        dir_sign = ChainEventProcessor._direction_sign(raw_dir)

        if isinstance(trade, dict):
            trade_dict = dict(trade)
            volume = ChainEventProcessor._safe_float(
                trade_dict.get("vol", 0.0) or trade_dict.get("volume", 0.0),
                default=0.0,
            )
            trade_dict["vol"] = volume
            trade_dict["volume"] = volume
            trade_dict["dir"] = dir_sign
            trade_dict["direction"] = dir_sign
            return trade_dict

        volume = ChainEventProcessor._safe_float(getattr(trade, "volume", 0), default=0.0)
        return {
            "price": ChainEventProcessor._safe_float(getattr(trade, "price", 0.0), default=0.0),
            "vol": volume,
            "volume": volume,
            "timestamp": ChainEventProcessor._to_ts_int(getattr(trade, "timestamp", 0)),
            "dir": dir_sign,
            "direction": dir_sign,
            "trade_type": ChainEventProcessor._safe_int(getattr(trade, "trade_type", 0), default=0),
        }

    @staticmethod
    def _direction_sign(raw_dir: Any) -> int:
        if raw_dir == TradeDirection.Up or str(raw_dir) == "2" or raw_dir == 2:
            return 1
        if raw_dir == TradeDirection.Down or str(raw_dir) == "1" or raw_dir == 1:
            return -1
        return 0

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_ts_int(value: Any) -> int:
        if hasattr(value, "timestamp"):
            return int(value.timestamp())
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return int(time.time())
