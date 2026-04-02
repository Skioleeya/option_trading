"""Composable helpers for OptionChainBuilder.fetch_chain."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from ._native_projection_support import (
    build_error_snapshot_native,
    build_governor_telemetry_native,
    build_runtime_status_native,
    build_uninitialized_snapshot_native,
    compose_fetch_chain_payload_native,
)


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
    return build_uninitialized_snapshot_native(version)


def build_error_snapshot(
    *,
    spot: float | None,
    version: int,
    now: datetime,
    now_utc_iso: str,
) -> dict[str, Any]:
    return build_error_snapshot_native(
        spot=spot,
        version=version,
        now=now,
        now_utc_iso=now_utc_iso,
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


def build_runtime_status(
    *,
    rust_active: bool,
    rust_shm_path: str | None,
    shm_stats: dict[str, Any] | None,
) -> dict[str, Any]:
    return build_runtime_status_native(
        rust_active=rust_active,
        rust_shm_path=rust_shm_path,
        shm_stats=shm_stats,
    )


def build_governor_telemetry(
    *,
    rate_limiter: Any,
    orchestrator: Any,
    sub_mgr: Any,
) -> dict[str, Any]:
    return build_governor_telemetry_native(
        symbols_per_min=rate_limiter.symbol_tokens,
        cooldown_active=rate_limiter.cooldown_active,
        limiter_profile=rate_limiter.symbol_profile,
        cooldown_hits_5m=rate_limiter.cooldown_hits_5m,
        warmup_pending_symbols=orchestrator.pending_warmup_count,
        metadata_cache_hit_rate=sub_mgr.metadata_cache_hit_rate,
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
    return compose_fetch_chain_payload_native(
        spot=spot,
        chain=chain,
        chain_arrow=chain_arrow,
        version=version,
        tier2_chain=tier2_chain,
        tier3_chain=tier3_chain,
        volume_map=volume_map,
        aggregate_greeks=aggregate_greeks,
        ttm_seconds=ttm_seconds,
        now=now,
        now_utc_iso=now_utc_iso,
        runtime_status=runtime_status,
        governor_telemetry=governor_telemetry,
        official_hv_diagnostics=official_hv_diagnostics,
        header_volatility_aux_diagnostics=header_volatility_aux_diagnostics,
    )
