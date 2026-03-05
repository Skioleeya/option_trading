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


class _Skew25dExtractor:
    """25-delta normalized skew: (put_IV_25d - call_IV_25d) / atm_IV."""

    def __call__(self, snapshot: Any) -> float:
        chain = _get_val(snapshot, "chain")
        spot = _get_val(snapshot, "spot")
        atm_iv = _get_agg(snapshot, "atm_iv")

        if not (chain is not None and spot and spot > 0 and atm_iv and atm_iv > 0):
            return 0.0

        try:
            import pyarrow as pa
            chain_list = chain.to_pylist() if isinstance(chain, pa.RecordBatch) else list(chain)
        except: return 0.0

        if not chain_list: return 0.0

        target_moneyness = 0.025
        call_ivs, put_ivs = [], []

        for row in chain_list:
            try:
                strike = float(row.get("strike", 0.0))
                iv = float(row.get("implied_volatility", 0.0))
                otype = str(row.get("type", "")).upper()
                if not (strike > 0 and iv > 0): continue
                m = abs(strike - spot) / spot
                if abs(m - target_moneyness) < 0.01:
                    if "CALL" in otype: call_ivs.append(iv)
                    elif "PUT" in otype: put_ivs.append(iv)
            except: continue

        if not call_ivs or not put_ivs: return 0.0
        return max(-1.0, min(1.0, (sum(put_ivs)/len(put_ivs) - sum(call_ivs)/len(call_ivs)) / atm_iv))


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
    skew_25d = _Skew25dExtractor()

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
            name="atm_iv",
            extractor=lambda s: _get_agg(s, "atm_iv", 0.0),
            ttl_seconds=1.0,
            description="ATM implied volatility (annualized)",
            tags=["iv", "regime"],
        ),
        FeatureSpec(
            name="net_gex_normalized",
            extractor=lambda s: _safe(lambda: max(-1.0, min(1.0, _get_agg(s, "net_gex", 0.0) / 1e9))),
            ttl_seconds=1.0,
            description="Net GEX normalized by $1B reference",
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
            description="(call_wall - spot) / spot — distance to resistance",
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
            description="Normalized 25-delta skew: (put25d - call25d) / atm_iv",
            tags=["skew", "regime"],
        ),
        FeatureSpec(
            name="mtf_consensus_score",
            extractor=mtf_consensus,
            ttl_seconds=5.0,
            description="Multi-timeframe IV velocity consensus [-1, +1]",
            tags=["iv", "mtf", "regime"],
        ),
        FeatureSpec(
            name="net_charm",
            extractor=lambda s: _get_agg(s, "net_charm", 0.0),
            ttl_seconds=1.0,
            description="Aggregated net charm exposure across the chain",
            tags=["gex", "charm", "sensitivity"],
        ),
        FeatureSpec(
            name="net_vanna",
            extractor=lambda s: _get_agg(s, "net_vanna", 0.0),
            ttl_seconds=1.0,
            description="Aggregated net vanna exposure across the chain",
            tags=["gex", "vanna", "sensitivity"],
        ),
        FeatureSpec(
            name="vol_risk_premium",
            extractor=lambda s: _safe(
                lambda: (_get_agg(s, "atm_iv", 0.0) * 100.0) - settings.vrp_baseline_hv
            ),
            ttl_seconds=1.0,
            description="ATM IV (%) minus baseline HV (%)",
            tags=["iv", "regime", "vrp"],
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
    except Exception:
        return default


def reset_all_default_extractors(specs: list[FeatureSpec]) -> None:
    """Call reset() on any stateful extractors in a spec list.

    Use at session boundary (day change) to flush historical deques.
    """
    for spec in specs:
        if hasattr(spec.extractor, "reset"):
            spec.extractor.reset()
