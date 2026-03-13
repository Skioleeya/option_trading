from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from app.loops.compute_loop import run_compute_loop
from app.loops.shared_state import SharedLoopState
from shared.config import settings


@dataclass
class _FakeAggregates:
    atm_iv: float = 0.22


class _FakeL1Snapshot:
    def __init__(self, version: int, spot: float, extra_metadata: dict[str, Any]) -> None:
        self.version = version
        self.spot = spot
        self.aggregates = _FakeAggregates()
        self.extra_metadata = extra_metadata
        self.ttm_seconds = 1200.0
        self.chain: list[dict[str, Any]] = []


class _FakeL1Reactor:
    def __init__(self) -> None:
        self.calls = 0
        self.compute_audits: list[dict[str, Any]] = []

    async def compute(
        self,
        *,
        chain_snapshot: list[dict[str, Any]],
        spot: float,
        l0_version: int,
        iv_cache: dict[str, float],
        spot_at_sync: dict[str, float],
        extra_metadata: dict[str, Any],
    ) -> _FakeL1Snapshot:
        del chain_snapshot, iv_cache, spot_at_sync
        self.calls += 1
        self.compute_audits.append(dict(extra_metadata.get("compute_audit", {})))
        return _FakeL1Snapshot(version=l0_version, spot=spot, extra_metadata=extra_metadata)


class _FakeDecision:
    direction = "NEUTRAL"
    confidence = 0.0
    latency_ms = 0.0
    data: dict[str, Any] = {"spy_atm_iv": 0.22}


class _FakeL2Reactor:
    async def decide(self, snapshot: Any) -> _FakeDecision:
        del snapshot
        return _FakeDecision()

    def flush_audit(self) -> int:
        return 0


class _FakeFrozen:
    def to_dict(self) -> dict[str, Any]:
        return {"agent_g": {"data": {"spy_atm_iv": 0.22, "gex_regime": "NEUTRAL"}}}


class _FakeL3Reactor:
    async def tick(self, **kwargs: Any) -> _FakeFrozen:
        del kwargs
        return _FakeFrozen()


class _FakeAtmDecayTracker:
    async def update(self, chain: list[dict[str, Any]], spot: float) -> dict[str, Any]:
        del chain, spot
        return {}


class _FakeActiveOptionsService:
    def get_latest(self) -> list[dict[str, Any]]:
        return []


class _FakeBuilder:
    def __init__(self, snapshots: list[dict[str, Any]]) -> None:
        self._snapshots = snapshots
        self._cursor = 0
        self._iv_cache: dict[str, float] = {}
        self._spot_at_sync: dict[str, float] = {}
        self.fetch_args: list[tuple[bool, str]] = []

    async def fetch_chain(
        self,
        include_legacy_greeks: bool = False,
        caller_tag: str = "unspecified",
    ) -> dict[str, Any]:
        self.fetch_args.append((include_legacy_greeks, caller_tag))
        if self._cursor >= len(self._snapshots):
            raise asyncio.CancelledError()
        snapshot = self._snapshots[self._cursor]
        self._cursor += 1
        await asyncio.sleep(0)
        return snapshot

    def get_iv_sync_context(self) -> tuple[dict[str, float], dict[str, float]]:
        return dict(self._iv_cache), dict(self._spot_at_sync)


class _FakeContainer:
    def __init__(self, snapshots: list[dict[str, Any]]) -> None:
        self.option_chain_builder = _FakeBuilder(snapshots)
        self.l1_reactor = _FakeL1Reactor()
        self.l2_reactor = _FakeL2Reactor()
        self.l3_reactor = _FakeL3Reactor()
        self.atm_decay_tracker = _FakeAtmDecayTracker()
        self.active_options_service = _FakeActiveOptionsService()


def _snapshot(version: int) -> dict[str, Any]:
    return {
        "spot": 560.0,
        "chain": [{"symbol": "SPY.TEST.C", "strike": 560.0, "type": "CALL", "volume": 10}],
        "version": version,
        "volume_map": {},
        "rust_active": True,
        "shm_stats": {"status": "OK", "head": 1, "tail": 1},
    }


@pytest.mark.asyncio
async def test_compute_loop_skips_duplicate_snapshot_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "websocket_update_interval", 0.001, raising=False)

    ctr = _FakeContainer([_snapshot(101), _snapshot(101), _snapshot(102), _snapshot(102)])
    state = SharedLoopState()

    task = asyncio.create_task(run_compute_loop(ctr, state))
    with pytest.raises(asyncio.CancelledError):
        await task

    assert ctr.l1_reactor.calls == 2
    assert all(flag is False for flag, _ in ctr.option_chain_builder.fetch_args)
    assert all(tag == "compute_loop" for _, tag in ctr.option_chain_builder.fetch_args)
    assert [audit.get("compute_id") for audit in ctr.l1_reactor.compute_audits] == [1, 2]
    assert [audit.get("snapshot_version") for audit in ctr.l1_reactor.compute_audits] == [101, 102]
    assert all(str(audit.get("gpu_task_id", "")).startswith("gpu-task-") for audit in ctr.l1_reactor.compute_audits)

    gpu_diag = state.get_diagnostics()["gpu_compute_audit"]
    assert gpu_diag["l1_compute_runs"] == 2
    assert gpu_diag["duplicate_snapshot_skips"] >= 2
    assert str(gpu_diag["last_gpu_task_id"]).startswith("gpu-task-")

