from __future__ import annotations

from l0_ingest.v2.normalize.bridges.rust_event_bridge import (
    dispatch_depth_event,
    dispatch_trade_event,
    parse_rust_event,
)
from l0_ingest.v2.normalize.pipeline import EventType


def _raw_event(**overrides):
    payload = {
        "symbol": "SPY.OPT.C",
        "seq_no": 1,
        "event_type": EventType.DEPTH.value,
        "bid": 1.2,
        "ask": 1.3,
        "last_price": 1.25,
        "volume": 20,
        "current_volume": 7,
        "turnover": 1250.5,
        "current_turnover": 300.2,
        "impact_index": 0.6,
        "is_sweep": False,
        "arrival_mono_ns": 1_000_000_000,
    }
    payload.update(overrides)
    return payload


def test_parse_rust_event_returns_none_for_unknown_symbol() -> None:
    event = parse_rust_event(_raw_event(), symbol_to_strike={})
    assert event is None


def test_parse_rust_event_returns_none_for_invalid_event_type() -> None:
    event = parse_rust_event(
        _raw_event(event_type=9999),
        symbol_to_strike={"SPY.OPT.C": 560.0},
    )
    assert event is None


def test_dispatch_depth_event_bridges_book_levels() -> None:
    clean = parse_rust_event(
        _raw_event(event_type=EventType.DEPTH.value),
        symbol_to_strike={"SPY.OPT.C": 560.0},
    )
    assert clean is not None

    calls = []
    dispatch_depth_event(clean, on_depth=lambda symbol, bids, asks: calls.append((symbol, bids, asks)))

    assert len(calls) == 1
    symbol, bids, asks = calls[0]
    assert symbol == "SPY.OPT.C"
    assert bids and asks


def test_parse_rust_event_maps_flow_fields() -> None:
    clean = parse_rust_event(
        _raw_event(event_type=EventType.QUOTE.value),
        symbol_to_strike={"SPY.OPT.C": 560.0},
    )
    assert clean is not None
    assert clean.current_volume == 7.0
    assert clean.turnover == 1250.5


def test_dispatch_trade_event_uses_price_delta_direction() -> None:
    calls = []
    cache: dict[str, float] = {}

    first = parse_rust_event(
        _raw_event(event_type=EventType.TRADE.value, last_price=1.25, impact_index=-0.5),
        symbol_to_strike={"SPY.OPT.C": 560.0},
    )
    second = parse_rust_event(
        _raw_event(event_type=EventType.TRADE.value, seq_no=2, last_price=1.28, impact_index=-0.5),
        symbol_to_strike={"SPY.OPT.C": 560.0},
    )
    assert first is not None and second is not None

    dispatch_trade_event(
        first,
        on_trade=lambda symbol, trades: calls.append((symbol, trades)),
        last_trade_price=cache,
    )
    dispatch_trade_event(
        second,
        on_trade=lambda symbol, trades: calls.append((symbol, trades)),
        last_trade_price=cache,
    )

    assert len(calls) == 2
    assert calls[0][1][0]["dir"] == -1
    assert calls[1][1][0]["dir"] == 1
