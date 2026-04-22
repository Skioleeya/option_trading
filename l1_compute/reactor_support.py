from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from l1_compute.output.enriched_snapshot import (
    AggregateGreeks as OutAggregateGreeks,
    ComputeQualityReport,
    EnrichedSnapshot,
    MicroSignals,
)
from shared.services.atm_iv import extract_atm_iv_value

_ET = ZoneInfo("US/Eastern")


def extract_atm_iv(
    strikes: Any,
    ivs: Any,
    spot: float,
) -> float:
    return extract_atm_iv_value(strikes=strikes, ivs=ivs, spot=spot)


def empty_snapshot(
    l0_version: int,
    extra_metadata: Optional[dict[str, Any]] = None,
) -> EnrichedSnapshot:
    return EnrichedSnapshot(
        spot=0.0,
        chain=None,
        aggregates=OutAggregateGreeks(),
        microstructure=MicroSignals(),
        quality=ComputeQualityReport(),
        ttm_seconds=0.0,
        version=l0_version,
        computed_at=datetime.now(_ET),
        extra_metadata=dict(extra_metadata or {}),
    )
