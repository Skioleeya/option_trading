"""Housekeeping loop for background non-critical computation syncs."""

import asyncio
import logging
import time
from typing import Any

from shared.config import settings
from app.loops.shared_state import SharedLoopState

# Only for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.container import AppContainer

logger = logging.getLogger(__name__)

ACTIVE_OPTIONS_LIMIT = 5
HOUSEKEEPING_OVERRUN_SLEEP_SECONDS = 0.01


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_active_options_row(raw: dict[str, Any]) -> dict[str, Any]:
    row = dict(raw)
    option_type = str(row.get("option_type", row.get("type", ""))).strip().upper()
    if option_type == "C":
        option_type = "CALL"
    elif option_type == "P":
        option_type = "PUT"
    elif option_type not in {"CALL", "PUT"}:
        is_call = row.get("is_call")
        option_type = "CALL" if bool(is_call) else "PUT"
    row["option_type"] = option_type

    # Prefer cumulative volume; fallback to current_volume when upstream omits volume.
    if _to_float(row.get("volume"), 0.0) <= 0.0:
        current_volume = _to_float(row.get("current_volume"), 0.0)
        if current_volume > 0.0:
            row["volume"] = int(current_volume)

    if _to_float(row.get("implied_volatility"), 0.0) <= 0.0:
        row["implied_volatility"] = _to_float(row.get("computed_iv"), 0.0)
    if _to_float(row.get("delta"), 0.0) == 0.0:
        row["delta"] = _to_float(row.get("computed_delta"), 0.0)
    if _to_float(row.get("gamma"), 0.0) == 0.0:
        row["gamma"] = _to_float(row.get("computed_gamma"), 0.0)
    if _to_float(row.get("vanna"), 0.0) == 0.0:
        row["vanna"] = _to_float(row.get("computed_vanna"), 0.0)
    return row


def _extract_chain_rows(snapshot: Any) -> list[dict[str, Any]]:
    chain = getattr(snapshot, "chain", None)
    if chain is None:
        return []
    if hasattr(chain, "to_pylist"):
        rows = chain.to_pylist()
    elif isinstance(chain, list):
        rows = chain
    else:
        try:
            rows = list(chain)
        except TypeError:
            return []
    return [_normalize_active_options_row(row) for row in rows if isinstance(row, dict)]


def _extract_agent_g_context(payload_dict: dict[str, Any] | None) -> tuple[float, str]:
    if not payload_dict:
        return 0.0, "NEUTRAL"
    g_data = payload_dict.get("agent_g", {}).get("data", {})
    return _to_float(g_data.get("spy_atm_iv"), 0.0), str(g_data.get("gex_regime", "NEUTRAL"))


def _resolve_l1_atm_iv(l1_snapshot: Any, current_atm_iv: float) -> float:
    if current_atm_iv > 0.0:
        return current_atm_iv
    aggregates = getattr(l1_snapshot, "aggregates", None)
    return _to_float(getattr(aggregates, "atm_iv", 0.0), 0.0)


async def _update_active_options_from_l1_snapshot(
    ctr: "AppContainer",
    state: SharedLoopState,
    *,
    atm_iv: float,
    gex_regime: str,
    last_l1_version: int | None,
) -> int | None:
    l1_snapshot = state.latest_l1_snapshot
    if l1_snapshot is None:
        return last_l1_version

    l1_version = int(getattr(l1_snapshot, "version", 0) or 0)
    if l1_version > 0 and last_l1_version == l1_version:
        logger.info(
            "[GPU-AUDIT] housekeeping_skip_duplicate_l1 snapshot_version=%s",
            l1_version,
        )
        return last_l1_version

    chain = _extract_chain_rows(l1_snapshot)
    spot = _to_float(getattr(l1_snapshot, "spot", 0.0), 0.0)
    resolved_atm_iv = _resolve_l1_atm_iv(l1_snapshot, atm_iv)
    await ctr.active_options_service.update_background(
        chain=chain,
        spot=spot,
        atm_iv=resolved_atm_iv,
        gex_regime=gex_regime,
        ttm_seconds=getattr(l1_snapshot, "ttm_seconds", None),
        redis=ctr.redis_service.client,
        limit=ACTIVE_OPTIONS_LIMIT,
    )
    return l1_version


async def _update_active_options_from_fetch_fallback(
    ctr: "AppContainer",
    *,
    atm_iv: float,
    gex_regime: str,
) -> None:
    snapshot = await ctr.option_chain_builder.fetch_chain(
        include_legacy_greeks=False,
        caller_tag="housekeeping_fallback",
    )
    await ctr.active_options_service.update_background(
        chain=snapshot.get("chain", []),
        spot=snapshot.get("spot", 0.0),
        atm_iv=atm_iv,
        gex_regime=gex_regime,
        ttm_seconds=snapshot.get("ttm_seconds"),
        redis=ctr.redis_service.client,
        limit=ACTIVE_OPTIONS_LIMIT,
    )


def _sync_anchor_symbols(ctr: "AppContainer") -> None:
    anchor_symbols = ctr.atm_decay_tracker.get_anchor_symbols()
    if anchor_symbols:
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
    atm_iv: float,
    gex_regime: str,
    last_l1_version: int | None,
) -> int | None:
    try:
        if state.latest_l1_snapshot is not None:
            next_version = await _update_active_options_from_l1_snapshot(
                ctr,
                state,
                atm_iv=atm_iv,
                gex_regime=gex_regime,
                last_l1_version=last_l1_version,
            )
            _sync_anchor_symbols(ctr)
            return next_version

        await _update_active_options_from_fetch_fallback(
            ctr,
            atm_iv=atm_iv,
            gex_regime=gex_regime,
        )
        _sync_anchor_symbols(ctr)
        return last_l1_version
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception(f"[Housekeeping] Error: {exc}")
        return last_l1_version


async def run_housekeeping_loop(ctr: 'AppContainer', state: SharedLoopState) -> None:
    """Background loop for Active Options calculation and missing symbol sync.

    Decouples the slow Redis OI aggregation and D/E/G flow engine
    from the microsecond-sensitive agent runner loop.
    """
    update_interval = settings.websocket_update_interval
    next_tick = time.monotonic()
    last_l1_version: int | None = None
    
    while True:
        atm_iv, gex_regime = _extract_agent_g_context(state.payload_dict)
        last_l1_version = await _run_housekeeping_tick_safe(
            ctr,
            state,
            atm_iv=atm_iv,
            gex_regime=gex_regime,
            last_l1_version=last_l1_version,
        )

        next_tick = await _sleep_until_next_tick(next_tick, update_interval)
