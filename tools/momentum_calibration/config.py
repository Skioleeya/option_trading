from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
import re
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
_LIVE_SIGNAL_CFG = Path("l2_decision/config/signals/momentum_signal.yaml")


@dataclass(frozen=True)
class CalibrationConfig:
    symbol: str = "SPY.US"

    # Longbridge budget for coexistence with live backend.
    max_rps: float = 3.0
    max_concurrency: int = 2
    max_retries: int = 5
    initial_backoff_seconds: float = 0.5
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 8.0

    # Window strategy
    month_calendar_days: int = 31
    rolling_trade_days: int = 22
    rolling_weeks: int = 12

    # Search grid
    bull_grid_min: float = 0.0005
    bull_grid_max: float = 0.0040
    bull_grid_step: float = 0.00025
    bear_grid_min: float = -0.0040
    bear_grid_max: float = -0.0005
    bear_grid_step: float = 0.00025
    min_signal_coverage: float = 0.15

    # Frozen in this phase (do not optimize)
    bbo_confirmation_min: float = 0.1
    max_roc_reference: float = 0.005
    confidence_floor: float = 0.3

    output_root: Path = Path("tools/momentum_calibration/outputs")


def parse_et_date(raw: str | None) -> date:
    if raw:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    return datetime.now(ET).date()


def build_run_id(stage: str, symbol: str, *, ts: datetime | None = None) -> str:
    now = (ts or datetime.now(ET)).strftime("%Y%m%d_%H%M%S")
    s = symbol.replace(".", "_")
    return f"{stage}_{s}_{now}"


def _extract_numeric(text: str, key: str) -> float | None:
    pattern = rf"^\s*{re.escape(key)}\s*:\s*([-+]?\d*\.?\d+)"
    for line in text.splitlines():
        m = re.search(pattern, line)
        if m:
            return float(m.group(1))
    return None


def load_live_momentum_defaults(path: Path = _LIVE_SIGNAL_CFG) -> dict[str, float]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    out: dict[str, float] = {}
    for key in ("bbo_confirmation_min", "max_roc_reference", "confidence_floor"):
        val = _extract_numeric(text, key)
        if val is not None:
            out[key] = val
    return out


def with_live_defaults(cfg: CalibrationConfig) -> CalibrationConfig:
    values = load_live_momentum_defaults()
    if not values:
        return cfg
    return replace(
        cfg,
        bbo_confirmation_min=values.get("bbo_confirmation_min", cfg.bbo_confirmation_min),
        max_roc_reference=values.get("max_roc_reference", cfg.max_roc_reference),
        confidence_floor=values.get("confidence_floor", cfg.confidence_floor),
    )

