from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from l0_ingest.feeds.chain_event_processor import ChainEventProcessor
from l0_ingest.feeds.sanitization import EventType


class _StoreStub:
    def __init__(self) -> None:
        self.spot_updates: list[float] = []
        self.applied_events: list[Any] = []
        self.oi_smooth_updates: list[tuple[str, Any]] = []
        self.applied_depth: list[Any] = []

    def update_spot(self, price: float) -> None:
        self.spot_updates.append(price)

    def apply_event(self, event: Any) -> None:
        self.applied_events.append(event)

    def apply_oi_smooth(self, symbol: str, open_interest: Any) -> None:
        self.oi_smooth_updates.append((symbol, open_interest))

    def apply_depth(self, depth: Any) -> None:
        self.applied_depth.append(depth)


class _SanitizerStub:
    def __init__(self) -> None:
        self.quote_result: Any = None
        self.depth_result: Any = None

    def parse_quote(self, _raw_event: Any, _strike: float) -> Any:
        return self.quote_result

    def parse_depth(self, _raw_event: Any) -> Any:
        return self.depth_result


class _EntropyFilterStub:
    def __init__(self, accepted: bool = True) -> None:
        self.accepted = accepted

    def accept(self, _symbol: str, _event: Any) -> bool:
        return self.accepted


class _DepthEngineStub:
    def __init__(self) -> None:
        self.depth_calls: list[tuple[str, list[Any], list[Any]]] = []
        self.trade_calls: list[tuple[str, list[dict[str, Any]]]] = []

    def update_depth(self, symbol: str, bids: list[Any], asks: list[Any]) -> None:
        self.depth_calls.append((symbol, bids, asks))

    def update_trades(self, symbol: str, trades: list[dict[str, Any]]) -> None:
        self.trade_calls.append((symbol, trades))


class _SubMgrStub:
    def __init__(self, symbol_to_strike: dict[str, float] | None = None) -> None:
        self.symbol_to_strike = symbol_to_strike or {}


def _build_processor() -> tuple[ChainEventProcessor, _StoreStub, _SanitizerStub, _DepthEngineStub]:
    store = _StoreStub()
    sanitizer = _SanitizerStub()
    depth_engine = _DepthEngineStub()
    processor = ChainEventProcessor(
        store=store,
        sanitizer=sanitizer,
        entropy_filter=_EntropyFilterStub(accepted=True),
        depth_engine=depth_engine,
        sub_mgr=_SubMgrStub(symbol_to_strike={"SPY.OPT.C": 560.0}),
    )
    return processor, store, sanitizer, depth_engine


def test_process_event_updates_spy_spot_quote() -> None:
    processor, store, _, _ = _build_processor()
    event = SimpleNamespace(
        symbol="SPY.US",
        event_type=EventType.QUOTE,
        payload=SimpleNamespace(last_done=561.25),
    )

    processor.process_event(event)

    assert store.spot_updates == [561.25]
    assert store.applied_events == []


def test_process_event_applies_option_quote_and_oi_smoothing() -> None:
    processor, store, sanitizer, _ = _build_processor()
    sanitizer.quote_result = SimpleNamespace(symbol="SPY.OPT.C", open_interest=1234)
    event = SimpleNamespace(
        symbol="SPY.OPT.C",
        event_type=EventType.QUOTE,
        payload=SimpleNamespace(last_done=1.0),
    )

    processor.process_event(event)

    assert len(store.applied_events) == 1
    assert store.oi_smooth_updates == [("SPY.OPT.C", 1234)]


def test_process_event_handles_depth_and_callback() -> None:
    processor, store, sanitizer, depth_engine = _build_processor()
    sanitizer.depth_result = SimpleNamespace(symbol="SPY.OPT.C")
    depth_callback_calls: list[tuple[str, list[Any], list[Any]]] = []
    event = SimpleNamespace(
        symbol="SPY.OPT.C",
        event_type=EventType.DEPTH,
        payload=SimpleNamespace(bids=[{"p": 1.0}], asks=[{"p": 2.0}]),
    )

    processor.process_event(
        event,
        on_depth=lambda symbol, bids, asks: depth_callback_calls.append((symbol, bids, asks)),
    )

    assert len(depth_engine.depth_calls) == 1
    assert store.applied_depth and store.applied_depth[0].symbol == "SPY.OPT.C"
    assert depth_callback_calls and depth_callback_calls[0][0] == "SPY.OPT.C"


def test_process_event_normalizes_trade_payload() -> None:
    processor, _, _, depth_engine = _build_processor()
    trade_callback_calls: list[tuple[str, list[dict[str, Any]]]] = []
    trade_obj = SimpleNamespace(
        price=1.2,
        volume="4",
        timestamp=1700000000,
        direction=1,
        trade_type=2,
    )
    event = SimpleNamespace(
        symbol="SPY.OPT.C",
        event_type=EventType.TRADE,
        payload=SimpleNamespace(
            trades=[
                {"price": 1.1, "vol": 2.0, "direction": "2", "trade_type": "3"},
                trade_obj,
            ]
        ),
    )

    processor.process_event(
        event,
        on_trade=lambda symbol, trades: trade_callback_calls.append((symbol, trades)),
    )

    assert len(depth_engine.trade_calls) == 1
    symbol, normalized = depth_engine.trade_calls[0]
    assert symbol == "SPY.OPT.C"
    assert normalized[0]["dir"] == 1
    assert normalized[0]["volume"] == 2.0
    assert normalized[1]["dir"] == -1
    assert normalized[1]["volume"] == 4.0
    assert trade_callback_calls and trade_callback_calls[0][0] == "SPY.OPT.C"
