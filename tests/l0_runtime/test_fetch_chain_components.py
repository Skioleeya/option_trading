from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from shared.services.l0_runtime.projection.snapshot.components import (
    LegacyGreeksAudit,
    aggregate_store_snapshot,
    build_error_snapshot,
    build_governor_telemetry,
    build_runtime_status,
    build_uninitialized_snapshot,
    compose_fetch_chain_payload,
)


def test_legacy_greeks_audit_records_dispatch_counts() -> None:
    audit = LegacyGreeksAudit()

    first = audit.record_dispatch(101, "compute_loop")
    second = audit.record_dispatch(101, "compute_loop")
    third = audit.record_dispatch(102, "housekeeping")

    assert (first, second, third) == (1, 2, 3)
    diagnostics = audit.diagnostics()
    assert diagnostics["invocations"] == 3
    assert diagnostics["by_version"] == {101: 2, 102: 1}
    assert diagnostics["by_caller"] == {"compute_loop": 2, "housekeeping": 1}


def test_aggregate_store_snapshot_delegates_to_store() -> None:
    captured: dict[str, object] = {}

    class _Store:
        def get_flow_merged_snapshot(self, flow_snapshot, target_symbols):
            captured["flow_snapshot"] = flow_snapshot
            captured["target_symbols"] = target_symbols
            return [{"symbol": "SPY.OPT.C"}]

    class _DepthEngine:
        @staticmethod
        def get_flow_snapshot():
            return {"flow": 1}

    out = aggregate_store_snapshot(
        store=_Store(),
        depth_engine=_DepthEngine(),
        target_symbols={"SPY.OPT.C"},
    )
    assert out == [{"symbol": "SPY.OPT.C"}]
    assert captured["flow_snapshot"] == {"flow": 1}
    assert captured["target_symbols"] == {"SPY.OPT.C"}


def test_aggregate_store_snapshot_allows_unfiltered_startup_snapshot() -> None:
    captured: dict[str, object] = {}

    class _Store:
        def get_flow_merged_snapshot(self, flow_snapshot, target_symbols):
            captured["flow_snapshot"] = flow_snapshot
            captured["target_symbols"] = target_symbols
            return [{"symbol": "SPY.OPT.ALL"}]

    class _DepthEngine:
        @staticmethod
        def get_flow_snapshot():
            return {"flow": 2}

    out = aggregate_store_snapshot(
        store=_Store(),
        depth_engine=_DepthEngine(),
        target_symbols=None,
    )
    assert out == [{"symbol": "SPY.OPT.ALL"}]
    assert captured["flow_snapshot"] == {"flow": 2}
    assert captured["target_symbols"] is None


def test_build_runtime_status_connected_and_disconnected() -> None:
    connected = build_runtime_status(
        rust_active=True,
        rust_shm_path="mmap://x",
        shm_stats={"head": 80, "tail": 160, "status": "OK"},
    )
    disconnected = build_runtime_status(
        rust_active=False,
        rust_shm_path=None,
        shm_stats=None,
    )

    assert connected["rust_active"] is True
    assert connected["shm_stats"] == {"head": 80, "tail": 160, "status": "OK"}
    assert disconnected["rust_active"] is False
    assert disconnected["shm_stats"] == {"head": 0, "tail": 0, "status": "DISCONNECTED"}


def test_build_governor_telemetry_shape() -> None:
    telemetry = build_governor_telemetry(
        rate_limiter=SimpleNamespace(
            symbol_tokens=12,
            cooldown_active=True,
            symbol_profile="startup",
            cooldown_hits_5m=3,
        ),
        orchestrator=SimpleNamespace(pending_warmup_count=7),
        sub_mgr=SimpleNamespace(metadata_cache_hit_rate=0.75),
    )
    assert telemetry == {
        "symbols_per_min": 12,
        "cooldown_active": True,
        "limiter_profile": "startup",
        "cooldown_hits_5m": 3,
        "warmup_pending_symbols": 7,
        "metadata_cache_hit_rate": 0.75,
    }


def test_snapshot_builders_return_contract_fields() -> None:
    uninitialized = build_uninitialized_snapshot(version=123)
    now = datetime(2026, 3, 13, 0, 0, 0, tzinfo=timezone.utc)
    error_snapshot = build_error_snapshot(
        spot=560.1,
        version=124,
        now=now,
        now_utc_iso=now.isoformat(),
    )

    assert uninitialized == {
        "spot": None,
        "chain": [],
        "as_of": None,
        "as_of_utc": None,
        "version": 123,
        "rust_active": False,
        "rust_shm_path": None,
        "shm_stats": {"head": 0, "tail": 0, "status": "UNINITIALIZED"},
    }
    assert error_snapshot["spot"] == 560.1
    assert error_snapshot["version"] == 124
    assert error_snapshot["as_of_utc"] == now.isoformat()
    assert error_snapshot["rust_active"] is False
    assert error_snapshot["rust_shm_path"] is None
    assert error_snapshot["shm_stats"] == {"head": 0, "tail": 0, "status": "ERROR"}


def test_compose_fetch_chain_payload_preserves_runtime_contract() -> None:
    now = datetime(2026, 3, 13, 0, 0, 0, tzinfo=timezone.utc)
    payload = compose_fetch_chain_payload(
        spot=560.0,
        chain=[{"symbol": "SPY.OPT.C"}],
        version=500,
        tier2_chain=[{"symbol": "T2"}],
        tier3_chain=[{"symbol": "T3"}],
        volume_map={"560": 10.0},
        aggregate_greeks={"net_gex": 1.2},
        ttm_seconds=3600.0,
        now=now,
        now_utc_iso=now.isoformat(),
        runtime_status={
            "rust_active": True,
            "rust_shm_path": "mmap://ok",
            "shm_stats": {"head": 1, "tail": 2, "status": "OK"},
        },
        governor_telemetry={"symbols_per_min": 100},
        official_hv_diagnostics={"official_hv_decimal": 0.2},
    )

    assert payload["spot"] == 560.0
    assert payload["version"] == 500
    assert payload["rust_active"] is True
    assert payload["governor_telemetry"]["symbols_per_min"] == 100
    assert payload["official_hv_diagnostics"]["official_hv_decimal"] == 0.2

