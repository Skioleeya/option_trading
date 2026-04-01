"""Project L0 state into stable snapshot payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from shared_rust.contracts import dicts_to_record_batch
from shared.services.l0_runtime.projection.snapshot.components import (
    build_error_snapshot,
    build_governor_telemetry,
    build_runtime_status,
    build_uninitialized_snapshot,
    compose_fetch_chain_payload,
)


def build_uninitialized_snapshot_payload(version: int) -> dict[str, Any]:
    return build_uninitialized_snapshot(version)


def build_error_snapshot_payload(
    *,
    spot: float | None,
    version: int,
) -> dict[str, Any]:
    now = datetime.now(ZoneInfo("US/Eastern"))
    now_utc_iso = now.astimezone(ZoneInfo("UTC")).isoformat()
    return build_error_snapshot(
        spot=spot,
        version=version,
        now=now,
        now_utc_iso=now_utc_iso,
    )


def build_snapshot_payload(
    *,
    state: Any,
    services: Any,
    rate_limiter: Any,
    runtime_status: dict[str, Any],
    include_chain_arrow: bool,
) -> dict[str, Any]:
    now = datetime.now(ZoneInfo("US/Eastern"))
    chain = state.snapshot_rows(services.sub_mgr.target_symbols)
    chain_arrow = dicts_to_record_batch(chain) if include_chain_arrow else None
    runtime_status = build_runtime_status(
        rust_active=bool(runtime_status.get("rust_active", False)),
        rust_shm_path=runtime_status.get("rust_shm_path"),
        shm_stats=runtime_status.get("shm_stats"),
    )
    governor_telemetry = build_governor_telemetry(
        rate_limiter=rate_limiter,
        orchestrator=services.orchestrator,
        sub_mgr=services.sub_mgr,
    )
    payload = compose_fetch_chain_payload(
        spot=state.store.spot,
        chain=chain,
        chain_arrow=chain_arrow,
        version=state.store.version,
        tier2_chain=services.tier2.cache,
        tier3_chain=services.tier3.cache,
        volume_map=state.store.volume_map,
        aggregate_greeks={},
        ttm_seconds=0.0,
        now=now,
        now_utc_iso=now.astimezone(ZoneInfo("UTC")).isoformat(),
        runtime_status=runtime_status,
        governor_telemetry=governor_telemetry,
        official_hv_diagnostics=services.orchestrator.official_hv_diagnostics,
        header_volatility_aux_diagnostics=services.orchestrator.header_volatility_aux_diagnostics,
    )
    payload.pop("aggregate_greeks", None)
    payload.pop("ttm_seconds", None)
    return payload

