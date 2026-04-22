"""Flow and momentum themed feature extractors."""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from typing import Any

from l2_decision.feature_store.extractors_common import _get_agg, _get_ms, _get_val

logger = logging.getLogger(__name__)

ROC_HISTORY_MAXLEN = 3600
IV_HISTORY_MAXLEN = 3600
IV_VELOCITY_REF = 0.02
WALL_HISTORY_MAXLEN = 600
TURNOVER_HISTORY_MAXLEN = 3600
WALL_SPEED_NORMALIZER = 0.001
MIN_ELAPSED_SECONDS = 0.1
MIN_HISTORY_POINTS = 2
SECONDS_PER_MINUTE = 60.0
SVOL_HISTORY_MAXLEN = 10000
SVOL_MIN_SAMPLES = 30
SVOL_STD_EPSILON = 1e-9
MTF_WEIGHT_1M = 0.5
MTF_WEIGHT_5M = 0.3
MTF_WEIGHT_15M = 0.2
WINDOW_1M_SECONDS = 60.0
WINDOW_5M_SECONDS = 300.0
WINDOW_15M_SECONDS = 900.0
WINDOW_30S_SECONDS = 30.0


class _SpotRoCExtractor:
    """1-minute spot rate-of-change tracker."""

    def __init__(self, window_seconds: float = WINDOW_1M_SECONDS) -> None:
        self._window = window_seconds
        self._history: deque[tuple[float, float]] = deque(maxlen=ROC_HISTORY_MAXLEN)

    def __call__(self, snapshot: Any) -> float:
        spot = _get_val(snapshot, "spot")
        if spot is None or not math.isfinite(spot) or spot <= 0:
            return 0.0

        now_mono = time.monotonic()
        self._history.append((now_mono, spot))

        cutoff = now_mono - self._window
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

        if len(self._history) < MIN_HISTORY_POINTS:
            return 0.0

        oldest_price = self._history[0][1]
        if oldest_price <= 0:
            return 0.0
        return (spot - oldest_price) / oldest_price

    def reset(self) -> None:
        self._history.clear()


class _IVVelocityExtractor:
    """1-minute IV velocity (rate of change of ATM IV)."""

    _REF_VELOCITY: float = IV_VELOCITY_REF

    def __init__(self, window_seconds: float = WINDOW_1M_SECONDS) -> None:
        self._window = window_seconds
        self._history: deque[tuple[float, float]] = deque(maxlen=IV_HISTORY_MAXLEN)

    def __call__(self, snapshot: Any) -> float:
        iv = _get_agg(snapshot, "atm_iv")
        if iv is None or not math.isfinite(iv) or iv <= 0:
            return 0.0

        now_mono = time.monotonic()
        self._history.append((now_mono, iv))

        cutoff = now_mono - self._window
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

        if len(self._history) < MIN_HISTORY_POINTS:
            return 0.0

        oldest_iv = self._history[0][1]
        velocity = (iv - oldest_iv) / self._window
        velocity_per_min = velocity * SECONDS_PER_MINUTE
        clamped = velocity_per_min / self._REF_VELOCITY
        return max(-1.0, min(1.0, clamped))

    def reset(self) -> None:
        self._history.clear()


class _WallMigrationSpeedExtractor:
    """5-second call/put wall migration speed feature."""

    def __init__(self, window_seconds: float = WINDOW_30S_SECONDS) -> None:
        self._window = window_seconds
        self._call_history: deque[tuple[float, float]] = deque(maxlen=WALL_HISTORY_MAXLEN)
        self._put_history: deque[tuple[float, float]] = deque(maxlen=WALL_HISTORY_MAXLEN)

    def __call__(self, snapshot: Any) -> float:
        call_wall = _get_agg(snapshot, "call_wall", 0.0)
        put_wall = _get_agg(snapshot, "put_wall", 0.0)
        spot = _get_val(snapshot, "spot", 0.0)

        if not all(math.isfinite(v) and v > 0 for v in (call_wall, put_wall, spot)):
            return 0.0

        now_mono = time.monotonic()
        self._call_history.append((now_mono, call_wall))
        self._put_history.append((now_mono, put_wall))

        cutoff = now_mono - self._window
        for history in (self._call_history, self._put_history):
            while history and history[0][0] < cutoff:
                history.popleft()

        def _speed(hist: deque[tuple[float, float]]) -> float:
            if len(hist) < MIN_HISTORY_POINTS:
                return 0.0
            old_val, new_val = hist[0][1], hist[-1][1]
            elapsed = hist[-1][0] - hist[0][0]
            if elapsed < MIN_ELAPSED_SECONDS or old_val <= 0:
                return 0.0
            return abs((new_val - old_val) / old_val / elapsed)

        speed = _speed(self._call_history) + _speed(self._put_history)
        return min(1.0, speed / WALL_SPEED_NORMALIZER)

    def reset(self) -> None:
        self._call_history.clear()
        self._put_history.clear()


class _TurnoverVelocityExtractor:
    """Measures the speed of turnover accumulation (institutional pressure)."""

    def __init__(self, window_seconds: float = WINDOW_1M_SECONDS) -> None:
        self._window = window_seconds
        self._history: deque[tuple[float, float]] = deque(maxlen=TURNOVER_HISTORY_MAXLEN)

    def __call__(self, snapshot: Any) -> float:
        chain = _get_val(snapshot, "chain")
        if chain is None:
            return 0.0

        try:
            import pyarrow as pa
            import pyarrow.compute as pc

            if isinstance(chain, pa.RecordBatch):
                turnover = self._recordbatch_flow_sum(chain, pc)
            else:
                turnover = self._iterable_flow_sum(chain)
        except Exception as exc:
            logger.debug("turnover_velocity extraction fallback: %s", exc)
            return 0.0

        now_mono = time.monotonic()
        self._history.append((now_mono, turnover))

        cutoff = now_mono - self._window
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

        if len(self._history) < MIN_HISTORY_POINTS:
            return 0.0

        delta_t = self._history[-1][0] - self._history[0][0]
        delta_v = self._history[-1][1] - self._history[0][1]
        if delta_t < MIN_ELAPSED_SECONDS:
            return 0.0
        return delta_v / delta_t

    def reset(self) -> None:
        self._history.clear()

    @staticmethod
    def _recordbatch_flow_sum(chain: Any, pc: Any) -> float:
        field_names = set(chain.schema.names)
        for field in ("turnover", "current_volume", "volume"):
            if field not in field_names:
                continue
            scalar = pc.sum(chain.column(field))
            if scalar is None:
                continue
            raw = scalar.as_py()
            if raw is None:
                continue
            total = float(raw)
            if total > 0.0:
                return total
        return 0.0

    @staticmethod
    def _iterable_flow_sum(chain: Any) -> float:
        total = 0.0
        for row in chain:
            if not isinstance(row, dict):
                continue
            raw = row.get("turnover")
            if raw in (None, 0, 0.0):
                raw = row.get("current_volume")
            if raw in (None, 0, 0.0):
                raw = row.get("volume", 0.0)
            try:
                total += float(raw or 0.0)
            except (TypeError, ValueError):
                continue
        return total


class _MaxImpactExtractor:
    """Heuristic for peak institutional impact (OFII proxy) at aggregate level."""

    def __call__(self, snapshot: Any) -> float:
        chain = _get_val(snapshot, "chain")
        if chain is None:
            return 0.0

        max_imp = 0.0
        try:
            import pyarrow as pa

            if isinstance(chain, pa.RecordBatch):
                if chain.num_rows == 0:
                    return 0.0
                return self._recordbatch_max_impact(chain)

            for row in chain:
                if not isinstance(row, dict):
                    continue
                flow_proxy = self._flow_proxy(row)
                gamma = self._gamma_proxy(row)
                impact = flow_proxy * gamma
                if impact > max_imp:
                    max_imp = impact
        except Exception as exc:
            logger.debug("max_impact extraction fallback: %s", exc)
            return 0.0
        return max_imp

    def reset(self) -> None:
        pass

    @staticmethod
    def _recordbatch_max_impact(chain: Any) -> float:
        rows = chain.to_pylist()
        max_imp = 0.0
        for row in rows:
            if not isinstance(row, dict):
                continue
            flow_proxy = _MaxImpactExtractor._flow_proxy(row)
            gamma = _MaxImpactExtractor._gamma_proxy(row)
            impact = flow_proxy * gamma
            if impact > max_imp:
                max_imp = impact
        return max_imp

    @staticmethod
    def _flow_proxy(row: dict[str, Any]) -> float:
        raw = row.get("turnover")
        if raw in (None, 0, 0.0):
            raw = row.get("current_volume")
        if raw in (None, 0, 0.0):
            raw = row.get("volume", 0.0)
        try:
            return abs(float(raw or 0.0))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _gamma_proxy(row: dict[str, Any]) -> float:
        raw = row.get("computed_gamma")
        if raw in (None, 0, 0.0):
            raw = row.get("gamma", 0.0)
        try:
            return abs(float(raw or 0.0))
        except (TypeError, ValueError):
            return 0.0


class _SVolCorrelationExtractor:
    """15-minute spot-vol correlation feature."""

    def __init__(self, window_seconds: float = WINDOW_15M_SECONDS) -> None:
        self._window = window_seconds
        self._history: deque[tuple[float, float, float]] = deque(maxlen=SVOL_HISTORY_MAXLEN)

    def __call__(self, snapshot: Any) -> float:
        spot = _get_val(snapshot, "spot")
        iv = _get_agg(snapshot, "atm_iv")
        if not self._is_valid_input(spot, iv):
            return 0.0

        self._append_and_trim(float(spot), float(iv))
        if len(self._history) < SVOL_MIN_SAMPLES:
            return 0.0
        return self._compute_correlation()

    def reset(self) -> None:
        self._history.clear()

    @staticmethod
    def _is_valid_input(spot: Any, iv: Any) -> bool:
        return (
            math.isfinite(spot or 0.0)
            and (spot or 0) > 0
            and math.isfinite(iv or 0.0)
            and (iv or 0) > 0
        )

    def _append_and_trim(self, spot: float, iv: float) -> None:
        now_mono = time.monotonic()
        self._history.append((now_mono, spot, iv))
        cutoff = now_mono - self._window
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

    def _compute_correlation(self) -> float:
        spots = [x[1] for x in self._history]
        ivs = [x[2] for x in self._history]
        size = len(spots)
        mean_s = sum(spots) / size
        mean_iv = sum(ivs) / size
        covariance = sum((s - mean_s) * (v - mean_iv) for s, v in zip(spots, ivs))
        std_s = math.sqrt(sum((s - mean_s) ** 2 for s in spots) / size)
        std_iv = math.sqrt(sum((v - mean_iv) ** 2 for v in ivs) / size)
        if std_s < SVOL_STD_EPSILON or std_iv < SVOL_STD_EPSILON:
            return 0.0
        corr = covariance / (size * std_s * std_iv)
        return max(-1.0, min(1.0, corr))


class _MTFConsensusExtractor:
    """Multi-timeframe IV consensus score [-1, +1]."""

    def __init__(self) -> None:
        self._iv1m = _IVVelocityExtractor(window_seconds=WINDOW_1M_SECONDS)
        self._iv5m = _IVVelocityExtractor(window_seconds=WINDOW_5M_SECONDS)
        self._iv15m = _IVVelocityExtractor(window_seconds=WINDOW_15M_SECONDS)

    def __call__(self, snapshot: Any) -> float:
        v1 = self._iv1m(snapshot)
        v5 = self._iv5m(snapshot)
        v15 = self._iv15m(snapshot)
        consensus = MTF_WEIGHT_1M * v1 + MTF_WEIGHT_5M * v5 + MTF_WEIGHT_15M * v15
        return max(-1.0, min(1.0, consensus))

    def reset(self) -> None:
        self._iv1m.reset()
        self._iv5m.reset()
        self._iv15m.reset()
