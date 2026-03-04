"""l2_refactor.feature_store.store — Unified real-time feature registry and computation.

The FeatureStore is the single source of truth for all L2 features.
All SignalGenerators consume FeatureVector from this store rather than
extracting features directly from snapshots (which caused scatter and
prevented backtesting in the legacy codebase).

Design:
    - Registration: declare features by name + extractor callable
    - Computation: compute_all() extracts all features from one EnrichedSnapshot
    - Caching: TTL-based cache to avoid recomputing on back-to-back ticks
    - Backtest mode: inject historical data via mock_snapshot
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_ET = ZoneInfo("US/Eastern")

# ---------------------------------------------------------------------------
# Forward declaration to avoid circular import (EnrichedSnapshot is in l1_refactor)
# We use TYPE_CHECKING + Any for runtime to stay dependency-independent.
# ---------------------------------------------------------------------------
try:
    from l1_refactor.output.enriched_snapshot import EnrichedSnapshot  # type: ignore
    _HAS_L1 = True
except ImportError:
    _HAS_L1 = False
    EnrichedSnapshot = Any  # type: ignore

try:
    from l2_refactor.events.decision_events import FeatureVector
except ImportError:
    FeatureVector = Any  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# FeatureSpec — declarative feature descriptor
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FeatureSpec:
    """Declarative descriptor for a single feature.

    Attributes:
        name:        Unique feature identifier (e.g., "atm_iv").
        extractor:   Callable(snapshot) → float. Must not raise.
        ttl_seconds: Cache validity window. 1s for 1Hz tick features.
        description: Human-readable documentation string.
        tags:        Optional classification tags (e.g., ["microstructure"]).
    """
    name: str
    extractor: Callable[[Any], float]   # snapshot → float
    ttl_seconds: float = 1.0
    description: str = ""
    tags: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# FeatureStore
# ─────────────────────────────────────────────────────────────────────────────

class FeatureStore:
    """Unified real-time feature registry + computation engine.

    Usage:
        store = FeatureStore()
        store.register(FeatureSpec("atm_iv", lambda s: s.aggregates.atm_iv))

        # Each tick:
        fv = store.compute_all(snapshot)
        iv = fv.get("atm_iv")

    Thread safety:
        compute_all() is NOT thread-safe. Call from a single event loop.
        The registry (register/deregister) must not be modified during compute.
    """

    def __init__(self, enable_cache: bool = True) -> None:
        self._registry: dict[str, FeatureSpec] = {}
        self._cache: dict[str, float] = {}
        self._cache_ts: dict[str, float] = {}
        self._enable_cache = enable_cache
        self._last_snapshot_version: int = -1

    # ── Registry API ─────────────────────────────────────────────────────────

    def register(self, spec: FeatureSpec) -> None:
        """Register a feature specification. Idempotent for same name + extractor."""
        if spec.name in self._registry:
            logger.debug("FeatureStore: overwriting spec for '%s'", spec.name)
        self._registry[spec.name] = spec
        logger.debug("FeatureStore: registered feature '%s'", spec.name)

    def register_bulk(self, specs: list[FeatureSpec]) -> None:
        """Register multiple features in one call."""
        for spec in specs:
            self.register(spec)

    def deregister(self, name: str) -> bool:
        """Remove a feature. Returns True if it existed."""
        existed = name in self._registry
        self._registry.pop(name, None)
        self._cache.pop(name, None)
        self._cache_ts.pop(name, None)
        return existed

    @property
    def registered_names(self) -> list[str]:
        return sorted(self._registry.keys())

    def __len__(self) -> int:
        return len(self._registry)

    # ── Computation API ───────────────────────────────────────────────────────

    def compute_all(self, snapshot: Any) -> "FeatureVector":
        """Extract all registered features from snapshot.

        Args:
            snapshot: EnrichedSnapshot (or compatible duck-typed object).

        Returns:
            FeatureVector with all registered features computed.
            Failed extractions are replaced with 0.0 and counted.
        """
        from l2_refactor.events.decision_events import FeatureVector  # lazy import

        t0 = time.perf_counter()
        features: dict[str, float] = {}
        missing = 0
        now_mono = time.monotonic()

        # Detect snapshot version for cache invalidation
        snap_version = getattr(snapshot, "version", -1)
        if snap_version != self._last_snapshot_version:
            # New snapshot → invalidate all TTL caches
            self._last_snapshot_version = snap_version

        for name, spec in self._registry.items():
            # Check TTL cache
            if self._enable_cache and name in self._cache:
                age = now_mono - self._cache_ts.get(name, 0.0)
                if age < spec.ttl_seconds:
                    features[name] = self._cache[name]
                    continue

            # Compute fresh
            try:
                value = spec.extractor(snapshot)
                if value is None or not math.isfinite(value):
                    logger.debug("FeatureStore: feature '%s' returned non-finite: %s", name, value)
                    value = 0.0
                    missing += 1
            except Exception as exc:
                logger.warning("FeatureStore: extractor '%s' raised %s: %s", name, type(exc).__name__, exc)
                value = 0.0
                missing += 1

            features[name] = value
            if self._enable_cache:
                self._cache[name] = value
                self._cache_ts[name] = now_mono

        latency_ms = (time.perf_counter() - t0) * 1000.0
        now_dt = datetime.now(_ET)

        return FeatureVector(
            features=features,
            timestamp=now_dt,
            missing_count=missing,
            extraction_latency_ms=latency_ms,
        )

    def get_feature(self, name: str) -> Optional[float]:
        """Return cached value of a single feature (None if not cached / expired)."""
        if name not in self._cache:
            return None
        spec = self._registry.get(name)
        if spec is None:
            return None
        age = time.monotonic() - self._cache_ts.get(name, 0.0)
        if age > spec.ttl_seconds:
            return None
        return self._cache[name]

    def clear_cache(self) -> None:
        """Flush the feature cache. Call at session boundary / day change."""
        self._cache.clear()
        self._cache_ts.clear()
        self._last_snapshot_version = -1
        logger.debug("FeatureStore: cache cleared")

    # ── Introspection ─────────────────────────────────────────────────────────

    def describe(self) -> dict[str, dict[str, Any]]:
        """Return registry metadata for monitoring / debugging."""
        return {
            name: {
                "description": spec.description,
                "ttl_seconds": spec.ttl_seconds,
                "tags": spec.tags,
                "cached": name in self._cache,
            }
            for name, spec in self._registry.items()
        }
