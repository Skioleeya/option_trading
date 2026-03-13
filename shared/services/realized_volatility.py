"""Rolling realized volatility helpers for research-path features."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass


_TRADING_YEAR_SECONDS = 252.0 * 6.5 * 3600.0


@dataclass(frozen=True)
class RealizedVolatilitySnapshot:
    """Latest realized-vol estimate on a decimal annualized basis."""

    realized_vol: float
    sample_count: int
    window_seconds: float


class RollingRealizedVolatility:
    """Compute annualized realized volatility from rolling spot history."""

    def __init__(
        self,
        *,
        window_seconds: float = 900.0,
        annualization_seconds: float = _TRADING_YEAR_SECONDS,
        min_samples: int = 5,
    ) -> None:
        self._window_seconds = max(float(window_seconds), 1.0)
        self._annualization_seconds = max(float(annualization_seconds), 1.0)
        self._min_samples = max(int(min_samples), 2)
        self._history: deque[tuple[float, float]] = deque(maxlen=10000)

    def update(self, *, spot: float, timestamp_mono: float) -> RealizedVolatilitySnapshot:
        """Append one spot sample and return the current realized-vol estimate."""
        if not math.isfinite(spot) or spot <= 0.0 or not math.isfinite(timestamp_mono):
            return RealizedVolatilitySnapshot(0.0, 0, self._window_seconds)

        self._history.append((float(timestamp_mono), float(spot)))
        self._trim_history(float(timestamp_mono))
        realized_vol = self._compute_realized_vol()
        return RealizedVolatilitySnapshot(
            realized_vol=realized_vol,
            sample_count=len(self._history),
            window_seconds=self._window_seconds,
        )

    def reset(self) -> None:
        self._history.clear()

    def _trim_history(self, now_mono: float) -> None:
        cutoff = now_mono - self._window_seconds
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

    def _compute_realized_vol(self) -> float:
        if len(self._history) < self._min_samples:
            return 0.0

        log_returns: list[float] = []
        prev_time, prev_spot = self._history[0]
        total_elapsed = 0.0
        for curr_time, curr_spot in list(self._history)[1:]:
            dt = curr_time - prev_time
            if dt <= 0.0 or prev_spot <= 0.0 or curr_spot <= 0.0:
                prev_time, prev_spot = curr_time, curr_spot
                continue
            log_returns.append(math.log(curr_spot / prev_spot))
            total_elapsed += dt
            prev_time, prev_spot = curr_time, curr_spot

        if len(log_returns) < self._min_samples - 1 or total_elapsed <= 0.0:
            return 0.0

        mean_ret = sum(log_returns) / len(log_returns)
        variance = sum((ret - mean_ret) ** 2 for ret in log_returns) / max(len(log_returns) - 1, 1)
        if not math.isfinite(variance) or variance <= 0.0:
            return 0.0

        avg_dt = total_elapsed / len(log_returns)
        if avg_dt <= 0.0 or not math.isfinite(avg_dt):
            return 0.0

        annualization_factor = self._annualization_seconds / avg_dt
        if annualization_factor <= 0.0 or not math.isfinite(annualization_factor):
            return 0.0

        realized_vol = math.sqrt(variance * annualization_factor)
        if not math.isfinite(realized_vol) or realized_vol < 0.0:
            return 0.0
        return realized_vol
