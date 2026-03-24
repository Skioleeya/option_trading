"""Project L0 state into stable snapshot payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from shared.contracts.option_chain_arrow import dicts_to_record_batch
from l0_ingest.v2.projection.snapshot.components import (
    build_error_snapshot,
    build_governor_telemetry,
    build_runtime_status,
    build_uninitialized_snapshot,
    compose_fetch_chain_payload,
)
from l0_ingest.v2.services.orchestration.support import read_shm_u64


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
    rust_bridge: Any,
    include_chain_arrow: bool,
) -> dict[str, Any]:
    now = datetime.now(ZoneInfo("US/Eastern"))
    chain = state.snapshot_rows(services.sub_mgr.target_symbols)
    chain_arrow = dicts_to_record_batch(chain) if include_chain_arrow else None
    runtime_status = build_runtime_status(
        rust_bridge=rust_bridge,
        shm_reader=lambda ptr: read_shm_u64(rust_bridge.mm, ptr),
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
    )
    payload.pop("aggregate_greeks", None)
    payload.pop("ttm_seconds", None)
    return payload
