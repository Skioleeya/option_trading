"""Runtime probe helpers for compute-loop snapshot drift diagnostics."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Mapping

from shared.config import settings

logger = logging.getLogger(__name__)

_NON_REACTIVE_IV_SOURCES = frozenset({"rest"})


def _extract_snapshot_version(snapshot: dict[str, Any]) -> int:
    """Best-effort parse of L0 snapshot version for L1/L2 cache invalidation."""
    raw = snapshot.get("version")
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        if not math.isfinite(raw):
            return 0
        return int(raw)
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return 0
        try:
            return int(text)
        except ValueError:
            return 0
    return 0


def _extract_runtime_spy_atm_iv(
    l1_snapshot: Any,
    decision: Any,
) -> float | None:
    """Best-effort extract current tick SPY ATM IV from runtime objects."""
    aggregates = getattr(l1_snapshot, "aggregates", None)
    if aggregates is not None:
        value = getattr(aggregates, "atm_iv", None)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return float(value)

    candidates: list[Any] = []
    decision_data = getattr(decision, "data", None)
    if isinstance(decision_data, dict):
        candidates.extend([decision_data.get("spy_atm_iv"), decision_data.get("atm_iv")])

    for candidate in candidates:
        if isinstance(candidate, (int, float)) and math.isfinite(float(candidate)):
            return float(candidate)
    return None


def _extract_runtime_atm_iv_context(l1_snapshot: Any) -> dict[str, Any]:
    metadata = getattr(l1_snapshot, "extra_metadata", {}) or {}
    context = metadata.get("atm_iv_context", {})
    return dict(context) if isinstance(context, dict) else {}


def _get_iv_sync_context(builder: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read IV sync cache context via public builder API only."""
    getter = getattr(builder, "get_iv_sync_context", None)
    if not callable(getter):
        return {}, {}
    iv_cache, spot_sync = getter()
    return dict(iv_cache or {}), dict(spot_sync or {})


@dataclass
class _SnapshotVersionIvDriftProbe:
    """Runtime probe for snapshot_version vs spy_atm_iv drift behavior."""

    confirm_ticks: int = int(settings.snapshot_iv_probe_confirm_ticks)
    epsilon: float = float(settings.snapshot_iv_probe_epsilon)
    activate_lag_seconds: float = float(settings.snapshot_iv_probe_activate_lag_seconds)
    ongoing_log_interval_seconds: float = float(
        settings.snapshot_iv_probe_ongoing_log_interval_seconds
    )
    last_version: int | None = None
    last_iv: float | None = None
    last_atm_symbol: str | None = None
    last_iv_source: str | None = None
    consecutive_drift_ticks: int = 0
    mismatch_count: int = 0
    drift_active: bool = False
    lag_start_monotonic: float | None = None
    current_lag_seconds: float = 0.0
    last_completed_lag_seconds: float = 0.0
    degraded_reason: str | None = None
    suppressed_reason: str | None = None
    next_ongoing_log_lag_seconds: float = 0.0

    def observe(
        self,
        snapshot_version: Any,
        spy_atm_iv: Any,
        now_monotonic: float,
        *,
        atm_iv_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Observe one compute tick and update internal drift diagnostics."""
        version = self._coerce_version(snapshot_version)
        iv_value = self._coerce_iv(spy_atm_iv)
        context = _normalize_atm_iv_context(atm_iv_context)
        if version is None or iv_value is None:
            self.suppressed_reason = None
            self._mark_degraded(version, iv_value)
            if self.drift_active and self.lag_start_monotonic is not None:
                self.current_lag_seconds = max(
                    0.0,
                    now_monotonic - self.lag_start_monotonic,
                )
            return self.snapshot()

        self.degraded_reason = None
        suppress_reason = self._context_suppress_reason(context)
        if suppress_reason is not None:
            self._reset_tracking(
                version,
                iv_value,
                context,
                suppression_reason=suppress_reason,
            )
            return self.snapshot()

        self.suppressed_reason = None
        if self.last_version is None or self.last_iv is None:
            self._set_baseline(version, iv_value, context)
            return self.snapshot()

        if version <= self.last_version:
            if self.drift_active and self.lag_start_monotonic is not None:
                self.current_lag_seconds = max(
                    0.0,
                    now_monotonic - self.lag_start_monotonic,
                )
            self._set_baseline(version, iv_value, context)
            return self.snapshot()

        if abs(iv_value - self.last_iv) <= self.epsilon:
            self._on_drift_tick(version, iv_value, now_monotonic, context)
        else:
            self._on_recovery(version, iv_value, now_monotonic, context)

        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "confirm_ticks": self.confirm_ticks,
            "epsilon": self.epsilon,
            "activate_lag_seconds": self.activate_lag_seconds,
            "ongoing_log_interval_seconds": self.ongoing_log_interval_seconds,
            "last_version": self.last_version,
            "last_spy_atm_iv": self.last_iv,
            "last_atm_symbol": self.last_atm_symbol,
            "last_iv_source": self.last_iv_source,
            "consecutive_drift_ticks": self.consecutive_drift_ticks,
            "mismatch_count": self.mismatch_count,
            "drift_active": self.drift_active,
            "current_lag_seconds": round(self.current_lag_seconds, 3),
            "last_completed_lag_seconds": round(self.last_completed_lag_seconds, 3),
            "degraded_reason": self.degraded_reason,
            "suppressed_reason": self.suppressed_reason,
        }

    def _context_suppress_reason(self, context: dict[str, str | None]) -> str | None:
        source = context["iv_source"]
        symbol = context["atm_symbol"]

        if self.last_atm_symbol and symbol and symbol != self.last_atm_symbol:
            return f"atm_symbol_changed:{self.last_atm_symbol}->{symbol}"
        if self.last_iv_source and source and source != self.last_iv_source:
            return f"iv_source_changed:{self.last_iv_source}->{source}"
        if source in _NON_REACTIVE_IV_SOURCES:
            return f"non_reactive_iv_source:{source}"
        return None

    def _set_baseline(
        self,
        version: int,
        iv_value: float,
        context: dict[str, str | None],
    ) -> None:
        self.last_version = version
        self.last_iv = iv_value
        self.last_atm_symbol = context["atm_symbol"]
        self.last_iv_source = context["iv_source"]

    def _reset_tracking(
        self,
        version: int,
        iv_value: float,
        context: dict[str, str | None],
        *,
        suppression_reason: str,
    ) -> None:
        if suppression_reason != self.suppressed_reason:
            logger.info(
                "[OBS] snapshot_version_iv_probe_suppressed reason=%s version=%s "
                "spy_atm_iv=%.6f iv_source=%s atm_symbol=%s",
                suppression_reason,
                version,
                iv_value,
                context["iv_source"],
                context["atm_symbol"],
            )
        self.drift_active = False
        self.consecutive_drift_ticks = 0
        self.lag_start_monotonic = None
        self.current_lag_seconds = 0.0
        self.next_ongoing_log_lag_seconds = 0.0
        self.suppressed_reason = suppression_reason
        self._set_baseline(version, iv_value, context)

    def _on_drift_tick(
        self,
        version: int,
        iv_value: float,
        now_monotonic: float,
        context: dict[str, str | None],
    ) -> None:
        self.consecutive_drift_ticks += 1
        if self.lag_start_monotonic is None:
            self.lag_start_monotonic = now_monotonic

        if self.lag_start_monotonic is not None:
            self.current_lag_seconds = max(
                0.0,
                now_monotonic - self.lag_start_monotonic,
            )

        can_activate = (
            self.consecutive_drift_ticks >= self.confirm_ticks
            and self.current_lag_seconds >= max(0.0, float(self.activate_lag_seconds))
        )
        if can_activate and not self.drift_active:
            self.drift_active = True
            self.mismatch_count += 1
            self.next_ongoing_log_lag_seconds = self.current_lag_seconds + max(
                0.0,
                float(self.ongoing_log_interval_seconds),
            )
            logger.warning(
                "[OBS] snapshot_version_iv_drift_start version=%s spy_atm_iv=%.6f "
                "confirm_ticks=%s lag_seconds=%.3f mismatch_count=%s iv_source=%s "
                "atm_symbol=%s",
                version,
                iv_value,
                self.confirm_ticks,
                self.current_lag_seconds,
                self.mismatch_count,
                context["iv_source"],
                context["atm_symbol"],
            )

        if self.drift_active and self.current_lag_seconds >= self.next_ongoing_log_lag_seconds:
            logger.warning(
                "[OBS] snapshot_version_iv_drift_ongoing version=%s spy_atm_iv=%.6f "
                "drift_ticks=%s lag_seconds=%.3f iv_source=%s atm_symbol=%s",
                version,
                iv_value,
                self.consecutive_drift_ticks,
                self.current_lag_seconds,
                context["iv_source"],
                context["atm_symbol"],
            )
            self.next_ongoing_log_lag_seconds = self.current_lag_seconds + max(
                0.0,
                float(self.ongoing_log_interval_seconds),
            )

        self._set_baseline(version, iv_value, context)

    def _on_recovery(
        self,
        version: int,
        iv_value: float,
        now_monotonic: float,
        context: dict[str, str | None],
    ) -> None:
        if self.drift_active and self.lag_start_monotonic is not None:
            lag = max(0.0, now_monotonic - self.lag_start_monotonic)
            self.last_completed_lag_seconds = lag
            logger.warning(
                "[OBS] snapshot_version_iv_drift_recovered version=%s spy_atm_iv=%.6f "
                "lag_seconds=%.3f drift_ticks=%s iv_source=%s atm_symbol=%s",
                version,
                iv_value,
                lag,
                self.consecutive_drift_ticks,
                context["iv_source"],
                context["atm_symbol"],
            )

        self.drift_active = False
        self.consecutive_drift_ticks = 0
        self.lag_start_monotonic = None
        self.current_lag_seconds = 0.0
        self.next_ongoing_log_lag_seconds = 0.0
        self._set_baseline(version, iv_value, context)

    def _mark_degraded(self, version: int | None, iv_value: float | None) -> None:
        if version is None and iv_value is None:
            reason = "invalid_version_and_iv"
        elif version is None:
            reason = "invalid_version"
        else:
            reason = "invalid_spy_atm_iv"

        if reason != self.degraded_reason:
            logger.debug(
                "[OBS] snapshot_version_iv_probe_degraded reason=%s "
                "raw_version=%r raw_spy_atm_iv=%r",
                reason,
                version,
                iv_value,
            )
        self.degraded_reason = reason

    @staticmethod
    def _coerce_version(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if not math.isfinite(value):
                return None
            return int(value)
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            try:
                return int(raw)
            except ValueError:
                return None
        return None

    @staticmethod
    def _coerce_iv(value: Any) -> float | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            value_f = float(value)
            return value_f if math.isfinite(value_f) else None
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            try:
                value_f = float(raw)
            except ValueError:
                return None
            return value_f if math.isfinite(value_f) else None
        return None


def _normalize_atm_iv_context(
    raw: Mapping[str, Any] | None,
) -> dict[str, str | None]:
    if not isinstance(raw, Mapping):
        return {"atm_symbol": None, "iv_source": None}

    symbol = raw.get("atm_symbol")
    source = raw.get("iv_source")
    if symbol is not None:
        symbol = str(symbol).strip() or None
    if source is not None:
        source = str(source).strip().lower() or None
    return {
        "atm_symbol": symbol,
        "iv_source": source,
    }
