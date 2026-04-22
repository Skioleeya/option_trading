"""Pearson correlation engine for Vanna Flow analysis.

Responsibilities:
    - SpotIVPoint data container
    - Rolling Pearson correlation (Rust SIMD or Python fallback)
    - Vanna Flip detection (rapid correlation sign reversal)

Layer:  L1
Deps:   stdlib, rust_kernel (optional)
"""

from __future__ import annotations

import math
import logging
from collections import deque
from typing import NamedTuple

logger = logging.getLogger(__name__)

try:
    import rust_kernel
    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False
    logger.warning("[PearsonEngine] rust_kernel not installed — using Python fallback")


# ── Data Types ────────────────────────────────────────────────────────────────

class SpotIVPoint(NamedTuple):
    """Single (timestamp, spot, atm_iv) observation."""
    timestamp_mono: float
    spot: float
    iv: float


# ── Engine ────────────────────────────────────────────────────────────────────

class PearsonEngine:
    """Maintains a rolling window deque and computes Pearson correlation.

    Args:
        rolling_window_size: Maximum number of recent points used by the
            correlation kernel (default 120).
        corr_history_maxlen: Sample buffer for Vanna-Flip detection (default 120).
    """

    FLIP_DELTA_THRESHOLD = 0.6   # Correlation jump > 0.6 within 2 min = FLIP
    FLIP_LOOKBACK_SECONDS = 120  # Seconds to look back for flip comparison

    def __init__(
        self,
        history_deque: deque[SpotIVPoint],
        rolling_window_size: int = 120,
        corr_history_maxlen: int = 120,
    ) -> None:
        # Shared reference to the analyzer's history deque
        self._history = history_deque
        self._rolling_window_size = rolling_window_size
        self._corr_history: deque[tuple[float, float]] = deque(maxlen=corr_history_maxlen)

    # ── Public API ────────────────────────────────────────────────────────────

    def push_correlation(self, now_mono: float, correlation: float | None) -> None:
        """Record a new correlation sample (for flip detection)."""
        if correlation is not None:
            self._corr_history.append((now_mono, correlation))

    def calculate(self) -> float | None:
        """Return Pearson correlation for the current history window.

        Returns None when there are fewer than 2 data points.
        """
        if len(self._history) < 2:
            return None

        recent = list(self._history)[-self._rolling_window_size:]
        spots = [d.spot for d in recent]
        ivs   = [d.iv   for d in recent]

        if len(spots) < 2:
            return None

        if _RUST_AVAILABLE:
            try:
                return rust_kernel.pearson_r(spots, ivs)
            except Exception as exc:
                logger.error("[PearsonEngine] rust_kernel.pearson_r failed: %s", exc)

        return self._python_pearson(spots, ivs)

    def detect_flip(self, now_mono: float, current_corr: float | None) -> bool:
        """Return True if correlation jumped > 0.6 within the past 2 minutes."""
        if current_corr is None or len(self._corr_history) < 10:
            return False

        if _RUST_AVAILABLE:
            try:
                return rust_kernel.detect_vanna_flip(
                    now_mono, current_corr, list(self._corr_history)
                )
            except Exception as exc:
                logger.error("[PearsonEngine] rust_kernel.detect_vanna_flip failed: %s", exc)

        return self._python_detect_flip(now_mono, current_corr)

    @property
    def corr_history(self) -> deque[tuple[float, float]]:
        """Expose corr_history for persistence serialization."""
        return self._corr_history

    @corr_history.setter
    def corr_history(self, value: deque[tuple[float, float]]) -> None:
        self._corr_history = value

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _python_pearson(spots: list[float], ivs: list[float]) -> float | None:
        n = len(spots)
        sum_x  = sum(spots)
        sum_y  = sum(ivs)
        sum_x2 = sum(x * x for x in spots)
        sum_y2 = sum(y * y for y in ivs)
        sum_xy = sum(x * y for x, y in zip(spots, ivs))

        numerator    = n * sum_xy - sum_x * sum_y
        denominator_x = n * sum_x2 - sum_x ** 2
        denominator_y = n * sum_y2 - sum_y ** 2

        if denominator_x <= 0 or denominator_y <= 0:
            return None

        return numerator / (math.sqrt(denominator_x) * math.sqrt(denominator_y))

    def _python_detect_flip(
        self, now_mono: float, current_corr: float
    ) -> bool:
        two_min_ago = now_mono - self.FLIP_LOOKBACK_SECONDS
        past_corr: float | None = None
        for ts, corr in self._corr_history:
            if ts >= two_min_ago:
                past_corr = corr
                break
        if past_corr is None:
            return False
        return (current_corr - past_corr) > self.FLIP_DELTA_THRESHOLD
