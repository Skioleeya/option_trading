from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shared.services.active_options.input_adapter import (
    ACTIVE_OPTIONS_INPUT_REASON_EMPTY_CHAIN,
    ACTIVE_OPTIONS_INPUT_REASON_INVALID_SPOT,
    build_active_options_input_snapshot,
)


@dataclass
class _FakeAggregates:
    atm_iv: float = 0.0


class _FakeL1Snapshot:
    def __init__(
        self,
        *,
        chain: list[dict[str, Any]],
        spot: float,
        version: int,
        atm_iv: float,
        ttm_seconds: float = 900.0,
    ) -> None:
        self.chain = chain
        self.spot = spot
        self.version = version
        self.aggregates = _FakeAggregates(atm_iv=atm_iv)
        self.ttm_seconds = ttm_seconds


def test_adapter_prefers_l1_computed_fields_over_l0() -> None:
    l0_snapshot = {
        "spot": 560.0,
        "version": 100,
        "as_of_utc": "2026-03-19T14:00:00+00:00",
        "chain": [
            {
                "symbol": "SPY260319C00560000",
                "option_type": "CALL",
                "strike": 560.0,
                "gamma": 0.0,
                "vanna": 0.0,
                "implied_volatility": 0.15,
            }
        ],
    }
    l1_snapshot = _FakeL1Snapshot(
        chain=[
            {
                "symbol": "SPY260319C00560000",
                "option_type": "CALL",
                "strike": 560.0,
                "computed_gamma": 0.012,
                "computed_vanna": 0.034,
                "computed_iv": 0.22,
                "computed_delta": 0.48,
            }
        ],
        spot=561.0,
        version=101,
        atm_iv=0.21,
        ttm_seconds=1200.0,
    )

    adapted = build_active_options_input_snapshot(
        l0_snapshot=l0_snapshot,
        l1_snapshot=l1_snapshot,
    )

    assert adapted.valid is True
    assert adapted.invalid_reason is None
    assert adapted.spot == 561.0
    assert adapted.atm_iv == 0.21
    assert adapted.source_version == 101
    row = adapted.chain[0]
    assert row["gamma"] == 0.012
    assert row["vanna"] == 0.034
    assert row["implied_volatility"] == 0.22
    assert row["delta"] == 0.48


def test_adapter_falls_back_to_l0_chain_when_l1_chain_unavailable() -> None:
    l0_snapshot = {
        "spot": 560.0,
        "version": 200,
        "as_of_utc": "2026-03-19T14:00:00+00:00",
        "chain": [{"symbol": "SPY260319P00559000", "option_type": "PUT", "strike": 559.0, "volume": 100}],
    }
    l1_snapshot = _FakeL1Snapshot(chain=[], spot=0.0, version=0, atm_iv=0.0)

    adapted = build_active_options_input_snapshot(
        l0_snapshot=l0_snapshot,
        l1_snapshot=l1_snapshot,
    )

    assert adapted.valid is True
    assert adapted.invalid_reason is None
    assert adapted.source_version == 200
    assert len(adapted.chain) == 1
    assert adapted.chain[0]["symbol"] == "SPY260319P00559000"


def test_adapter_marks_invalid_when_chain_empty() -> None:
    adapted = build_active_options_input_snapshot(
        l0_snapshot={"spot": 560.0, "version": 1, "chain": []},
        l1_snapshot=_FakeL1Snapshot(chain=[], spot=560.0, version=1, atm_iv=0.2),
    )
    assert adapted.valid is False
    assert adapted.invalid_reason == ACTIVE_OPTIONS_INPUT_REASON_EMPTY_CHAIN


def test_adapter_marks_invalid_when_spot_non_positive() -> None:
    adapted = build_active_options_input_snapshot(
        l0_snapshot={"spot": 0.0, "version": 1, "chain": [{"symbol": "SPY", "strike": 560.0}]},
        l1_snapshot=_FakeL1Snapshot(
            chain=[{"symbol": "SPY", "strike": 560.0, "option_type": "CALL"}],
            spot=0.0,
            version=1,
            atm_iv=0.2,
        ),
    )
    assert adapted.valid is False
    assert adapted.invalid_reason == ACTIVE_OPTIONS_INPUT_REASON_INVALID_SPOT


def test_adapter_logs_l1_field_promotion_trace(caplog) -> None:
    l0_snapshot = {
        "spot": 560.0,
        "version": 100,
        "as_of_utc": "2026-03-19T14:00:00+00:00",
        "chain": [{"symbol": "SPY260319C00560000", "option_type": "CALL", "strike": 560.0}],
    }
    l1_snapshot = _FakeL1Snapshot(
        chain=[{
            "symbol": "SPY260319C00560000",
            "option_type": "CALL",
            "strike": 560.0,
            "computed_gamma": 0.012,
            "computed_vanna": 0.034,
            "computed_iv": 0.22,
            "computed_delta": 0.48,
        }],
        spot=561.0,
        version=101,
        atm_iv=0.21,
    )

    with caplog.at_level("DEBUG"):
        build_active_options_input_snapshot(
            l0_snapshot=l0_snapshot,
            l1_snapshot=l1_snapshot,
        )

    assert "[ActiveOptionsInput]" in caplog.text
    assert "source_version=101" in caplog.text
    assert "promoted_gamma=1" in caplog.text
    assert "promoted_vanna=1" in caplog.text
    assert "promoted_iv=1" in caplog.text
    assert "promoted_delta=1" in caplog.text
