"""Lifespan event handler for the FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.container import build_container, USE_L2
from app.ws.manager import WSManager
from app.loops.shared_state import SharedLoopState
from app.loops.compute_loop import run_compute_loop
from app.loops.broadcast_loop import run_broadcast_loop
from app.loops.housekeeping_loop import run_housekeeping_loop

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Orchestrates application startup and shutdown via AppContainer."""
    print("[DEBUG] ========== LIFESPAN START ==========")
    
    # 1. Build Container (No I/O logic, just dependency injection)
    ctr = build_container()
    
    # 2. Sequential I/O Initialization
    await ctr.redis_service.start()
    if ctr.redis_service.client:
        await ctr.agent_g.set_redis_client(ctr.redis_service.client)
        if ctr.l3_reactor:
            await ctr.l3_reactor.ui_tracker.set_redis_client(ctr.redis_service.client)
            
    await ctr.option_chain_builder.initialize()
    
    # 3. Patch late-bound dependencies (Explicit ordered resolution)
    ctr.atm_decay_tracker.ctx = ctr.option_chain_builder._gateway.quote_ctx
    
    # 4. Fetch initial spot to initialize trackers
    try:
        _init_snapshot = await ctr.option_chain_builder.fetch_chain()
        _init_spot = _init_snapshot.get("spot", 0.0)
    except Exception:
        _init_spot = 0.0
    await ctr.atm_decay_tracker.initialize(spot=_init_spot)
    ctr.quote_hub_ready.set()
    
    # Hook L1 microstructure into WS depth/trade callbacks
    if USE_L2 and ctr.l1_reactor:
        ctr.option_chain_builder.on_depth = ctr.l1_reactor.update_microstructure_depth
        ctr.option_chain_builder.on_trade = ctr.l1_reactor.update_microstructure_trades


    # 5. Build Shared Loop Objects
    ws_manager = WSManager()
    shared_state = SharedLoopState()
    
    # 6. Attach to app state for Routes to access
    app.state.container = ctr
    app.state.ws_manager = ws_manager
    app.state.state = shared_state
    app.state.market_data_service = ctr.option_chain_builder # required for backward compat

    # 7. Start Background Loops
    tasks = [
        asyncio.create_task(run_compute_loop(ctr, shared_state)),
        asyncio.create_task(run_broadcast_loop(ctr, ws_manager, shared_state)),
        asyncio.create_task(run_housekeeping_loop(ctr, shared_state)),
    ]
    
    logger.info("[Lifespan] All services and background loops initialized")

    yield  # Application runs here

    # 8. Shutdown sequence
    print("[DEBUG] ========== LIFESPAN END ==========")
    for task in tasks:
        task.cancel()
        
    await asyncio.gather(*tasks, return_exceptions=True)

    if USE_L2 and ctr.l2_reactor and hasattr(ctr.l2_reactor, "_audit_writer"):
        ctr.l2_reactor._audit_writer.flush()

    await ctr.option_chain_builder.shutdown()
    await ctr.redis_service.stop()
