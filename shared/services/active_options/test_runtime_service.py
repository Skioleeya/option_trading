import pytest

from shared.contracts.metric_semantics import get_metric_semantics
from shared.models.flow_engine import FlowEngineOutput
from shared.services.active_options.runtime_service import ActiveOptionsRuntimeService


def _output(
    *,
    symbol: str = "SPY",
    option_type: str = "CALL",
    strike: float = 560.0,
    volume: int = 12000,
    turnover: float = 2_500_000.0,
    flow_d: float,
    flow_e: float,
    flow_g: float,
    flow_deg: float,
    impact_index: float = 88.0,
) -> FlowEngineOutput:
    return FlowEngineOutput(
        symbol=symbol,
        option_type=option_type,
        strike=strike,
        implied_volatility=0.2,
        volume=volume,
        turnover=turnover,
        flow_d=flow_d,
        flow_e=flow_e,
        flow_g=flow_g,
        flow_d_z=0.1,
        flow_e_z=0.2,
        flow_g_z=0.3,
        flow_deg=flow_deg,
        impact_index=impact_index,
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


def test_rank_outputs_prefers_vol_turnover_impact_then_stable_key():
    outputs = [
        _output(symbol="Z", option_type="PUT", strike=560.0, volume=1000, turnover=1_000_000.0, impact_index=9.0, flow_d=1, flow_e=0, flow_g=0, flow_deg=0.2),
        _output(symbol="B", option_type="CALL", strike=561.0, volume=1200, turnover=1_200_000.0, impact_index=4.0, flow_d=1, flow_e=0, flow_g=0, flow_deg=0.2),
        _output(symbol="A", option_type="CALL", strike=561.0, volume=1200, turnover=1_200_000.0, impact_index=4.0, flow_d=1, flow_e=0, flow_g=0, flow_deg=0.2),
        _output(symbol="C", option_type="CALL", strike=561.0, volume=1200, turnover=1_500_000.0, impact_index=1.0, flow_d=1, flow_e=0, flow_g=0, flow_deg=0.2),
        _output(symbol="D", option_type="CALL", strike=562.0, volume=1200, turnover=1_200_000.0, impact_index=6.0, flow_d=1, flow_e=0, flow_g=0, flow_deg=0.2),
    ]

    ranked = ActiveOptionsRuntimeService._rank_outputs(outputs)
    order = [f"{o.symbol}:{o.strike}:{o.option_type}" for o in ranked]

    assert order == [
        "C:561.0:CALL",  # highest turnover under same volume
        "D:562.0:CALL",  # then impact_index
        "A:561.0:CALL",  # tie -> stable key symbol asc
        "B:561.0:CALL",
        "Z:560.0:PUT",   # lower volume last
    ]


def test_commit_or_hold_candidate_switches_after_three_consecutive_ticks():
    svc = ActiveOptionsRuntimeService()

    rows_a = [{"slot_index": 1, "is_placeholder": False, "id": "A"}]
    rows_b = [{"slot_index": 1, "is_placeholder": False, "id": "B"}]
    sig_a = (("A", "CALL", 560.0),)
    sig_b = (("B", "CALL", 561.0),)

    svc._commit_or_hold_candidate(rows=rows_a, signature=sig_a)
    assert svc.get_latest() == rows_a

    svc._commit_or_hold_candidate(rows=rows_b, signature=sig_b)
    assert svc.get_latest() == rows_a

    svc._commit_or_hold_candidate(rows=rows_b, signature=sig_b)
    assert svc.get_latest() == rows_a

    svc._commit_or_hold_candidate(rows=rows_b, signature=sig_b)
    assert svc.get_latest() == rows_b



def test_commit_or_hold_candidate_refreshes_payload_when_signature_is_unchanged():
    svc = ActiveOptionsRuntimeService()

    rows_a = [{"slot_index": 1, "is_placeholder": False, "id": "A", "volume": 100}]
    rows_a_updated = [{"slot_index": 1, "is_placeholder": False, "id": "A", "volume": 300}]
    sig_a = (("A", "CALL", 560.0),)

    svc._commit_or_hold_candidate(rows=rows_a, signature=sig_a)
    assert svc.get_latest() == rows_a

    svc._commit_or_hold_candidate(rows=rows_a_updated, signature=sig_a)
    assert svc.get_latest() == rows_a_updated


def test_commit_or_hold_candidate_cuts_over_immediately_for_placeholder_signature():
    svc = ActiveOptionsRuntimeService()

    rows_real = [{"slot_index": 1, "is_placeholder": False, "id": "A"}]
    rows_placeholder = [{"slot_index": 1, "is_placeholder": True, "id": "P"}]
    sig_real = (("A", "CALL", 560.0),)
    sig_placeholder = (("__placeholder__#1", "CALL", 0.0),)

    svc._commit_or_hold_candidate(rows=rows_real, signature=sig_real)
    assert svc.get_latest() == rows_real

    svc._commit_or_hold_candidate(rows=rows_placeholder, signature=sig_placeholder)
    assert svc.get_latest() == rows_placeholder
    assert svc._pending_signature is None
    assert svc._pending_hits == 0


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


def test_flow_engines_have_registry_semantics_entries():
    for metric_name in ("FLOW_D", "FLOW_E", "FLOW_G"):
        semantics = get_metric_semantics(metric_name)
        assert semantics.classification == "heuristic"
        assert semantics.live_usage == "live"
        assert "proxy" in semantics.canonical_description.lower() or "heuristic" in semantics.canonical_description.lower()

