from __future__ import annotations

from dataclasses import dataclass

from tools.momentum_calibration.config import CalibrationConfig
from tools.momentum_calibration.models import Direction, FeatureRow, ThresholdCandidate


def _frange(start: float, stop: float, step: float) -> list[float]:
    if step <= 0:
        return [round(start, 6)]
    n = int(round((stop - start) / step))
    return [round(start + (i * step), 6) for i in range(max(0, n) + 1)]


def predict_direction(spot_roc_1m: float, *, bull_threshold: float, bear_threshold: float) -> Direction:
    if spot_roc_1m > bull_threshold:
        return "BULLISH"
    if spot_roc_1m < bear_threshold:
        return "BEARISH"
    return "NEUTRAL"


@dataclass(frozen=True)
class SearchSummary:
    best: ThresholdCandidate
    grid_size: int
    objective: str = "fwd_5m_direction_accuracy"


def evaluate_candidate(
    rows: list[FeatureRow],
    *,
    bull_threshold: float,
    bear_threshold: float,
) -> ThresholdCandidate:
    total = len(rows)
    signal_rows = 0
    scored_rows = 0
    correct_rows = 0

    for row in rows:
        pred = predict_direction(row.spot_roc_1m, bull_threshold=bull_threshold, bear_threshold=bear_threshold)
        if pred == "NEUTRAL":
            continue
        signal_rows += 1
        if row.label_direction == "NEUTRAL":
            continue
        scored_rows += 1
        if pred == row.label_direction:
            correct_rows += 1

    coverage = (signal_rows / total) if total > 0 else 0.0
    accuracy = (correct_rows / scored_rows) if scored_rows > 0 else 0.0
    return ThresholdCandidate(
        roc_bull_threshold=bull_threshold,
        roc_bear_threshold=bear_threshold,
        accuracy=accuracy,
        coverage=coverage,
        total_rows=total,
        signal_rows=signal_rows,
        scored_rows=scored_rows,
        correct_rows=correct_rows,
    )


def search_best_thresholds(rows: list[FeatureRow], cfg: CalibrationConfig) -> SearchSummary:
    bulls = _frange(cfg.bull_grid_min, cfg.bull_grid_max, cfg.bull_grid_step)
    bears = _frange(cfg.bear_grid_min, cfg.bear_grid_max, cfg.bear_grid_step)

    all_results: list[ThresholdCandidate] = []
    for bull in bulls:
        for bear in bears:
            if bear >= -1e-9:
                continue
            all_results.append(evaluate_candidate(rows, bull_threshold=bull, bear_threshold=bear))

    if not all_results:
        fallback = evaluate_candidate(rows, bull_threshold=0.0015, bear_threshold=-0.0015)
        return SearchSummary(best=fallback, grid_size=0)

    constrained = [r for r in all_results if r.coverage >= cfg.min_signal_coverage]
    target_pool = constrained if constrained else all_results

    best = max(
        target_pool,
        key=lambda r: (r.accuracy, r.coverage, r.signal_rows, -abs(r.roc_bull_threshold + r.roc_bear_threshold)),
    )
    return SearchSummary(best=best, grid_size=len(all_results))

