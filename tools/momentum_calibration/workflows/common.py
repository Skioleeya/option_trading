from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any

from tools.momentum_calibration.config import CalibrationConfig


def month_window(end_date: date, *, calendar_days: int) -> tuple[date, date]:
    start = end_date - timedelta(days=max(1, calendar_days) - 1)
    return start, end_date


def previous_month_window(train_start: date, *, calendar_days: int) -> tuple[date, date]:
    oos_end = train_start - timedelta(days=1)
    oos_start = oos_end - timedelta(days=max(1, calendar_days) - 1)
    return oos_start, oos_end


def load_train_metrics(output_root: Path, run_id: str) -> dict[str, Any]:
    path = output_root / run_id / "metrics_train.json"
    if not path.exists():
        raise FileNotFoundError(f"train metrics not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_output_root(cfg: CalibrationConfig) -> Path:
    cfg.output_root.mkdir(parents=True, exist_ok=True)
    return cfg.output_root

