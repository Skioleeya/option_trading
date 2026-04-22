from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from .constants import (
    QUADRANT_CALL_ASK,
    QUADRANT_CALL_BID,
    QUADRANT_PUT_ASK,
    QUADRANT_PUT_BID,
    SUPPRESSION_NEUTRAL,
)


@dataclass
class LiveStats:
    depth_events: int = 0
    trade_events: int = 0
    classified_total: int = 0
    oi_enriched_events: int = 0
    oi_symbols_cached: int = 0
    oi_backfill_batches: int = 0
    oi_backfill_failures: int = 0
    underlying_tape_samples: int = 0
    underlying_pull_failures: int = 0
    large_flow_hits: int = 0
    last_zscore: float = 0.0
    suppression_state: str = SUPPRESSION_NEUTRAL
    dominance_latest: float = 0.0
    quadrant_hits: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    large_hits_by_quadrant: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    fetch_snapshot_calls: int = 0
    option_quote_calls: int = 0
    underlying_pull_calls: int = 0
    net_delta_exposure_live: float = 0.0
    net_gamma_exposure_live: float = 0.0
    midpoint_tickrule_count: int = 0
    condition_filtered_count: int = 0
    complex_spread_count: int = 0
    residual_delta_after_netting: float = 0.0
    greek_stale_reads: int = 0
    start_et: str = ""
    end_et: str = ""

    @property
    def oi_enriched_ratio(self) -> float:
        if self.classified_total <= 0:
            return 0.0
        return float(self.oi_enriched_events) / float(self.classified_total)

    def quadrant_snapshot(self) -> tuple[int, int, int, int]:
        return (
            self.quadrant_hits.get(QUADRANT_PUT_ASK, 0),
            self.quadrant_hits.get(QUADRANT_CALL_BID, 0),
            self.quadrant_hits.get(QUADRANT_PUT_BID, 0),
            self.quadrant_hits.get(QUADRANT_CALL_ASK, 0),
        )


@dataclass(frozen=True)
class LiveSample:
    timestamp_et: str
    elapsed_sec: float
    depth_events: int
    trade_events: int
    classified_total: int
    oi_enriched_events: int
    oi_enriched_ratio: float
    oi_symbols_cached: int
    large_flow_hits: int
    suppression_state: str
    dominance_latest: float
    underlying_tape_samples: int
    fetch_snapshot_calls: int
    option_quote_calls: int
    underlying_pull_calls: int
    net_delta_exposure_live: float
    net_gamma_exposure_live: float
    midpoint_tickrule_count: int
    condition_filtered_count: int
    complex_spread_count: int
    residual_delta_after_netting: float
    greek_stale_reads: int
    put_ask_hits: int
    call_bid_hits: int
    put_bid_hits: int
    call_ask_hits: int


_CONTRACT_RE = re.compile(r"(\d{6})([CP])(\d+)")


def contract_identity(symbol: str) -> tuple[str, str]:
    match = _CONTRACT_RE.search(symbol.upper())
    if match is None:
        return "", ""
    return match.group(1), match.group(3)
