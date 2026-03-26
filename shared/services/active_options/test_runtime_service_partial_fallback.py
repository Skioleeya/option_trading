import pytest

from shared.models.flow_engine import FlowEngineOutput
from shared.services.active_options.runtime_service import ActiveOptionsRuntimeService


def _flow_output_from_row(row: dict[str, object]) -> FlowEngineOutput:
    return FlowEngineOutput(
        symbol=str(row.get("symbol", "SPY")),
        option_type=str(row.get("option_type", "CALL")).upper(),
        strike=float(row.get("strike", 0.0) or 0.0),
        implied_volatility=float(row.get("implied_volatility", 0.0) or 0.0),
        volume=int(row.get("volume", 0) or 0),
        turnover=float(row.get("turnover", 0.0) or 0.0),
        flow_d=25_000.0,
        flow_e=0.0,
        flow_g=0.0,
        flow_d_z=1.2,
        flow_e_z=0.0,
        flow_g_z=0.0,
        flow_deg=2.4,
        impact_index=42.0,
        is_sweep=False,
        flow_direction="BULLISH",
        flow_intensity="HIGH",
        engine_d_active=True,
        engine_e_active=True,
        engine_g_active=True,
    )


@pytest.mark.asyncio
async def test_partial_fallback_supplements_sparse_filtered_rows_without_overwriting_real_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = ActiveOptionsRuntimeService()

    async def _run_flow_pipeline(**kwargs):
        return [_flow_output_from_row(row) for row in kwargs["filtered"]]

    monkeypatch.setattr(svc, "_run_flow_pipeline", _run_flow_pipeline)
    chain = [
        {"symbol": "SPY_REAL_A", "option_type": "C", "strike": 560.0, "volume": 240, "turnover": 240000.0, "implied_volatility": 0.22},
        {"symbol": "SPY_REAL_B", "option_type": "P", "strike": 559.0, "volume": 180, "turnover": 210000.0, "implied_volatility": 0.21},
        {"symbol": "SPY_FB_C", "option_type": "C", "strike": 561.0, "volume": 0, "turnover": 190000.0, "open_interest": 900, "last_price": 2.0, "implied_volatility": 0.2},
        {"symbol": "SPY_FB_D", "option_type": "P", "strike": 558.0, "volume": 0, "turnover": 170000.0, "open_interest": 850, "last_price": 1.7, "implied_volatility": 0.19},
        {"symbol": "SPY_FB_E", "option_type": "C", "strike": 562.0, "volume": 0, "turnover": 150000.0, "open_interest": 800, "last_price": 1.5, "implied_volatility": 0.18},
    ]

    await svc.update_background(chain=chain, spot=560.0, atm_iv=0.2, redis=None, limit=5)
    rows = svc.get_latest()

    assert len(rows) == 5
    assert sum(1 for row in rows if row["is_placeholder"]) == 0
    assert {row["contract_symbol"] for row in rows if row["row_quality"] == "REAL"} == {"SPY_REAL_A", "SPY_REAL_B"}
    assert {row["contract_symbol"] for row in rows if row["row_quality"] == "FALLBACK_SYNTHETIC"} == {
        "SPY_FB_C",
        "SPY_FB_D",
        "SPY_FB_E",
    }

    diag = svc.get_diagnostics()
    assert diag["rows_real"] == 5
    assert diag["rows_real_non_synthetic"] == 2
    assert diag["rows_synthetic_fallback"] == 3
    assert diag["partial_fallback_count"] >= 1
    assert diag["last_partial_fallback_mode"] == "turnover_open_interest"
    assert diag["filtered_candidates_count"] == 2
    assert diag["supplemented_rows"] == 3
    assert diag["last_fallback_mode"] == "turnover_open_interest"


@pytest.mark.asyncio
async def test_partial_fallback_still_preserves_placeholders_when_chain_cannot_fill_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = ActiveOptionsRuntimeService()

    async def _run_flow_pipeline(**kwargs):
        return [_flow_output_from_row(row) for row in kwargs["filtered"]]

    monkeypatch.setattr(svc, "_run_flow_pipeline", _run_flow_pipeline)
    chain = [
        {"symbol": "SPY_REAL_A", "option_type": "C", "strike": 560.0, "volume": 240, "turnover": 240000.0, "implied_volatility": 0.22},
        {"symbol": "SPY_REAL_B", "option_type": "P", "strike": 559.0, "volume": 180, "turnover": 210000.0, "implied_volatility": 0.21},
        {"symbol": "SPY_FB_C", "option_type": "C", "strike": 561.0, "volume": 0, "turnover": 190000.0, "open_interest": 900, "last_price": 2.0, "implied_volatility": 0.2},
    ]

    await svc.update_background(chain=chain, spot=560.0, atm_iv=0.2, redis=None, limit=5)
    rows = svc.get_latest()

    assert len(rows) == 5
    assert sum(1 for row in rows if row["is_placeholder"]) == 2
    assert {row["contract_symbol"] for row in rows if row["row_quality"] == "REAL"} == {"SPY_REAL_A", "SPY_REAL_B"}
    assert {row["contract_symbol"] for row in rows if row["row_quality"] == "FALLBACK_SYNTHETIC"} == {"SPY_FB_C"}

    diag = svc.get_diagnostics()
    assert diag["rows_real"] == 3
    assert diag["rows_real_non_synthetic"] == 2
    assert diag["rows_synthetic_fallback"] == 1
    assert diag["filtered_candidates_count"] == 2
    assert diag["supplemented_rows"] == 1
