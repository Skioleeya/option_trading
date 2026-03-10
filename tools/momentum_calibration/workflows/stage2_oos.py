from __future__ import annotations

import argparse
from datetime import date
import logging

from tools.momentum_calibration.config import CalibrationConfig, with_live_defaults
from tools.momentum_calibration.eval.oos_eval import evaluate_oos
from tools.momentum_calibration.features.kline_features import build_feature_rows
from tools.momentum_calibration.io.report_writer import write_oos_metrics
from tools.momentum_calibration.models import ThresholdCandidate
from tools.momentum_calibration.sources.longbridge_kline import LongbridgeKlineSource
from tools.momentum_calibration.workflows.common import (
    load_train_metrics,
    previous_month_window,
    resolve_output_root,
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage2 MOMENTUM OOS validation")
    p.add_argument("--symbol", default="SPY.US", help="Longbridge symbol, default SPY.US")
    p.add_argument("--train-run-id", required=True, help="Stage1 run_id")
    return p.parse_args()


def _to_candidate(d: dict[str, object]) -> ThresholdCandidate:
    return ThresholdCandidate(
        roc_bull_threshold=float(d.get("roc_bull_threshold", 0.0015)),
        roc_bear_threshold=float(d.get("roc_bear_threshold", -0.0015)),
        accuracy=float(d.get("accuracy", 0.0)),
        coverage=float(d.get("coverage", 0.0)),
        total_rows=int(d.get("total_rows", 0)),
        signal_rows=int(d.get("signal_rows", 0)),
        scored_rows=int(d.get("scored_rows", 0)),
        correct_rows=int(d.get("correct_rows", 0)),
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    cfg = with_live_defaults(CalibrationConfig(symbol=str(args.symbol).strip().upper()))
    output_root = resolve_output_root(cfg)

    train_metrics = load_train_metrics(output_root, args.train_run_id)
    selected = train_metrics.get("selected_thresholds")
    if not isinstance(selected, dict):
        raise RuntimeError("invalid train metrics: selected_thresholds missing")
    candidate = _to_candidate(selected)

    train_start_raw = train_metrics.get("train_start_et")
    if not isinstance(train_start_raw, str):
        raise RuntimeError("invalid train metrics: train_start_et missing")
    train_start = date.fromisoformat(train_start_raw)
    oos_start, oos_end = previous_month_window(train_start, calendar_days=cfg.month_calendar_days)

    source = LongbridgeKlineSource(cfg)
    bars, fetch_stats = source.fetch_range(cfg.symbol, start_date=oos_start, end_date=oos_end)
    rows = build_feature_rows(bars, horizon_minutes=5)
    if not rows:
        raise RuntimeError("no feature rows built for OOS window")

    metrics = evaluate_oos(rows, candidate)
    metrics["fetch_stats"] = {
        "request_count": fetch_stats.request_count,
        "retry_count": fetch_stats.retry_count,
        "bar_count": fetch_stats.bar_count,
        "feature_rows": len(rows),
    }

    out_dir = output_root / args.train_run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = write_oos_metrics(
        out_dir,
        train_run_id=args.train_run_id,
        symbol=cfg.symbol,
        oos_start=oos_start.isoformat(),
        oos_end=oos_end.isoformat(),
        metrics=metrics,
    )

    logger.info(
        "[Stage2] run_id=%s oos=%s..%s acc=%.4f cov=%.4f",
        args.train_run_id,
        oos_start.isoformat(),
        oos_end.isoformat(),
        float(metrics.get("accuracy", 0.0)),
        float(metrics.get("coverage", 0.0)),
    )
    logger.info("[Stage2] metrics: %s", path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

