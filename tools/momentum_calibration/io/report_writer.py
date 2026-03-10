from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import csv
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from tools.momentum_calibration.config import CalibrationConfig
from tools.momentum_calibration.models import ThresholdCandidate

ET = ZoneInfo("America/New_York")


def ensure_output_dir(root: Path, run_id: str) -> Path:
    out = root / run_id
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_candidate_yaml(
    out_dir: Path,
    *,
    cfg: CalibrationConfig,
    candidate: ThresholdCandidate,
    run_id: str,
    train_start: str,
    train_end: str,
) -> Path:
    path = out_dir / "candidate_momentum_signal.yaml"
    rows = [
        'signal_name: "momentum_signal"',
        f'version: "calibrated-{run_id}"',
        'description: "Offline calibrated with Longbridge 1m kline (K-line only phase)."',
        "parameters:",
        f"  roc_bull_threshold: {candidate.roc_bull_threshold:.6f}",
        f"  roc_bear_threshold: {candidate.roc_bear_threshold:.6f}",
        f"  bbo_confirmation_min: {cfg.bbo_confirmation_min:.6f}",
        f"  max_roc_reference: {cfg.max_roc_reference:.6f}",
        f"  confidence_floor: {cfg.confidence_floor:.6f}",
        "calibration:",
        '  objective: "fwd_5m_direction_accuracy"',
        f'  symbol: "{cfg.symbol}"',
        f'  train_start_et: "{train_start}"',
        f'  train_end_et: "{train_end}"',
        f"  accuracy: {candidate.accuracy:.6f}",
        f"  coverage: {candidate.coverage:.6f}",
        f"  total_rows: {candidate.total_rows}",
        f"  signal_rows: {candidate.signal_rows}",
        f"  scored_rows: {candidate.scored_rows}",
        f"  correct_rows: {candidate.correct_rows}",
        f'  generated_at_et: "{datetime.now(ET).isoformat()}"',
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def write_train_metrics(
    out_dir: Path,
    *,
    cfg: CalibrationConfig,
    run_id: str,
    train_start: str,
    train_end: str,
    best: ThresholdCandidate,
    grid_size: int,
    fetch_stats: dict[str, object],
    research_available: bool,
) -> Path:
    path = out_dir / "metrics_train.json"
    payload = {
        "run_id": run_id,
        "stage": "stage1_train",
        "objective": "fwd_5m_direction_accuracy",
        "symbol": cfg.symbol,
        "train_start_et": train_start,
        "train_end_et": train_end,
        "selected_thresholds": asdict(best),
        "frozen_params": {
            "bbo_confirmation_min": cfg.bbo_confirmation_min,
            "max_roc_reference": cfg.max_roc_reference,
            "confidence_floor": cfg.confidence_floor,
        },
        "search": {"grid_size": grid_size, "min_signal_coverage": cfg.min_signal_coverage},
        "fetch_stats": fetch_stats,
        "research_available": research_available,
        "generated_at_et": datetime.now(ET).isoformat(),
    }
    write_json(path, payload)
    return path


def write_oos_metrics(
    out_dir: Path,
    *,
    train_run_id: str,
    symbol: str,
    oos_start: str,
    oos_end: str,
    metrics: dict[str, object],
) -> Path:
    path = out_dir / "metrics_oos.json"
    payload = {
        "train_run_id": train_run_id,
        "stage": "stage2_oos",
        "symbol": symbol,
        "oos_start_et": oos_start,
        "oos_end_et": oos_end,
        "metrics": metrics,
        "generated_at_et": datetime.now(ET).isoformat(),
    }
    write_json(path, payload)
    return path


def write_weekly_roll_csv(out_dir: Path, rows: list[dict[str, object]]) -> Path:
    path = out_dir / "weekly_roll.csv"
    headers = [
        "week_end_et",
        "train_start_et",
        "train_end_et",
        "roc_bull_threshold",
        "roc_bear_threshold",
        "accuracy",
        "coverage",
        "total_rows",
        "signal_rows",
        "scored_rows",
        "correct_rows",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h) for h in headers})
    return path

