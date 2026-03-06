"""Main data fetching and computation loop."""

import asyncio
import logging
import math
import time
from typing import Any

from shared.config import settings
from app.loops.shared_state import SharedLoopState

# Only for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.container import AppContainer

logger = logging.getLogger(__name__)


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


def _build_l1_extra_metadata(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Build the L0->L1 metadata pass-through contract."""
    return {
        "rust_active": snapshot.get("rust_active", False),
        "shm_stats": snapshot.get("shm_stats"),
        "volume_map": _normalize_volume_map(snapshot.get("volume_map")),
    }


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


async def run_compute_loop(ctr: 'AppContainer', state: SharedLoopState) -> None:
    """Compute loop: fetch data → run agents → build payload → save state.

    Runs at a constant cadence defined by websocket_update_interval.
    """
    next_tick = time.monotonic()

    while True:
        try:
            start = time.monotonic()
            compute_interval = settings.websocket_update_interval
            state.current_compute_interval = compute_interval

            # 1. Fetch snapshot
            snapshot = await ctr.option_chain_builder.fetch_chain()
            snapshot_time = time.monotonic() - start
            
            logger.info(f"[Debug] L0 Fetch: rust_active={snapshot.get('rust_active')} shm_stats={snapshot.get('shm_stats') is not None}")

            chain_size = len(snapshot.get("chain", []))
            iv_sync_obj = getattr(ctr.option_chain_builder, "_iv_sync", None)
            iv_cache_size = len(iv_sync_obj.iv_cache) if iv_sync_obj else 0

            # 2. Run agent pipeline (L1+L2 or legacy AgentG)
            agent_start = time.monotonic()
            decision = None
            l1_snap = None
            if ctr.l1_reactor:
                iv_cache = getattr(iv_sync_obj, "iv_cache", {}) if iv_sync_obj else {}
                spot_sync = getattr(iv_sync_obj, "spot_at_sync", {}) if iv_sync_obj else {}

                l1_snap = await ctr.l1_reactor.compute(
                    chain_snapshot=snapshot.get("chain", []),
                    spot=snapshot.get("spot", 0.0),
                    l0_version=_extract_snapshot_version(snapshot),
                    iv_cache=iv_cache,
                    spot_at_sync=spot_sync,
                    extra_metadata=_build_l1_extra_metadata(snapshot),
                )

            if l1_snap and ctr.l2_reactor:
                decision = await ctr.l2_reactor.decide(l1_snap)
                result = decision.to_legacy_agent_result()
                
                logger.debug(
                    f"[L2] direction={decision.direction}, "
                    f"conf={decision.confidence:.2f}, "
                    f"lat={decision.latency_ms:.1f}ms"
                )
            else:
                # If no L1, pass raw snapshot. If L1 exists, pass legacy dict shim.
                target_snapshot = l1_snap.to_legacy_dict() if l1_snap else snapshot
                result = await ctr.agent_g.run(target_snapshot)
                decision = result

            # 2.5 Calculate ATM Decay via Tracker
            atm_decay_payload = await ctr.atm_decay_tracker.update(
                snapshot.get("chain", []),
                snapshot.get("spot", 0.0)
            )

            agent_time = time.monotonic() - agent_start

            logger.info(
                f"[PERF] build_payload breakdown: "
                f"snapshot={snapshot_time*1000:.1f}ms, "
                f"agent={agent_time*1000:.1f}ms, "
                f"interval={compute_interval}s"
            )
            logger.debug(
                f"[RACE_PROBE] runner tick: chain_size={chain_size}, "
                f"iv_cache_size={iv_cache_size}, "
                f"spot={snapshot.get('spot')}"
            )

            # 3. Build and cache payload via L3 Reactor
            if result and ctr.l3_reactor:
                active_opts = ctr.agent_g._active_options_presenter.get_latest()
                
                target_snap = l1_snap if l1_snap is not None else snapshot

                frozen = await ctr.l3_reactor.tick(
                    decision=decision,
                    snapshot=target_snap,
                    atm_decay=atm_decay_payload,
                    active_options=active_opts
                )
                
                # Atomically update global state
                state.update(frozen, snapshot.get("spot"))
            else:
                if not result:
                    logger.warning("[AgentRunner] Agent result is None, skipping payload update")

            # 4. Periodically flush L2 audit logs
            if ctr.l2_reactor and hasattr(ctr.l2_reactor, "_audit_writer"):
                if state.total_computations > 0 and state.total_computations % 60 == 0:
                    ctr.l2_reactor._audit_writer.flush()

        except asyncio.CancelledError:
            raise
        except Exception as e:
            state.record_failure()
            logger.exception(f"[AgentRunner] Error in compute loop: {e}")

        # Drift-corrected sleep with dynamic cadence
        next_tick += compute_interval
        sleep_dur = next_tick - time.monotonic()
        if sleep_dur > 0:
            await asyncio.sleep(sleep_dur)
        else:
            next_tick = time.monotonic()
            await asyncio.sleep(0.01)
