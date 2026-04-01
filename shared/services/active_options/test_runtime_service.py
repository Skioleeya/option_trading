import pytest

from shared_rust.contracts import get_metric_semantics
from shared.config import settings
from shared_rust.models import FlowEngineOutput
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
    assert row["row_quality"] == "REAL"
    assert row["fallback_reason"] is None
    assert row["is_synthetic_fallback"] is False
    assert row["flow_signal_state"] == "LIVE"
    assert row["flow_signal_reason"] is None
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
    assert row["row_quality"] == "REAL"
    assert row["fallback_reason"] is None
    assert row["is_synthetic_fallback"] is False
    assert row["flow_signal_state"] == "LIVE"
    assert row["flow_signal_reason"] is None
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
    assert row["row_quality"] == "REAL"
    assert row["fallback_reason"] is None
    assert row["is_synthetic_fallback"] is False
    assert row["flow_signal_state"] == "LIVE"
    assert row["flow_signal_reason"] is None
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


def test_commit_or_hold_candidate_recovers_immediately_from_placeholder_to_real():
    svc = ActiveOptionsRuntimeService()

    rows_placeholder = [{"slot_index": 1, "is_placeholder": True, "id": "P"}]
    rows_real = [{"slot_index": 1, "is_placeholder": False, "id": "A"}]
    sig_placeholder = (("__placeholder__#1", "CALL", 0.0),)
    sig_real = (("A", "CALL", 560.0),)

    svc._commit_or_hold_candidate(rows=rows_placeholder, signature=sig_placeholder)
    assert svc.get_latest() == rows_placeholder

    svc._commit_or_hold_candidate(rows=rows_real, signature=sig_real)
    assert svc.get_latest() == rows_real
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
    assert all(r["row_quality"] == "PLACEHOLDER" for r in rows)
    assert all(r["flow_signal_state"] == "DEGRADED" for r in rows)
    assert all(r["flow_signal_reason"] == "all_engines_inactive" for r in rows)
    assert [r["slot_index"] for r in rows] == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_diagnostics_reports_placeholder_and_empty_filter_stats():
    svc = ActiveOptionsRuntimeService()
    await svc.update_background(chain=[], spot=0.0, atm_iv=0.0, redis=None, limit=5)

    diag = svc.get_diagnostics()
    assert diag["rows_total"] == 5
    assert diag["rows_placeholder"] == 5
    assert diag["rows_real"] == 0
    assert diag["rows_real_non_synthetic"] == 0
    assert diag["rows_synthetic_fallback"] == 0
    assert diag["degraded_rows"] == 5
    assert diag["live_rows"] == 0
    assert diag["missing_gamma_rows"] == 0
    assert diag["missing_turnover_rows"] == 0
    assert diag["last_fallback_mode"] is None
    assert diag["all_placeholder"] is True
    assert diag["empty_filter_count"] >= 1
    assert isinstance(diag["last_empty_filter_at_utc"], str)
    assert isinstance(diag["last_update_at_utc"], str)
    assert isinstance(diag["min_volume_threshold"], int)


@pytest.mark.asyncio
async def test_update_background_uses_turnover_open_interest_fallback_when_min_volume_empty():
    svc = ActiveOptionsRuntimeService()
    chain = [
        {
            "symbol": "SPY_FALLBACK_A",
            "option_type": "C",
            "strike": 560.0,
            "volume": 0,
            "current_volume": 0,
            "turnover": 250000.0,
            "implied_volatility": 0.2,
            "historical_volatility": 0.19,
            "open_interest": 1200,
            "gamma": 0.01,
            "vanna": 0.02,
        },
        {
            "symbol": "SPY_FALLBACK_B",
            "option_type": "P",
            "strike": 559.0,
            "volume": 0,
            "current_volume": 0,
            "turnover": 180000.0,
            "implied_volatility": 0.21,
            "historical_volatility": 0.2,
            "open_interest": 900,
            "gamma": 0.01,
            "vanna": 0.02,
        },
    ]

    await svc.update_background(chain=chain, spot=560.0, atm_iv=0.2, redis=None, limit=5)
    rows = svc.get_latest()
    assert len(rows) == 5
    assert rows[0]["is_placeholder"] is False
    assert rows[0]["row_quality"] == "FALLBACK_SYNTHETIC"
    assert rows[0]["fallback_reason"] == "turnover_open_interest"
    assert rows[0]["is_synthetic_fallback"] is True
    assert rows[0]["flow_signal_state"] == "DEGRADED"
    assert rows[0]["flow_signal_reason"] == "missing_turnover"
    diag = svc.get_diagnostics()
    assert diag["rows_real"] >= 1
    assert diag["rows_real_non_synthetic"] == 0
    assert diag["rows_synthetic_fallback"] >= 1
    assert diag["last_fallback_mode"] == "turnover_open_interest"
    assert diag["empty_filter_fallback_count"] >= 1
    assert isinstance(diag["last_empty_filter_fallback_at_utc"], str)


@pytest.mark.asyncio
async def test_update_background_fallback_accepts_alias_fields_and_normalizes_option_type():
    svc = ActiveOptionsRuntimeService()
    chain = [
        {
            "symbol": "SPY_ALIAS_A",
            "type": "C",
            "strike_price": 560.0,
            "volume": 0,
            "currentVolume": 0,
            "amount": 210000.0,
            "openInterest": 1200,
            "last_done": 2.1,
            "iv": 0.2,
            "hv": 0.18,
            "gamma": 0.01,
            "vanna": 0.02,
        }
    ]

    await svc.update_background(chain=chain, spot=560.0, atm_iv=0.2, redis=None, limit=5)
    rows = svc.get_latest()
    assert len(rows) == 5
    assert rows[0]["is_placeholder"] is False
    assert rows[0]["option_type"] == "CALL"
    assert rows[0]["strike"] == pytest.approx(560.0)
    assert rows[0]["row_quality"] == "FALLBACK_SYNTHETIC"
    assert rows[0]["fallback_reason"] == "turnover_open_interest"
    assert rows[0]["flow_signal_state"] == "DEGRADED"
    assert rows[0]["flow_signal_reason"] == "missing_turnover"
    diag = svc.get_diagnostics()
    assert diag["empty_filter_fallback_count"] >= 1


@pytest.mark.asyncio
async def test_update_background_hard_fallback_emits_real_row_when_chain_non_empty_but_no_turnover_or_oi():
    svc = ActiveOptionsRuntimeService()
    chain = [
        {
            "symbol": "SPY_HARD_FALLBACK_A",
            "type": "C",
            "strike": 560.0,
            "volume": 0,
            "current_volume": 0,
            "turnover": 0.0,
            "open_interest": 0,
            "last_price": 1.5,
        },
        {
            "symbol": "SPY_HARD_FALLBACK_B",
            "type": "P",
            "strike": 559.0,
            "volume": 0,
            "current_volume": 0,
            "turnover": 0.0,
            "open_interest": 0,
            "last_price": 1.6,
        },
    ]

    await svc.update_background(chain=chain, spot=560.0, atm_iv=0.2, redis=None, limit=5)
    rows = svc.get_latest()
    assert len(rows) == 5
    assert rows[0]["is_placeholder"] is False
    assert rows[0]["volume"] >= 1
    assert rows[0]["row_quality"] == "FALLBACK_SYNTHETIC"
    assert rows[0]["fallback_reason"] == "hard_chain"
    assert rows[0]["is_synthetic_fallback"] is True
    assert rows[0]["flow_signal_state"] == "DEGRADED"
    assert rows[0]["flow_signal_reason"] == "missing_gamma"
    diag = svc.get_diagnostics()
    assert diag["rows_real"] >= 1
    assert diag["rows_real_non_synthetic"] == 0
    assert diag["rows_synthetic_fallback"] >= 1
    assert diag["last_fallback_mode"] == "hard_chain"
    assert diag["empty_filter_fallback_count"] >= 1


@pytest.mark.asyncio
async def test_update_background_forces_hard_fallback_when_config_disables_empty_filter_fallback(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "flow_active_empty_filter_fallback_enabled", False, raising=False)
    monkeypatch.setattr(settings, "flow_active_empty_filter_fallback_max_candidates", 0, raising=False)

    svc = ActiveOptionsRuntimeService()
    chain = [
        {
            "symbol": "SPY_FORCED_FALLBACK_A",
            "type": "C",
            "strike": 560.0,
            "volume": 0,
            "current_volume": 0,
            "turnover": 0.0,
            "open_interest": 0,
            "last_price": 1.5,
        }
    ]

    await svc.update_background(chain=chain, spot=560.0, atm_iv=0.2, redis=None, limit=5)
    rows = svc.get_latest()
    assert len(rows) == 5
    assert rows[0]["is_placeholder"] is False
    assert rows[0]["volume"] >= 1
    assert rows[0]["row_quality"] == "FALLBACK_SYNTHETIC"
    assert rows[0]["fallback_reason"] == "hard_chain"
    assert rows[0]["flow_signal_state"] == "DEGRADED"
    assert rows[0]["flow_signal_reason"] == "missing_gamma"

    diag = svc.get_diagnostics()
    assert diag["rows_real"] >= 1
    assert diag["rows_real_non_synthetic"] == 0
    assert diag["rows_synthetic_fallback"] >= 1
    assert diag["last_fallback_mode"] == "hard_chain"
    assert diag["empty_filter_fallback_count"] >= 1
    assert diag["empty_filter_fallback_enabled"] is False


@pytest.mark.asyncio
async def test_update_background_uses_neutral_output_fallback_when_flow_pipeline_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
):
    svc = ActiveOptionsRuntimeService()

    async def _return_empty_outputs(**kwargs):
        del kwargs
        return []

    monkeypatch.setattr(svc, "_run_flow_pipeline", _return_empty_outputs)

    chain = [
        {
            "symbol": "SPY_ENGINE_EMPTY_A",
            "option_type": "C",
            "strike": 560.0,
            "volume": 220,
            "turnover": 0.0,
            "implied_volatility": 0.2,
            "historical_volatility": 0.18,
            "open_interest": 1000,
        }
    ]

    await svc.update_background(chain=chain, spot=560.0, atm_iv=0.2, redis=None, limit=5)
    rows = svc.get_latest()
    assert len(rows) == 5
    assert rows[0]["is_placeholder"] is False
    assert rows[0]["flow"] == pytest.approx(0.0)
    assert rows[0]["flow_direction"] == "NEUTRAL"
    assert rows[0]["row_quality"] == "FALLBACK_SYNTHETIC"
    assert rows[0]["fallback_reason"] == "engine_empty_output"
    assert rows[0]["is_synthetic_fallback"] is True
    assert rows[0]["flow_signal_state"] == "DEGRADED"
    assert rows[0]["flow_signal_reason"] == "all_engines_inactive"

    diag = svc.get_diagnostics()
    assert diag["rows_real"] >= 1
    assert diag["rows_real_non_synthetic"] == 0
    assert diag["rows_synthetic_fallback"] >= 1
    assert diag["last_fallback_mode"] == "engine_empty_output"
    assert diag["engine_empty_output_fallback_count"] >= 1
    assert isinstance(diag["last_engine_empty_output_fallback_at_utc"], str)


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


@pytest.mark.asyncio
async def test_update_background_uses_current_volume_fallback_for_min_volume_filter():
    svc = ActiveOptionsRuntimeService()
    chain = [
        {
            "symbol": "SPY_FALLBACK",
            "option_type": "C",
            "strike": 562.0,
            "volume": 0,
            "current_volume": 220,
            "turnover": 130000.0,
            "implied_volatility": 0.19,
            "historical_volatility": 0.17,
            "open_interest": 900,
            "gamma": 0.01,
            "vanna": 0.02,
        }
    ]

    await svc.update_background(chain=chain, spot=560.0, atm_iv=0.2, redis=None, limit=3)
    rows = svc.get_latest()
    assert len(rows) == 3
    assert rows[0]["is_placeholder"] is False
    assert rows[0]["volume"] == 220
    assert rows[0]["row_quality"] == "REAL"
    assert rows[0]["fallback_reason"] is None
    assert rows[0]["is_synthetic_fallback"] is False
    assert rows[0]["flow_signal_state"] == "DEGRADED"
    assert rows[0]["flow_signal_reason"] == "missing_turnover"

def test_apply_zero_limit_guard_resets_runtime_cache_state():
    svc = ActiveOptionsRuntimeService()
    svc._latest_payload = [{"slot_index": 1, "is_placeholder": False}]
    svc._latest_signature = (("A", "CALL", 560.0),)
    svc._pending_signature = (("B", "CALL", 561.0),)
    svc._pending_rows = [{"slot_index": 1, "is_placeholder": False, "id": "B"}]
    svc._pending_hits = 2

    handled = svc._apply_zero_limit_guard(0)

    assert handled is True
    assert svc.get_latest() == []
    assert svc._latest_signature is None
    assert svc._pending_signature is None
    assert svc._pending_rows == []
    assert svc._pending_hits == 0


def test_normalize_and_filter_chain_uses_volume_fallback_before_threshold():
    chain = [
        {"symbol": "A", "volume": 0, "current_volume": 220},
        {"symbol": "B", "volume": 150, "current_volume": 0},
    ]

    filtered = ActiveOptionsRuntimeService._normalize_and_filter_chain(
        chain=chain,
        min_volume=200,
    )

    assert len(filtered) == 1
    assert filtered[0]["symbol"] == "A"
    assert int(filtered[0]["volume"]) == 220


def test_normalize_and_filter_chain_drops_implausible_volume_but_keeps_valid_current_volume():
    chain = [
        {"symbol": "A", "volume": 3617287935039721472, "current_volume": 220},
    ]

    filtered = ActiveOptionsRuntimeService._normalize_and_filter_chain(
        chain=chain,
        min_volume=200,
    )

    assert len(filtered) == 1
    assert filtered[0]["symbol"] == "A"
    assert int(filtered[0]["volume"]) == 220


def test_normalize_and_filter_chain_drops_row_when_dual_volume_are_implausible():
    chain = [
        {"symbol": "A", "volume": 3617287935039721472, "current_volume": 3617287935039721472},
    ]

    filtered = ActiveOptionsRuntimeService._normalize_and_filter_chain(
        chain=chain,
        min_volume=1,
    )

    assert filtered == []
