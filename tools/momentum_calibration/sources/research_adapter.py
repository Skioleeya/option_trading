from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ResearchFeatureProvider:
    """Reserved adapter for future research feature integration.

    Current phase intentionally returns None because local research history
    is insufficient for reliable calibration.
    """

    def load(self, start_et: datetime, end_et: datetime, symbol: str) -> Any | None:
        logger.info(
            "[MomentumCalibration] ResearchFeatureProvider unavailable: start=%s end=%s symbol=%s",
            start_et.isoformat(),
            end_et.isoformat(),
            symbol,
        )
        return None

