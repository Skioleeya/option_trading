"""Housekeeping loop for background non-critical computation syncs."""

import asyncio
import logging
import time

from shared.config import settings
from app.loops.shared_state import SharedLoopState

# Only for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.container import AppContainer

logger = logging.getLogger(__name__)


async def run_housekeeping_loop(ctr: 'AppContainer', state: SharedLoopState) -> None:
    """Background loop for Active Options calculation and missing symbol sync.

    Decouples the slow Redis OI aggregation and D/E/G flow engine
    from the microsecond-sensitive agent runner loop.
    """
    update_interval = settings.websocket_update_interval
    next_tick = time.monotonic()
    
    while True:
        try:
            # 1. Fetch cheap in-memory snapshot
            snapshot = await ctr.option_chain_builder.fetch_chain()
            chain = snapshot.get("chain", [])
            spot = snapshot.get("spot", 0.0)
            
            # 2. Extract context from latest computed payload (AgentB1)
            atm_iv = 0.0
            gex_regime = "NEUTRAL"
            if state.payload_dict:
                g_data = state.payload_dict.get("agent_g", {}).get("data", {})
                atm_iv = g_data.get("spy_atm_iv") or 0.0
                gex_regime = g_data.get("gex_regime", "NEUTRAL")
            
            # 3. Refresh ActiveOptions via shared neutral service
            await ctr.active_options_service.update_background(
                chain=chain,
                spot=spot,
                atm_iv=atm_iv,
                gex_regime=gex_regime,
                ttm_seconds=snapshot.get("ttm_seconds"),
                redis=ctr.redis_service.client,
                limit=5
            )

            # 4. Sync mandatory symbols (ATM anchors) back to data feed
            # This ensures the symbols used for the chart are always depth-subscribed.
            # Moved out of the compute loop into housekeeping.
            anchor_symbols = ctr.atm_decay_tracker.get_anchor_symbols()
            if anchor_symbols:
                ctr.option_chain_builder.set_mandatory_symbols(anchor_symbols)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception(f"[Housekeeping] Error: {e}")
            
        next_tick += update_interval
        sleep_dur = next_tick - time.monotonic()
        if sleep_dur > 0:
            await asyncio.sleep(sleep_dur)
        else:
            next_tick = time.monotonic()
            await asyncio.sleep(0.01)
