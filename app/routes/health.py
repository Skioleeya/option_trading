"""Health and diagnostics endpoints."""

from copy import deepcopy
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder

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


def _extract_active_options_payload(payload_dict: Any) -> dict[str, Any]:
    if not isinstance(payload_dict, dict):
        return {
            "source_version": 0,
            "data_timestamp": None,
            "rows": [],
            "rows_total": 0,
            "rows_real": 0,
            "rows_placeholder": 0,
        }
    agent_g = payload_dict.get("agent_g") or {}
    agent_data = agent_g.get("data") or {}
    ui_state = agent_data.get("ui_state") or {}
    rows = ui_state.get("active_options")
    if not isinstance(rows, list):
        rows = []
    placeholder_rows = sum(
        1 for row in rows if isinstance(row, dict) and bool(row.get("is_placeholder", False))
    )
    return {
        "source_version": int(agent_data.get("version", payload_dict.get("version", 0)) or 0),
        "data_timestamp": payload_dict.get("data_timestamp") or payload_dict.get("timestamp"),
        "rows": deepcopy(rows),
        "rows_total": len(rows),
        "rows_real": max(0, len(rows) - placeholder_rows),
        "rows_placeholder": placeholder_rows,
    }


def _build_active_options_input_capture(snapshot: Any) -> dict[str, Any]:
    if snapshot is None:
        return {
            "valid": False,
            "invalid_reason": "missing_input",
            "source_version": 0,
            "source_timestamp_utc": None,
            "spot": 0.0,
            "atm_iv": 0.0,
            "gex_regime": "NEUTRAL",
            "ttm_seconds": None,
            "chain_size": 0,
            "chain": [],
        }
    chain = getattr(snapshot, "chain", []) or []
    if not isinstance(chain, list):
        chain = []
    return {
        "valid": bool(getattr(snapshot, "valid", False)),
        "invalid_reason": getattr(snapshot, "invalid_reason", None),
        "source_version": int(getattr(snapshot, "source_version", 0) or 0),
        "source_timestamp_utc": getattr(snapshot, "source_timestamp_utc", None),
        "spot": float(getattr(snapshot, "spot", 0.0) or 0.0),
        "atm_iv": float(getattr(snapshot, "atm_iv", 0.0) or 0.0),
        "gex_regime": str(getattr(snapshot, "gex_regime", "NEUTRAL") or "NEUTRAL"),
        "ttm_seconds": getattr(snapshot, "ttm_seconds", None),
        "chain_size": len(chain),
        "chain": deepcopy(chain),
    }


def _is_sparse_active_options_window(
    active_options_diag: dict[str, Any],
    payload_capture: dict[str, Any],
) -> bool:
    filtered_candidates = int(active_options_diag.get("filtered_candidates_count", 0) or 0)
    displayed_real = int(payload_capture.get("rows_real", 0) or 0)
    if filtered_candidates <= 0:
        return False
    return filtered_candidates <= max(5, displayed_real)

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


@router.get("/debug/active_options_capture")
async def active_options_capture(request: Request):
    """Expose version-aligned ActiveOptions raw input and displayed rows for diagnostics."""
    container = request.app.state.container
    state = request.app.state.state

    active_options_diag = {}
    active_options_service = getattr(container, "active_options_service", None)
    if active_options_service is not None and hasattr(active_options_service, "get_diagnostics"):
        active_options_diag = active_options_service.get_diagnostics()

    input_capture = _build_active_options_input_capture(
        getattr(state, "latest_active_options_input", None)
    )
    payload_capture = _extract_active_options_payload(getattr(state, "payload_dict", None))
    input_version = int(input_capture.get("source_version", 0) or 0)
    payload_version = int(payload_capture.get("source_version", 0) or 0)
    aligned = input_version > 0 and input_version == payload_version

    return jsonable_encoder(
        {
            "capture_timestamp": datetime.now().isoformat(),
            "version_alignment": {
                "input_source_version": input_version,
                "payload_source_version": payload_version,
                "aligned": aligned,
            },
            "sparse_window": {
                "is_sparse_window": _is_sparse_active_options_window(
                    active_options_diag,
                    payload_capture,
                ),
                "filtered_candidates_count": int(
                    active_options_diag.get("filtered_candidates_count", 0) or 0
                ),
                "displayed_real_rows": int(payload_capture.get("rows_real", 0) or 0),
                "display_limit": 5,
            },
            "active_options_input": input_capture,
            "displayed_payload": payload_capture,
            "active_options_diagnostics": active_options_diag,
        }
    )
