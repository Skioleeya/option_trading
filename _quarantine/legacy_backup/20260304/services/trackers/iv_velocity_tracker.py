"""IV Velocity Tracker for Agent B1 v2.0.

Tracks the rate of change of ATM IV relative to Spot price movement
to classify microstructure states (PAID_MOVE, ORGANIC_GRIND, etc.).
"""

from __future__ import annotations

import time
from collections import deque
from datetime import datetime
from typing import NamedTuple
from zoneinfo import ZoneInfo

from app.config import settings
from app.models.microstructure import IVVelocityResult, IVVelocityState


class _DataPoint(NamedTuple):
    timestamp_mono: float
    spot: float
    iv: float


class IVVelocityTracker:
    """Tracks IV velocity (rate of change) and classifies divergence states.

    Compares Spot RoC vs IV RoC to detect:
    - PAID_MOVE: Both spot and IV moving together (real conviction)
    - ORGANIC_GRIND: Spot moving but IV stable (trend without panic)
    - HOLLOW_RISE: Spot up but IV down (gamma-assisted, weak)
    - HOLLOW_DROP: Spot down but IV down (fake breakdown)
    - PAID_DROP: Spot down and IV up (panic selling, genuine fear)
    - VOL_EXPANSION: IV spiking without spot move
    - EXHAUSTION: Big spot move but IV collapsing
    """

    def __init__(self, window_seconds: float = 120.0):
        self._window_seconds = window_seconds
        self._history: deque[_DataPoint] = deque(maxlen=300)
        self._last_result: IVVelocityResult | None = None

    def update(
        self,
        *,
        spot: float | None,
        atm_iv: float | None,
        sim_clock_mono: float | None = None,
    ) -> IVVelocityResult:
        """Update tracker with new data point."""
        now_mono = sim_clock_mono if sim_clock_mono is not None else time.monotonic()

        if spot is None or atm_iv is None or atm_iv <= 0:
            return IVVelocityResult(state=IVVelocityState.UNAVAILABLE)

        self._history.append(_DataPoint(now_mono, spot, atm_iv))

        # Prune old data
        cutoff = now_mono - self._window_seconds
        while self._history and self._history[0].timestamp_mono < cutoff:
            self._history.popleft()

        if len(self._history) < 10:
            return IVVelocityResult(state=IVVelocityState.UNAVAILABLE)

        # Calculate RoC
        oldest = self._history[0]
        newest = self._history[-1]

        spot_roc = ((newest.spot - oldest.spot) / oldest.spot) * 100.0  # %
        iv_roc = newest.iv - oldest.iv  # Percentage points

        # Classify state
        state = self._classify(spot_roc, iv_roc)

        # Confidence based on magnitude
        magnitude = abs(spot_roc) + abs(iv_roc)
        confidence = min(1.0, magnitude / 5.0)

        result = IVVelocityResult(
            state=state,
            confidence=confidence,
            iv_roc=iv_roc,
            spot_roc=spot_roc,
            divergence_score=abs(spot_roc) - abs(iv_roc),
        )
        self._last_result = result
        return result

    def _classify(self, spot_roc: float, iv_roc: float) -> IVVelocityState:
        """Classify IV velocity state based on Spot RoC vs IV RoC."""
        spot_threshold = settings.spot_roc_threshold_pct  # 0.03%
        iv_threshold = settings.iv_roc_threshold_pct      # 2.0 pp

        spot_up = spot_roc > spot_threshold
        spot_down = spot_roc < -spot_threshold
        spot_flat = not spot_up and not spot_down

        iv_up = iv_roc > iv_threshold
        iv_down = iv_roc < -iv_threshold
        iv_flat = not iv_up and not iv_down

        # Classification matrix
        if spot_up and iv_up:
            return IVVelocityState.PAID_MOVE
        elif spot_up and iv_flat:
            return IVVelocityState.ORGANIC_GRIND
        elif spot_up and iv_down:
            return IVVelocityState.HOLLOW_RISE
        elif spot_down and iv_up:
            return IVVelocityState.PAID_DROP
        elif spot_down and iv_down:
            return IVVelocityState.HOLLOW_DROP
        elif spot_down and iv_flat:
            return IVVelocityState.ORGANIC_GRIND
        elif spot_flat and iv_up:
            return IVVelocityState.VOL_EXPANSION
        elif spot_flat and iv_down:
            # Large prior spot move + IV now collapsing = exhaustion
            if abs(spot_roc) > spot_threshold * 3:
                return IVVelocityState.EXHAUSTION
            return IVVelocityState.UNAVAILABLE
        else:
            return IVVelocityState.UNAVAILABLE

    def get_confidence(self) -> float:
        """Return confidence of last result."""
        return self._last_result.confidence if self._last_result else 0.0

    def reset(self) -> None:
        """Reset tracker state."""
        self._history.clear()
        self._last_result = None
