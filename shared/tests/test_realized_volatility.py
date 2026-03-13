from __future__ import annotations

import pytest

from shared.services.realized_volatility import RollingRealizedVolatility


def test_rolling_realized_volatility_requires_minimum_samples() -> None:
    rv = RollingRealizedVolatility(window_seconds=900.0, min_samples=5)
    for idx, spot in enumerate((100.0, 100.2, 100.4, 100.3)):
        snap = rv.update(spot=spot, timestamp_mono=float(idx * 60.0))
    assert snap.realized_vol == pytest.approx(0.0)


def test_rolling_realized_volatility_annualizes_log_return_variance() -> None:
    rv = RollingRealizedVolatility(window_seconds=900.0, min_samples=5)
    spots = (100.0, 100.5, 99.9, 100.8, 100.1, 101.0)
    snap = None
    for idx, spot in enumerate(spots):
        snap = rv.update(spot=spot, timestamp_mono=float(idx * 180.0))
    assert snap is not None
    assert snap.sample_count == len(spots)
    assert snap.realized_vol > 0.0


def test_rolling_realized_volatility_drops_stale_history() -> None:
    rv = RollingRealizedVolatility(window_seconds=300.0, min_samples=3)
    rv.update(spot=100.0, timestamp_mono=0.0)
    rv.update(spot=100.2, timestamp_mono=60.0)
    rv.update(spot=100.1, timestamp_mono=120.0)
    snap = rv.update(spot=100.3, timestamp_mono=700.0)
    assert snap.sample_count == 1
    assert snap.realized_vol == pytest.approx(0.0)
