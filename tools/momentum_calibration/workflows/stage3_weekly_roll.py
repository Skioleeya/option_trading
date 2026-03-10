from __future__ import annotations

import argparse
from datetime import timedelta
import logging

from tools.momentum_calibration.config import CalibrationConfig, build_run_id, parse_et_date, with_live_defaults
from tools.momentum_calibration.features.kline_features import build_feature_rows, slice_last_trade_days
from tools.momentum_calibration.io.report_writer import ensure_output_dir, write_json, write_weekly_roll_csv
from tools.momentum_calibration.optimize.roc_threshold_search import search_best_thresholds
from tools.momentum_calibration.sources.longbridge_kline import LongbridgeKlineSource
from tools.momentum_calibration.workflows.common import resolve_output_root

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage3 weekly rolling MOMENTUM re-estimation")
    p.add_argument("--symbol", default="SPY.US", help="Longbridge symbol, default SPY.US")
    p.add_argument("--anchor-date", default=None, help="ET date in YYYY-MM-DD; default today")
    p.add_argument("--weeks", type=int, default=None, help="Number of weekly checkpoints, default from config")
    return p.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    cfg = with_live_defaults(CalibrationConfig(symbol=str(args.symbol).strip().upper()))
    weeks = max(1, int(args.weeks or cfg.rolling_weeks))
    anchor_date = parse_et_date(args.anchor_date)

    earliest_week_end = anchor_date - timedelta(days=7 * (weeks - 1))
    # 60 calendar days gives enough room for 22 trading-day slices.
    fetch_start = earliest_week_end - timedelta(days=60)

    source = LongbridgeKlineSource(cfg)
    bars, fetch_stats = source.fetch_range(cfg.symbol, start_date=fetch_start, end_date=anchor_date)
    all_rows = build_feature_rows(bars, horizon_minutes=5)
    if not all_rows:
        raise RuntimeError("no feature rows built for rolling stage")

    weekly_rows: list[dict[str, object]] = []
    for idx in range(weeks):
        week_end = earliest_week_end + timedelta(days=7 * idx)
        train_rows = slice_last_trade_days(
            all_rows,
            end_date=week_end,
            trade_days=cfg.rolling_trade_days,
        )
        if not train_rows:
            continue
        summary = search_best_thresholds(train_rows, cfg)
        train_start = min(r.ts_et.date() for r in train_rows)
        train_end = max(r.ts_et.date() for r in train_rows)
        best = summary.best
        weekly_rows.append(
            {
                "week_end_et": week_end.isoformat(),
                "train_start_et": train_start.isoformat(),
                "train_end_et": train_end.isoformat(),
                "roc_bull_threshold": f"{best.roc_bull_threshold:.6f}",
                "roc_bear_threshold": f"{best.roc_bear_threshold:.6f}",
                "accuracy": f"{best.accuracy:.6f}",
                "coverage": f"{best.coverage:.6f}",
                "total_rows": best.total_rows,
                "signal_rows": best.signal_rows,
                "scored_rows": best.scored_rows,
                "correct_rows": best.correct_rows,
            }
        )

    if not weekly_rows:
        raise RuntimeError("weekly rolling produced no rows")

    output_root = resolve_output_root(cfg)
    run_id = build_run_id("stage3", cfg.symbol)
    out_dir = ensure_output_dir(output_root, run_id)
    csv_path = write_weekly_roll_csv(out_dir, weekly_rows)
    write_json(
        out_dir / "metrics_roll.json",
        {
            "run_id": run_id,
            "stage": "stage3_weekly_roll",
            "symbol": cfg.symbol,
            "anchor_date_et": anchor_date.isoformat(),
            "weeks": weeks,
            "rolling_trade_days": cfg.rolling_trade_days,
            "fetch_stats": {
                "request_count": fetch_stats.request_count,
                "retry_count": fetch_stats.retry_count,
                "bar_count": fetch_stats.bar_count,
                "feature_rows": len(all_rows),
            },
            "rows": len(weekly_rows),
        },
    )
    logger.info("[Stage3] run_id=%s rows=%d", run_id, len(weekly_rows))
    logger.info("[Stage3] csv: %s", csv_path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

