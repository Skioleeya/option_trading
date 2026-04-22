"""WebSocket broadcast loop."""

import asyncio
import logging
import time

from shared.config import settings
from app.ws.manager import WSManager
from app.loops.shared_state import SharedLoopState

# Only for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.container import AppContainer

logger = logging.getLogger(__name__)
_LOOP_ERROR_BACKOFF_SEC = 0.01


def _timeout_until(next_heartbeat: float) -> float:
    return max(0.0, next_heartbeat - time.monotonic())


def _heartbeat_due(next_heartbeat: float) -> bool:
    return time.monotonic() >= next_heartbeat


def _select_trigger(*, state: SharedLoopState, ctr: 'AppContainer', has_new_payload: bool, heartbeat_due: bool) -> str | None:
    if state.frozen is None or not ctr.l3_reactor:
        return None
    if has_new_payload:
        return "payload"
    if heartbeat_due:
        return "heartbeat"
    return None


def _log_idle_state(state: SharedLoopState) -> None:
    if state.payload_dict:
        logger.debug("[L3 Broadcast] Stalled: frozen is None")
        return
    logger.debug("[L3 Broadcast] Skipped: payload_dict is None. Compute loop may be stalled.")


async def _broadcast_once(
    *,
    ctr: 'AppContainer',
    ws_manager: WSManager,
    state: SharedLoopState,
    trigger: str,
) -> None:
    report = await ctr.l3_reactor.governor.broadcast(
        payload=state.frozen,
        clients=ws_manager.clients,
        payload_time=state.last_payload_time,
        compute_interval=state.current_compute_interval,
    )
    if report.client_count <= 0:
        return
    logger.debug(
        f"[L3 Governor] broadcast cycle: clients={report.client_count}, "
        f"msg={report.message_type}, trigger={trigger}, "
        f"lat={report.broadcast_latency_ms:.1f}ms, "
        f"bytes={report.serialized_bytes}"
    )


async def run_broadcast_loop(
    ctr: 'AppContainer', ws_manager: WSManager, state: SharedLoopState
) -> None:
    """Broadcast loop: send new payloads immediately and stale heartbeats on cadence."""
    broadcast_interval = settings.ws_broadcast_interval
    next_heartbeat = time.monotonic()
    last_broadcast_epoch = 0

    while True:
        try:
            state.raise_if_fatal()
            timeout_sec = _timeout_until(next_heartbeat)
            has_new_payload = await state.wait_for_payload_after(
                last_broadcast_epoch,
                timeout_sec=timeout_sec,
            )
            heartbeat_due = _heartbeat_due(next_heartbeat)
            current_epoch = state.payload_epoch
            trigger = _select_trigger(
                state=state,
                ctr=ctr,
                has_new_payload=has_new_payload,
                heartbeat_due=heartbeat_due,
            )

            if trigger is not None:
                await _broadcast_once(
                    ctr=ctr,
                    ws_manager=ws_manager,
                    state=state,
                    trigger=trigger,
                )
                last_broadcast_epoch = current_epoch
                next_heartbeat = time.monotonic() + broadcast_interval
            else:
                _log_idle_state(state)
                if heartbeat_due and state.frozen is None:
                    next_heartbeat = time.monotonic() + broadcast_interval
        except asyncio.CancelledError:
            raise
        except RuntimeError as exc:
            logger.critical("[L3 Broadcast Loop] Fatal runtime stop: %s", exc)
            raise
        except Exception as e:
            logger.error(f"[L3 Broadcast Loop] Unexpected error: {e}", exc_info=True)
            await asyncio.sleep(_LOOP_ERROR_BACKOFF_SEC)
