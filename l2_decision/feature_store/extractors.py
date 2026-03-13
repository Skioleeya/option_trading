"""l2_decision.feature_store.extractors — 12 pre-defined feature extractor specs.

Each extractor maps from an EnrichedSnapshot (L1 output) to a single float.
Extractors are pure functions — no side effects, no mutable state.

Features map to the 12 described in L2_DECISION_ANALYSIS.md §3.3.
Stateful features (spot_roc_1m, iv_velocity_1m, etc.) are wrapped in
StatefulExtractor objects that carry their own deque state.

Usage:
    from l2_decision.feature_store.extractors import build_default_extractors
    store = FeatureStore()
    store.register_bulk(build_default_extractors())
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

from l2_decision.feature_store.store import FeatureSpec
from shared.services.realized_volatility import RollingRealizedVolatility
from shared.system.tactical_triad_logic import compute_vrp

logger = logging.getLogger(__name__)


# ── Parity Helpers ──

def _get_val(obj, key, default=None):
    """Get value from EnrichedSnapshot object (attribute) or dict (key)."""
    if hasattr(obj, key): return getattr(obj, key, default)
    if isinstance(obj, dict): return obj.get(key, default)
    return default

def _get_agg(obj, key, default=None):
    """Get aggregate field from EnrichedSnapshot.aggregates or flat dict."""
    # EnrichedSnapshot: aggregates is a nested dataclass
    if hasattr(obj, "aggregates"):
        return getattr(obj.aggregates, key, default)
    # Legacy dict: aggregates are often flat at top-level
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default

def _get_agg_first(obj, keys: tuple[str, ...], default=None):
    """Get the first populated aggregate field across canonical/legacy aliases."""
    for key in keys:
        value = _get_agg(obj, key, None)
        if value is not None:
            return value
    return default

def _get_ms(obj, key, default=None):
    """Get microstructure field from EnrichedSnapshot.microstructure or nested dict."""
    if hasattr(obj, "microstructure") and obj.microstructure is not None:
        return getattr(obj.microstructure, key, default)
    if isinstance(obj, dict):
        # Handle both flat and nested legacy microstructure dicts
        ms = obj.get("microstructure") or obj.get("micro_structure", {})
        if isinstance(ms, dict):
            # Check nested state
            state = ms.get("micro_structure_state")
            if isinstance(state, dict):
                return state.get(key, default)
            return ms.get(key, default)
    return default


# ─────────────────────────────────────────────────────────────────────────────
# Stateful extractor helpers (carry deque state for ROC / velocity features)
# ─────────────────────────────────────────────────────────────────────────────

class _SpotRoCExtractor:
    """1-minute spot rate-of-change tracker."""

    def __init__(self, window_seconds: float = 60.0) -> None:
        self._window = window_seconds
        self._history: deque[tuple[float, float]] = deque(maxlen=3600)

    def __call__(self, snapshot: Any) -> float:
        spot = _get_val(snapshot, "spot")
        if spot is None or not math.isfinite(spot) or spot <= 0:
            return 0.0

        now_mono = time.monotonic()
        self._history.append((now_mono, spot))

        cutoff = now_mono - self._window
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

        if len(self._history) < 2:
            return 0.0

        oldest_price = self._history[0][1]
        if oldest_price <= 0: return 0.0
        return (spot - oldest_price) / oldest_price

    def reset(self) -> None:
        self._history.clear()


class _IVVelocityExtractor:
    """1-minute IV velocity (rate of change of ATM IV)."""
    _REF_VELOCITY: float = 0.02

    def __init__(self, window_seconds: float = 60.0) -> None:
        self._window = window_seconds
        self._history: deque[tuple[float, float]] = deque(maxlen=3600)

    def __call__(self, snapshot: Any) -> float:
        iv = _get_agg(snapshot, "atm_iv")
        if iv is None or not math.isfinite(iv) or iv <= 0:
            return 0.0

        now_mono = time.monotonic()
        self._history.append((now_mono, iv))

        cutoff = now_mono - self._window
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

        if len(self._history) < 2:
            return 0.0

        oldest_iv = self._history[0][1]
        velocity = (iv - oldest_iv) / self._window
        velocity_per_min = velocity * 60.0
        clamped = velocity_per_min / self._REF_VELOCITY
        return max(-1.0, min(1.0, clamped))

    def reset(self) -> None:
        self._history.clear()


class _WallMigrationSpeedExtractor:
    """5-second call/put wall migration speed feature."""

    def __init__(self, window_seconds: float = 30.0) -> None:
        self._window = window_seconds
        self._call_history: deque[tuple[float, float]] = deque(maxlen=600)
        self._put_history: deque[tuple[float, float]] = deque(maxlen=600)

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
        for h in (self._call_history, self._put_history):
            while h and h[0][0] < cutoff: h.popleft()

        def _speed(hist: deque) -> float:
            if len(hist) < 2: return 0.0
            old_val, new_val = hist[0][1], hist[-1][1]
            elapsed = hist[-1][0] - hist[0][0]
            if elapsed < 0.1 or old_val <= 0: return 0.0
            return abs((new_val - old_val) / old_val / elapsed)

        speed = _speed(self._call_history) + _speed(self._put_history)
        return min(1.0, speed / 0.001)

    def reset(self) -> None:
        self._call_history.clear()
        self._put_history.clear()


class _TurnoverVelocityExtractor:
    """Measures the speed of turnover accumulation (institutional pressure)."""

    def __init__(self, window_seconds: float = 60.0) -> None:
        self._window = window_seconds
        self._history: deque[tuple[float, float]] = deque(maxlen=3600)

    def __call__(self, snapshot: Any) -> float:
        # Aggregate turnover across the entire chain
        chain = _get_val(snapshot, "chain")
        if chain is None:
            return 0.0

        try:
            import pyarrow as pa
            if isinstance(chain, pa.RecordBatch):
                # Use pyarrow optimized sum if possible
                turnover = float(pa.compute.sum(chain.column("turnover")).as_py())
            else:
                turnover = sum(float(row.get("turnover", 0.0)) for row in chain)
        except Exception as exc:
            logger.debug("turnover_velocity extraction fallback: %s", exc)
            return 0.0

        now_mono = time.monotonic()
        self._history.append((now_mono, turnover))

        cutoff = now_mono - self._window
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

        if len(self._history) < 2:
            return 0.0

        delta_t = self._history[-1][0] - self._history[0][0]
        delta_v = self._history[-1][1] - self._history[0][1]

        if delta_t < 0.1:
            return 0.0

        # Returns USD per second of institutional turnover
        return delta_v / delta_t

    def reset(self) -> None:
        self._history.clear()


class _MaxImpactExtractor:
    """Heuristic for peak institutional impact (OFII proxy) at aggregate level."""

    def __call__(self, snapshot: Any) -> float:
        chain = _get_val(snapshot, "chain")
        if not chain:
            return 0.0

        # Heuristic OFII proxy: peak (|Flow| * |Gamma|) 
        max_imp = 0.0
        try:
            for row in chain:
                # Use turnover/volume * gamma as impact proxy for the aggregate signal
                flow_proxy = abs(float(row.get("turnover", 0.0) or row.get("volume", 0.0)))
                gamma = abs(float(row.get("gamma", 0.0) or 0.0))
                imp = flow_proxy * gamma
                if imp > max_imp:
                    max_imp = imp
        except Exception as exc:
            logger.debug("max_impact extraction fallback: %s", exc)
            return 0.0

        return max_imp

    def reset(self) -> None:
        pass


class _SVolCorrelationExtractor:
    """15-minute spot-vol correlation feature."""

    def __init__(self, window_seconds: float = 900.0) -> None:
        self._window = window_seconds
        self._history: deque[tuple[float, float, float]] = deque(maxlen=10000)

    def __call__(self, snapshot: Any) -> float:
        spot = _get_val(snapshot, "spot")
        iv = _get_agg(snapshot, "atm_iv")

        if not (math.isfinite(spot or 0.0) and (spot or 0) > 0 and math.isfinite(iv or 0.0) and (iv or 0) > 0):
            return 0.0

        now_mono = time.monotonic()
        self._history.append((now_mono, spot, iv))

        cutoff = now_mono - self._window
        while self._history and self._history[0][0] < cutoff: self._history.popleft()

        if len(self._history) < 30: return 0.0

        spots, ivs = [x[1] for x in self._history], [x[2] for x in self._history]
        n = len(spots)
        mean_s, mean_iv = sum(spots)/n, sum(ivs)/n
        num = sum((s - mean_s) * (v - mean_iv) for s, v in zip(spots, ivs))
        std_s = math.sqrt(sum((s - mean_s)**2 for s in spots)/n)
        std_iv = math.sqrt(sum((v - mean_iv)**2 for v in ivs)/n)

        if std_s < 1e-9 or std_iv < 1e-9: return 0.0
        return max(-1.0, min(1.0, num / (n * std_s * std_iv)))

    def reset(self) -> None:
        self._history.clear()


class _MTFConsensusExtractor:
    """Multi-timeframe IV consensus score [-1, +1]."""

    def __init__(self) -> None:
        self._iv1m = _IVVelocityExtractor(window_seconds=60.0)
        self._iv5m = _IVVelocityExtractor(window_seconds=300.0)
        self._iv15m = _IVVelocityExtractor(window_seconds=900.0)

    def __call__(self, snapshot: Any) -> float:
        v1, v5, v15 = self._iv1m(snapshot), self._iv5m(snapshot), self._iv15m(snapshot)
        consensus = 0.5 * v1 + 0.3 * v5 + 0.2 * v15
        return max(-1.0, min(1.0, consensus))

    def reset(self) -> None:
        self._iv1m.reset(); self._iv5m.reset(); self._iv15m.reset()


class _Skew25dMetricsExtractor:
    """Compute true 25-delta skew and validity from L1/L2 snapshot contracts."""

    _CALL_TARGET_DELTA: float = 0.25
    _PUT_TARGET_DELTA: float = -0.25
    _DEFAULT_DELTA_TOLERANCE: float = 0.10

    def __init__(self, delta_tolerance: float = _DEFAULT_DELTA_TOLERANCE) -> None:
        self._delta_tolerance = abs(float(delta_tolerance))
        self._last_key: tuple[int, int | None, int] | None = None
        self._last_value: float = 0.0
        self._last_valid: float = 0.0
        self._last_rr25: float = 0.0

    def extract_value(self, snapshot: Any) -> float:
        value, _, _ = self._compute(snapshot)
        return value

    def extract_rr25(self, snapshot: Any) -> float:
        _, _, rr25 = self._compute(snapshot)
        return rr25

    def extract_valid(self, snapshot: Any) -> float:
        _, valid, _ = self._compute(snapshot)
        return valid

    def reset(self) -> None:
        self._last_key = None
        self._last_value = 0.0
        self._last_valid = 0.0
        self._last_rr25 = 0.0

    def _compute(self, snapshot: Any) -> tuple[float, float, float]:
        key = self._build_cache_key(snapshot)
        if key is not None and key == self._last_key:
            return self._last_value, self._last_valid, self._last_rr25

        value, valid, rr25 = self._compute_uncached(snapshot)
        if key is not None:
            self._last_key = key
            self._last_value = value
            self._last_valid = valid
            self._last_rr25 = rr25
        return value, valid, rr25

    def _compute_uncached(self, snapshot: Any) -> tuple[float, float, float]:
        chain = _get_val(snapshot, "chain")
        atm_iv = self._normalize_iv(_get_agg(snapshot, "atm_iv"))
        if chain is None or atm_iv is None or atm_iv <= 0.0:
            return 0.0, 0.0, 0.0

        rows = self._coerce_chain_rows(chain)
        if not rows:
            return 0.0, 0.0, 0.0

        call_match: tuple[float, float] | None = None  # (distance, iv)
        put_match: tuple[float, float] | None = None

        for row in rows:
            if not isinstance(row, dict):
                continue

            is_call = self._extract_is_call(row)
            if is_call is None:
                continue

            iv = self._extract_iv(row)
            if iv is None:
                continue

            delta = self._extract_delta(row, is_call=is_call)
            if delta is None:
                continue

            target = self._CALL_TARGET_DELTA if is_call else self._PUT_TARGET_DELTA
            distance = abs(delta - target)
            if not math.isfinite(distance):
                continue

            if is_call:
                if call_match is None or distance < call_match[0]:
                    call_match = (distance, iv)
            else:
                if put_match is None or distance < put_match[0]:
                    put_match = (distance, iv)

        if call_match is None or put_match is None:
            return 0.0, 0.0, 0.0
        if call_match[0] > self._delta_tolerance or put_match[0] > self._delta_tolerance:
            return 0.0, 0.0, 0.0

        skew = (put_match[1] - call_match[1]) / atm_iv
        rr25 = call_match[1] - put_match[1]
        if not math.isfinite(skew):
            return 0.0, 0.0, 0.0
        if not math.isfinite(rr25):
            rr25 = 0.0

        return max(-1.0, min(1.0, skew)), 1.0, rr25

    @staticmethod
    def _build_cache_key(snapshot: Any) -> tuple[int, int | None, int] | None:
        chain = _get_val(snapshot, "chain")
        if chain is None:
            return None
        version = getattr(snapshot, "version", None)
        if version is None and isinstance(snapshot, dict):
            version = snapshot.get("version")
        if isinstance(version, bool):
            version = None
        elif isinstance(version, float):
            version = int(version) if math.isfinite(version) else None
        elif isinstance(version, str):
            text = version.strip()
            version = int(text) if text.isdigit() else None
        elif not isinstance(version, int):
            version = None
        return (id(snapshot), version, id(chain))

    @staticmethod
    def _coerce_chain_rows(chain: Any) -> list[dict[str, Any]]:
        try:
            import pyarrow as pa
        except Exception as exc:
            logger.debug("pyarrow import unavailable for skew extractor: %s", exc)
            pa = None  # type: ignore[assignment]

        if pa is not None and isinstance(chain, pa.RecordBatch):
            try:
                rows = chain.to_pylist()
            except Exception as exc:
                logger.debug("recordbatch to_pylist failed for skew extractor: %s", exc)
                return []
            return [row for row in rows if isinstance(row, dict)]

        if isinstance(chain, (str, bytes)):
            return []
        if isinstance(chain, dict):
            return []
        try:
            rows = list(chain)
        except TypeError:
            return []
        return [row for row in rows if isinstance(row, dict)]

    @staticmethod
    def _extract_is_call(row: dict[str, Any]) -> bool | None:
        raw_is_call = row.get("is_call")
        if isinstance(raw_is_call, bool):
            return raw_is_call

        raw_type = row.get("option_type", row.get("type"))
        text = str(raw_type).strip().upper()
        if text in ("CALL", "C"):
            return True
        if text in ("PUT", "P"):
            return False
        return None

    @classmethod
    def _extract_iv(cls, row: dict[str, Any]) -> float | None:
        for key in ("computed_iv", "iv", "implied_volatility"):
            iv = cls._normalize_iv(row.get(key))
            if iv is not None and iv > 0.0:
                return iv
        return None

    @classmethod
    def _extract_delta(cls, row: dict[str, Any], *, is_call: bool) -> float | None:
        for key in ("computed_delta", "delta"):
            raw = row.get(key)
            if raw is None:
                continue
            try:
                delta = float(raw)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(delta):
                continue

            if abs(delta) > 1.0 and abs(delta) <= 100.0:
                delta = delta / 100.0
            if abs(delta) > 1.0:
                continue

            if is_call and delta < 0:
                delta = abs(delta)
            if not is_call and delta > 0:
                delta = -delta
            return delta
        return None

    @staticmethod
    def _normalize_iv(value: Any) -> float | None:
        try:
            iv = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(iv):
            return None
        if iv > 3.0 and iv <= 300.0:
            iv = iv / 100.0
        if iv <= 0.0:
            return None
        return iv


class _Skew25dExtractor:
    """Return normalized true 25-delta skew value."""

    def __init__(self, metrics: _Skew25dMetricsExtractor) -> None:
        self._metrics = metrics

    def __call__(self, snapshot: Any) -> float:
        return self._metrics.extract_value(snapshot)

    def reset(self) -> None:
        self._metrics.reset()


class _Skew25dValidExtractor:
    """Return validity flag (1.0/0.0) for true 25-delta skew."""

    def __init__(self, metrics: _Skew25dMetricsExtractor) -> None:
        self._metrics = metrics

    def __call__(self, snapshot: Any) -> float:
        return self._metrics.extract_valid(snapshot)

    def reset(self) -> None:
        self._metrics.reset()


class _RR25CallMinusPutExtractor:
    """Return canonical 25-delta risk reversal: call IV minus put IV."""

    def __init__(self, metrics: _Skew25dMetricsExtractor) -> None:
        self._metrics = metrics

    def __call__(self, snapshot: Any) -> float:
        return self._metrics.extract_rr25(snapshot)

    def reset(self) -> None:
        self._metrics.reset()


class _RealizedVolatilityMetricsExtractor:
    """Rolling annualized realized volatility with per-snapshot memoization."""

    def __init__(self, window_seconds: float = 900.0, min_samples: int = 5) -> None:
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
            vrp = _safe(lambda: compute_vrp(_get_agg(snapshot, "atm_iv", 0.0), realized_vol * 100.0))

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


# ─────────────────────────────────────────────────────────────────────────────
# Factory: build_default_extractors
# ─────────────────────────────────────────────────────────────────────────────

def build_default_extractors() -> list[FeatureSpec]:
    """Build the 12 pre-defined feature specs for L2."""
    spot_roc = _SpotRoCExtractor(window_seconds=60.0)
    iv_vel = _IVVelocityExtractor(window_seconds=60.0)
    wall_speed = _WallMigrationSpeedExtractor(window_seconds=30.0)
    svol_corr = _SVolCorrelationExtractor(window_seconds=900.0)
    mtf_consensus = _MTFConsensusExtractor()
    skew_25d_metrics = _Skew25dMetricsExtractor(delta_tolerance=0.10)
    skew_25d = _Skew25dExtractor(skew_25d_metrics)
    skew_25d_valid = _Skew25dValidExtractor(skew_25d_metrics)
    rr25_call_minus_put = _RR25CallMinusPutExtractor(skew_25d_metrics)
    realized_vol_metrics = _RealizedVolatilityMetricsExtractor(window_seconds=900.0, min_samples=5)
    realized_vol = _RealizedVolatilityExtractor(realized_vol_metrics)
    vrp_realized_based = _RealizedVrpExtractor(realized_vol_metrics)
    turnover_vel = _TurnoverVelocityExtractor()
    max_impact = _MaxImpactExtractor()

    from shared.config import settings

    specs = [
        FeatureSpec(
            name="spot_roc_1m",
            extractor=spot_roc,
            ttl_seconds=1.0,
            description="1-minute spot price rate-of-change (fractional)",
            tags=["momentum", "spot"],
        ),
        FeatureSpec(
            name="turnover_velocity",
            extractor=turnover_vel,
            ttl_seconds=1.0,
            description="Institutional turnover speed (USD/sec)",
            tags=["microstructure", "flow", "institutional"],
        ),
        FeatureSpec(
            name="atm_iv",
            extractor=lambda s: _get_agg(s, "atm_iv", 0.0),
            ttl_seconds=1.0,
            description="ATM implied volatility (annualized)",
            tags=["iv", "regime"],
        ),
        FeatureSpec(
            name="net_gex_normalized",
            # net_gex is MMUSD; normalize by $1B => divide by 1000 MMUSD.
            extractor=lambda s: _safe(lambda: max(-1.0, min(1.0, _get_agg(s, "net_gex", 0.0) / 1000.0))),
            ttl_seconds=1.0,
            description="OI-based net GEX proxy (MMUSD) normalized by $1B reference (/1000)",
            tags=["gex", "regime"],
        ),
        FeatureSpec(
            name="vpin_composite",
            extractor=lambda s: _get_ms(s, "vpin_composite", 0.0),
            ttl_seconds=1.0,
            description="Composite VPIN toxicity score [0, 1]",
            tags=["microstructure", "flow"],
        ),
        FeatureSpec(
            name="bbo_imbalance_ewma",
            extractor=lambda s: _safe(lambda: max(-1.0, min(1.0, _get_ms(s, "bbo_ewma_fast", 0.0)))),
            ttl_seconds=1.0,
            description="BBO imbalance fast EWMA, clamped to [-1, 1]",
            tags=["microstructure", "orderbook"],
        ),
        FeatureSpec(
            name="call_wall_distance",
            extractor=lambda s: _safe(
                lambda: (_get_agg(s, "call_wall", 0.0) - _get_val(s, "spot", 0.0)) / _get_val(s, "spot", 1.0)
                if _get_val(s, "spot", 0.0) > 0 else 0.0
            ),
            ttl_seconds=1.0,
            description="(call_wall proxy - spot) / spot — distance to trading-practice resistance proxy",
            tags=["gex", "structure"],
        ),
        FeatureSpec(
            name="iv_velocity_1m",
            extractor=iv_vel,
            ttl_seconds=1.0,
            description="1-min IV velocity, scaled to [-1, +1]",
            tags=["iv", "momentum"],
        ),
        FeatureSpec(
            name="wall_migration_speed",
            extractor=wall_speed,
            ttl_seconds=5.0,
            description="Call+put wall migration speed, normalized [0, 1]",
            tags=["gex", "structure", "momentum"],
        ),
        FeatureSpec(
            name="svol_correlation_15m",
            extractor=svol_corr,
            ttl_seconds=15.0,
            description="15-min Pearson correlation (spot, IV). Negative=normal.",
            tags=["vanna", "regime"],
        ),
        FeatureSpec(
            name="vol_accel_ratio",
            extractor=lambda s: _safe(
                lambda: max(-1.0, min(1.0, (_get_ms(s, "vol_accel_ratio", 1.0) - 1.0)))
            ),
            ttl_seconds=1.0,
            description="Vol accel ratio minus 1.0, clamped to [-1,+1]",
            tags=["microstructure", "momentum"],
        ),
        FeatureSpec(
            name="skew_25d_normalized",
            extractor=skew_25d,
            ttl_seconds=5.0,
            description=(
                "Legacy normalized skew contract: (put_iv - call_iv) / atm_iv "
                "using nearest ±25d legs and IV priority computed_iv>iv>implied_volatility"
            ),
            tags=["skew", "regime"],
        ),
        FeatureSpec(
            name="rr25_call_minus_put",
            extractor=rr25_call_minus_put,
            ttl_seconds=5.0,
            description=(
                "Canonical RR25 contract: call_iv(+0.25 delta) - put_iv(-0.25 delta) "
                "using IV priority computed_iv>iv>implied_volatility"
            ),
            tags=["skew", "regime", "canonical"],
        ),
        FeatureSpec(
            name="skew_25d_valid",
            extractor=skew_25d_valid,
            ttl_seconds=5.0,
            description="1.0 when both ±25d legs are valid within delta tolerance; otherwise 0.0",
            tags=["skew", "quality"],
        ),
        FeatureSpec(
            name="realized_volatility_15m",
            extractor=realized_vol,
            ttl_seconds=1.0,
            description="Rolling 15-minute annualized realized volatility (decimal) from spot log returns",
            tags=["iv", "research", "realized-vol"],
        ),
        FeatureSpec(
            name="mtf_consensus_score",
            extractor=mtf_consensus,
            ttl_seconds=5.0,
            description="Multi-timeframe IV velocity consensus [-1, +1]",
            tags=["iv", "mtf", "regime"],
        ),
        FeatureSpec(
            name="net_charm_raw_sum",
            extractor=lambda s: _get_agg_first(s, ("net_charm_raw_sum", "net_charm"), 0.0),
            ttl_seconds=1.0,
            description="Canonical raw chain sum of charm sensitivities; not position-weighted exposure",
            tags=["gex", "charm", "sensitivity", "canonical"],
        ),
        FeatureSpec(
            name="net_charm",
            extractor=lambda s: _get_agg_first(s, ("net_charm_raw_sum", "net_charm"), 0.0),
            ttl_seconds=1.0,
            description="Legacy alias of net_charm_raw_sum",
            tags=["gex", "charm", "sensitivity"],
        ),
        FeatureSpec(
            name="net_vanna_raw_sum",
            extractor=lambda s: _get_agg_first(s, ("net_vanna_raw_sum", "net_vanna"), 0.0),
            ttl_seconds=1.0,
            description="Canonical raw chain sum of vanna sensitivities; not position-weighted exposure",
            tags=["gex", "vanna", "sensitivity", "canonical"],
        ),
        FeatureSpec(
            name="net_vanna",
            extractor=lambda s: _get_agg_first(s, ("net_vanna_raw_sum", "net_vanna"), 0.0),
            ttl_seconds=1.0,
            description="Legacy alias of net_vanna_raw_sum",
            tags=["gex", "vanna", "sensitivity"],
        ),
        FeatureSpec(
            name="vol_risk_premium",
            extractor=lambda s: _safe(
                lambda: compute_vrp(_get_agg(s, "atm_iv", 0.0), settings.vrp_baseline_hv)
            ),
            ttl_seconds=1.0,
            description="ATM IV minus baseline HV in percent points (decimal/percent baseline auto-normalized)",
            tags=["iv", "regime", "vrp"],
        ),
        FeatureSpec(
            name="vrp_realized_based",
            extractor=vrp_realized_based,
            ttl_seconds=1.0,
            description="Research-path VRP in percent points using rolling realized volatility baseline",
            tags=["iv", "research", "vrp", "canonical"],
        ),
        FeatureSpec(
            name="peak_impact",
            extractor=max_impact,
            ttl_seconds=1.0,
            description="Peak institutional impact index proxy (max flow * gamma)",
            tags=["institutional", "threat"],
        ),
    ]
    return specs


def _safe(fn: Callable[[], float], default: float = 0.0) -> float:
    """Safely evaluate a feature extractor, returning default on exception."""
    try:
        v = fn()
        if v is None or not math.isfinite(v):
            return default
        return float(v)
    except Exception as exc:
        logger.debug("feature extractor fallback in _safe(): %s", exc)
        return default


def reset_all_default_extractors(specs: list[FeatureSpec]) -> None:
    """Call reset() on any stateful extractors in a spec list.

    Use at session boundary (day change) to flush historical deques.
    """
    for spec in specs:
        if hasattr(spec.extractor, "reset"):
            spec.extractor.reset()
