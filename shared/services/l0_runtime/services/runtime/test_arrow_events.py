from __future__ import annotations

from types import SimpleNamespace

from shared.services.l0_runtime.normalize.pipeline import EventType
from shared.services.l0_runtime.services.runtime import arrow_events


class _FakeStore:
    def __init__(self) -> None:
        self.spot_updates: list[float] = []
        self.applied: list[object] = []

    def update_spot_from_source(self, price: float) -> None:
        self.spot_updates.append(price)

    def apply_event(self, event: object) -> None:
        self.applied.append(event)


def test_extract_spy_spot_from_arrow_event_only_accepts_spy_depth_midpoint() -> None:
    assert (
        arrow_events.extract_spy_spot_from_arrow_event(
            {"symbol": "SPY.US", "event_type": EventType.DEPTH.value, "bid": 707.14, "ask": 707.16}
        )
        == 707.15
    )
    assert (
        arrow_events.extract_spy_spot_from_arrow_event(
            {"symbol": "SPY260421C00707000.US", "event_type": EventType.DEPTH.value, "bid": 4.1, "ask": 4.3}
        )
        is None
    )
    assert (
        arrow_events.extract_spy_spot_from_arrow_event(
            {"symbol": "SPY.US", "event_type": EventType.QUOTE.value, "last_price": 707.15}
        )
        is None
    )


def test_handle_arrow_event_updates_spy_spot_before_option_parse(monkeypatch) -> None:
    store = _FakeStore()
    parse_calls: list[dict[str, object]] = []

    def _fake_parse(event: dict[str, object], *, symbol_to_strike: dict[str, float]) -> object | None:
        parse_calls.append(dict(event))
        return None

    monkeypatch.setattr(arrow_events, "parse_market_event", _fake_parse)

    arrow_events.handle_arrow_event(
        {"symbol": "SPY.US", "event_type": EventType.DEPTH.value, "bid": 707.14, "ask": 707.16},
        store=store,
        symbol_to_strike={},
        on_depth=None,
        on_trade=None,
        last_trade_price={},
        last_trade_direction={},
        top_of_book={},
    )

    assert store.spot_updates == [707.15]
    assert store.applied == []
    assert parse_calls == []


def test_handle_arrow_event_applies_option_rows_to_store(monkeypatch) -> None:
    store = _FakeStore()
    clean = SimpleNamespace(
        symbol="SPY260421C00707000.US",
        event_type=EventType.QUOTE,
        bid=1.0,
        ask=1.1,
    )

    monkeypatch.setattr(arrow_events, "parse_market_event", lambda event, *, symbol_to_strike: clean)

    arrow_events.handle_arrow_event(
        {"symbol": "SPY260421C00707000.US", "event_type": EventType.QUOTE.value, "last_price": 4.2},
        store=store,
        symbol_to_strike={"SPY260421C00707000.US": 707.0},
        on_depth=None,
        on_trade=None,
        last_trade_price={},
        last_trade_direction={},
        top_of_book={},
    )

    assert store.spot_updates == []
    assert store.applied == [clean]
