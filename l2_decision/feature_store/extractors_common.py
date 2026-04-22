"""Shared helper utilities for feature extractor modules."""

from __future__ import annotations

import logging
import math
from typing import Any, Callable

logger = logging.getLogger(__name__)


def _get_val(obj: Any, key: str, default: Any = None):
    """Get value from EnrichedSnapshot object (attribute) or dict (key)."""
    if hasattr(obj, key):
        return getattr(obj, key, default)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def _get_agg(obj: Any, key: str, default: Any = None):
    """Get aggregate field from EnrichedSnapshot.aggregates or flat dict."""
    if hasattr(obj, "aggregates"):
        return getattr(obj.aggregates, key, default)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def _get_agg_first(obj: Any, keys: tuple[str, ...], default: Any = None):
    """Get first populated aggregate field across canonical/legacy aliases."""
    for key in keys:
        value = _get_agg(obj, key, None)
        if value is not None:
            return value
    return default


def _get_ms(obj: Any, key: str, default: Any = None):
    """Get microstructure field from EnrichedSnapshot.microstructure or nested dict."""
    if hasattr(obj, "microstructure") and obj.microstructure is not None:
        return getattr(obj.microstructure, key, default)
    if isinstance(obj, dict):
        ms = obj.get("microstructure") or obj.get("micro_structure", {})
        if isinstance(ms, dict):
            state = ms.get("micro_structure_state")
            if isinstance(state, dict):
                return state.get(key, default)
            return ms.get(key, default)
    return default


def _get_meta(obj: Any, key: str, default: Any = None):
    """Get value from EnrichedSnapshot.extra_metadata or nested dict payload."""
    if hasattr(obj, "extra_metadata") and isinstance(obj.extra_metadata, dict):
        return obj.extra_metadata.get(key, default)
    if isinstance(obj, dict):
        meta = obj.get("extra_metadata") or {}
        if isinstance(meta, dict):
            return meta.get(key, default)
    return default


def _get_mm_metric(obj: Any, key: str, default: float = 0.0) -> float:
    metrics = _get_meta(obj, "mm_flow_metrics", {})
    if not isinstance(metrics, dict):
        return default
    raw = metrics.get(key, default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(value):
        return default
    return value


def _safe(fn: Callable[[], float], default: float = 0.0) -> float:
    """Safely evaluate a feature extractor, returning default on exception."""
    try:
        value = fn()
        if value is None or not math.isfinite(value):
            return default
        return float(value)
    except Exception as exc:
        logger.debug("feature extractor fallback in _safe(): %s", exc)
        return default
