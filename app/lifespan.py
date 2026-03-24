"""Lifespan event handler for the FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.container import build_container
from app.ws.manager import WSManager
from app.loops.shared_state import SharedLoopState
from app.loops.compute_loop import run_compute_loop
from app.loops.broadcast_loop import run_broadcast_loop
from app.loops.housekeeping_loop import run_housekeeping_loop

logger = logging.getLogger(__name__)
_ATM_BOOTSTRAP_RETRIES = 20
_ATM_BOOTSTRAP_DELAY_SECONDS = 0.5

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Orchestrates application startup and shutdown via AppContainer."""
    print("[DEBUG] ========== LIFESPAN START ==========")
    
    # 1. Build container
    ctr = build_container()
    
    # 2. Sequential I/O Initialization
    await ctr.redis_service.start()
    if ctr.redis_service.client:
        await ctr.agent_g.set_redis_client(ctr.redis_service.client)
        ctr.atm_decay_tracker.redis = ctr.redis_service.client
        await ctr.l3_reactor.ui_tracker.set_redis_client(ctr.redis_service.client)
            
    await ctr.option_chain_builder.initialize()
    
    # 3. Fetch initial spot to initialize trackers
    try:
        _init_snapshot = await ctr.option_chain_builder.fetch_snapshot()
        _init_spot = _init_snapshot.get("spot", 0.0)
    except Exception as exc:
        logger.warning("[Lifespan] Initial fetch_chain failed, using spot=0. reason=%s", exc)
        _init_spot = 0.0
        _init_chain = []
    else:
        _init_chain = ctr.option_chain_builder.get_startup_chain_snapshot()
    await ctr.atm_decay_tracker.initialize(spot=_init_spot)
    if not ctr.atm_decay_tracker.anchor:
        try:
            await ctr.atm_decay_tracker.bootstrap_intraday_anchor(_init_chain, _init_spot)
        except Exception as exc:
            logger.warning("[Lifespan] Intraday ATM bootstrap lock failed. reason=%s", exc)
    if not ctr.atm_decay_tracker.anchor:
        for attempt in range(1, _ATM_BOOTSTRAP_RETRIES + 1):
            await asyncio.sleep(_ATM_BOOTSTRAP_DELAY_SECONDS)
            retry_spot, retry_chain = ctr.option_chain_builder.get_startup_bootstrap_context()
            try:
                await ctr.atm_decay_tracker.bootstrap_intraday_anchor(retry_chain, retry_spot)
            except Exception as exc:
                logger.warning(
                    "[Lifespan] Intraday ATM bootstrap retry failed (attempt=%s/%s). reason=%s",
                    attempt,
                    _ATM_BOOTSTRAP_RETRIES,
                    exc,
                )
            if ctr.atm_decay_tracker.anchor:
                logger.info(
                    "[Lifespan] Intraday ATM bootstrap succeeded during startup retry window (attempt=%s/%s).",
                    attempt,
                    _ATM_BOOTSTRAP_RETRIES,
                )
                break
    restored_anchor_symbols = ctr.atm_decay_tracker.get_anchor_symbols()
    if restored_anchor_symbols:
        ctr.option_chain_builder.set_mandatory_symbols(restored_anchor_symbols)
        retry_spot, retry_chain = ctr.option_chain_builder.get_startup_bootstrap_context()
        try:
            if retry_spot and retry_spot > 0:
                await ctr.option_chain_builder.refresh_subscriptions_once(retry_spot)
            repaired = await ctr.option_chain_builder.repair_symbols_once(
                restored_anchor_symbols,
                log_prefix="[Lifespan]",
            )
            retry_spot, retry_chain = ctr.option_chain_builder.get_startup_bootstrap_context()
            ctr.atm_decay_tracker.compute_current_decay(retry_chain)
            if repaired > 0:
                logger.info(
                    "[Lifespan] Startup ATM anchor repair seeded via one-shot price repair: symbols=%d repaired=%d",
                    len(restored_anchor_symbols),
                    repaired,
                )
            else:
                logger.info(
                    "[Lifespan] Startup ATM anchor recompute attempted without additional repair hits: symbols=%d",
                    len(restored_anchor_symbols),
                )
        except Exception as exc:
            logger.warning("[Lifespan] Startup ATM one-shot price repair failed. reason=%s", exc)
    ctr.quote_hub_ready.set()
    
    # Hook L1 microstructure into WS depth/trade callbacks
    ctr.option_chain_builder.on_depth = ctr.l1_reactor.update_microstructure_depth
    ctr.option_chain_builder.on_trade = ctr.l1_reactor.update_microstructure_trades


    # 4. Build Shared Loop Objects
    ws_manager = WSManager()
    shared_state = SharedLoopState()
    
    # 5. Attach to app state for Routes to access
    app.state.container = ctr
    app.state.ws_manager = ws_manager
    app.state.state = shared_state
    app.state.market_data_service = ctr.option_chain_builder # required for backward compat

    # 6. Start Background Loops
    tasks = [
        asyncio.create_task(run_compute_loop(ctr, shared_state)),
        asyncio.create_task(run_broadcast_loop(ctr, ws_manager, shared_state)),
        asyncio.create_task(run_housekeeping_loop(ctr, shared_state)),
    ]
    
    logger.info("[Lifespan] All services and background loops initialized")

    yield  # Application runs here

    # 7. Shutdown sequence
    print("[DEBUG] ========== LIFESPAN END ==========")
    for task in tasks:
        task.cancel()
        
    await asyncio.gather(*tasks, return_exceptions=True)

    ctr.l2_reactor.flush_audit()

    await ctr.option_chain_builder.shutdown()
    await ctr.redis_service.stop()
