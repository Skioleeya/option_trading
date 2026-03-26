from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

import numpy as np

from l1_compute.output.enriched_snapshot import (
    AggregateGreeks as OutAggregateGreeks,
    ComputeQualityReport,
    EnrichedSnapshot,
    MicroSignals,
)

_ET = ZoneInfo("US/Eastern")


def extract_atm_iv(
    strikes: np.ndarray,
    ivs: np.ndarray,
    spot: float,
) -> float:
    """Return IV of the option strike closest to ATM."""
    if len(strikes) == 0:
        return 0.0
    idx = int(np.argmin(np.abs(strikes - spot)))
    return float(ivs[idx]) if ivs[idx] > 0 else 0.0


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
