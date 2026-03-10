import pytest

from shared.models.flow_engine import FlowEngineOutput
from shared.services.active_options.runtime_service import ActiveOptionsRuntimeService


def _output(*, flow_d: float, flow_e: float, flow_g: float, flow_deg: float) -> FlowEngineOutput:
    return FlowEngineOutput(
        symbol="SPY",
        option_type="CALL",
        strike=560.0,
        implied_volatility=0.2,
        volume=12000,
        turnover=2_500_000.0,
        flow_d=flow_d,
        flow_e=flow_e,
        flow_g=flow_g,
        flow_d_z=0.1,
        flow_e_z=0.2,
        flow_g_z=0.3,
        flow_deg=flow_deg,
        impact_index=88.0,
        is_sweep=False,
        flow_direction="BULLISH",
        flow_intensity="HIGH",
    )


def test_format_row_uses_flow_amount_for_direction_color_when_score_conflicts_negative():
    row = ActiveOptionsRuntimeService._format_row(
        _output(flow_d=-300_000.0, flow_e=-100_000.0, flow_g=-50_000.0, flow_deg=1.7)
    )
    assert row["flow"] == -450_000.0
    assert row["flow_score"] == 1.7
    assert row["flow_direction"] == "BEARISH"
    assert row["flow_color"] == "text-accent-green"
    assert row["flow_deg_formatted"] == "-$450K"
    assert row["is_placeholder"] is False
    assert row["slot_index"] == 1


def test_format_row_uses_flow_amount_for_direction_color_when_score_conflicts_positive():
    row = ActiveOptionsRuntimeService._format_row(
        _output(flow_d=500_000.0, flow_e=200_000.0, flow_g=100_000.0, flow_deg=-2.2)
    )
    assert row["flow"] == 800_000.0
    assert row["flow_score"] == -2.2
    assert row["flow_direction"] == "BULLISH"
    assert row["flow_color"] == "text-accent-red"
    assert row["flow_deg_formatted"] == "$800K"
    assert row["is_placeholder"] is False
    assert row["slot_index"] == 1


def test_format_row_zero_flow_is_neutral():
    row = ActiveOptionsRuntimeService._format_row(
        _output(flow_d=0.0, flow_e=0.0, flow_g=0.0, flow_deg=3.3)
    )
    assert row["flow"] == 0.0
    assert row["flow_score"] == 3.3
    assert row["flow_direction"] == "NEUTRAL"
    assert row["flow_color"] == "text-text-secondary"
    assert row["flow_deg_formatted"] == "$0"
    assert row["is_placeholder"] is False
    assert row["slot_index"] == 1


def test_pad_rows_preserves_order_and_fills_placeholders():
    real_rows = [
        ActiveOptionsRuntimeService._format_row(_output(flow_d=10.0, flow_e=0.0, flow_g=0.0, flow_deg=0.1), slot_index=1),
        ActiveOptionsRuntimeService._format_row(_output(flow_d=-8.0, flow_e=0.0, flow_g=0.0, flow_deg=-0.2), slot_index=2),
        ActiveOptionsRuntimeService._format_row(_output(flow_d=5.0, flow_e=0.0, flow_g=0.0, flow_deg=0.3), slot_index=3),
    ]
    rows = ActiveOptionsRuntimeService._pad_rows(real_rows, 5)
    assert len(rows) == 5
    assert [r["slot_index"] for r in rows] == [1, 2, 3, 4, 5]
    assert [r["is_placeholder"] for r in rows] == [False, False, False, True, True]


@pytest.mark.asyncio
async def test_update_background_with_empty_chain_emits_five_placeholders():
    svc = ActiveOptionsRuntimeService()
    await svc.update_background(chain=[], spot=0.0, atm_iv=0.0, redis=None, limit=5)
    rows = svc.get_latest()
    assert len(rows) == 5
    assert all(r["is_placeholder"] is True for r in rows)
    assert [r["slot_index"] for r in rows] == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_update_background_pads_when_real_rows_below_limit():
    svc = ActiveOptionsRuntimeService()
    chain = [
        {
            "symbol": "SPY_A",
            "option_type": "C",
            "strike": 560.0,
            "volume": 220,
            "turnover": 120000.0,
            "implied_volatility": 0.2,
            "historical_volatility": 0.18,
            "open_interest": 1000,
            "gamma": 0.01,
            "vanna": 0.02,
        },
        {
            "symbol": "SPY_B",
            "option_type": "P",
            "strike": 559.0,
            "volume": 260,
            "turnover": 140000.0,
            "implied_volatility": 0.21,
            "historical_volatility": 0.19,
            "open_interest": 1100,
            "gamma": 0.01,
            "vanna": 0.02,
        },
        {
            "symbol": "SPY_C",
            "option_type": "C",
            "strike": 561.0,
            "volume": 300,
            "turnover": 160000.0,
            "implied_volatility": 0.22,
            "historical_volatility": 0.20,
            "open_interest": 1200,
            "gamma": 0.01,
            "vanna": 0.02,
        },
    ]
    await svc.update_background(chain=chain, spot=560.0, atm_iv=0.2, redis=None, limit=5)
    rows = svc.get_latest()
    assert len(rows) == 5
    assert [r["slot_index"] for r in rows] == [1, 2, 3, 4, 5]
    assert sum(1 for r in rows if r["is_placeholder"]) == 2
