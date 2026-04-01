from __future__ import annotations

import pytest

from shared_rust.models import AgentB1Output, FlowEngineInput, FusedSignalResult, GexRegime, VannaFlowResult


def test_flow_engine_wrapper_uses_rust_backed_validation_fields() -> None:
    with pytest.raises(ValueError):
        FlowEngineInput(
            symbol="SPY",
            option_type="CALL",
            strike=560.0,
            spot=560.0,
            volume=1,
            turnover=1.0,
            last_price=1.0,
            implied_volatility=float("nan"),
            historical_volatility=0.2,
            open_interest=1,
        )


def test_microstructure_wrapper_uses_rust_backed_enums_and_defaults() -> None:
    assert GexRegime.ACCELERATION == "ACCELERATION"
    assert VannaFlowResult().gex_regime == GexRegime.NEUTRAL
    assert FusedSignalResult().regime == "UNKNOWN"


def test_agent_output_wrapper_uses_rust_backed_defaults() -> None:
    assert AgentB1Output().gamma_flip is False
