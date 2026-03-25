from __future__ import annotations

import numpy as np

from l1_compute.iv.iv_resolver import IVSource, ResolvedIV
from l1_compute.observability.atm_iv_context import build_atm_iv_context


def test_build_atm_iv_context_reports_nearest_valid_contract() -> None:
    context = build_atm_iv_context(
        spot=600.0,
        symbols=["SPY.C595", "SPY.C600", "SPY.P605"],
        strikes=np.array([595.0, 600.0, 605.0]),
        valid_mask=np.array([True, True, False]),
        resolved_ivs={
            "SPY.C595": ResolvedIV(value=0.21, source=IVSource.REST, raw_value=0.20, confidence=0.8),
            "SPY.C600": ResolvedIV(value=0.24, source=IVSource.WS, raw_value=0.24, confidence=1.0),
        },
    )

    assert context["atm_symbol"] == "SPY.C600"
    assert context["atm_strike"] == 600.0
    assert context["atm_distance"] == 0.0
    assert context["atm_iv"] == 0.24
    assert context["raw_iv"] == 0.24
    assert context["iv_source"] == "ws"
    assert context["iv_confidence"] == 1.0


def test_build_atm_iv_context_returns_empty_when_no_valid_contracts() -> None:
    context = build_atm_iv_context(
        spot=600.0,
        symbols=["SPY.C600"],
        strikes=np.array([600.0]),
        valid_mask=np.array([False]),
        resolved_ivs={},
    )

    assert context == {}
