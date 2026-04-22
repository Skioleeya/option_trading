from __future__ import annotations

import numpy as np
import pytest

from shared.services.greeks_engine_batch import build_greeks_batch_sync


def test_greeks_engine_batch_uses_rust_owner_and_returns_batch_payload() -> None:
    chain_data = [
        {"symbol": "SPY250403C00580000", "strike": 580.0, "type": "CALL", "volume": 12, "open_interest": 100, "contract_multiplier": 100},
        {"symbol": "SPY250403P00575000", "strike": 575.0, "type": "PUT", "volume": 9, "open_interest": 80, "contract_multiplier": 100},
    ]
    iv_cache = {
        "SPY250403C00580000": 0.20,
        "SPY250403P00575000": 0.22,
    }
    spot_at_sync = {
        "SPY250403C00580000": 579.5,
        "SPY250403P00575000": 579.5,
    }

    results, agg = build_greeks_batch_sync(
        chain_data,
        580.0,
        iv_cache,
        spot_at_sync,
        0.05,
        0.0,
    )

    assert len(results) == 2
    assert all("implied_volatility" in greeks for _, greeks in results)
    assert agg["ttm_seconds"] > 0
    assert np.isfinite(float(agg["net_gex"]))
    assert np.isfinite(float(agg["atm_iv"]))


def test_greeks_engine_batch_requires_rust_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "shared.services.greeks_engine_batch._rust_bsm_batch_numpy_tier",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("forced-rust-bsm-fail")),
    )

    chain_data = [{"symbol": "SPY250403C00580000", "strike": 580.0, "type": "CALL", "volume": 12, "open_interest": 100, "contract_multiplier": 100}]
    iv_cache = {"SPY250403C00580000": 0.20}
    spot_at_sync = {"SPY250403C00580000": 579.5}

    with pytest.raises(RuntimeError, match="forced-rust-bsm-fail"):
        build_greeks_batch_sync(chain_data, 580.0, iv_cache, spot_at_sync, 0.05, 0.0)
