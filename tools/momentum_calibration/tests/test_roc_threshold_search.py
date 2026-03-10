from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tools.momentum_calibration.config import CalibrationConfig
from tools.momentum_calibration.models import FeatureRow
from tools.momentum_calibration.optimize.roc_threshold_search import (
    evaluate_candidate,
    predict_direction,
    search_best_thresholds,
)

ET = ZoneInfo("America/New_York")


def _rows() -> list[FeatureRow]:
    base = datetime(2026, 3, 10, 10, 0, tzinfo=ET)
    data = [
        (0.0020, 0.0030, "BULLISH"),
        (-0.0022, -0.0031, "BEARISH"),
        (0.0004, 0.0001, "BULLISH"),
        (-0.0003, -0.0001, "BEARISH"),
        (0.0018, 0.0022, "BULLISH"),
        (-0.0019, -0.0020, "BEARISH"),
    ]
    out: list[FeatureRow] = []
    for i, (roc, fwd, label) in enumerate(data):
        out.append(
            FeatureRow(
                ts_et=base + timedelta(minutes=i),
                close=100.0,
                spot_roc_1m=roc,
                fwd_ret_5m=fwd,
                label_direction=label,  # type: ignore[arg-type]
            )
        )
    return out


def test_predict_direction() -> None:
    assert predict_direction(0.002, bull_threshold=0.0015, bear_threshold=-0.0015) == "BULLISH"
    assert predict_direction(-0.002, bull_threshold=0.0015, bear_threshold=-0.0015) == "BEARISH"
    assert predict_direction(0.0002, bull_threshold=0.0015, bear_threshold=-0.0015) == "NEUTRAL"


def test_evaluate_candidate_counts() -> None:
    rows = _rows()
    out = evaluate_candidate(rows, bull_threshold=0.0015, bear_threshold=-0.0015)
    assert out.total_rows == len(rows)
    assert out.signal_rows == 4
    assert out.correct_rows >= 3


def test_search_best_thresholds_returns_stable_candidate() -> None:
    cfg = CalibrationConfig(
        bull_grid_min=0.0010,
        bull_grid_max=0.0020,
        bull_grid_step=0.0005,
        bear_grid_min=-0.0020,
        bear_grid_max=-0.0010,
        bear_grid_step=0.0005,
        min_signal_coverage=0.2,
    )
    rows = _rows()
    best = search_best_thresholds(rows, cfg).best
    assert best.accuracy > 0.5
    assert best.coverage >= 0.2

