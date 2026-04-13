"""ActiveOptions same-version synchronization helpers for compute loop."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.loops.shared_state import ActiveOptionsInputSnapshot
from shared.services.active_options_constants import ACTIVE_OPTIONS_DEFAULT_LIMIT

if TYPE_CHECKING:
    from app.container import AppContainer

logger = logging.getLogger(__name__)

ACTIVE_OPTIONS_DEFAULT_GEX_REGIME = "NEUTRAL"
ACTIVE_OPTIONS_INVALID_REASON_MISSING_INPUT = "missing_input"


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _latest_source_version(service: Any) -> int:
    if service is None or not hasattr(service, "get_diagnostics"):
        return 0
    diagnostics = service.get_diagnostics()
    if not isinstance(diagnostics, dict):
        return 0
    return max(0, _to_int(diagnostics.get("latest_source_version", 0), 0))


async def ensure_active_options_same_version(
    ctr: "AppContainer",
    *,
    active_options_input: ActiveOptionsInputSnapshot,
    snapshot_version: int,
) -> None:
    source_version = max(0, _to_int(active_options_input.source_version, 0))
    target_version = source_version if source_version > 0 else max(0, _to_int(snapshot_version, 0))
    if target_version <= 0:
        return

    service = ctr.active_options_service
    if _latest_source_version(service) == target_version:
        return

    if not bool(active_options_input.valid):
        raise RuntimeError(
            "active_options_input_invalid: reason=%s gex_regime=%s source_version=%s"
            % (
                str(active_options_input.invalid_reason or ACTIVE_OPTIONS_INVALID_REASON_MISSING_INPUT),
                str(active_options_input.gex_regime or ACTIVE_OPTIONS_DEFAULT_GEX_REGIME),
                target_version,
            )
        )

    redis_client = getattr(getattr(ctr, "redis_service", None), "client", None)
    await service.update_background(
        chain=active_options_input.chain,
        spot=float(active_options_input.spot or 0.0),
        atm_iv=float(active_options_input.atm_iv or 0.0),
        gex_regime=str(active_options_input.gex_regime or ACTIVE_OPTIONS_DEFAULT_GEX_REGIME),
        ttm_seconds=active_options_input.ttm_seconds,
        redis=redis_client,
        limit=ACTIVE_OPTIONS_DEFAULT_LIMIT,
        source_version=target_version,
    )
