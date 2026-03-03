"""
Breadth Momentum Calculator - Dual Signal Architecture
=======================================================

Signal Pair (empirically derived from 29.3k+ Redis records):
-------------------------------------------------------------
  BM_BROAD   (weights 5:2:1 for Tier1:Tier2:Tier3)
     - Small-cap movers (0~3%) have the highest correlation with net_breadth (r=0.94)
     - Used for: Regime classification (Trend, Chop, Reversal)
     - Think: "How many soldiers are advancing" — breadth-first signal

  BM_MOMENTUM (weights 1:3:9 for Tier1:Tier2:Tier3)
     - Emphasises extreme movers (>5%), amplifying institutional conviction bursts
     - Used for: Momentum burst detection, SPY options trigger
     - Think: "How hard are the lead units hitting" — intensity-first signal

Architecture:
  compute() → returns (BM_broad, BM_momentum, delta_broad, delta_momentum)
  regime()   → driven by BM_broad (stable, empirically validated)
"""
import os
import math
from collections import deque
from typing import Dict, Tuple

# ============================================================================
# BM_BROAD weights: empirically derived (Pearson r vs net_breadth)
# Tier1 (0~3%): r=0.94 — dominant signal, highest weight
# Tier2 (3~5%): r=0.48 — moderate signal
# Tier3 (>5%):  r=0.20 — noise (individual stock events), lowest weight
# ============================================================================
_B1 = int(os.getenv("BM_BROAD_WEIGHT_TIER1", "5"))  # 0~3%   empirical best
_B2 = int(os.getenv("BM_BROAD_WEIGHT_TIER2", "2"))  # 3~5%
_B3 = int(os.getenv("BM_BROAD_WEIGHT_TIER3", "1"))  # >5%    empirical worst

BROAD_WEIGHTS = {
    "up0":    0,
    "up0_3":  _B1,   "down0_3": -_B1,
    "up3_5":  _B2,   "down3_5": -_B2,
    "up5":    _B3,   "down5":   -_B3,
}

# ============================================================================
# BM_MOMENTUM weights: exponential scale to capture conviction bursts
# Used for 0DTE trigger detection where momentum explosions matter most.
# ============================================================================
_M1 = int(os.getenv("BM_WEIGHT_TIER1", "1"))   # 0~3%
_M2 = int(os.getenv("BM_WEIGHT_TIER2", "3"))   # 3~5%
_M3 = int(os.getenv("BM_WEIGHT_TIER3", "9"))   # >5%

MOMENTUM_WEIGHTS = {
    "up0":    0,
    "up0_3":  _M1,   "down0_3": -_M1,
    "up3_5":  _M2,   "down3_5": -_M2,
    "up5":    _M3,   "down5":   -_M3,
}

# ============================================================================
# Dynamic regime threshold parameters (driven by BM_BROAD)
# ============================================================================
_VOL_WINDOW          = int(os.getenv("BM_VOL_WINDOW", "20"))
_VOL_MULTIPLIER      = float(os.getenv("BM_VOL_MULTIPLIER", "0.8"))
_STATIC_BM_THRESHOLD = int(os.getenv("BM_STATIC_THRESHOLD", "2500"))
_STATIC_DELTA_THRESHOLD = int(os.getenv("BM_STATIC_DELTA_THRESHOLD", "12"))


class BreadthMomentumCalculator:
    """
    Dual-signal BM calculator.
    Outputs both BM_broad (regime-stable) and BM_momentum (burst-capture).
    Regime classification is driven by BM_broad.
    """

    def __init__(self) -> None:
        self._last_broad: int | None = None
        self._last_momentum: int | None = None
        self._broad_history: deque[int] = deque(maxlen=_VOL_WINDOW)

    def compute(self, metrics: Dict[str, int]) -> Tuple[int, int, int, int]:
        """
        Compute both BM signals and their deltas.

        Returns:
            (BM_broad, BM_momentum, delta_broad, delta_momentum)
        """
        bm_broad = sum(
            metrics.get(k, 0) * w for k, w in BROAD_WEIGHTS.items()
        )
        bm_momentum = sum(
            metrics.get(k, 0) * w for k, w in MOMENTUM_WEIGHTS.items()
        )

        delta_broad    = 0 if self._last_broad    is None else bm_broad    - self._last_broad
        delta_momentum = 0 if self._last_momentum is None else bm_momentum - self._last_momentum

        self._last_broad    = bm_broad
        self._last_momentum = bm_momentum
        self._broad_history.append(bm_broad)

        return bm_broad, bm_momentum, delta_broad, delta_momentum

    def regime(self, bm_broad: int, delta_broad: int) -> str:
        """
        Regime classification driven by BM_BROAD (empirically more stable).
        Uses rolling Std of BM_broad for adaptive Chop threshold.
        """
        bm_thr, delta_thr = self._get_adaptive_thresholds()
        return self._classify_regime(bm_broad, delta_broad, bm_thr, delta_thr)

    def _get_adaptive_thresholds(self) -> Tuple[float, float]:
        n = len(self._broad_history)
        if n < max(2, _VOL_WINDOW // 2):
            return float(_STATIC_BM_THRESHOLD), float(_STATIC_DELTA_THRESHOLD)
        history = list(self._broad_history)
        mean_bm = sum(history) / n
        variance = sum((x - mean_bm) ** 2 for x in history) / (n - 1)
        bm_std = math.sqrt(variance)
        bm_chop = max(bm_std * _VOL_MULTIPLIER, 10.0)
        delta_chop = max(bm_chop * 0.5, 5.0)
        return bm_chop, delta_chop

    @staticmethod
    def _classify_regime(bm: int, delta: int, bm_threshold: float, delta_threshold: float) -> str:
        if bm > 0 and delta > 0:
            return "Trend Up"
        if bm < 0 and delta < 0:
            return "Trend Down"
        if abs(bm) < bm_threshold and abs(delta) < delta_threshold:
            return "Chop"
        if (bm >= 0 and delta < 0) or (bm <= 0 and delta > 0):
            return "Reversal"
        return "Chop"

    def get_volatility_state(self) -> dict:
        bm_chop, delta_chop = self._get_adaptive_thresholds()
        n = len(self._broad_history)
        return {
            "observations": n,
            "window_size": _VOL_WINDOW,
            "bm_chop_threshold": round(bm_chop, 1),
            "delta_chop_threshold": round(delta_chop, 1),
            "using_dynamic": n >= max(2, _VOL_WINDOW // 2),
        }
