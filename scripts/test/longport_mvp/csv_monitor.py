from __future__ import annotations

import csv
from pathlib import Path
from typing import TextIO

from .models import LiveSample


class FlowCsvMonitor:
    def __init__(self, csv_path: Path) -> None:
        self.csv_path = csv_path
        self._fp: TextIO = csv_path.open("w", encoding="utf-8", newline="")
        self._writer = csv.writer(self._fp)
        self._writer.writerow(
            [
                "timestamp_et",
                "elapsed_sec",
                "depth_events",
                "trade_events",
                "classified_total",
                "oi_enriched_events",
                "oi_enriched_ratio",
                "oi_symbols_cached",
                "large_flow_hits",
                "suppression_state",
                "dominance_latest",
                "underlying_tape_samples",
                "fetch_snapshot_calls",
                "option_quote_calls",
                "underlying_pull_calls",
                "net_delta_exposure_live",
                "net_gamma_exposure_live",
                "midpoint_tickrule_count",
                "condition_filtered_count",
                "complex_spread_count",
                "residual_delta_after_netting",
                "greek_stale_reads",
                "put_ask_hits",
                "call_bid_hits",
                "put_bid_hits",
                "call_ask_hits",
            ]
        )
        self._fp.flush()

    def write(self, sample: LiveSample) -> None:
        self._writer.writerow(
            [
                sample.timestamp_et,
                f"{sample.elapsed_sec:.2f}",
                sample.depth_events,
                sample.trade_events,
                sample.classified_total,
                sample.oi_enriched_events,
                f"{sample.oi_enriched_ratio:.6f}",
                sample.oi_symbols_cached,
                sample.large_flow_hits,
                sample.suppression_state,
                f"{sample.dominance_latest:.6f}",
                sample.underlying_tape_samples,
                sample.fetch_snapshot_calls,
                sample.option_quote_calls,
                sample.underlying_pull_calls,
                f"{sample.net_delta_exposure_live:.6f}",
                f"{sample.net_gamma_exposure_live:.6f}",
                sample.midpoint_tickrule_count,
                sample.condition_filtered_count,
                sample.complex_spread_count,
                f"{sample.residual_delta_after_netting:.6f}",
                sample.greek_stale_reads,
                sample.put_ask_hits,
                sample.call_bid_hits,
                sample.put_bid_hits,
                sample.call_ask_hits,
            ]
        )
        self._fp.flush()

    def close(self) -> None:
        self._fp.close()
