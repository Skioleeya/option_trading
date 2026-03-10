from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tools.momentum_calibration.features.kline_features import build_feature_rows, direction_from_return
from tools.momentum_calibration.models import KlineBar

ET = ZoneInfo("America/New_York")


def _bars() -> list[KlineBar]:
    base = datetime(2026, 3, 10, 9, 30, tzinfo=ET)
    closes = [100.0, 100.2, 100.4, 100.3, 100.5, 100.6, 100.8, 100.7]
    out: list[KlineBar] = []
    for i, c in enumerate(closes):
        ts = base + timedelta(minutes=i)
        out.append(KlineBar(ts_et=ts, open=c, high=c, low=c, close=c, volume=1000.0))
    return out


def test_direction_from_return() -> None:
    assert direction_from_return(0.001) == "BULLISH"
    assert direction_from_return(-0.001) == "BEARISH"
    assert direction_from_return(0.0) == "NEUTRAL"


def test_build_feature_rows_has_expected_roc_and_label() -> None:
    rows = build_feature_rows(_bars(), horizon_minutes=5)
    assert len(rows) == 2

    first = rows[0]
    assert round(first.spot_roc_1m, 6) == round((100.2 / 100.0) - 1.0, 6)
    assert round(first.fwd_ret_5m, 6) == round((100.8 / 100.2) - 1.0, 6)
    assert first.label_direction == "BULLISH"

