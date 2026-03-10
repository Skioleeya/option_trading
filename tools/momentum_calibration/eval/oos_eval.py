from __future__ import annotations

from dataclasses import asdict

from tools.momentum_calibration.models import FeatureRow, ThresholdCandidate
from tools.momentum_calibration.optimize.roc_threshold_search import evaluate_candidate


def evaluate_oos(rows: list[FeatureRow], candidate: ThresholdCandidate) -> dict[str, object]:
    out = evaluate_candidate(
        rows,
        bull_threshold=candidate.roc_bull_threshold,
        bear_threshold=candidate.roc_bear_threshold,
    )
    d = asdict(out)
    d["window"] = "oos_prev_month"
    return d

