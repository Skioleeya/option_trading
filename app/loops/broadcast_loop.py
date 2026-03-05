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


async def run_broadcast_loop(
    ctr: 'AppContainer', ws_manager: WSManager, state: SharedLoopState
) -> None:
    """Broadcast loop: push the latest cached payload to WS clients at 1Hz.

    Runs independently of the compute loop so the frontend always gets
    smooth 1-second updates even when backend computation is slower.
    """
    broadcast_interval = settings.ws_broadcast_interval
    next_tick = time.monotonic()

    while True:
        try:
            if state.frozen is not None and ctr.l3_reactor:
                # L3 Refactor: Delegate broadcast timing, encoding and fanout to Governor
                report = await ctr.l3_reactor.governor.broadcast(
                    payload=state.frozen,
                    clients=ws_manager.clients,
                    payload_time=state.last_payload_time,
                    compute_interval=state.current_compute_interval
                )
                
                if report.client_count > 0:
                    logger.debug(
                        f"[L3 Governor] broadcast cycle: clients={report.client_count}, "
                        f"msg={report.message_type}, lat={report.broadcast_latency_ms:.1f}ms, "
                        f"bytes={report.serialized_bytes}"
                    )
            elif state.payload_dict:
                logger.debug("[L3 Broadcast] Stalled: frozen is None")
            else:
                logger.debug(f"[L3 Broadcast] Skipped: payload_dict is None. Compute loop may be stalled.")
                
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"[L3 Broadcast Loop] Unexpected error: {e}", exc_info=True)

        next_tick += broadcast_interval
        sleep_dur = next_tick - time.monotonic()
        if sleep_dur > 0:
            await asyncio.sleep(sleep_dur)
        else:
            next_tick = time.monotonic()
            await asyncio.sleep(0.01)
