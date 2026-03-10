from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Direction = Literal["BULLISH", "BEARISH", "NEUTRAL"]


@dataclass(frozen=True)
class KlineBar:
    ts_et: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class FeatureRow:
    ts_et: datetime
    close: float
    spot_roc_1m: float
    fwd_ret_5m: float
    label_direction: Direction


@dataclass(frozen=True)
class ThresholdCandidate:
    roc_bull_threshold: float
    roc_bear_threshold: float
    accuracy: float
    coverage: float
    total_rows: int
    signal_rows: int
    scored_rows: int
    correct_rows: int

