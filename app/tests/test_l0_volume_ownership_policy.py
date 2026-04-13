from __future__ import annotations

import pytest

from shared.services.l0_runtime.normalize.pipeline import CleanQuoteEvent, EventType
from shared.services.l0_runtime.state.runtime import ChainStateStore


def _event(
    *,
    seq_no: int,
    event_type: EventType,
    volume: int | None = None,
    current_volume: float | None = None,
    turnover: float | None = None,
    last_price: float | None = 1.0,
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
        current_volume=current_volume,
        turnover=turnover,
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
