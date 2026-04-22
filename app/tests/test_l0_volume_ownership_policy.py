from __future__ import annotations

import pytest

from shared.services.l0_runtime.normalize.pipeline import CleanQuoteEvent, EventType
from shared.services.l0_runtime.state.runtime import ChainStateStore


def _event(
    *,
    seq_no: int,
    event_type: EventType,
    volume: int | None = None,
    bid_volume: int | None = None,
    ask_volume: int | None = None,
    current_volume: float | None = None,
    turnover: float | None = None,
    last_price: float | None = 1.0,
    impact_index: float | None = 0.0,
    trade_type: str | None = None,
    trade_session: str | None = None,
    is_sweep: bool | None = None,
) -> CleanQuoteEvent:
    return CleanQuoteEvent(
        seq_no=seq_no,
        event_type=event_type,
        symbol="SPY260413C680000.US",
        strike=680.0,
        opt_type="CALL",
        arrival_mono=1.0,
        last_price=last_price,
        volume=volume,
        bid_volume=bid_volume,
        ask_volume=ask_volume,
        current_volume=current_volume,
        turnover=turnover,
        impact_index=impact_index,
        trade_type=trade_type,
        trade_session=trade_session,
        is_sweep=is_sweep,
    )


def _row(store: ChainStateStore) -> dict[str, object]:
    rows = store.get_snapshot()
    assert len(rows) == 1
    return rows[0]


def test_quote_day_volume_does_not_collapse_to_current_volume() -> None:
    store = ChainStateStore()
    accepted = store.apply_event(
        _event(
            seq_no=1,
            event_type=EventType.QUOTE,
            volume=441000,
            current_volume=1.0,
            turnover=45_029_661.0,
            last_price=7.5,
        )
    )
    assert accepted is True

    row = _row(store)
    assert int(float(row["volume"])) == 441000
    assert float(row["current_volume"]) == pytest.approx(1.0)
    assert store.diagnostics()["ws_volume_seen"] == 1


def test_trade_update_does_not_override_existing_day_volume() -> None:
    store = ChainStateStore()
    store.apply_event(
        _event(
            seq_no=1,
            event_type=EventType.QUOTE,
            volume=441000,
            current_volume=8.0,
            turnover=45_029_661.0,
            last_price=7.4,
        )
    )
    store.apply_event(
        _event(
            seq_no=2,
            event_type=EventType.TRADE,
            volume=1,
            current_volume=None,
            turnover=None,
            last_price=7.6,
        )
    )

    row = _row(store)
    assert int(float(row["volume"])) == 441000


def test_trade_first_must_not_lock_rest_day_volume_backfill() -> None:
    store = ChainStateStore()
    store.apply_event(
        _event(
            seq_no=1,
            event_type=EventType.TRADE,
            volume=1,
            current_volume=None,
            turnover=None,
            last_price=7.6,
        )
    )
    row_after_trade = _row(store)
    assert int(float(row_after_trade["volume"])) == 0
    assert store.diagnostics()["ws_volume_seen"] == 0

    accepted = store.apply_event(
        _event(
            seq_no=2,
            event_type=EventType.REST,
            volume=441000,
            current_volume=12.0,
            turnover=45_029_661.0,
            last_price=7.7,
        )
    )
    assert accepted is True
    row_after_rest = _row(store)
    assert int(float(row_after_rest["volume"])) == 441000


def test_depth_and_trade_fields_persist_to_chain_snapshot() -> None:
    store = ChainStateStore()
    store.apply_event(
        _event(
            seq_no=1,
            event_type=EventType.DEPTH,
            bid_volume=410,
            ask_volume=230,
            impact_index=1.75,
            last_price=None,
        )
    )
    store.apply_event(
        _event(
            seq_no=2,
            event_type=EventType.TRADE,
            volume=3,
            trade_type="Late Print",
            trade_session="RTH",
            is_sweep=True,
            last_price=7.8,
        )
    )
    row = _row(store)
    assert int(float(row["bid_volume"])) == 410
    assert int(float(row["ask_volume"])) == 230
    assert float(row["impact_index"]) == pytest.approx(1.75)
    assert row["trade_type"] == "Late Print"
    assert row["trade_session"] == "RTH"
    assert bool(row["is_sweep"]) is True
