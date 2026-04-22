from __future__ import annotations

from types import SimpleNamespace

from shared_rust.services import (
    active_options_normalize_and_filter_chain,
    active_options_rank_outputs,
)


def test_active_options_normalize_enforces_spot_window_without_volume_gate() -> None:
    chain = [
        {
            "symbol": "SPY260408C670000.US",
            "type": "CALL",
            "strike": 670.0,
            "volume": 0,
            "current_volume": 500,
            "turnover": 120000.0,
            "gamma": 0.02,
        },
        {
            "symbol": "SPY260408C671000.US",
            "type": "CALL",
            "strike": 671.0,
            "volume": 120,
            "current_volume": 1,
            "turnover": 140000.0,
            "gamma": 0.03,
        },
        {
            "symbol": "SPY260408C666000.US",
            "type": "CALL",
            "strike": 666.0,
            "volume": 9999,
            "current_volume": 9999,
            "turnover": 200000.0,
            "gamma": 0.05,
        },
    ]

    filtered = active_options_normalize_and_filter_chain(
        chain=chain,
        spot=670.5,
        spot_window_steps=1,
    )

    assert len(filtered) == 2
    symbols = {row["symbol"] for row in filtered}
    assert symbols == {"SPY260408C670000.US", "SPY260408C671000.US"}
    by_symbol = {row["symbol"]: row for row in filtered}
    assert by_symbol["SPY260408C670000.US"]["volume"] == 0
    assert by_symbol["SPY260408C670000.US"]["day_volume"] == 0
    assert by_symbol["SPY260408C671000.US"]["volume"] == 120
    assert by_symbol["SPY260408C671000.US"]["day_volume"] == 120


def test_active_options_normalize_excludes_far_high_volume_strikes() -> None:
    chain = [
        {
            "symbol": "SPY260408P666000.US",
            "type": "PUT",
            "strike": 666.0,
            "volume": 5000,
            "turnover": 500000.0,
            "gamma": 0.03,
        },
        {
            "symbol": "SPY260408P679000.US",
            "type": "PUT",
            "strike": 679.0,
            "volume": 12,
            "turnover": 60000.0,
            "gamma": 0.02,
        },
        {
            "symbol": "SPY260408P678000.US",
            "type": "PUT",
            "strike": 678.0,
            "volume": 8,
            "turnover": 55000.0,
            "gamma": 0.02,
        },
        {
            "symbol": "SPY260408P686000.US",
            "type": "PUT",
            "strike": 686.0,
            "volume": 40,
            "turnover": 90000.0,
            "gamma": 0.02,
        },
    ]

    filtered = active_options_normalize_and_filter_chain(
        chain=chain,
        spot=679.0,
        spot_window_steps=7,
    )

    symbols = {row["symbol"] for row in filtered}
    assert "SPY260408P666000.US" not in symbols
    assert "SPY260408P679000.US" in symbols
    assert "SPY260408P686000.US" in symbols


def test_active_options_rank_outputs_orders_by_volume_desc() -> None:
    outputs = [
        SimpleNamespace(
            symbol="A",
            option_type="CALL",
            strike=670.0,
            volume=180.0,
            turnover=1000.0,
            impact_index=2.0,
            engine_d_active=True,
            engine_e_active=True,
            engine_g_active=True,
        ),
        SimpleNamespace(
            symbol="B",
            option_type="CALL",
            strike=671.0,
            volume=420.0,
            turnover=900.0,
            impact_index=1.0,
            engine_d_active=True,
            engine_e_active=True,
            engine_g_active=True,
        ),
        SimpleNamespace(
            symbol="C",
            option_type="CALL",
            strike=672.0,
            volume=260.0,
            turnover=1100.0,
            impact_index=3.0,
            engine_d_active=True,
            engine_e_active=True,
            engine_g_active=True,
        ),
    ]

    ranked = active_options_rank_outputs(outputs)

    assert [row.symbol for row in ranked] == ["B", "C", "A"]


def test_active_options_normalize_volume_ignores_legacy_vol_alias() -> None:
    chain = [
        {
            "symbol": "SPY260408C680000.US",
            "type": "CALL",
            "strike": 680.0,
            "volume": 12,
            "vol": 9999,
            "turnover": 1000.0,
            "gamma": 0.02,
        }
    ]

    filtered = active_options_normalize_and_filter_chain(
        chain=chain,
        spot=680.0,
        spot_window_steps=7,
    )

    assert len(filtered) == 1
    assert filtered[0]["volume"] == 12
    assert filtered[0]["day_volume"] == 12


def test_active_options_rank_outputs_does_not_prioritize_engine_status_over_volume() -> None:
    outputs = [
        SimpleNamespace(
            symbol="HIGH_VOL_DEGRADED",
            option_type="CALL",
            strike=680.0,
            volume=1000.0,
            turnover=100.0,
            impact_index=1.0,
            engine_d_active=False,
            engine_e_active=False,
            engine_g_active=False,
        ),
        SimpleNamespace(
            symbol="LOW_VOL_LIVE",
            option_type="CALL",
            strike=681.0,
            volume=100.0,
            turnover=1000.0,
            impact_index=5.0,
            engine_d_active=True,
            engine_e_active=True,
            engine_g_active=True,
        ),
    ]

    ranked = active_options_rank_outputs(outputs)

    assert [row.symbol for row in ranked] == ["HIGH_VOL_DEGRADED", "LOW_VOL_LIVE"]
