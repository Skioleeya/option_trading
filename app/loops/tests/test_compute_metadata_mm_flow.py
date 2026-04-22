from __future__ import annotations

from app.loops.compute_metadata import _build_l1_extra_metadata


def test_build_l1_extra_metadata_contains_mm_flow_metrics() -> None:
    snapshot = {
        "as_of_utc": "2026-04-16T14:30:00Z",
        "rust_active": True,
        "chain": [
            {
                "symbol": "SPY250416P00550000",
                "opt_type": "PUT",
                "impact_index": 1.0,
                "ask_volume": 90.0,
                "bid_volume": 0.0,
                "delta": -0.42,
                "gamma": 0.02,
                "open_interest": 700.0,
                "last_price": 2.0,
                "bid": 1.9,
                "ask": 2.1,
                "trade_type": "Regular",
                "strike": 550.0,
            }
        ],
    }
    metadata = _build_l1_extra_metadata(snapshot)
    mm_flow = metadata.get("mm_flow_metrics")
    assert isinstance(mm_flow, dict)
    assert mm_flow.get("net_delta_exposure_live", 0.0) < 0.0
    assert mm_flow.get("oi_participation_ratio_live", 0.0) > 0.0

