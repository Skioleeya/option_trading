"""Main data fetching and computation loop."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from app.loops.atm_live_payload import build_duplicate_snapshot_atm_refresh
from app.loops.compute_metadata import _build_l1_extra_metadata
from app.loops.payload_debug import emit_payload_debug, should_log_duplicate_payload_debug
from app.loops.compute_probe import (
    _SnapshotVersionIvDriftProbe,
    _extract_runtime_atm_iv_context,
    _extract_runtime_spy_atm_iv,
    _extract_snapshot_version,
    _get_iv_sync_context,
)
from app.loops.shared_state import ActiveOptionsInputSnapshot, SharedLoopState
from shared.config import settings
from shared.services.active_options.input_adapter import (
    ActiveOptionsInputSnapshotData,
    build_active_options_input_snapshot,
)

if TYPE_CHECKING:
    from app.container import AppContainer

logger = logging.getLogger(__name__)

L2_AUDIT_FLUSH_EVERY_TICKS = 60
LOOP_OVERRUN_SLEEP_SECONDS = 0.01
ACTIVE_OPTIONS_DEFAULT_GEX_REGIME = "NEUTRAL"


def _to_shared_active_options_input(
    snapshot: ActiveOptionsInputSnapshotData,
) -> ActiveOptionsInputSnapshot:
    return ActiveOptionsInputSnapshot(
        chain=snapshot.chain,
        spot=snapshot.spot,
        atm_iv=snapshot.atm_iv,
        gex_regime=ACTIVE_OPTIONS_DEFAULT_GEX_REGIME,
        ttm_seconds=snapshot.ttm_seconds,
        source_version=snapshot.source_version,
        source_timestamp_utc=snapshot.source_timestamp_utc,
        valid=snapshot.valid,
        invalid_reason=snapshot.invalid_reason,
    )


def _publish_active_options_input(
    state: SharedLoopState,
    *,
    l0_snapshot: dict[str, Any],
    l1_snapshot: Any,
) -> None:
    adapted = build_active_options_input_snapshot(
        l0_snapshot=l0_snapshot,
        l1_snapshot=l1_snapshot,
    )
    state.update_active_options_input(_to_shared_active_options_input(adapted))


def _select_l1_chain_input(snapshot: dict[str, Any]) -> Any:
    chain_arrow = snapshot.get("chain_arrow")
    if chain_arrow is not None:
        return chain_arrow
    return snapshot.get("chain", [])


def _count_rows(rows: Any) -> int:
    if not isinstance(rows, list):
        return 0
    return len(rows)


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
    version_iv_probe: _SnapshotVersionIvDriftProbe,
    compute_interval: float,
) -> tuple[int, int | None]:
    chain_size = _count_rows(snapshot.get("chain"))
    snapshot_version = _extract_snapshot_version(snapshot)
    state.record_compute_tick(snapshot_version)

    iv_cache, spot_sync = _get_iv_sync_context(ctr.option_chain_builder)
    iv_cache_size = len(iv_cache)

    if _is_duplicate_snapshot(snapshot_version, last_processed_version):
        atm_decay_payload = await ctr.atm_decay_tracker.update(
            snapshot.get("chain", []),
            snapshot.get("spot", 0.0),
        )
        refreshed = build_duplicate_snapshot_atm_refresh(state.frozen, atm_decay_payload)
        if refreshed is not None:
            state.update(refreshed, snapshot.get("spot"))
        state.record_duplicate_snapshot_skip(snapshot_version)
        logger.info(
            "[GPU-AUDIT] duplicate snapshot skipped tick_id=%s snapshot_version=%s "
            "last_compute_id=%s",
            tick_id,
            snapshot_version,
            compute_id,
        )
        if refreshed is not None:
            logger.info(
                "[AtmDecay] duplicate snapshot live refresh tick_id=%s snapshot_version=%s atm_timestamp=%s",
                tick_id,
                snapshot_version,
                str((atm_decay_payload or {}).get("timestamp", "")),
            )
        if refreshed is not None or should_log_duplicate_payload_debug(tick_id):
            emit_payload_debug(
                logger,
                frozen=refreshed or state.frozen,
                tick_id=tick_id,
                snapshot_version=snapshot_version,
                duplicate_snapshot=True,
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
        atm_iv_context=_extract_runtime_atm_iv_context(l1_snap),
    )
    state.update_snapshot_version_iv_probe(probe_diag)
    _publish_active_options_input(
        state,
        l0_snapshot=snapshot,
        l1_snapshot=l1_snap,
    )

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
        chain_snapshot=_select_l1_chain_input(snapshot),
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
        "[L2] direction=%s, conf=%.2f, lat=%.1fms",
        decision.direction,
        decision.confidence,
        decision.latency_ms,
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
        "[PERF] build_payload breakdown: snapshot=%.1fms, agent=%.1fms, interval=%ss",
        snapshot_time * 1000,
        agent_time * 1000,
        compute_interval,
    )
    logger.debug(
        "[RACE_PROBE] runner tick: chain_size=%s, iv_cache_size=%s, spot=%s",
        chain_size,
        iv_cache_size,
        spot,
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
    emit_payload_debug(
        logger,
        frozen=frozen,
        tick_id=state.compute_ticks_seen,
        snapshot_version=int(getattr(frozen, "version", 0) or 0),
        duplicate_snapshot=False,
    )
    state.update(frozen, spot)


async def _run_compute_tick_safe(
    ctr: "AppContainer",
    state: SharedLoopState,
    *,
    tick_id: int,
    compute_id: int,
    last_processed_version: int | None,
    version_iv_probe: _SnapshotVersionIvDriftProbe,
    compute_interval: float,
) -> tuple[int, int | None]:
    start = time.monotonic()
    try:
        snapshot = await ctr.option_chain_builder.fetch_snapshot(include_chain_arrow=True)
        snapshot_time = time.monotonic() - start
        logger.info(
            "[Debug] L0 Fetch: rust_active=%s shm_stats=%s",
            snapshot.get("rust_active"),
            snapshot.get("shm_stats") is not None,
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
        logger.exception("[AgentRunner] Error in compute loop: %s", exc)
        return compute_id, last_processed_version


async def run_compute_loop(ctr: "AppContainer", state: SharedLoopState) -> None:
    """Compute loop: fetch data -> run agents -> build payload -> save state."""
    next_tick = time.monotonic()
    tick_id = 0
    compute_id = 0
    last_processed_version: int | None = None
    version_iv_probe = _SnapshotVersionIvDriftProbe(
        confirm_ticks=max(1, int(settings.snapshot_iv_probe_confirm_ticks)),
        epsilon=max(0.0, float(settings.snapshot_iv_probe_epsilon)),
        activate_lag_seconds=max(0.0, float(settings.snapshot_iv_probe_activate_lag_seconds)),
        ongoing_log_interval_seconds=max(
            0.0,
            float(settings.snapshot_iv_probe_ongoing_log_interval_seconds),
        ),
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
        next_tick = await _sleep_until_next_tick(next_tick, compute_interval)
