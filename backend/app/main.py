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


logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
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
        self.quote_hub_ready = asyncio.Event()

        # Agent runner state
        self._runner_task: asyncio.Task | None = None
        self._running = False
        self._last_payload: dict[str, Any] | None = None
        self._last_payload_time: float = 0.0
        self._total_computations = 0
        self._failed_computations = 0

        # WebSocket clients
        self._ws_clients: set[WebSocket] = set()

    async def initialize_all(self) -> None:
        """Initialize all services."""
        print("[DEBUG] ========== LIFESPAN START ==========")

        # Initialize data feed
        await self.option_chain_builder.initialize()
        self.quote_hub_ready.set()

        # Start agent runner loop
        self._running = True
        self._runner_task = asyncio.create_task(self._agent_runner_loop())

        logger.info("[AppContainer] All services initialized")

    async def shutdown_all(self) -> None:
        """Shutdown all services."""
        self._running = False
        if self._runner_task:
            self._runner_task.cancel()
            try:
                await self._runner_task
            except asyncio.CancelledError:
                pass

        await self.option_chain_builder.shutdown()
        print("[DEBUG] ========== LIFESPAN END ==========")

    async def _agent_runner_loop(self) -> None:
        """Main loop: fetch data → run agents → broadcast."""
        while self._running:
            try:
                start = time.monotonic()

                # 1. Fetch snapshot
                snapshot = await self.option_chain_builder.fetch_chain()

                snapshot_time = time.monotonic() - start

                # 2. Run agent pipeline
                agent_start = time.monotonic()
                result = self.agent_g.run(snapshot)
                agent_time = time.monotonic() - agent_start

                logger.warning(
                    f"[PERF] build_payload breakdown: "
                    f"snapshot={snapshot_time*1000:.1f}ms, "
                    f"agent={agent_time*1000:.1f}ms"
                )

                # 3. Build payload
                payload = self._build_payload(snapshot, result)
                self._last_payload = payload
                self._last_payload_time = time.monotonic()
                self._total_computations += 1

                # 4. Broadcast to WebSocket clients
                await self._broadcast(payload)

            except Exception as e:
                self._failed_computations += 1
                logger.error(f"[AgentRunner] Error in loop: {e}")

            # Sleep for update interval
            await asyncio.sleep(settings.websocket_update_interval)

    def _build_payload(
        self,
        snapshot: dict[str, Any],
        agent_result: Any,
    ) -> dict[str, Any]:
        """Build WebSocket broadcast payload."""
        now = datetime.now(ZoneInfo("US/Eastern"))

        return {
            "type": "dashboard_update",
            "timestamp": now.isoformat(),
            "spot": snapshot.get("spot"),
            "agent_g": agent_result.model_dump() if agent_result else None,
        }

    async def _broadcast(self, payload: dict[str, Any]) -> None:
        """Broadcast payload to all connected WebSocket clients."""
        if not self._ws_clients:
            return

        message = json.dumps(payload, default=str)
        disconnected = set()

        for ws in self._ws_clients:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.add(ws)

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


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
