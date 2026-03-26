"""Diagnostics helpers for ActiveOptionsRuntimeService."""

from __future__ import annotations

from typing import Any

from shared.config import settings
from . import runtime_service_support as support
from .constants import (
    ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_MISSING_GAMMA,
    ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_MISSING_TURNOVER,
    ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_DEGRADED,
    ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_LIVE,
)


def build_runtime_service_diagnostics(service: Any, latest: list[dict[str, Any]]) -> dict[str, Any]:
    """Build /debug/persistence_status payload for the runtime service."""
    placeholder_rows = sum(1 for row in latest if bool(row.get("is_placeholder", False)))
    synthetic_rows = sum(
        1
        for row in latest
        if bool(row.get("row_quality") == support.ROW_QUALITY_FALLBACK_SYNTHETIC)
        or bool(row.get("is_synthetic_fallback", False))
    )
    total_rows = len(latest)
    real_rows = max(0, total_rows - placeholder_rows)
    real_non_synthetic = max(0, real_rows - synthetic_rows)
    degraded_rows = sum(
        1
        for row in latest
        if str(row.get("flow_signal_state", "")).strip().upper()
        == ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_DEGRADED
    )
    live_rows = sum(
        1
        for row in latest
        if str(row.get("flow_signal_state", "")).strip().upper()
        == ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_LIVE
    )
    missing_gamma_rows = sum(
        1
        for row in latest
        if str(row.get("flow_signal_reason", "")).strip()
        == ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_MISSING_GAMMA
    )
    missing_turnover_rows = sum(
        1
        for row in latest
        if str(row.get("flow_signal_reason", "")).strip()
        == ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_MISSING_TURNOVER
    )
    return {
        "rows_total": total_rows,
        "rows_placeholder": placeholder_rows,
        "rows_real": real_rows,
        "rows_real_non_synthetic": real_non_synthetic,
        "rows_synthetic_fallback": synthetic_rows,
        "degraded_rows": degraded_rows,
        "live_rows": live_rows,
        "missing_gamma_rows": missing_gamma_rows,
        "missing_turnover_rows": missing_turnover_rows,
        "all_placeholder": bool(total_rows > 0 and placeholder_rows == total_rows),
        "empty_filter_count": service._empty_filter_count,
        "last_empty_filter_at_utc": service._last_empty_filter_at_utc,
        "empty_filter_fallback_count": service._empty_filter_fallback_count,
        "last_empty_filter_fallback_at_utc": service._last_empty_filter_fallback_at_utc,
        "partial_fallback_count": service._partial_fallback_count,
        "last_partial_fallback_at_utc": service._last_partial_fallback_at_utc,
        "last_partial_fallback_mode": service._last_partial_fallback_mode,
        "filtered_candidates_count": service._last_filtered_candidates_count,
        "supplemented_rows": service._last_supplemented_rows,
        "engine_empty_output_fallback_count": service._engine_empty_output_fallback_count,
        "last_engine_empty_output_fallback_at_utc": service._last_engine_empty_output_fallback_at_utc,
        "last_fallback_mode": service._last_fallback_mode,
        "last_update_at_utc": service._last_update_at_utc,
        "min_volume_threshold": int(getattr(settings, "flow_active_min_volume", 100) or 100),
        "empty_filter_fallback_enabled": bool(
            getattr(settings, "flow_active_empty_filter_fallback_enabled", True)
        ),
        "empty_filter_fallback_max_candidates": max(
            0,
            int(getattr(settings, "flow_active_empty_filter_fallback_max_candidates", 120) or 120),
        ),
    }
