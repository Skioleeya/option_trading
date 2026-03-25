from __future__ import annotations

from types import SimpleNamespace

import pyarrow as pa

from shared.services.l0_runtime import OptionChainBuilder
from shared.services.l0_runtime.contracts import CallbackHooks
from shared.services.l0_runtime.normalize.pipeline import EventType


class _StoreStub:
    def __init__(self) -> None:
        self.events = []

    def apply_event(self, event):
        self.events.append(event)
        return True


def _build_builder() -> OptionChainBuilder:
    builder = OptionChainBuilder.__new__(OptionChainBuilder)
    builder._state = SimpleNamespace(store=_StoreStub())
    builder._services = SimpleNamespace(sub_mgr=SimpleNamespace(symbol_to_strike={"SPY.OPT.C": 560.0}))
    builder._last_trade_price = {}
    builder._last_arrow_batch_id = 0
    builder._transport_status = "DISCONNECTED"
    builder._transport_error = None
    builder._hooks = CallbackHooks()
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

    assert len(builder._state.store.events) == 1
    assert builder._state.store.events[0].event_type == EventType.DEPTH
    assert builder._state.store.events[0].turnover == 5200.0
    assert builder._state.store.events[0].current_volume == 12.0
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
    assert builder._state.store.events[0].turnover == 2400.0
    assert builder._state.store.events[0].current_volume == 6.0


def test_arrow_batch_bridges_events_and_tracks_batch_id() -> None:
    builder = _build_builder()

    batch = pa.record_batch(
        [
            pa.array(["SPY.OPT.C", "SPY.OPT.C"]),
            pa.array([20, 21], type=pa.uint64()),
            pa.array([EventType.DEPTH.value, EventType.TRADE.value], type=pa.uint8()),
            pa.array([1.2, None], type=pa.float64()),
            pa.array([1.3, None], type=pa.float64()),
            pa.array([None, 1.26], type=pa.float64()),
            pa.array([50, 20], type=pa.uint64()),
            pa.array([12, 6], type=pa.uint64()),
            pa.array([5200.0, 2400.0], type=pa.float64()),
            pa.array([450.0, 180.0], type=pa.float64()),
            pa.array([0.8, -0.5], type=pa.float64()),
            pa.array([False, True], type=pa.bool_()),
            pa.array([1_000_000_000, 2_000_000_000], type=pa.uint64()),
            pa.array([7, 7], type=pa.uint64()),
        ],
        names=[
            "symbol",
            "seq_no",
            "event_type",
            "bid",
            "ask",
            "last_price",
            "volume",
            "current_volume",
            "turnover",
            "current_turnover",
            "impact_index",
            "is_sweep",
            "arrival_mono_ns",
            "batch_id",
        ],
    )

    builder._record_arrow_batch(batch)
    builder._handle_arrow_batch(batch)

    assert builder._last_arrow_batch_id == 7
    assert builder._transport_status == "OK"
    assert len(builder._state.store.events) == 2
    assert builder._state.store.events[0].event_type == EventType.DEPTH
    assert builder._state.store.events[1].event_type == EventType.TRADE

