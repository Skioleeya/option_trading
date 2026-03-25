"""Health and diagnostics endpoints."""

from datetime import datetime
from typing import Any
from fastapi import APIRouter, Request

router = APIRouter()


def _build_l1_runtime_diag(snapshot: Any) -> dict[str, Any]:
    if snapshot is None:
        return {}
    quality = getattr(snapshot, "quality", None)
    metadata = getattr(snapshot, "extra_metadata", {}) or {}
    return {
        "version": int(getattr(snapshot, "version", 0) or 0),
        "computed_at": (
            snapshot.computed_at.isoformat()
            if hasattr(getattr(snapshot, "computed_at", None), "isoformat")
            else str(getattr(snapshot, "computed_at", "") or "")
        ),
        "atm_iv_context": metadata.get("atm_iv_context", {}),
        "iv_resolution": {
            "ws": int(getattr(quality, "iv_ws_count", 0) or 0),
            "rest": int(getattr(quality, "iv_rest_count", 0) or 0),
            "chain": int(getattr(quality, "iv_chain_count", 0) or 0),
            "sabr": int(getattr(quality, "iv_sabr_count", 0) or 0),
            "missing": int(getattr(quality, "iv_missing_count", 0) or 0),
        },
    }

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
    active_options_input_diag = runner_stats.get("active_options_input", {})
    active_options_diag = {}
    active_options_service = getattr(container, "active_options_service", None)
    if active_options_service is not None and hasattr(active_options_service, "get_diagnostics"):
        active_options_diag = active_options_service.get_diagnostics()

    return {
        "timestamp": datetime.now().isoformat(),
        "quote_hub": {
            "active": quote_hub_active,
            "ready_event_set": quote_hub_active,
        },
        "l1_runtime": _build_l1_runtime_diag(getattr(state, "latest_l1_snapshot", None)),
        "agent_runner": {
            "running": runner_stats.get("is_running"),
            "stats": runner_stats,
            "last_update_age_seconds": runner_stats.get("last_update_age_seconds"),
        },
        "active_options_input": active_options_input_diag,
        "l3_layer": container.l3_reactor.get_diagnostics() if container.l3_reactor else {},
        "active_options": active_options_diag,
        "redis": container.redis_service.get_diagnostics(),
        "stores": service_diag,
    }
