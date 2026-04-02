"""Snapshot projection helpers for L0 V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from shared_rust.contracts import dicts_to_record_batch
from shared.services.l0_runtime.native_loader import l0_rust


@dataclass
class LegacyGreeksAudit:
    """Tracks legacy greeks dispatch frequency by version/caller."""

    invocations: int = 0
    by_version: dict[int, int] = field(default_factory=dict)
    by_caller: dict[str, int] = field(default_factory=dict)

    def record_dispatch(self, snapshot_version: int, caller_tag: str) -> int:
        self.invocations += 1
        self.by_version[snapshot_version] = self.by_version.get(snapshot_version, 0) + 1
        self.by_caller[caller_tag] = self.by_caller.get(caller_tag, 0) + 1
        return self.invocations

    def diagnostics(self) -> dict[str, Any]:
        return {
            "invocations": self.invocations,
            "by_version": dict(self.by_version),
            "by_caller": dict(self.by_caller),
        }


def build_uninitialized_snapshot(version: int) -> dict[str, Any]:
    return dict(l0_rust.l0_projection_build_uninitialized_snapshot(int(version)))


def build_error_snapshot(
    *,
    spot: float | None,
    version: int,
    now: datetime,
    now_utc_iso: str,
) -> dict[str, Any]:
    return dict(
        l0_rust.l0_projection_build_error_snapshot(
            spot,
            int(version),
            now,
            str(now_utc_iso),
        )
    )


def build_runtime_status(
    *,
    rust_active: bool,
    rust_shm_path: str | None,
    shm_stats: dict[str, Any] | None,
) -> dict[str, Any]:
    return dict(
        l0_rust.l0_projection_build_runtime_status(
            bool(rust_active),
            rust_shm_path,
            shm_stats,
        )
    )


def build_governor_telemetry(
    *,
    rate_limiter: Any,
    orchestrator: Any,
    sub_mgr: Any,
) -> dict[str, Any]:
    return dict(
        l0_rust.l0_projection_build_governor_telemetry(
            int(rate_limiter.symbol_tokens),
            bool(rate_limiter.cooldown_active),
            str(rate_limiter.symbol_profile),
            int(rate_limiter.cooldown_hits_5m),
            int(orchestrator.pending_warmup_count),
            float(sub_mgr.metadata_cache_hit_rate),
        )
    )


def aggregate_store_snapshot(
    *,
    store: Any,
    depth_engine: Any,
    target_symbols: set[str],
) -> list[dict[str, Any]]:
    return store.get_flow_merged_snapshot(
        depth_engine.get_flow_snapshot(),
        target_symbols=target_symbols,
    )


def compose_fetch_chain_payload(
    *,
    spot: float | None,
    chain: list[dict[str, Any]],
    chain_arrow: Any = None,
    version: int,
    tier2_chain: list[dict[str, Any]],
    tier3_chain: list[dict[str, Any]],
    volume_map: dict[str, float],
    aggregate_greeks: dict[str, Any],
    ttm_seconds: float,
    now: datetime,
    now_utc_iso: str,
    runtime_status: dict[str, Any],
    governor_telemetry: dict[str, Any],
    official_hv_diagnostics: dict[str, Any],
    header_volatility_aux_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    return dict(
        l0_rust.l0_projection_compose_fetch_chain_payload(
            spot,
            chain,
            int(version),
            tier2_chain,
            tier3_chain,
            volume_map,
            aggregate_greeks,
            float(ttm_seconds),
            now,
            str(now_utc_iso),
            runtime_status,
            governor_telemetry,
            official_hv_diagnostics,
            header_volatility_aux_diagnostics,
            chain_arrow,
        )
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


__all__ = [
    "LegacyGreeksAudit",
    "aggregate_store_snapshot",
    "build_error_snapshot",
    "build_error_snapshot_payload",
    "build_governor_telemetry",
    "build_runtime_status",
    "build_snapshot_payload",
    "build_uninitialized_snapshot",
    "build_uninitialized_snapshot_payload",
    "compose_fetch_chain_payload",
]
