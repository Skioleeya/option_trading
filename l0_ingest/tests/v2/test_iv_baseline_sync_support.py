from __future__ import annotations

from dataclasses import dataclass

from l0_ingest.v2.services.sync.support import (
    clamp_subscription_cap,
    parse_implied_volatility,
    parse_open_interest,
    safe_batch_size,
    split_sync_chunks,
)


@dataclass
class _Item:
    implied_volatility_decimal: float | None = None
    implied_volatility: float | None = None
    open_interest: int | None = None


def test_cap_and_batch_clamps() -> None:
    assert clamp_subscription_cap(0) == 1
    assert clamp_subscription_cap(9999) == 500
    assert safe_batch_size(0) == 1
    assert safe_batch_size(999) == 50


def test_parse_iv_and_oi() -> None:
    normalized = _Item(implied_volatility_decimal=0.24, open_interest=123)
    assert parse_implied_volatility(normalized) == 0.24
    assert parse_open_interest(normalized) == 123

    legacy_pct = _Item(implied_volatility=24.0, open_interest=10)
    assert parse_implied_volatility(legacy_pct) == 0.24
    assert parse_open_interest(legacy_pct) == 10


def test_split_sync_chunks_keeps_order() -> None:
    symbols = ["A", "B", "C", "D", "E"]
    chunks = split_sync_chunks(symbols)
    assert chunks[0] == ["A", "B"]
    assert chunks[1] == ["C", "D", "E"]
