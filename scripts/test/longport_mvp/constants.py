from __future__ import annotations

import re
from dataclasses import dataclass
from zoneinfo import ZoneInfo

RUN_FLAG = "RUN_LONGPORT_LIVE_MVP"
ET = ZoneInfo("America/New_York")

SIDE_ASK = "ASK_SIDE"
SIDE_BID = "BID_SIDE"
SIDE_MID = "MID_OR_UNKNOWN"

QUADRANT_PUT_ASK = "PUT_ASK"
QUADRANT_CALL_BID = "CALL_BID"
QUADRANT_PUT_BID = "PUT_BID"
QUADRANT_CALL_ASK = "CALL_ASK"

SUPPRESSION_NEUTRAL = "NEUTRAL"
SUPPRESSION_BEAR = "SUPPRESSION_BEAR"
SUPPRESSION_BULL = "SUPPRESSION_BULL"

OPTION_RE = re.compile(r"\d{6}([CP])\d+")


@dataclass(frozen=True)
class ProbeConfig:
    timeout_sec: float = 120.0
    rolling_window_sec: float = 30.0
    z_threshold: float = 2.0
    min_oi_participation: float = 0.01
    dom_threshold: float = 0.35
    hold_sec: float = 8.0
    underlying_pull_interval_sec: float = 2.5
    underlying_pull_count: int = 200
    oi_refresh_sec: float = 1.2
    oi_max_age_sec: float = 120.0
    min_oi_enriched_ratio: float = 0.60
    oi_backfill_batch_size: int = 32
    sample_interval_sec: float = 1.0


DEFAULT_CONFIG = ProbeConfig()
