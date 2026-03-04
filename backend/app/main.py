"""SPY 0DTE Dashboard — FastAPI Application.

Main entry point for the backend service.
Orchestrates all services via AppContainer with async lifespan management.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.agents.agent_g import AgentG
from app.config import settings
from app.services.feeds.option_chain_builder import OptionChainBuilder
from app.services.system.redis_service import RedisService
from app.services.system.historical_store import HistoricalStore
from app.services.system.snapshot_builder import SnapshotBuilder
from app.services.analysis.atm_decay_tracker import AtmDecayTracker


logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format='%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# AppContainer — Service Orchestration
# ============================================================================
class AppContainer:
    """Central service container for the application.

    Manages lifecycle of all services:
    - OptionChainBuilder (data feed)
    - AgentG (decision framework)
    - Agent runner loop
    - WebSocket broadcaster
    """

    def __init__(self) -> None:
        self.option_chain_builder = OptionChainBuilder()
        self.agent_g = AgentG()
        self.redis_service = RedisService()
        self.historical_store = HistoricalStore(self.redis_service)
        self.atm_decay_tracker = AtmDecayTracker(self.redis_service.client, self.option_chain_builder._quote_ctx)
        self.quote_hub_ready = asyncio.Event()

        # Agent runner state
        self._runner_task: asyncio.Task | None = None
        self._broadcast_task: asyncio.Task | None = None
        self._active_options_task: asyncio.Task | None = None
        self._running = False
        self._last_payload: dict[str, Any] | None = None
        self._last_payload_time: float = 0.0
        self._last_broadcast_payload: dict[str, Any] | None = None
        self._last_full_snapshot_time: float = 0.0
        self._total_computations = 0
        self._failed_computations = 0
        # PP-L3D: Track current compute interval so broadcast_loop can set
        # a dynamic is_stale threshold instead of a fixed constant.
        self._current_compute_interval: float = 3.0

        # WebSocket clients
        self._ws_clients: set[WebSocket] = set()

    async def initialize_all(self) -> None:
        """Initialize all services."""
        print("[DEBUG] ========== LIFESPAN START ==========")

        # 1. Start Redis
        await self.redis_service.start()
        if self.redis_service.client:
            await self.agent_g.set_redis_client(self.redis_service.client)
            self.atm_decay_tracker.redis = self.redis_service.client

        # 2. Initialize data feed and tracker
        await self.option_chain_builder.initialize()
        self.atm_decay_tracker.ctx = self.option_chain_builder._quote_ctx

        # Fetch current spot for anchor staleness validation
        try:
            _init_snapshot = await self.option_chain_builder.fetch_chain()
            _init_spot = _init_snapshot.get("spot", 0.0)
        except Exception:
            _init_spot = 0.0
        await self.atm_decay_tracker.initialize(spot=_init_spot)
        self.quote_hub_ready.set()

        # Start agent runner loop (compute every 3s) and broadcast loop (1Hz)
        self._running = True
        self._runner_task = asyncio.create_task(self._agent_runner_loop())
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        self._active_options_task = asyncio.create_task(self._active_options_loop())

        logger.info("[AppContainer] All services initialized")

    async def shutdown_all(self) -> None:
        """Shutdown all services."""
        self._running = False
        for task in (self._runner_task, self._broadcast_task, self._active_options_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        await self.option_chain_builder.shutdown()
        await self.redis_service.stop()
        print("[DEBUG] ========== LIFESPAN END ==========")

    async def _active_options_loop(self) -> None:
        """Background loop for Active Options calculation.

        Decouples the slow Redis OI aggregation and D/E/G flow engine
        from the microsecond-sensitive AgentG compute loop.
        """
        update_interval = settings.websocket_update_interval
        next_tick = time.monotonic()
        
        while self._running:
            try:
                # 1. Fetch cheap in-memory snapshot
                snapshot = await self.option_chain_builder.fetch_chain()
                chain = snapshot.get("chain", [])
                spot = snapshot.get("spot", 0.0)
                
                # 2. Extract context from latest computed payload (AgentB1)
                atm_iv = 0.0
                gex_regime = "NEUTRAL"
                if self._last_payload:
                    g_data = self._last_payload.get("agent_g", {}).get("data", {})
                    atm_iv = g_data.get("spy_atm_iv") or 0.0
                    gex_regime = g_data.get("gex_regime", "NEUTRAL")
                
                # 3. Call the newly async decoupled presenter
                redis_client = getattr(self.agent_g, "_redis", None)
                await self.agent_g._active_options_presenter.update_background(
                    chain=chain,
                    spot=spot,
                    atm_iv=atm_iv,
                    gex_regime=gex_regime,
                    redis=redis_client,
                    limit=5
                )

            except Exception as e:
                logger.exception(f"[ActiveOptionsLoop] Error: {e}")
                
            next_tick += update_interval
            sleep_dur = next_tick - time.monotonic()
            if sleep_dur > 0:
                await asyncio.sleep(sleep_dur)
            else:
                next_tick = time.monotonic()
                await asyncio.sleep(0.01)

    async def _agent_runner_loop(self) -> None:
        """Compute loop: fetch data → run agents → build payload → save Redis.

        Runs at a constant 1Hz cadence.
        Does NOT broadcast — that is handled by _broadcast_loop.

        RACE FIX (Race 1): payload is stored as copy.deepcopy so the broadcast
        loop always holds a fully-isolated snapshot, immune to in-place mutations
        by subsequent SnapshotBuilder.build() calls.
        """
        from app.services.feeds.rate_limiter import longport_limiter
        next_tick = time.monotonic()

        while self._running:
            # 0. Dynamically adjust interval based on available API tokens
            compute_interval = settings.websocket_update_interval
            # PP-L3D: Expose current compute_interval so broadcast_loop can
            # calculate a dynamic is_stale threshold.
            self._current_compute_interval = compute_interval
            
            try:
                start = time.monotonic()

                # 1. Fetch snapshot
                snapshot = await self.option_chain_builder.fetch_chain()
                snapshot_time = time.monotonic() - start

                chain_size = len(snapshot.get("chain", []))
                iv_cache_size = len(self.option_chain_builder._iv_sync.iv_cache)

                # 2. Run agent pipeline
                agent_start = time.monotonic()
                result = await self.agent_g.run(snapshot)

                # 2.5 Calculate ATM Decay via Tracker
                atm_decay_payload = await self.atm_decay_tracker.update(
                    snapshot.get("chain", []),
                    snapshot.get("spot", 0.0)
                )
                
                # 2.6 Sync mandatory symbols (ATM anchors) back to data feed
                # This ensures the symbols used for the chart are always depth-subscribed.
                anchor_symbols = self.atm_decay_tracker.get_anchor_symbols()
                if anchor_symbols:
                    self.option_chain_builder.set_mandatory_symbols(anchor_symbols)

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

                # 3. Build and cache payload — pure dictionary assembly, no deepcopy
                # PP-1 FIX: Only update _last_payload if agent result is valid to prevent UI flickering.
                if result:
                    new_payload = SnapshotBuilder.build(snapshot, result, atm_decay_payload)
                    # RACE FIX: We removed deepcopy here because SnapshotBuilder now
                    # guarantees a pure, non-mutating assembly of fresh dictionaries.
                    self._last_payload = new_payload
                    self._last_payload_time = time.monotonic()
                    self._total_computations += 1
                else:
                    logger.warning("[AgentRunner] Agent result is None, skipping payload update (Outcome Cache active)")

                # 4. Save to Redis (use original payload if available)
                if self._last_payload:
                    await self.historical_store.save_snapshot(self._last_payload)

            except Exception as e:
                self._failed_computations += 1
                logger.exception(f"[AgentRunner] Error in compute loop: {e}")

            # Drift-corrected sleep with dynamic cadence
            next_tick += compute_interval
            sleep_dur = next_tick - time.monotonic()
            if sleep_dur > 0:
                await asyncio.sleep(sleep_dur)
            else:
                next_tick = time.monotonic()
                await asyncio.sleep(0.01)

    async def _broadcast_loop(self) -> None:
        """Broadcast loop: push the latest cached payload to WS clients at 1Hz.

        Runs independently of the compute loop so the frontend always gets
        smooth 1-second updates even when backend computation is slower.

        RACE FIX (Race 1): _last_payload is already a deepcopy (set by runner),
        so a top-level dict() copy here is safe — only 'timestamp' is mutated
        at the top level, which does not affect the runner's next deepcopy.
        """
        import jsonpatch
        broadcast_interval = settings.ws_broadcast_interval  # configurable via WS_BROADCAST_INTERVAL in .env
        next_tick = time.monotonic()

        while self._running:
            try:
                if self._last_payload is not None:
                    # PP-L3E FIX: Use shallow copy instead of deepcopy for performance.
                    # Since we only mutate top-level keys (heartbeat_timestamp, is_stale, timestamp),
                    # the nested dictionaries remain fully isolated. Deepcopy incurred a 9-30ms penalty.
                    fresh_payload = dict(self._last_payload)
                    fresh_payload["heartbeat_timestamp"] = datetime.now(ZoneInfo("US/Eastern")).isoformat()
                    
                    # PP-L3D FIX: Dynamic is_stale threshold scaled to current
                    # compute_interval, so the stale flag only fires when the
                    # payload is older than 2.5× the *actual* compute cadence,
                    # not a hard-coded constant that may not match.
                    payload_age = time.monotonic() - self._last_payload_time
                    stale_threshold = self._current_compute_interval * 2.5
                    fresh_payload["is_stale"] = payload_age > stale_threshold

                    # PP-L3F FIX: Expose a canonical `timestamp` alias at the top
                    # level so the frontend Header component reads a consistent
                    # key name regardless of internal rename history.
                    fresh_payload["timestamp"] = fresh_payload.get("data_timestamp", "")

                    # Delta Push optimization: only send differences if we already sent a full payload recently
                    now_time = time.monotonic()
                    if (
                        not self._last_broadcast_payload or 
                        (now_time - self._last_full_snapshot_time > 30.0)
                    ):
                        # Send full snapshot
                        msg = {**fresh_payload, "type": "dashboard_update"}
                        self._last_broadcast_payload = fresh_payload
                        self._last_full_snapshot_time = now_time
                    else:
                        # Calculate JSON patch
                        try:
                            patch_obj = jsonpatch.make_patch(self._last_broadcast_payload, fresh_payload)
                            msg = {
                                "type": "dashboard_delta",
                                "patch": patch_obj.patch,
                                "timestamp": fresh_payload["timestamp"],
                                "heartbeat_timestamp": fresh_payload["heartbeat_timestamp"]
                            }
                            self._last_broadcast_payload = fresh_payload
                        except Exception as patch_err:
                            logger.warning(f"[L3 Broadcast] Delta patch generation failed: {patch_err}. Falling back to full snapshot.")
                            msg = {**fresh_payload, "type": "dashboard_update"}
                            self._last_broadcast_payload = fresh_payload
                            self._last_full_snapshot_time = now_time

                    client_count = len(self._ws_clients)
                    logger.debug(
                        f"[RACE_PROBE] broadcast: payload_age={payload_age:.2f}s, "
                        f"ws_clients={client_count}, type={msg['type']}"
                    )

                    await self._broadcast(msg)
                else:
                    logger.debug(f"[L3 Broadcast] Skipped: _last_payload is None. Compute loop may be stalled. (Stalled for {(time.monotonic() - next_tick):.1f}s)")
            except Exception as e:
                logger.error(f"[L3 Broadcast Loop] Unexpected error: {e}", exc_info=True)

            next_tick += broadcast_interval
            sleep_dur = next_tick - time.monotonic()
            if sleep_dur > 0:
                await asyncio.sleep(sleep_dur)
            else:
                next_tick = time.monotonic()
                await asyncio.sleep(0.01)

    async def _broadcast(self, payload: dict[str, Any]) -> None:
        """Broadcast payload to all connected WebSocket clients."""
        if not self._ws_clients:
            return

        message = json.dumps(payload, default=str)
        disconnected = set()

        for ws in self._ws_clients:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.debug(f"[L3 Broadcast] Disconnecting WS client due to error: {e}")
                disconnected.add(ws)

        if disconnected:
            self._ws_clients -= disconnected

    def register_ws(self, ws: WebSocket) -> None:
        """Register a WebSocket client."""
        self._ws_clients.add(ws)

    def unregister_ws(self, ws: WebSocket) -> None:
        """Unregister a WebSocket client."""
        self._ws_clients.discard(ws)

    def get_runner_diagnostics(self) -> dict[str, Any]:
        """Return agent runner diagnostics."""
        age = time.monotonic() - self._last_payload_time if self._last_payload_time else None
        total = self._total_computations + self._failed_computations
        return {
            "total_computations": self._total_computations,
            "failed_computations": self._failed_computations,
            "success_rate": (self._total_computations / total * 100) if total > 0 else 100.0,
            "last_update_age_seconds": age,
            "is_running": self._running,
        }


# ============================================================================
# FastAPI Application
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Orchestrates application startup and shutdown via AppContainer."""
    container = AppContainer()
    await container.initialize_all()

    app.state.container = container
    app.state.market_data_service = container.option_chain_builder

    yield

    await container.shutdown_all()


app = FastAPI(
    title="SPY 0DTE Dashboard",
    description="Real-time SPY options GEX analysis dashboard",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Routes
# ============================================================================
@app.get("/debug/persistence_status")
async def persistence_status():
    """Aggregated diagnostic view."""
    container: AppContainer = app.state.container

    service_diag = container.option_chain_builder.get_diagnostics()
    quote_hub_active = container.quote_hub_ready.is_set()
    runner_stats = container.get_runner_diagnostics()

    return {
        "timestamp": datetime.now().isoformat(),
        "quote_hub": {
            "active": quote_hub_active,
            "ready_event_set": quote_hub_active,
        },
        "agent_runner": {
            "running": runner_stats.get("is_running"),
            "stats": runner_stats,
            "last_update_age_seconds": runner_stats.get("last_update_age_seconds"),
        },
        "redis": container.redis_service.get_diagnostics(),
        "stores": service_diag,
    }


@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    container: AppContainer = app.state.container

    await websocket.accept()
    container.register_ws(websocket)

    try:
        # Send initial payload if available
        if container._last_payload:
            init_msg = {**container._last_payload, "type": "dashboard_init"}
            await websocket.send_text(json.dumps(init_msg, default=str))

        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Handle ping/pong or commands
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send keepalive
                try:
                    await websocket.send_text(json.dumps({"type": "keepalive"}))
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"[WS] Client error: {e}")
    finally:
        container.unregister_ws(websocket)


@app.get("/history")
async def get_history(count: int = 50):
    """Retrieve historical snapshots from Redis."""
    container: AppContainer = app.state.container
    history = await container.historical_store.get_latest(count)
    return {"history": history, "count": len(history)}


@app.get("/api/atm-decay/history")
async def get_atm_decay_history():
    """Retrieve the full historical ATM decay series for the current trade date."""
    container: AppContainer = app.state.container
    date_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
    history = await container.atm_decay_tracker.get_history(date_str)
    
    return {
        "date": date_str,
        "history": history,
        "count": len(history)
    }

@app.post("/api/atm-decay/flush-history")
async def flush_atm_decay_history():
    """Flush and rebuild the ATM decay history from the Intraday API."""
    container: AppContainer = app.state.container
    date_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
    await container.atm_decay_tracker.flush_and_rebuild()
    history = await container.atm_decay_tracker.get_history(date_str)
    
    return {
        "date": date_str,
        "message": "History flushed and rebuilt",
        "history": history,
        "count": len(history)
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
