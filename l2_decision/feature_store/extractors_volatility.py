"""Volatility themed feature extractors."""

from __future__ import annotations

import math
import time
from typing import Any

from l2_decision.feature_store.extractors_common import _get_agg, _get_val, _safe
from shared_rust.services import RollingRealizedVolatility
from shared_rust.services import tactical_compute_vrp as compute_vrp

DEFAULT_REALIZED_WINDOW_SECONDS = 900.0
DEFAULT_REALIZED_MIN_SAMPLES = 5
PERCENT_SCALE = 100.0


class _RealizedVolatilityMetricsExtractor:
    """Rolling annualized realized volatility with per-snapshot memoization."""

    def __init__(
        self,
        window_seconds: float = DEFAULT_REALIZED_WINDOW_SECONDS,
        min_samples: int = DEFAULT_REALIZED_MIN_SAMPLES,
    ) -> None:
        self._rv = RollingRealizedVolatility(
            window_seconds=window_seconds,
            min_samples=min_samples,
        )
        self._last_key: tuple[int, int | None, float] | None = None
        self._last_realized_vol: float = 0.0
        self._last_vrp: float = 0.0

    def extract_realized_vol(self, snapshot: Any) -> float:
        realized_vol, _ = self._compute(snapshot)
        return realized_vol

    def extract_vrp(self, snapshot: Any) -> float:
        _, vrp = self._compute(snapshot)
        return vrp

    def reset(self) -> None:
        self._rv.reset()
        self._last_key = None
        self._last_realized_vol = 0.0
        self._last_vrp = 0.0

    def _compute(self, snapshot: Any) -> tuple[float, float]:
        spot = _get_val(snapshot, "spot")
        if spot is None:
            return 0.0, 0.0
        try:
            spot_f = float(spot)
        except (TypeError, ValueError):
            return 0.0, 0.0
        if not math.isfinite(spot_f) or spot_f <= 0.0:
            return 0.0, 0.0

        now_mono = time.monotonic()
        key = self._build_cache_key(snapshot, spot_f)
        if key is not None and key == self._last_key:
            return self._last_realized_vol, self._last_vrp

        rv = self._rv.update(spot=spot_f, timestamp_mono=now_mono)
        realized_vol = rv.realized_vol
        vrp = 0.0
        if realized_vol > 0.0:
            vrp = _safe(lambda: compute_vrp(_get_agg(snapshot, "atm_iv", 0.0), realized_vol * PERCENT_SCALE))

        if key is not None:
            self._last_key = key
            self._last_realized_vol = realized_vol
            self._last_vrp = vrp
        return realized_vol, vrp

    @staticmethod
    def _build_cache_key(snapshot: Any, spot: float) -> tuple[int, int | None, float] | None:
        version = getattr(snapshot, "version", None)
        if version is None and isinstance(snapshot, dict):
            version = snapshot.get("version")
        if isinstance(version, float):
            version = int(version) if math.isfinite(version) else None
        elif isinstance(version, str):
            version = int(version) if version.strip().isdigit() else None
        elif not isinstance(version, int):
            version = None
        return (id(snapshot), version, spot)


class _RealizedVolatilityExtractor:
    """Feature wrapper over realized-vol metrics."""

    def __init__(self, metrics: _RealizedVolatilityMetricsExtractor) -> None:
        self._metrics = metrics

    def __call__(self, snapshot: Any) -> float:
        return self._metrics.extract_realized_vol(snapshot)

    def reset(self) -> None:
        self._metrics.reset()


class _RealizedVrpExtractor:
    """Research-path VRP feature wrapper over realized-vol metrics."""

    def __init__(self, metrics: _RealizedVolatilityMetricsExtractor) -> None:
        self._metrics = metrics

    def __call__(self, snapshot: Any) -> float:
        return self._metrics.extract_vrp(snapshot)

    def reset(self) -> None:
        self._metrics.reset()
