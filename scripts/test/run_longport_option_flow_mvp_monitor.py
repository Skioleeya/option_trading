from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from scripts.test.longport_mvp.constants import DEFAULT_CONFIG
from scripts.test.longport_mvp.csv_monitor import FlowCsvMonitor
from scripts.test.longport_mvp.live_probe import run_live_probe


def _build_csv_path() -> Path:
    script_dir = Path(__file__).resolve().parent
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return script_dir / f"longport_option_flow_monitor_{stamp}.csv"


async def _main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger = logging.getLogger("mvp.monitor.runner")
    logger.info(
        "start monitor | duration=%.0fs oi_refresh=%.2fs underlying_pull=%.2fs sample_interval=%.2fs "
        "| longport_limit=req<=10/s concurrent<=5",
        DEFAULT_CONFIG.timeout_sec,
        DEFAULT_CONFIG.oi_refresh_sec,
        DEFAULT_CONFIG.underlying_pull_interval_sec,
        DEFAULT_CONFIG.sample_interval_sec,
    )

    csv_path = _build_csv_path()
    monitor = FlowCsvMonitor(csv_path)
    try:
        stats = await run_live_probe(DEFAULT_CONFIG, sample_hook=monitor.write)
    finally:
        monitor.close()

    logger.info(
        "monitor done | csv=%s depth=%d trades=%d classified=%d oi_enriched=%d ratio=%.3f large=%d "
        "fetch_snapshot_calls=%d option_quote_calls=%d underlying_pull_calls=%d "
        "net_delta=%.4f net_gamma=%.4f filtered=%d complex=%d suppression=%s dominance=%.4f",
        csv_path,
        stats.depth_events,
        stats.trade_events,
        stats.classified_total,
        stats.oi_enriched_events,
        stats.oi_enriched_ratio,
        stats.large_flow_hits,
        stats.fetch_snapshot_calls,
        stats.option_quote_calls,
        stats.underlying_pull_calls,
        stats.net_delta_exposure_live,
        stats.net_gamma_exposure_live,
        stats.condition_filtered_count,
        stats.complex_spread_count,
        stats.suppression_state,
        stats.dominance_latest,
    )
    print(f"CSV_PATH={csv_path}")


if __name__ == "__main__":
    asyncio.run(_main())
