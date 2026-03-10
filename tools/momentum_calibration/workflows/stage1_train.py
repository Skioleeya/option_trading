from __future__ import annotations

import argparse
from datetime import datetime
import logging
from zoneinfo import ZoneInfo

from tools.momentum_calibration.config import CalibrationConfig, build_run_id, parse_et_date, with_live_defaults
from tools.momentum_calibration.features.kline_features import build_feature_rows
from tools.momentum_calibration.io.report_writer import (
    ensure_output_dir,
    write_candidate_yaml,
    write_train_metrics,
)
from tools.momentum_calibration.optimize.roc_threshold_search import search_best_thresholds
from tools.momentum_calibration.sources.longbridge_kline import LongbridgeKlineSource
from tools.momentum_calibration.sources.research_adapter import ResearchFeatureProvider
from tools.momentum_calibration.workflows.common import month_window, resolve_output_root

ET = ZoneInfo("America/New_York")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage1 MOMENTUM threshold training (K-line only phase)")
    p.add_argument("--symbol", default="SPY.US", help="Longbridge symbol, default SPY.US")
    p.add_argument("--end-date", default=None, help="ET date in YYYY-MM-DD; default today")
    return p.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()

    cfg = with_live_defaults(CalibrationConfig(symbol=str(args.symbol).strip().upper()))
    end_date = parse_et_date(args.end_date)
    train_start, train_end = month_window(end_date, calendar_days=cfg.month_calendar_days)

    source = LongbridgeKlineSource(cfg)
    bars, fetch_stats = source.fetch_range(cfg.symbol, start_date=train_start, end_date=train_end)
    rows = build_feature_rows(bars, horizon_minutes=5)
    if not rows:
        raise RuntimeError("no feature rows built for stage1 training window")

    research_provider = ResearchFeatureProvider()
    research_df = research_provider.load(
        datetime.combine(train_start, datetime.min.time(), tzinfo=ET),
        datetime.combine(train_end, datetime.min.time(), tzinfo=ET),
        cfg.symbol,
    )

    summary = search_best_thresholds(rows, cfg)
    output_root = resolve_output_root(cfg)
    run_id = build_run_id("stage1", cfg.symbol)
    out_dir = ensure_output_dir(output_root, run_id)

    candidate_path = write_candidate_yaml(
        out_dir,
        cfg=cfg,
        candidate=summary.best,
        run_id=run_id,
        train_start=train_start.isoformat(),
        train_end=train_end.isoformat(),
    )
    metrics_path = write_train_metrics(
        out_dir,
        cfg=cfg,
        run_id=run_id,
        train_start=train_start.isoformat(),
        train_end=train_end.isoformat(),
        best=summary.best,
        grid_size=summary.grid_size,
        fetch_stats={
            "request_count": fetch_stats.request_count,
            "retry_count": fetch_stats.retry_count,
            "bar_count": fetch_stats.bar_count,
            "feature_rows": len(rows),
        },
        research_available=research_df is not None,
    )

    logger.info("[Stage1] run_id=%s", run_id)
    logger.info(
        "[Stage1] best bull=%.6f bear=%.6f acc=%.4f cov=%.4f rows=%d",
        summary.best.roc_bull_threshold,
        summary.best.roc_bear_threshold,
        summary.best.accuracy,
        summary.best.coverage,
        summary.best.total_rows,
    )
    logger.info("[Stage1] candidate: %s", candidate_path.as_posix())
    logger.info("[Stage1] metrics: %s", metrics_path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

