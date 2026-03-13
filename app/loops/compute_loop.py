"""Main data fetching and computation loop."""

import asyncio
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from shared.config import settings
from app.loops.shared_state import SharedLoopState

# Only for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.container import AppContainer

logger = logging.getLogger(__name__)

L2_AUDIT_FLUSH_EVERY_TICKS = 60
LOOP_OVERRUN_SLEEP_SECONDS = 0.01


def _coerce_utc_datetime(raw: Any) -> datetime | None:
    if isinstance(raw, datetime):
        dt = raw
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_volume_map(raw: Any) -> dict[str, float]:
    """Normalize volume_map into a JSON-safe strike->volume dict."""
    if not isinstance(raw, dict):
        return {}

    out: dict[str, float] = {}
    for strike, volume in raw.items():
        try:
            strike_f = float(strike)
            volume_f = float(volume)
        except (TypeError, ValueError):
            continue
        if strike_f <= 0 or volume_f < 0:
            continue
        out[str(strike)] = volume_f
    return out


def _normalize_source_timestamp_utc(snapshot: dict[str, Any]) -> str | None:
    """Normalize L0 source timestamp to UTC ISO8601."""
    raw = snapshot.get("as_of_utc")
    if raw is None:
        raw = snapshot.get("as_of")
    dt = _coerce_utc_datetime(raw)
    if dt is None:
        return None
    return dt.isoformat()


def _build_l1_extra_metadata(
    snapshot: dict[str, Any],
    compute_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the L0->L1 metadata pass-through contract."""
    metadata = {
        "rust_active": snapshot.get("rust_active", False),
        "shm_stats": snapshot.get("shm_stats"),
        "volume_map": _normalize_volume_map(snapshot.get("volume_map")),
        "source_data_timestamp_utc": _normalize_source_timestamp_utc(snapshot),
        "longport_option_diagnostics": _build_longport_option_diagnostics(snapshot),
    }
    if compute_audit:
        metadata["compute_audit"] = dict(compute_audit)
    return metadata


def _build_longport_option_diagnostics(snapshot: dict[str, Any]) -> dict[str, float | int | str | None]:
    """Summarize official LongPort premium/standard diagnostics from Tier2/Tier3 caches."""
    diag: dict[str, float | int | str | None] = {
        "tier2_contracts": _count_rows(snapshot.get("tier2_chain")),
        "tier3_contracts": _count_rows(snapshot.get("tier3_chain")),
        "tier2_standard_ratio": _standard_ratio(snapshot.get("tier2_chain")),
        "tier3_standard_ratio": _standard_ratio(snapshot.get("tier3_chain")),
        "tier2_avg_premium": _average_numeric(snapshot.get("tier2_chain"), "premium"),
        "tier3_avg_premium": _average_numeric(snapshot.get("tier3_chain"), "premium"),
    }
    official = snapshot.get("official_hv_diagnostics")
    official_hv_decimal: float | None = None
    official_hv_sample_count = 0
    official_hv_synced_at_utc: str | None = None
    official_hv_age_sec: float | None = None
    official_hv_synced_dt: datetime | None = None

    if isinstance(official, dict):
        raw_hv = official.get("official_hv_decimal")
        try:
            hv_val = float(raw_hv)
        except (TypeError, ValueError):
            hv_val = None
        if hv_val is not None and math.isfinite(hv_val) and hv_val > 0.0:
            official_hv_decimal = hv_val

        raw_count = official.get("official_hv_sample_count")
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            count = 0
        official_hv_sample_count = max(0, count)

        official_hv_synced_dt = _coerce_utc_datetime(official.get("official_hv_synced_at_utc"))
        if official_hv_synced_dt is not None:
            official_hv_synced_at_utc = official_hv_synced_dt.isoformat()

    source_dt = _coerce_utc_datetime(snapshot.get("as_of_utc") or snapshot.get("as_of"))
    if source_dt is not None and official_hv_synced_dt is not None:
        official_hv_age_sec = max(0.0, (source_dt - official_hv_synced_dt).total_seconds())

    diag.update(
        {
            "official_hv_decimal": official_hv_decimal,
            "official_hv_sample_count": official_hv_sample_count,
            "official_hv_synced_at_utc": official_hv_synced_at_utc,
            "official_hv_age_sec": official_hv_age_sec,
        }
    )
    return diag


def _count_rows(rows: Any) -> int:
    if not isinstance(rows, list):
        return 0
    return len(rows)


def _standard_ratio(rows: Any) -> float:
    if not isinstance(rows, list) or not rows:
        return 0.0
    standard_flags = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        standard_flags.append(1 if bool(row.get("standard", False)) else 0)
    if not standard_flags:
        return 0.0
    return sum(standard_flags) / len(standard_flags)


def _average_numeric(rows: Any, key: str) -> float:
    if not isinstance(rows, list) or not rows:
        return 0.0
    values: list[float] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw = row.get(key)
        if raw is None:
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            values.append(value)
    if not values:
        return 0.0
    return sum(values) / len(values)


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


def _get_iv_sync_context(builder: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read IV sync cache context via public builder API only."""
    getter = getattr(builder, "get_iv_sync_context", None)
    if not callable(getter):
        return {}, {}
    iv_cache, spot_sync = getter()
    return dict(iv_cache or {}), dict(spot_sync or {})


def _is_duplicate_snapshot(snapshot_version: int, last_processed_version: int | None) -> bool:
    return (
        snapshot_version > 0
        and last_processed_version is not None
        and snapshot_version == last_processed_version
    )


async def _sleep_until_next_tick(next_tick: float, compute_interval: float) -> float:
    next_tick += compute_interval
    sleep_dur = next_tick - time.monotonic()
    if sleep_dur > 0:
        await asyncio.sleep(sleep_dur)
        return next_tick
    await asyncio.sleep(LOOP_OVERRUN_SLEEP_SECONDS)
    return time.monotonic()


async def _process_snapshot_tick(
    ctr: "AppContainer",
    state: SharedLoopState,
    *,
    snapshot: dict[str, Any],
    snapshot_time: float,
    tick_id: int,
    compute_id: int,
    last_processed_version: int | None,
    version_iv_probe: "_SnapshotVersionIvDriftProbe",
    compute_interval: float,
) -> tuple[int, int | None]:
    chain_size = len(snapshot.get("chain", []))
    snapshot_version = _extract_snapshot_version(snapshot)
    state.record_compute_tick(snapshot_version)

    iv_cache, spot_sync = _get_iv_sync_context(ctr.option_chain_builder)
    iv_cache_size = len(iv_cache)

    if _is_duplicate_snapshot(snapshot_version, last_processed_version):
        state.record_duplicate_snapshot_skip(snapshot_version)
        logger.info(
            "[GPU-AUDIT] duplicate snapshot skipped tick_id=%s snapshot_version=%s last_compute_id=%s",
            tick_id,
            snapshot_version,
            compute_id,
        )
        return compute_id, last_processed_version

    agent_start = time.monotonic()
    next_compute_id, l1_snap, decision = await _run_l1_l2_pipeline(
        ctr,
        state,
        snapshot=snapshot,
        snapshot_version=snapshot_version,
        tick_id=tick_id,
        compute_id=compute_id,
        iv_cache=iv_cache,
        spot_sync=spot_sync,
    )

    probe_diag = version_iv_probe.observe(
        snapshot_version=snapshot_version,
        spy_atm_iv=_extract_runtime_spy_atm_iv(l1_snap, decision),
        now_monotonic=time.monotonic(),
    )
    state.update_snapshot_version_iv_probe(probe_diag)

    atm_decay_payload = await ctr.atm_decay_tracker.update(
        snapshot.get("chain", []),
        snapshot.get("spot", 0.0),
    )
    _log_pipeline_perf(
        snapshot_time=snapshot_time,
        agent_time=time.monotonic() - agent_start,
        compute_interval=compute_interval,
        chain_size=chain_size,
        iv_cache_size=iv_cache_size,
        spot=snapshot.get("spot"),
    )

    await _build_and_store_payload(
        ctr,
        state,
        decision=decision,
        l1_snap=l1_snap,
        atm_decay_payload=atm_decay_payload,
        spot=snapshot.get("spot"),
    )

    if state.total_computations > 0 and state.total_computations % L2_AUDIT_FLUSH_EVERY_TICKS == 0:
        ctr.l2_reactor.flush_audit()

    return next_compute_id, snapshot_version


async def _run_l1_l2_pipeline(
    ctr: "AppContainer",
    state: SharedLoopState,
    *,
    snapshot: dict[str, Any],
    snapshot_version: int,
    tick_id: int,
    compute_id: int,
    iv_cache: dict[str, Any],
    spot_sync: dict[str, Any],
) -> tuple[int, Any, Any]:
    next_compute_id = compute_id + 1
    gpu_task_id = f"gpu-task-{snapshot_version}-{next_compute_id}"
    compute_audit = {
        "tick_id": tick_id,
        "snapshot_version": snapshot_version,
        "compute_id": next_compute_id,
        "gpu_task_id": gpu_task_id,
    }
    l1_snap = await ctr.l1_reactor.compute(
        chain_snapshot=snapshot.get("chain", []),
        spot=snapshot.get("spot", 0.0),
        l0_version=snapshot_version,
        iv_cache=iv_cache,
        spot_at_sync=spot_sync,
        extra_metadata=_build_l1_extra_metadata(snapshot, compute_audit),
    )
    state.record_l1_compute(
        snapshot_version=snapshot_version,
        compute_id=next_compute_id,
        gpu_task_id=gpu_task_id,
    )
    state.update_latest_l1_snapshot(l1_snap)
    decision = await ctr.l2_reactor.decide(l1_snap)
    logger.debug(
        f"[L2] direction={decision.direction}, "
        f"conf={decision.confidence:.2f}, "
        f"lat={decision.latency_ms:.1f}ms"
    )
    return next_compute_id, l1_snap, decision


def _log_pipeline_perf(
    *,
    snapshot_time: float,
    agent_time: float,
    compute_interval: float,
    chain_size: int,
    iv_cache_size: int,
    spot: Any,
) -> None:
    logger.info(
        f"[PERF] build_payload breakdown: "
        f"snapshot={snapshot_time*1000:.1f}ms, "
        f"agent={agent_time*1000:.1f}ms, "
        f"interval={compute_interval}s"
    )
    logger.debug(
        f"[RACE_PROBE] runner tick: chain_size={chain_size}, "
        f"iv_cache_size={iv_cache_size}, "
        f"spot={spot}"
    )


async def _build_and_store_payload(
    ctr: "AppContainer",
    state: SharedLoopState,
    *,
    decision: Any,
    l1_snap: Any,
    atm_decay_payload: dict[str, Any],
    spot: Any,
) -> None:
    frozen = await ctr.l3_reactor.tick(
        decision=decision,
        snapshot=l1_snap,
        atm_decay=atm_decay_payload,
        active_options=ctr.active_options_service.get_latest(),
    )
    state.update(frozen, spot)


async def _run_compute_tick_safe(
    ctr: "AppContainer",
    state: SharedLoopState,
    *,
    tick_id: int,
    compute_id: int,
    last_processed_version: int | None,
    version_iv_probe: "_SnapshotVersionIvDriftProbe",
    compute_interval: float,
) -> tuple[int, int | None]:
    start = time.monotonic()
    try:
        snapshot = await ctr.option_chain_builder.fetch_chain(
            include_legacy_greeks=False,
            caller_tag="compute_loop",
        )
        snapshot_time = time.monotonic() - start
        logger.info(
            f"[Debug] L0 Fetch: rust_active={snapshot.get('rust_active')} "
            f"shm_stats={snapshot.get('shm_stats') is not None}"
        )
        return await _process_snapshot_tick(
            ctr,
            state,
            snapshot=snapshot,
            snapshot_time=snapshot_time,
            tick_id=tick_id,
            compute_id=compute_id,
            last_processed_version=last_processed_version,
            version_iv_probe=version_iv_probe,
            compute_interval=compute_interval,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        state.record_failure()
        logger.exception(f"[AgentRunner] Error in compute loop: {exc}")
        return compute_id, last_processed_version


@dataclass
class _SnapshotVersionIvDriftProbe:
    """Runtime probe for snapshot_version vs spy_atm_iv drift behavior."""

    confirm_ticks: int = int(settings.snapshot_iv_probe_confirm_ticks)
    epsilon: float = float(settings.snapshot_iv_probe_epsilon)
    activate_lag_seconds: float = float(settings.snapshot_iv_probe_activate_lag_seconds)
    ongoing_log_interval_seconds: float = float(settings.snapshot_iv_probe_ongoing_log_interval_seconds)
    last_version: int | None = None
    last_iv: float | None = None
    consecutive_drift_ticks: int = 0
    mismatch_count: int = 0
    drift_active: bool = False
    lag_start_monotonic: float | None = None
    current_lag_seconds: float = 0.0
    last_completed_lag_seconds: float = 0.0
    degraded_reason: str | None = None
    next_ongoing_log_lag_seconds: float = 0.0

    def observe(
        self,
        snapshot_version: Any,
        spy_atm_iv: Any,
        now_monotonic: float,
    ) -> dict[str, Any]:
        """Observe one compute tick and update internal drift diagnostics."""
        version = self._coerce_version(snapshot_version)
        iv_value = self._coerce_iv(spy_atm_iv)
        if version is None or iv_value is None:
            self._mark_degraded(version, iv_value)
            if self.drift_active and self.lag_start_monotonic is not None:
                self.current_lag_seconds = max(0.0, now_monotonic - self.lag_start_monotonic)
            return self.snapshot()

        self.degraded_reason = None

        if self.last_version is None or self.last_iv is None:
            self.last_version = version
            self.last_iv = iv_value
            return self.snapshot()

        if version <= self.last_version:
            if self.drift_active and self.lag_start_monotonic is not None:
                self.current_lag_seconds = max(0.0, now_monotonic - self.lag_start_monotonic)
            self.last_version = version
            self.last_iv = iv_value
            return self.snapshot()

        if abs(iv_value - self.last_iv) <= self.epsilon:
            self._on_drift_tick(version, iv_value, now_monotonic)
        else:
            self._on_recovery(version, iv_value, now_monotonic)

        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "confirm_ticks": self.confirm_ticks,
            "epsilon": self.epsilon,
            "activate_lag_seconds": self.activate_lag_seconds,
            "ongoing_log_interval_seconds": self.ongoing_log_interval_seconds,
            "last_version": self.last_version,
            "last_spy_atm_iv": self.last_iv,
            "consecutive_drift_ticks": self.consecutive_drift_ticks,
            "mismatch_count": self.mismatch_count,
            "drift_active": self.drift_active,
            "current_lag_seconds": round(self.current_lag_seconds, 3),
            "last_completed_lag_seconds": round(self.last_completed_lag_seconds, 3),
            "degraded_reason": self.degraded_reason,
        }

    def _on_drift_tick(self, version: int, iv_value: float, now_monotonic: float) -> None:
        self.consecutive_drift_ticks += 1
        if self.lag_start_monotonic is None:
            self.lag_start_monotonic = now_monotonic

        if self.lag_start_monotonic is not None:
            self.current_lag_seconds = max(0.0, now_monotonic - self.lag_start_monotonic)

        can_activate = (
            self.consecutive_drift_ticks >= self.confirm_ticks
            and self.current_lag_seconds >= max(0.0, float(self.activate_lag_seconds))
        )
        if can_activate and not self.drift_active:
            self.drift_active = True
            self.mismatch_count += 1
            self.next_ongoing_log_lag_seconds = self.current_lag_seconds + max(
                0.0, float(self.ongoing_log_interval_seconds)
            )
            logger.warning(
                "[OBS] snapshot_version_iv_drift_start version=%s spy_atm_iv=%.6f confirm_ticks=%s lag_seconds=%.3f mismatch_count=%s",
                version,
                iv_value,
                self.confirm_ticks,
                self.current_lag_seconds,
                self.mismatch_count,
            )

        if self.drift_active:
            if self.current_lag_seconds >= self.next_ongoing_log_lag_seconds:
                logger.warning(
                    "[OBS] snapshot_version_iv_drift_ongoing version=%s spy_atm_iv=%.6f drift_ticks=%s lag_seconds=%.3f",
                    version,
                    iv_value,
                    self.consecutive_drift_ticks,
                    self.current_lag_seconds,
                )
                self.next_ongoing_log_lag_seconds = self.current_lag_seconds + max(
                    0.0, float(self.ongoing_log_interval_seconds)
                )

        self.last_version = version
        self.last_iv = iv_value

    def _on_recovery(self, version: int, iv_value: float, now_monotonic: float) -> None:
        if self.drift_active and self.lag_start_monotonic is not None:
            lag = max(0.0, now_monotonic - self.lag_start_monotonic)
            self.last_completed_lag_seconds = lag
            logger.warning(
                "[OBS] snapshot_version_iv_drift_recovered version=%s spy_atm_iv=%.6f lag_seconds=%.3f drift_ticks=%s",
                version,
                iv_value,
                lag,
                self.consecutive_drift_ticks,
            )

        self.drift_active = False
        self.consecutive_drift_ticks = 0
        self.lag_start_monotonic = None
        self.current_lag_seconds = 0.0
        self.next_ongoing_log_lag_seconds = 0.0
        self.last_version = version
        self.last_iv = iv_value

    def _mark_degraded(self, version: int | None, iv_value: float | None) -> None:
        if version is None and iv_value is None:
            reason = "invalid_version_and_iv"
        elif version is None:
            reason = "invalid_version"
        else:
            reason = "invalid_spy_atm_iv"

        if reason != self.degraded_reason:
            logger.debug(
                "[OBS] snapshot_version_iv_probe_degraded reason=%s raw_version=%r raw_spy_atm_iv=%r",
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


async def run_compute_loop(ctr: 'AppContainer', state: SharedLoopState) -> None:
    """Compute loop: fetch data → run agents → build payload → save state.

    Runs at a constant cadence defined by websocket_update_interval.
    """
    next_tick = time.monotonic()
    tick_id = 0
    compute_id = 0
    last_processed_version: int | None = None
    version_iv_probe = _SnapshotVersionIvDriftProbe(
        confirm_ticks=max(1, int(settings.snapshot_iv_probe_confirm_ticks)),
        epsilon=max(0.0, float(settings.snapshot_iv_probe_epsilon)),
        activate_lag_seconds=max(0.0, float(settings.snapshot_iv_probe_activate_lag_seconds)),
        ongoing_log_interval_seconds=max(0.0, float(settings.snapshot_iv_probe_ongoing_log_interval_seconds)),
    )

    while True:
        compute_interval = settings.websocket_update_interval
        state.current_compute_interval = compute_interval
        tick_id += 1
        compute_id, last_processed_version = await _run_compute_tick_safe(
            ctr,
            state,
            tick_id=tick_id,
            compute_id=compute_id,
            last_processed_version=last_processed_version,
            version_iv_probe=version_iv_probe,
            compute_interval=compute_interval,
        )

        # Drift-corrected sleep with dynamic cadence
        next_tick = await _sleep_until_next_tick(next_tick, compute_interval)
