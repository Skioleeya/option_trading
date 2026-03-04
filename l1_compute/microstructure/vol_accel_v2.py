"""Volume Acceleration v2 — Adaptive Volume Acceleration Ratio.

Improvements over VolumeImbalanceEngine (v1):
    1. Session-phase-adaptive baseline window (open/mid/close)
    2. Dynamic threshold from daily percentile rank (vs fixed 3.0)
    3. Volume Entropy: measures trade dispersion (detects wash trading)
    4. ndm_rust bridge interface reserved for Phase 2

Session phases:
    OPEN  (9:30-10:00 ET): narrow window (10-tick EMA), higher alert sensitivity
    MID   (10:00-15:30 ET): standard 60-tick EMA
    CLOSE (15:30-16:00 ET): wider 30-tick EMA, elevated tail alert

Volume Entropy formula:
    H = -Σ(p_i × log(p_i))   where p_i = vol_i / total_vol (over window)
    High entropy = volume uniformly distributed across contracts (noise)
    Low entropy  = volume concentrated (directional, potential institutional)
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# EMA decay factors per session phase
_EMA_ALPHA: dict[str, float] = {
    "open":  2.0 / (10.0 + 1.0),   # 10-tick window
    "mid":   2.0 / (60.0 + 1.0),   # 60-tick window
    "close": 2.0 / (30.0 + 1.0),   # 30-tick window
}
# Percentile buffer length for dynamic threshold
_PERCENTILE_BUFFER: int = 200


class SessionPhase(str, Enum):
    PRE_MARKET = "pre_market"
    OPEN       = "open"
    MID        = "mid"
    CLOSE      = "close"
    POST_MARKET = "post_market"


@dataclass
class VolAccelSignal:
    """Volume acceleration signal with entropy."""
    ratio: float                  # tick_vol / EMA_baseline
    threshold: float              # dynamic threshold (percentile-based)
    is_elevated: bool             # ratio >= threshold
    entropy: float                # volume entropy [0, log(N)]
    phase: SessionPhase           # session phase at computation time
    ema_vol: float                # current EMA volume baseline
    tick_vol: float               # most recent tick volume
    percentile_rank: float        # ratio's rank in recent history [0, 1]


class VolAccelV2:
    """Adaptive Volume Acceleration Ratio calculator.

    Usage::

        va = VolAccelV2()
        signal = va.update(
            tick_volume=1500,
            phase=SessionPhase.MID,
            per_contract_volumes={"SPY...560C": 800, "SPY...560P": 700},
        )
        if signal.is_elevated:
            logger.info("Volume spike detected: ratio=%.2f", signal.ratio)
    """

    def __init__(
        self,
        alert_percentile: float = 0.95,    # Top-5% = alert
        dynamic_threshold_min: float = 2.0,
    ) -> None:
        self._alert_percentile = alert_percentile
        self._threshold_min = dynamic_threshold_min
        self._ema_vol: float = 0.0
        self._ratio_history: deque[float] = deque(maxlen=_PERCENTILE_BUFFER)
        self._prev_cumulative: Optional[float] = None

    def update(
        self,
        tick_volume: float,
        phase: SessionPhase = SessionPhase.MID,
        per_contract_volumes: Optional[dict[str, float]] = None,
    ) -> VolAccelSignal:
        """Compute acceleration ratio and entropy for a single tick.

        Args:
            tick_volume:           Volume for this tick.
            phase:                 Session phase (affects EMA window).
            per_contract_volumes:  Dict of {symbol: vol} for entropy calculation.

        Returns:
            VolAccelSignal with ratio, threshold, entropy, and flags.
        """
        alpha = _EMA_ALPHA.get(phase.value, _EMA_ALPHA["mid"])

        # Update EMA
        if self._ema_vol == 0:
            self._ema_vol = tick_volume
        else:
            self._ema_vol += alpha * (tick_volume - self._ema_vol)

        ratio = tick_volume / max(self._ema_vol, 1.0)
        self._ratio_history.append(ratio)

        threshold = self._compute_dynamic_threshold()
        percentile = self._compute_percentile_rank(ratio)
        entropy = self._compute_entropy(per_contract_volumes)

        return VolAccelSignal(
            ratio=ratio,
            threshold=threshold,
            is_elevated=(ratio >= threshold),
            entropy=entropy,
            phase=phase,
            ema_vol=self._ema_vol,
            tick_vol=tick_volume,
            percentile_rank=percentile,
        )

    def update_from_cumulative(
        self,
        cumulative_volume: float,
        phase: SessionPhase = SessionPhase.MID,
        per_contract_volumes: Optional[dict[str, float]] = None,
    ) -> VolAccelSignal:
        """Derive tick volume from cumulative daily volume and update.

        Handles the delta-volume pattern used by upstream chain state.
        """
        if self._prev_cumulative is None:
            tick_vol = cumulative_volume
        else:
            tick_vol = max(0.0, cumulative_volume - self._prev_cumulative)
        self._prev_cumulative = cumulative_volume
        return self.update(tick_vol, phase, per_contract_volumes)

    def classify_phase(self, hour: int, minute: int) -> SessionPhase:
        """Classify session phase from ET hour/minute."""
        total_minutes = hour * 60 + minute
        if total_minutes < 9 * 60 + 30:
            return SessionPhase.PRE_MARKET
        if total_minutes < 10 * 60:
            return SessionPhase.OPEN
        if total_minutes < 15 * 60 + 30:
            return SessionPhase.MID
        if total_minutes < 16 * 60:
            return SessionPhase.CLOSE
        return SessionPhase.POST_MARKET

    # ── Private ──────────────────────────────────────────────────────────────

    def _compute_dynamic_threshold(self) -> float:
        """Compute alert threshold as percentile of recent ratio history."""
        if len(self._ratio_history) < 10:
            return self._threshold_min

        sorted_ratios = sorted(self._ratio_history)
        idx = int(self._alert_percentile * len(sorted_ratios))
        idx = min(idx, len(sorted_ratios) - 1)
        threshold = sorted_ratios[idx]
        return max(threshold, self._threshold_min)

    def _compute_percentile_rank(self, ratio: float) -> float:
        """Rank of current ratio in recent history [0, 1]."""
        if not self._ratio_history:
            return 0.5
        below = sum(1 for r in self._ratio_history if r < ratio)
        return below / len(self._ratio_history)

    @staticmethod
    def _compute_entropy(per_contract_volumes: Optional[dict[str, float]]) -> float:
        """Shannon entropy of volume distribution across contracts.

        High entropy → diffuse volume (noise / random).
        Low entropy  → concentrated volume (directional / institutional).

        Returns H in [0, log(N)] nats.
        """
        if not per_contract_volumes:
            return 0.0

        vols = [max(0.0, v) for v in per_contract_volumes.values()]
        total = sum(vols)
        if total <= 0:
            return 0.0

        entropy = 0.0
        for v in vols:
            if v > 0:
                p = v / total
                entropy -= p * math.log(p)

        return entropy
