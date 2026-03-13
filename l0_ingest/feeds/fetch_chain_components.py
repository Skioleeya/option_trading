"""Composable helpers for OptionChainBuilder.fetch_chain."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

ShmReader = Callable[[int], int]


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
    return {
        "spot": None,
        "chain": [],
        "as_of": None,
        "as_of_utc": None,
        "version": version,
    }


def build_error_snapshot(
    *,
    spot: float | None,
    version: int,
    now: datetime,
    now_utc_iso: str,
) -> dict[str, Any]:
    return {
        "spot": spot,
        "chain": [],
        "as_of": now,
        "as_of_utc": now_utc_iso,
        "version": version,
    }


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
    rust_bridge: Any,
    shm_reader: ShmReader,
) -> dict[str, Any]:
    rust_active = rust_bridge.mm is not None
    return {
        "rust_active": rust_active,
        "rust_shm_path": rust_bridge.mm_path if rust_active else None,
        "shm_stats": {
            "head": shm_reader(rust_bridge.head_ptr) if rust_active else 0,
            "tail": shm_reader(rust_bridge.tail_ptr) if rust_active else 0,
            "status": "OK" if rust_active else "DISCONNECTED",
        },
    }


def build_governor_telemetry(
    *,
    rate_limiter: Any,
    orchestrator: Any,
    sub_mgr: Any,
) -> dict[str, Any]:
    return {
        "symbols_per_min": rate_limiter.symbol_tokens,
        "cooldown_active": rate_limiter.cooldown_active,
        "limiter_profile": rate_limiter.symbol_profile,
        "cooldown_hits_5m": rate_limiter.cooldown_hits_5m,
        "warmup_pending_symbols": orchestrator.pending_warmup_count,
        "metadata_cache_hit_rate": sub_mgr.metadata_cache_hit_rate,
    }


def compose_fetch_chain_payload(
    *,
    spot: float | None,
    chain: list[dict[str, Any]],
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
) -> dict[str, Any]:
    return {
        "spot": spot,
        "chain": chain,
        "version": version,
        "tier2_chain": tier2_chain,
        "tier3_chain": tier3_chain,
        "volume_map": volume_map,
        "aggregate_greeks": aggregate_greeks,
        "ttm_seconds": ttm_seconds,
        "as_of": now,
        "as_of_utc": now_utc_iso,
        "rust_active": runtime_status.get("rust_active", False),
        "rust_shm_path": runtime_status.get("rust_shm_path"),
        "shm_stats": runtime_status.get("shm_stats"),
        "governor_telemetry": governor_telemetry,
        "official_hv_diagnostics": official_hv_diagnostics,
    }
