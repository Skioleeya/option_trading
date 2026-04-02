"""Volume Acceleration v2 - Adaptive Volume Acceleration Ratio."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from shared_rust.services import compute_vol_accel_entropy as _rust_compute_vol_accel_entropy  # type: ignore
    _RUST_AVAILABLE = True
except (ImportError, AttributeError):
    _rust_compute_vol_accel_entropy = None
    _RUST_AVAILABLE = False

_EMA_ALPHA: dict[str, float] = {
    "open": 2.0 / (10.0 + 1.0),
    "mid": 2.0 / (60.0 + 1.0),
    "close": 2.0 / (30.0 + 1.0),
}
_PERCENTILE_BUFFER: int = 200


class SessionPhase(str, Enum):
    PRE_MARKET = "pre_market"
    OPEN = "open"
    MID = "mid"
    CLOSE = "close"
    POST_MARKET = "post_market"


@dataclass
class VolAccelSignal:
    ratio: float
    threshold: float
    is_elevated: bool
    entropy: float
    phase: SessionPhase
    ema_vol: float
    tick_vol: float
    percentile_rank: float


class VolAccelV2:
    def __init__(
        self,
        alert_percentile: float = 0.95,
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
        alpha = _EMA_ALPHA.get(phase.value, _EMA_ALPHA["mid"])
        entropy, ema_next = self._compute_entropy_and_ema(tick_volume, per_contract_volumes, alpha)
        self._ema_vol = ema_next

        ratio = tick_volume / max(self._ema_vol, 1.0)
        self._ratio_history.append(ratio)
        threshold = self._compute_dynamic_threshold()
        percentile = self._compute_percentile_rank(ratio)

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
        if self._prev_cumulative is None:
            tick_vol = cumulative_volume
        else:
            tick_vol = max(0.0, cumulative_volume - self._prev_cumulative)
        self._prev_cumulative = cumulative_volume
        return self.update(tick_vol, phase, per_contract_volumes)

    def classify_phase(self, hour: int, minute: int) -> SessionPhase:
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

    def _compute_dynamic_threshold(self) -> float:
        if len(self._ratio_history) < 10:
            return self._threshold_min

        sorted_ratios = sorted(self._ratio_history)
        idx = int(self._alert_percentile * len(sorted_ratios))
        idx = min(idx, len(sorted_ratios) - 1)
        return max(sorted_ratios[idx], self._threshold_min)

    def _compute_percentile_rank(self, ratio: float) -> float:
        if not self._ratio_history:
            return 0.5
        below = sum(1 for r in self._ratio_history if r < ratio)
        return below / len(self._ratio_history)

    def _compute_entropy_and_ema(
        self,
        tick_volume: float,
        per_contract_volumes: Optional[dict[str, float]],
        alpha: float,
    ) -> tuple[float, float]:
        if not _RUST_AVAILABLE or _rust_compute_vol_accel_entropy is None:
            raise RuntimeError("shared_rust.services.compute_vol_accel_entropy unavailable")

        if per_contract_volumes:
            features = [max(0.0, float(v)) for v in per_contract_volumes.values()]
        else:
            features = [float(tick_volume)]
        if not features:
            features = [float(tick_volume)]
        feature_total = sum(features)
        tick = max(0.0, float(tick_volume))
        if feature_total > 0.0 and tick > 0.0:
            scale = tick / feature_total
            features = [value * scale for value in features]
        elif tick >= 0.0:
            features = [tick]

        try:
            entropy, ema_next = _rust_compute_vol_accel_entropy(
                features,
                float(self._ema_vol),
                float(alpha),
            )
        except Exception as exc:  # nosec B904 - explicit bridge failure context
            logger.error("[VolAccelV2] Rust entropy bridge failed: %s", exc)
            raise RuntimeError("Rust vol_accel entropy bridge failed") from exc

        return float(entropy), float(ema_next)
