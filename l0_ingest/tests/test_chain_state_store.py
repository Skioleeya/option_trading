from __future__ import annotations

import time

from l0_ingest.feeds.chain_state_store import ChainStateStore
from l0_ingest.feeds.sanitization import CleanDepthEvent, CleanQuoteEvent, EventType


def _quote_event(
    seq_no: int,
    *,
    symbol: str = "SPY260306C560000.US",
    bid: float | None = 1.0,
    ask: float | None = 1.1,
    last_price: float | None = 1.05,
) -> CleanQuoteEvent:
    return CleanQuoteEvent(
        seq_no=seq_no,
        event_type=EventType.QUOTE,
        symbol=symbol,
        strike=560.0,
        opt_type="CALL",
        arrival_mono=time.monotonic(),
        bid=bid,
        ask=ask,
        last_price=last_price,
        volume=100,
        open_interest=200,
    )


def _depth_event(
    seq_no: int,
    *,
    symbol: str = "SPY260306C560000.US",
    bid: float | None = 1.2,
    ask: float | None = 1.3,
) -> CleanDepthEvent:
    return CleanDepthEvent(
        seq_no=seq_no,
        symbol=symbol,
        bid=bid,
        ask=ask,
        bid_size=10,
        ask_size=12,
        arrival_mono=time.monotonic(),
    )


def test_version_starts_at_zero() -> None:
    store = ChainStateStore()
    assert store.version == 0


def test_update_spot_bumps_version_once_for_value_change() -> None:
    store = ChainStateStore()
    store.update_spot(560.0)
    first = store.version
    store.update_spot(560.0)
    second = store.version
    store.update_spot(561.0)
    third = store.version

    assert first == 1
    assert second == 1
    assert third == 2


def test_apply_event_bumps_version_on_new_or_changed_entry() -> None:
    store = ChainStateStore()

    assert store.apply_event(_quote_event(1)) is True
    v1 = store.version

    # Same values with newer seq should not bump version.
    assert store.apply_event(_quote_event(2)) is True
    v2 = store.version

    # Changed bid should bump version.
    assert store.apply_event(_quote_event(3, bid=1.4)) is True
    v3 = store.version

    assert v1 == 1
    assert v2 == 1
    assert v3 == 2


def test_stale_rest_event_does_not_bump_version() -> None:
    store = ChainStateStore()

    assert store.apply_event(_quote_event(10)) is True
    before = store.version

    stale_rest = CleanQuoteEvent(
        seq_no=9,
        event_type=EventType.REST,
        symbol="SPY260306C560000.US",
        strike=560.0,
        opt_type="CALL",
        arrival_mono=time.monotonic(),
        implied_volatility=0.2,
    )
    assert store.apply_event(stale_rest) is False
    assert store.version == before


def test_apply_depth_bumps_version_on_actual_change() -> None:
    store = ChainStateStore()
    store.apply_event(_quote_event(1))
    before = store.version

    store.apply_depth(_depth_event(2, bid=1.2, ask=1.3))
    changed = store.version

    store.apply_depth(_depth_event(3, bid=1.2, ask=1.3))
    unchanged = store.version

    assert changed == before + 1
    assert unchanged == changed
