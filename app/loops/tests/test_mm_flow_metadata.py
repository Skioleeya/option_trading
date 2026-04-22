from __future__ import annotations

from app.loops.mm_flow_metadata import build_mm_flow_metrics


def test_build_mm_flow_metrics_empty_snapshot_returns_zeroes() -> None:
    metrics = build_mm_flow_metrics({"chain": []})
    assert metrics["net_delta_exposure_live"] == 0.0
    assert metrics["net_gamma_exposure_live"] == 0.0
    assert metrics["condition_filtered_count"] == 0.0


def test_build_mm_flow_metrics_aggregates_directional_pressure() -> None:
    snapshot = {
        "chain": [
            {
                "symbol": "SPY250101C00550000",
                "opt_type": "CALL",
                "impact_index": -1.0,
                "bid_volume": 120.0,
                "ask_volume": 0.0,
                "delta": 0.45,
                "gamma": 0.02,
                "open_interest": 800.0,
                "last_price": 2.0,
                "bid": 1.9,
                "ask": 2.1,
                "trade_type": "Regular",
                "strike": 550.0,
            },
            {
                "symbol": "SPY250101P00550000",
                "opt_type": "PUT",
                "impact_index": 1.0,
                "bid_volume": 0.0,
                "ask_volume": 100.0,
                "delta": -0.40,
                "gamma": 0.018,
                "open_interest": 900.0,
                "last_price": 2.0,
                "bid": 1.9,
                "ask": 2.1,
                "trade_type": "Regular",
                "strike": 550.0,
            },
            {
                "symbol": "SPY250101P00545000",
                "opt_type": "PUT",
                "impact_index": 1.0,
                "bid_volume": 0.0,
                "ask_volume": 80.0,
                "delta": -0.35,
                "gamma": 0.015,
                "open_interest": 600.0,
                "last_price": 1.8,
                "bid": 1.7,
                "ask": 1.9,
                "trade_type": "Late Print",
                "strike": 545.0,
            },
        ]
    }
    metrics = build_mm_flow_metrics(snapshot)
    assert metrics["condition_filtered_count"] == 1.0
    assert metrics["call_bid_side_volume"] > 0.0
    assert metrics["put_ask_side_volume"] > 0.0
    assert metrics["oi_participation_ratio_live"] > 0.0
    assert metrics["flow_suppression_bias"] > 0.0


def test_build_mm_flow_metrics_does_not_use_legacy_trade_size_fallback() -> None:
    snapshot = {
        "chain": [
            {
                "symbol": "SPY250101C00550000",
                "opt_type": "CALL",
                "impact_index": 1.0,
                "bid_volume": 0.0,
                "ask_volume": 0.0,
                "last_size": 250.0,
                "trade_size": 250.0,
                "delta": 0.4,
                "gamma": 0.02,
                "open_interest": 1000.0,
                "trade_type": "Regular",
            }
        ]
    }
    metrics = build_mm_flow_metrics(snapshot)
    assert metrics["net_delta_exposure_live"] == 0.0
    assert metrics["net_gamma_exposure_live"] == 0.0
    assert metrics["call_ask_side_volume"] == 0.0
