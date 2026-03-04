"""Agent A — Spot Micro-Signal (VWAP-based).

Classifies the current spot price action relative to the anchored VWAP
as BULLISH, BEARISH, or NEUTRAL.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from l2_decision.agents.base import AgentResult
from shared.config import settings


logger = logging.getLogger(__name__)


class _PricePoint(NamedTuple):
    timestamp_mono: float
    price: float
    volume: float


class AgentA:
    """VWAP-based spot micro-signal agent.

    Uses Anchored VWAP (Volume-Weighted Average Price) to determine
    short-term directional bias.

    Signal Logic:
    - BULLISH: Price above VWAP + slope positive
    - BEARISH: Price below VWAP + slope negative
    - NEUTRAL: Price near VWAP or conflicting signals
    """

    AGENT_ID = "agent_a"

    def __init__(self) -> None:
        self._history: deque[_PricePoint] = deque(maxlen=5000)
        self._cumulative_volume: float = 0.0
        self._cumulative_pv: float = 0.0  # Price × Volume sum

    def run(self, snapshot: dict[str, Any], slope_multiplier: float = 1.0) -> AgentResult:
        """Process market snapshot and return directional signal."""
        now = datetime.now(ZoneInfo("US/Eastern"))
        now_mono = time.monotonic()

        spot = snapshot.get("spot")
        volume = snapshot.get("volume", 1.0) or 1.0

        if spot is None or spot <= 0:
            return AgentResult(
                agent=self.AGENT_ID,
                signal="NEUTRAL",
                as_of=now,
                data={"spot": spot, "reason": "no_spot"},
                summary="No spot price available.",
            )

        # Update VWAP
        self._history.append(_PricePoint(now_mono, spot, volume))
        self._cumulative_volume += volume
        self._cumulative_pv += spot * volume

        # Calculate VWAP
        if self._cumulative_volume > 0:
            vwap = self._cumulative_pv / self._cumulative_volume
        else:
            vwap = spot

        # Calculate VWAP Standard Deviation
        if len(self._history) >= 10:
            variance_sum = sum(
                (p.price - vwap) ** 2 * p.volume for p in self._history
            )
            vwap_std = (variance_sum / self._cumulative_volume) ** 0.5
        else:
            vwap_std = 0.0

        # Bands
        band1_upper = vwap + settings.agent_a_vwap_std_band_1 * vwap_std
        band1_lower = vwap - settings.agent_a_vwap_std_band_1 * vwap_std

        # VWAP Slope (price change over window)
        slope = 0.0
        window = settings.agent_a_vwap_slope_window  # 60 seconds
        cutoff = now_mono - window
        recent = [p for p in self._history if p.timestamp_mono >= cutoff]
        if len(recent) >= 2:
            slope = (recent[-1].price - recent[0].price) / len(recent)

        # Classification
        slope_threshold = settings.agent_a_vwap_slope_threshold * slope_multiplier

        if spot > band1_upper and slope > slope_threshold:
            signal = "BULLISH"
            reason = f"Above VWAP+1σ ({band1_upper:.2f}), slope={slope:.4f}"
        elif spot < band1_lower and slope < -slope_threshold:
            signal = "BEARISH"
            reason = f"Below VWAP-1σ ({band1_lower:.2f}), slope={slope:.4f}"
        else:
            signal = "NEUTRAL"
            reason = f"Near VWAP ({vwap:.2f}), slope={slope:.4f}"

        return AgentResult(
            agent=self.AGENT_ID,
            signal=signal,
            as_of=now,
            data={
                "spot": spot,
                "vwap": vwap,
                "vwap_std": vwap_std,
                "band1_upper": band1_upper,
                "band1_lower": band1_lower,
                "slope": slope,
                "reason": reason,
            },
            summary=reason,
        )

    def reset(self) -> None:
        """Reset agent state (call on day change)."""
        self._history.clear()
        self._cumulative_volume = 0.0
        self._cumulative_pv = 0.0
