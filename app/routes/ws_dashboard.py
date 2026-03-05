"""WebSocket dashboard endpoint."""

import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    # Obtain the container and ws_manager instances attached to the app state
    container = websocket.app.state.container
    ws_manager = websocket.app.state.ws_manager
    state = websocket.app.state.state

    await websocket.accept()
    ws_manager.register(websocket)

    try:
        # Send initial payload if available
        if container.l3_reactor and state.frozen:
            await container.l3_reactor.governor.broadcast_init(state.frozen, websocket)
        elif state.payload_dict:
            init_msg = {**state.payload_dict, "type": "dashboard_init"}
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
        ws_manager.unregister(websocket)
