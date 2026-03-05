"""Health and diagnostics endpoints."""

from datetime import datetime
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@router.get("/debug/persistence_status")
async def persistence_status(request: Request):
    """Aggregated diagnostic view."""
    container = request.app.state.container
    state = request.app.state.state

    service_diag = container.option_chain_builder.get_diagnostics()
    quote_hub_active = container.quote_hub_ready.is_set()
    runner_stats = state.get_diagnostics()

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
        "l3_layer": container.l3_reactor.get_diagnostics() if container.l3_reactor else {},
        "redis": container.redis_service.get_diagnostics(),
        "stores": service_diag,
    }
