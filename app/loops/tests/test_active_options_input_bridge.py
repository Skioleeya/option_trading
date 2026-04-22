from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa
import pytest

from app.loops.compute_loop import _publish_active_options_input


@dataclass
class _Agg:
    atm_iv: float


class _L1Snapshot:
    def __init__(self) -> None:
        self.chain = pa.record_batch(
            {
                "symbol": ["SPY260406C656000.US"],
                "option_type": ["CALL"],
                "strike": [656.0],
                "computed_gamma": [0.123],
                "computed_vanna": [0.456],
                "computed_iv": [0.1458],
                "computed_delta": [0.5],
            }
        )
        self.spot = 655.83
        self.aggregates = _Agg(atm_iv=0.1458)
        self.ttm_seconds = 3600.0
        self.version = 1485


class _EmptyL1Snapshot:
    def __init__(self) -> None:
        self.chain = None
        self.spot = 655.83
        self.aggregates = _Agg(atm_iv=0.1458)
        self.ttm_seconds = 3600.0
        self.version = 1485


def _l0_snapshot() -> dict[str, object]:
    return {
        "version": 1485,
        "spot": 655.83,
        "as_of_utc": "2026-04-03T16:01:13.198375+00:00",
        "chain": [
            {
                "symbol": "SPY260406C656000.US",
                "option_type": "CALL",
                "strike": 656.0,
                "volume": 25456.0,
                "turnover": 10_543_674.0,
            }
        ],
    }


def test_publish_active_options_input_uses_enriched_snapshot_chain_and_atm_iv() -> None:
    snap = _publish_active_options_input(l0_snapshot=_l0_snapshot(), l1_snapshot=_L1Snapshot())
    assert snap.valid is True
    assert snap.source_version == 1485
    assert snap.atm_iv == pytest.approx(0.1458)
    assert len(snap.chain) == 1
    row = snap.chain[0]
    assert row["gamma"] == pytest.approx(0.123)
    assert row["vanna"] == pytest.approx(0.456)
    assert row["implied_volatility"] == pytest.approx(0.1458)
    assert row["delta"] == pytest.approx(0.5)


def test_publish_active_options_input_accepts_dict_chain_elements_contract() -> None:
    l1_snapshot = {
        "version": 1485,
        "spot": 655.83,
        "atm_iv": 0.1458,
        "chain_elements": [
            {
                "symbol": "SPY260406C656000.US",
                "option_type": "CALL",
                "strike": 656.0,
                "computed_gamma": 0.321,
                "computed_vanna": 0.654,
                "computed_iv": 0.211,
                "computed_delta": 0.25,
            }
        ],
    }
    snap = _publish_active_options_input(l0_snapshot=_l0_snapshot(), l1_snapshot=l1_snapshot)
    assert snap.valid is True
    assert snap.atm_iv == pytest.approx(0.1458)
    row = snap.chain[0]
    assert row["gamma"] == pytest.approx(0.321)
    assert row["vanna"] == pytest.approx(0.654)
    assert row["implied_volatility"] == pytest.approx(0.211)
    assert row["delta"] == pytest.approx(0.25)


def test_publish_active_options_input_treats_none_chain_as_empty_input() -> None:
    snap = _publish_active_options_input(
        l0_snapshot=_l0_snapshot(),
        l1_snapshot=_EmptyL1Snapshot(),
    )
    assert snap.valid is True
    assert snap.source_version == 1485
    assert snap.atm_iv == pytest.approx(0.1458)
    assert len(snap.chain) == 1
