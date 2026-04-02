"""Rust-backed helpers for L0 snapshot projection semantics."""

from __future__ import annotations

from typing import Any

from shared.services.l0_runtime._native_generated import l0_rust


def build_uninitialized_snapshot_native(version: int) -> dict[str, Any]:
    return dict(l0_rust.l0_projection_build_uninitialized_snapshot(int(version)))


def build_error_snapshot_native(
    *,
    spot: float | None,
    version: int,
    now: Any,
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


def build_runtime_status_native(
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


def build_governor_telemetry_native(
    *,
    symbols_per_min: int,
    cooldown_active: bool,
    limiter_profile: str,
    cooldown_hits_5m: int,
    warmup_pending_symbols: int,
    metadata_cache_hit_rate: float,
) -> dict[str, Any]:
    return dict(
        l0_rust.l0_projection_build_governor_telemetry(
            int(symbols_per_min),
            bool(cooldown_active),
            str(limiter_profile),
            int(cooldown_hits_5m),
            int(warmup_pending_symbols),
            float(metadata_cache_hit_rate),
        )
    )


def compose_fetch_chain_payload_native(
    *,
    spot: float | None,
    chain: list[dict[str, Any]],
    version: int,
    tier2_chain: list[dict[str, Any]],
    tier3_chain: list[dict[str, Any]],
    volume_map: dict[str, Any],
    aggregate_greeks: dict[str, Any],
    ttm_seconds: float,
    now: Any,
    now_utc_iso: str,
    runtime_status: dict[str, Any],
    governor_telemetry: dict[str, Any],
    official_hv_diagnostics: dict[str, Any],
    header_volatility_aux_diagnostics: dict[str, Any],
    chain_arrow: Any = None,
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
