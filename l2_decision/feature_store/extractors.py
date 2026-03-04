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


# ─────────────────────────────────────────────────────────────────────────────
# Stateful extractor helpers (carry deque state for ROC / velocity features)
# ─────────────────────────────────────────────────────────────────────────────

class _SpotRoCExtractor:
    """1-minute spot rate-of-change tracker.

    Maintains a sliding window deque of (timestamp, price) pairs.
    Computes ROC = (latest - oldest) / oldest over the window.
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        self._window = window_seconds
        self._history: deque[tuple[float, float]] = deque(maxlen=3600)

    def __call__(self, snapshot: Any) -> float:
        spot = getattr(snapshot, "spot", None)
        if spot is None or not math.isfinite(spot) or spot <= 0:
            return 0.0

        now_mono = time.monotonic()
        self._history.append((now_mono, spot))

        # Prune entries older than window
        cutoff = now_mono - self._window
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

        if len(self._history) < 2:
            return 0.0

        oldest_price = self._history[0][1]
        if oldest_price <= 0:
            return 0.0

        return (spot - oldest_price) / oldest_price  # fractional ROC

    def reset(self) -> None:
        self._history.clear()


class _IVVelocityExtractor:
    """1-minute IV velocity (rate of change of ATM IV).

    Tracks how fast implied volatility is changing, scaled to [-1, +1]
    via soft clamp using a 200bps/min reference velocity.
    """

    _REF_VELOCITY: float = 0.02   # 200bps/min in annualized IV units

    def __init__(self, window_seconds: float = 60.0) -> None:
        self._window = window_seconds
        self._history: deque[tuple[float, float]] = deque(maxlen=3600)

    def __call__(self, snapshot: Any) -> float:
        try:
            iv = snapshot.aggregates.atm_iv
        except AttributeError:
            return 0.0

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
        velocity = (iv - oldest_iv) / self._window  # IV units per second

        # Scale to per-minute and soft-clamp to [-1, +1]
        velocity_per_min = velocity * 60.0
        clamped = velocity_per_min / self._REF_VELOCITY
        return max(-1.0, min(1.0, clamped))

    def reset(self) -> None:
        self._history.clear()


class _WallMigrationSpeedExtractor:
    """5-second call/put wall migration speed feature.

    Measures how fast the gamma wall (call or put) is shifting,
    normalized by the spot price.
    """

    def __init__(self, window_seconds: float = 30.0) -> None:
        self._window = window_seconds
        self._call_history: deque[tuple[float, float]] = deque(maxlen=600)
        self._put_history: deque[tuple[float, float]] = deque(maxlen=600)

    def __call__(self, snapshot: Any) -> float:
        try:
            call_wall = snapshot.aggregates.call_wall
            put_wall = snapshot.aggregates.put_wall
            spot = snapshot.spot
        except AttributeError:
            return 0.0

        if not all(math.isfinite(v) and v > 0 for v in (call_wall, put_wall, spot)):
            return 0.0

        now_mono = time.monotonic()
        self._call_history.append((now_mono, call_wall))
        self._put_history.append((now_mono, put_wall))

        cutoff = now_mono - self._window
        for h in (self._call_history, self._put_history):
            while h and h[0][0] < cutoff:
                h.popleft()

        def _speed(hist: deque) -> float:
            if len(hist) < 2:
                return 0.0
            old_val = hist[0][1]
            new_val = hist[-1][1]
            elapsed = hist[-1][0] - hist[0][0]
            if elapsed < 0.1 or old_val <= 0:
                return 0.0
            return abs((new_val - old_val) / old_val / elapsed)  # fractional speed per sec

        speed = _speed(self._call_history) + _speed(self._put_history)
        # Normalize: 0.001/s (0.1%/s) maps to 1.0
        return min(1.0, speed / 0.001)

    def reset(self) -> None:
        self._call_history.clear()
        self._put_history.clear()


class _SVolCorrelationExtractor:
    """15-minute spot-vol correlation feature.

    Estimates Pearson r between spot moves and IV changes over 15min window.
    Negative correlation (normal regime) → -1; Positive (DANGER_ZONE) → +1.
    """

    def __init__(self, window_seconds: float = 900.0) -> None:
        self._window = window_seconds
        self._history: deque[tuple[float, float, float]] = deque(maxlen=10000)  # (ts, spot, iv)

    def __call__(self, snapshot: Any) -> float:
        try:
            spot = snapshot.spot
            iv = snapshot.aggregates.atm_iv
        except AttributeError:
            return 0.0

        if not (math.isfinite(spot) and spot > 0 and math.isfinite(iv) and iv > 0):
            return 0.0

        now_mono = time.monotonic()
        self._history.append((now_mono, spot, iv))

        cutoff = now_mono - self._window
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

        if len(self._history) < 30:
            return 0.0

        spots = [x[1] for x in self._history]
        ivs = [x[2] for x in self._history]

        # Pearson correlation
        n = len(spots)
        mean_s = sum(spots) / n
        mean_iv = sum(ivs) / n
        num = sum((s - mean_s) * (iv - mean_iv) for s, iv in zip(spots, ivs))
        std_s = math.sqrt(sum((s - mean_s) ** 2 for s in spots) / n)
        std_iv = math.sqrt(sum((iv - mean_iv) ** 2 for iv in ivs) / n)

        if std_s < 1e-9 or std_iv < 1e-9:
            return 0.0

        return max(-1.0, min(1.0, num / (n * std_s * std_iv)))

    def reset(self) -> None:
        self._history.clear()


class _MTFConsensusExtractor:
    """Multi-timeframe IV consensus score [-1, +1].

    Combines 3 IV velocity timeframes (1m/5m/15m) into a consensus:
    All three agree → ±1.0; All neutral → 0.0.
    """

    def __init__(self) -> None:
        self._iv1m = _IVVelocityExtractor(window_seconds=60.0)
        self._iv5m = _IVVelocityExtractor(window_seconds=300.0)
        self._iv15m = _IVVelocityExtractor(window_seconds=900.0)

    def __call__(self, snapshot: Any) -> float:
        v1 = self._iv1m(snapshot)
        v5 = self._iv5m(snapshot)
        v15 = self._iv15m(snapshot)
        # Weighted average: shorter timeframes get higher weight for 0DTE
        consensus = 0.5 * v1 + 0.3 * v5 + 0.2 * v15
        return max(-1.0, min(1.0, consensus))

    def reset(self) -> None:
        self._iv1m.reset()
        self._iv5m.reset()
        self._iv15m.reset()


class _Skew25dExtractor:
    """25-delta normalized skew: (put_IV_25d - call_IV_25d) / atm_IV.

    Uses the full option chain from the snapshot to find approx 25-delta strikes.
    Falls back to 0.0 if chain is not available.
    """

    def __call__(self, snapshot: Any) -> float:
        try:
            chain = snapshot.chain
            spot = snapshot.spot
            atm_iv = snapshot.aggregates.atm_iv
        except AttributeError:
            return 0.0

        if not (chain is not None and math.isfinite(spot) and spot > 0
                and math.isfinite(atm_iv) and atm_iv > 0):
            return 0.0

        # Try to get chain as list of dicts
        try:
            import pyarrow as pa
            if isinstance(chain, pa.RecordBatch):
                chain_list = chain.to_pylist()
            else:
                chain_list = list(chain)
        except (ImportError, Exception):
            return 0.0

        if not chain_list:
            return 0.0

        # Find OTM call and put nearest to 25-delta by moneyness proxy
        # Approx: 25Δ call at ~2.5% OTM, 25Δ put at ~2.5% OTM
        target_moneyness = 0.025
        call_ivs = []
        put_ivs = []

        for row in chain_list:
            try:
                strike = float(row.get("strike", 0.0))
                iv = float(row.get("implied_volatility", 0.0))
                otype = str(row.get("type", "")).upper()
                if not (math.isfinite(strike) and strike > 0
                        and math.isfinite(iv) and iv > 0):
                    continue
                m = abs(strike - spot) / spot
                if abs(m - target_moneyness) < 0.01:
                    if "CALL" in otype:
                        call_ivs.append(iv)
                    elif "PUT" in otype:
                        put_ivs.append(iv)
            except (TypeError, ValueError):
                continue

        if not call_ivs or not put_ivs:
            return 0.0

        put_iv_25d = sum(put_ivs) / len(put_ivs)
        call_iv_25d = sum(call_ivs) / len(call_ivs)
        skew = (put_iv_25d - call_iv_25d) / atm_iv
        return max(-1.0, min(1.0, skew))


# ─────────────────────────────────────────────────────────────────────────────
# Factory: build_default_extractors
# ─────────────────────────────────────────────────────────────────────────────

def build_default_extractors() -> list[FeatureSpec]:
    """Build the 12 pre-defined feature specs for L2.

    Stateful extractors (ROC, velocity, correlation) carry their own deque
    state. These objects must persist across ticks — do not re-instantiate.

    Returns:
        List of FeatureSpec ready for FeatureStore.register_bulk().
    """
    # Instantiate stateful extractors once
    spot_roc = _SpotRoCExtractor(window_seconds=60.0)
    iv_vel = _IVVelocityExtractor(window_seconds=60.0)
    wall_speed = _WallMigrationSpeedExtractor(window_seconds=30.0)
    svol_corr = _SVolCorrelationExtractor(window_seconds=900.0)
    mtf_consensus = _MTFConsensusExtractor()
    skew_25d = _Skew25dExtractor()

    specs = [
        # 1. Spot momentum: 1-min ROC (fractional)
        FeatureSpec(
            name="spot_roc_1m",
            extractor=spot_roc,
            ttl_seconds=1.0,
            description="1-minute spot price rate-of-change (fractional)",
            tags=["momentum", "spot"],
        ),
        # 2. ATM implied volatility (raw)
        FeatureSpec(
            name="atm_iv",
            extractor=lambda s: _safe(lambda: s.aggregates.atm_iv),
            ttl_seconds=1.0,
            description="ATM implied volatility (annualized)",
            tags=["iv", "regime"],
        ),
        # 3. Net GEX normalized to [-1, +1] via $1B reference
        FeatureSpec(
            name="net_gex_normalized",
            extractor=lambda s: _safe(lambda: max(-1.0, min(1.0, s.aggregates.net_gex / 1e9))),
            ttl_seconds=1.0,
            description="Net GEX normalized by $1B reference",
            tags=["gex", "regime"],
        ),
        # 4. VPIN composite toxicity score
        FeatureSpec(
            name="vpin_composite",
            extractor=lambda s: _safe(lambda: s.microstructure.vpin_composite),
            ttl_seconds=1.0,
            description="Composite VPIN toxicity score [0, 1]",
            tags=["microstructure", "flow"],
        ),
        # 5. BBO imbalance EWMA (fast)
        FeatureSpec(
            name="bbo_imbalance_ewma",
            extractor=lambda s: _safe(lambda: max(-1.0, min(1.0, s.microstructure.bbo_ewma_fast))),
            ttl_seconds=1.0,
            description="BBO imbalance fast EWMA, clamped to [-1, 1]",
            tags=["microstructure", "orderbook"],
        ),
        # 6. Call wall distance (fractional, positive = wall above spot)
        FeatureSpec(
            name="call_wall_distance",
            extractor=lambda s: _safe(
                lambda: (s.aggregates.call_wall - s.spot) / s.spot
                if s.spot > 0 else 0.0
            ),
            ttl_seconds=1.0,
            description="(call_wall - spot) / spot — distance to resistance",
            tags=["gex", "structure"],
        ),
        # 7. IV velocity 1-minute
        FeatureSpec(
            name="iv_velocity_1m",
            extractor=iv_vel,
            ttl_seconds=1.0,
            description="1-min IV velocity, scaled to [-1, +1]",
            tags=["iv", "momentum"],
        ),
        # 8. Wall migration speed (combined call+put wall drift)
        FeatureSpec(
            name="wall_migration_speed",
            extractor=wall_speed,
            ttl_seconds=5.0,
            description="Call+put wall migration speed, normalized [0, 1]",
            tags=["gex", "structure", "momentum"],
        ),
        # 9. Spot-Vol 15-min Pearson correlation
        FeatureSpec(
            name="svol_correlation_15m",
            extractor=svol_corr,
            ttl_seconds=15.0,
            description="15-min Pearson correlation (spot, IV). Negative=normal.",
            tags=["vanna", "regime"],
        ),
        # 10. Volume acceleration ratio
        FeatureSpec(
            name="vol_accel_ratio",
            extractor=lambda s: _safe(
                lambda: max(-1.0, min(1.0, (s.microstructure.vol_accel_ratio - 1.0)))
            ),
            ttl_seconds=1.0,
            description="Vol accel ratio minus 1.0, clamped to [-1,+1]",
            tags=["microstructure", "momentum"],
        ),
        # 11. 25-delta skew (normalized by ATM IV)
        FeatureSpec(
            name="skew_25d_normalized",
            extractor=skew_25d,
            ttl_seconds=5.0,
            description="Normalized 25-delta skew: (put25d - call25d) / atm_iv",
            tags=["skew", "regime"],
        ),
        # 12. MTF IV consensus
        FeatureSpec(
            name="mtf_consensus_score",
            extractor=mtf_consensus,
            ttl_seconds=5.0,
            description="Multi-timeframe IV velocity consensus [-1, +1]",
            tags=["iv", "mtf", "regime"],
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
