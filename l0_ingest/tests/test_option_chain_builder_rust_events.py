from __future__ import annotations

from types import SimpleNamespace

from l0_ingest.feeds.option_chain_builder import OptionChainBuilder
from l0_ingest.feeds.sanitization import EventType


class _StoreStub:
    def __init__(self) -> None:
        self.events = []

    def apply_event(self, event):
        self.events.append(event)
        return True


def _build_builder() -> OptionChainBuilder:
    builder = OptionChainBuilder.__new__(OptionChainBuilder)
    builder._store = _StoreStub()
    builder._sub_mgr = SimpleNamespace(symbol_to_strike={"SPY.OPT.C": 560.0})
    builder._last_trade_price = {}
    return builder


def test_rust_depth_event_bridges_to_on_depth() -> None:
    builder = _build_builder()
    depth_calls = []
    builder.on_depth = lambda symbol, bids, asks: depth_calls.append((symbol, bids, asks))

    builder._handle_rust_event(
        {
            "symbol": "SPY.OPT.C",
            "seq_no": 10,
            "event_type": EventType.DEPTH.value,
            "bid": 1.2,
            "ask": 1.3,
            "last_price": 1.25,
            "volume": 50,
            "current_volume": 12,
            "turnover": 5200.0,
            "current_turnover": 450.0,
            "impact_index": 0.8,
            "is_sweep": False,
            "arrival_mono_ns": 1_000_000_000,
        }
    )

    assert len(builder._store.events) == 1
    assert builder._store.events[0].event_type == EventType.DEPTH
    assert builder._store.events[0].turnover == 5200.0
    assert builder._store.events[0].current_volume == 12.0
    assert len(depth_calls) == 1
    assert depth_calls[0][0] == "SPY.OPT.C"
    assert depth_calls[0][1]
    assert depth_calls[0][2]


def test_rust_trade_event_bridges_to_on_trade_with_direction() -> None:
    builder = _build_builder()
    trade_calls = []
    builder.on_trade = lambda symbol, trades: trade_calls.append((symbol, trades))

    builder._handle_rust_event(
        {
            "symbol": "SPY.OPT.C",
            "seq_no": 11,
            "event_type": EventType.TRADE.value,
            "bid": 1.2,
            "ask": 1.3,
            "last_price": 1.26,
            "volume": 20,
            "current_volume": 6,
            "turnover": 2400.0,
            "current_turnover": 180.0,
            "impact_index": -0.5,
            "is_sweep": True,
            "arrival_mono_ns": 2_000_000_000,
        }
    )

    assert len(trade_calls) == 1
    symbol, trades = trade_calls[0]
    assert symbol == "SPY.OPT.C"
    assert len(trades) == 1
    assert trades[0]["dir"] == -1
    assert trades[0]["vol"] == 20.0
    assert builder._store.events[0].turnover == 2400.0
    assert builder._store.events[0].current_volume == 6.0
