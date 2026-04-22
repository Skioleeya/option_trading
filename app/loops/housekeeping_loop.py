"""Housekeeping loop for background non-critical computation syncs."""

import asyncio
import logging
import time
from typing import Any

from shared.config import settings
from shared.services.active_options_constants import ACTIVE_OPTIONS_DEFAULT_LIMIT
from app.loops.shared_state import ActiveOptionsInputSnapshot, SharedLoopState

# Only for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.container import AppContainer

logger = logging.getLogger(__name__)

ACTIVE_OPTIONS_LIMIT = ACTIVE_OPTIONS_DEFAULT_LIMIT
HOUSEKEEPING_OVERRUN_SLEEP_SECONDS = 0.01
ACTIVE_OPTIONS_DEFAULT_GEX_REGIME = "NEUTRAL"
ACTIVE_OPTIONS_INVALID_REASON_MISSING_INPUT = "missing_input"


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_agent_g_context(payload_dict: dict[str, Any] | None) -> tuple[float, str]:
    if not payload_dict:
        return 0.0, ACTIVE_OPTIONS_DEFAULT_GEX_REGIME
    g_data = payload_dict.get("agent_g", {}).get("data", {})
    atm_iv = _to_float(g_data.get("spy_atm_iv"), 0.0)
    gex_regime = str(g_data.get("gex_regime", ACTIVE_OPTIONS_DEFAULT_GEX_REGIME))
    return atm_iv, gex_regime


def _resolve_runtime_context(
    state: SharedLoopState,
    snapshot: ActiveOptionsInputSnapshot | None,
) -> tuple[float, str]:
    payload_atm_iv, payload_gex_regime = _extract_agent_g_context(state.payload_dict)
    if snapshot is None:
        return payload_atm_iv, payload_gex_regime

    atm_iv = _to_float(snapshot.atm_iv, 0.0)
    resolved_atm_iv = atm_iv if atm_iv > 0.0 else payload_atm_iv
    snapshot_gex_regime = str(snapshot.gex_regime or "").strip()
    resolved_gex_regime = snapshot_gex_regime or payload_gex_regime or ACTIVE_OPTIONS_DEFAULT_GEX_REGIME
    return resolved_atm_iv, resolved_gex_regime


def _next_input_version(
    snapshot: ActiveOptionsInputSnapshot | None,
    last_source_version: int | None,
) -> int | None:
    if snapshot is None:
        return last_source_version
    source_version = int(snapshot.source_version or 0)
    if source_version <= 0:
        return last_source_version
    return source_version


def _is_duplicate_source_version(
    snapshot: ActiveOptionsInputSnapshot | None,
    last_source_version: int | None,
) -> bool:
    if snapshot is None:
        return False
    source_version = int(snapshot.source_version or 0)
    return source_version > 0 and last_source_version == source_version


def _summarize_active_options_input(
    snapshot: ActiveOptionsInputSnapshot,
) -> dict[str, Any]:
    chain = snapshot.chain if isinstance(snapshot.chain, list) else []
    day_volume_gt_zero = 0
    current_volume_gt_zero = 0
    turnover_gt_zero = 0
    gamma_nonzero = 0
    for row in chain:
        if not isinstance(row, dict):
            continue
        day_volume = _to_float(row.get("volume"), 0.0)
        current_volume = _to_float(row.get("current_volume"), 0.0)
        turnover = _to_float(row.get("turnover"), 0.0)
        gamma = _to_float(row.get("gamma"), 0.0)
        if day_volume > 0.0:
            day_volume_gt_zero += 1
        if current_volume > 0.0:
            current_volume_gt_zero += 1
        if turnover > 0.0:
            turnover_gt_zero += 1
        if gamma != 0.0:
            gamma_nonzero += 1
    return {
        "chain_size": len(chain),
        "day_volume_gt_zero": day_volume_gt_zero,
        "current_volume_gt_zero": current_volume_gt_zero,
        "turnover_gt_zero": turnover_gt_zero,
        "gamma_nonzero": gamma_nonzero,
    }


def _log_active_options_flow_snapshot(
    ctr: "AppContainer",
    *,
    source_version: int | None,
) -> None:
    service = getattr(ctr, "active_options_service", None)
    if service is None or not hasattr(service, "get_latest"):
        return
    rows = service.get_latest()
    if not isinstance(rows, list):
        return
    top_rows = []
    for row in rows[:3]:
        if not isinstance(row, dict):
            continue
        top_rows.append(
            "%s/%s/%s flow=%s score=%s state=%s"
            % (
                row.get("symbol"),
                row.get("option_type"),
                row.get("strike"),
                row.get("flow"),
                row.get("flow_score"),
                row.get("flow_signal_state"),
            )
        )
    logger.debug(
        "[ActiveOptionsFlow] source_version=%s rows=%d top=%s",
        source_version,
        len(rows),
        " | ".join(top_rows) if top_rows else "none",
    )


def _service_latest_source_version(ctr: "AppContainer") -> int:
    service = getattr(ctr, "active_options_service", None)
    if service is None or not hasattr(service, "get_diagnostics"):
        return 0
    diagnostics = service.get_diagnostics()
    if not isinstance(diagnostics, dict):
        return 0
    try:
        return max(0, int(diagnostics.get("latest_source_version", 0) or 0))
    except (TypeError, ValueError):
        return 0


async def _update_active_options_from_shared_input(
    ctr: "AppContainer",
    state: SharedLoopState,
    *,
    last_source_version: int | None,
) -> int | None:
    snapshot = state.latest_active_options_input
    if _is_duplicate_source_version(snapshot, last_source_version):
        logger.info(
            "[GPU-AUDIT] housekeeping_skip_duplicate_active_input source_version=%s",
            int(snapshot.source_version or 0),
        )
        return last_source_version

    resolved_atm_iv, resolved_gex_regime = _resolve_runtime_context(state, snapshot)
    if snapshot is None:
        logger.warning(
            "[ActiveOptionsFlow] waiting_input reason=%s gex_regime=%s",
            ACTIVE_OPTIONS_INVALID_REASON_MISSING_INPUT,
            resolved_gex_regime,
        )
        return last_source_version

    if not bool(snapshot.valid):
        logger.error(
            "[ActiveOptionsFlow] invalid_input reason=%s source_version=%s gex_regime=%s",
            str(snapshot.invalid_reason or ACTIVE_OPTIONS_INVALID_REASON_MISSING_INPUT),
            int(snapshot.source_version or 0),
            resolved_gex_regime,
        )
        raise RuntimeError(
            "active_options_input_invalid: reason=%s gex_regime=%s"
            % (str(snapshot.invalid_reason or ACTIVE_OPTIONS_INVALID_REASON_MISSING_INPUT), resolved_gex_regime)
        )

    summary = _summarize_active_options_input(snapshot)
    source_version = int(snapshot.source_version or 0)
    if source_version > 0 and _service_latest_source_version(ctr) == source_version:
        logger.debug(
            "[ActiveOptionsFlow] source_version_already_synced=%s skip_housekeeping_compute=true",
            source_version,
        )
        return _next_input_version(snapshot, last_source_version)
    logger.debug(
        "[ActiveOptionsFlow] input source_version=%s valid=%s gex_regime=%s "
        "chain_size=%s day_volume_gt_zero=%s current_volume_gt_zero=%s "
        "turnover_gt_zero=%s gamma_nonzero=%s",
        int(snapshot.source_version or 0),
        bool(snapshot.valid),
        resolved_gex_regime,
        summary["chain_size"],
        summary["day_volume_gt_zero"],
        summary["current_volume_gt_zero"],
        summary["turnover_gt_zero"],
        summary["gamma_nonzero"],
    )

    await ctr.active_options_service.update_background(
        chain=snapshot.chain,
        spot=_to_float(snapshot.spot, 0.0),
        atm_iv=resolved_atm_iv,
        gex_regime=resolved_gex_regime,
        ttm_seconds=snapshot.ttm_seconds,
        redis=ctr.redis_service.client,
        limit=ACTIVE_OPTIONS_LIMIT,
        source_version=source_version,
    )
    _log_active_options_flow_snapshot(
        ctr,
        source_version=int(snapshot.source_version or 0),
    )
    return _next_input_version(snapshot, last_source_version)


def _sync_anchor_symbols(ctr: "AppContainer") -> None:
    anchor_symbols = ctr.atm_decay_tracker.get_anchor_symbols()
    ctr.option_chain_builder.set_mandatory_symbols(anchor_symbols)


async def _sleep_until_next_tick(next_tick: float, update_interval: float) -> float:
    next_tick += update_interval
    sleep_dur = next_tick - time.monotonic()
    if sleep_dur > 0:
        await asyncio.sleep(sleep_dur)
        return next_tick
    await asyncio.sleep(HOUSEKEEPING_OVERRUN_SLEEP_SECONDS)
    return time.monotonic()


async def _run_housekeeping_tick_safe(
    ctr: "AppContainer",
    state: SharedLoopState,
    *,
    last_source_version: int | None,
) -> int | None:
    try:
        next_version = await _update_active_options_from_shared_input(
            ctr,
            state,
            last_source_version=last_source_version,
        )
        _sync_anchor_symbols(ctr)
        return next_version
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception(f"[Housekeeping] Error: {exc}")
        raise


async def run_housekeeping_loop(ctr: 'AppContainer', state: SharedLoopState) -> None:
    """Background loop for Active Options calculation and missing symbol sync."""
    update_interval = settings.websocket_update_interval
    next_tick = time.monotonic()
    last_source_version: int | None = None

    while True:
        state.raise_if_fatal()
        last_source_version = await _run_housekeeping_tick_safe(
            ctr,
            state,
            last_source_version=last_source_version,
        )
        next_tick = await _sleep_until_next_tick(next_tick, update_interval)
