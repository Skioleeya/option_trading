from __future__ import annotations

from types import SimpleNamespace

import pytest

from l0_ingest.feeds.longport_option_contracts import (
    build_calc_index_contract,
    build_option_quote_contract,
)


def test_build_option_quote_contract_normalizes_raw_and_nested_fields() -> None:
    row = SimpleNamespace(
        symbol="SPY260101C560000.US",
        implied_volatility="20.51",
        open_interest=42,
        expiry_date="20260101",
        strike_price="560",
        contract_multiplier="100",
        contract_type="A",
        contract_size="100",
        direction="C",
        historical_volatility="18.40",
        underlying_symbol="SPY.US",
    )

    contract = build_option_quote_contract(row)

    assert contract.option_extend is not None
    assert contract.option_extend.implied_volatility == "20.51"
    assert contract.implied_volatility_raw == "20.51"
    assert contract.implied_volatility_decimal == pytest.approx(0.2051)
    assert contract.historical_volatility_decimal == pytest.approx(0.184)
    assert contract.expiry_date == "2026-01-01"
    assert contract.expiry_date_iso == "2026-01-01"


def test_build_calc_index_contract_handles_short_date_and_invalid_values() -> None:
    row = SimpleNamespace(
        symbol="OPT1",
        expiry_date="260101",
        strike_price_raw="560",
        implied_volatility_raw="bad",
        delta="oops",
    )

    contract = build_calc_index_contract(row)

    assert contract.expiry_date == "2026-01-01"
    assert contract.implied_volatility_decimal is None
    assert contract.delta is None
    assert contract.strike_price == pytest.approx(560.0)
