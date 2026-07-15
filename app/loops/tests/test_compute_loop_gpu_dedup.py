from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from app.loops.compute_loop import run_compute_loop
from app.loops.shared_state import SharedLoopState
from l3_assembly.reactor import ResearchPersistenceFatalError
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
    def __init__(self, *, returned_spot: float | None = None) -> None:
        self.calls = 0
        self.compute_audits: list[dict[str, Any]] = []
        self.chain_inputs: list[Any] = []
        self.returned_spot = returned_spot

    async def compute(
        self,
        *,
        chain_snapshot: Any,
        spot: float,
        l0_version: int,
        iv_cache: dict[str, float],
        spot_at_sync: dict[str, float],
        extra_metadata: dict[str, Any],
    ) -> _FakeL1Snapshot:
        del iv_cache, spot_at_sync
        self.calls += 1
        self.compute_audits.append(dict(extra_metadata.get("compute_audit", {})))
        self.chain_inputs.append(chain_snapshot)
        snapshot_spot = spot if self.returned_spot is None else self.returned_spot
        return _FakeL1Snapshot(version=l0_version, spot=snapshot_spot, extra_metadata=extra_metadata)


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
    def get_anchor_symbols(self) -> set[str]:
        return set()

    async def update(
        self,
        chain: list[dict[str, Any]],
        spot: float,
        *,
        source_freshness: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        del chain, spot, source_freshness
        return {}


class _FakeActiveOptionsService:
    def __init__(self) -> None:
        self._latest: list[dict[str, Any]] = []
        self._latest_source_version = 0

    async def update_background(self, **kwargs: Any) -> None:
        source_version = int(kwargs.get("source_version", 0) or 0)
        if source_version > 0:
            self._latest_source_version = source_version
        chain = kwargs.get("chain") or []
        if not chain:
            self._latest = []
            return
        row = dict(chain[0])
        self._latest = [{
            "symbol": row.get("symbol", "SPY"),
            "option_type": row.get("option_type", row.get("type", "CALL")),
            "strike": row.get("strike", 0.0),
            "volume": int(row.get("volume", 0) or 0),
            "turnover": float(row.get("turnover", 0.0) or 0.0),
            "flow": 0.0,
            "flow_score": 0.0,
            "impact_index": 0.0,
            "is_sweep": False,
            "flow_deg_formatted": "$0",
            "flow_volume_label": "0",
            "flow_color": "text-accent-red",
            "flow_glow": "",
            "flow_intensity": "LOW",
            "flow_direction": "NEUTRAL",
            "flow_d_z": 0.0,
            "flow_e_z": 0.0,
            "flow_g_z": 0.0,
            "is_placeholder": False,
            "slot_index": 1,
            "row_quality": "REAL",
            "flow_signal_state": "LIVE",
            "flow_signal_reason": None,
        }]

    def get_diagnostics(self) -> dict[str, Any]:
        return {"latest_source_version": self._latest_source_version}

    def get_latest(self) -> list[dict[str, Any]]:
        return list(self._latest)


class _FakeBuilder:
    def __init__(self, snapshots: list[dict[str, Any]]) -> None:
        self._snapshots = snapshots
        self._cursor = 0
        self._iv_cache: dict[str, float] = {}
        self._spot_at_sync: dict[str, float] = {}
        self.fetch_include_chain_arrow: list[bool] = []
        self.last_mandatory_symbols: set[str] = set()

    async def fetch_snapshot(self, *, include_chain_arrow: bool = False) -> dict[str, Any]:
        self.fetch_include_chain_arrow.append(include_chain_arrow)
        if self._cursor >= len(self._snapshots):
            raise asyncio.CancelledError()
        snapshot = self._snapshots[self._cursor]
        self._cursor += 1
        await asyncio.sleep(0)
        return snapshot

    def get_iv_sync_context(self) -> tuple[dict[str, float], dict[str, float]]:
        return dict(self._iv_cache), dict(self._spot_at_sync)

    def set_mandatory_symbols(self, symbols: set[str]) -> None:
        self.last_mandatory_symbols = set(symbols)

    async def refresh_subscriptions_once(self, spot: float | None) -> set[str]:
        del spot
        return {"SPY.US"}

    async def repair_symbols_once(self, symbols: set[str], *, log_prefix: str) -> int:
        del symbols, log_prefix
        return 0


class _FakeContainer:
    def __init__(self, snapshots: list[dict[str, Any]]) -> None:
        self.option_chain_builder = _FakeBuilder(snapshots)
        self.l1_reactor = _FakeL1Reactor()
        self.l2_reactor = _FakeL2Reactor()
        self.l3_reactor = _FakeL3Reactor()
        self.atm_decay_tracker = _FakeAtmDecayTracker()
        self.active_options_service = _FakeActiveOptionsService()


class _FatalL3Reactor:
    async def tick(self, **kwargs: Any) -> _FakeFrozen:
        del kwargs
        raise ResearchPersistenceFatalError("PyValueError: corrupt raw parquet")


class _CaptureL3Reactor:
    def __init__(self) -> None:
        self.snapshot_spots: list[float] = []

    async def tick(self, **kwargs: Any) -> _FakeFrozen:
        self.snapshot_spots.append(float(kwargs["snapshot"].spot))
        return _FakeFrozen()


def _snapshot(version: int) -> dict[str, Any]:
    return {
        "spot": 560.0,
        "chain": [{"symbol": "SPY.TEST.C", "strike": 560.0, "type": "CALL", "volume": 10}],
        "version": version,
        "volume_map": {},
        "rust_active": True,
        "shm_stats": {"status": "OK", "head": 1, "tail": 1},
    }


def _snapshot_with_arrow(version: int, chain_arrow: Any) -> dict[str, Any]:
    snap = _snapshot(version)
    snap["chain_arrow"] = chain_arrow
    return snap


@pytest.mark.asyncio
async def test_compute_loop_skips_duplicate_snapshot_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "websocket_update_interval", 0.001, raising=False)

    ctr = _FakeContainer([_snapshot(101), _snapshot(101), _snapshot(102), _snapshot(102)])
    state = SharedLoopState()

    task = asyncio.create_task(run_compute_loop(ctr, state))
    with pytest.raises(asyncio.CancelledError):
        await task

    assert ctr.l1_reactor.calls == 2
    assert all(ctr.option_chain_builder.fetch_include_chain_arrow)
    assert [audit.get("compute_id") for audit in ctr.l1_reactor.compute_audits] == [1, 2]
    assert [audit.get("snapshot_version") for audit in ctr.l1_reactor.compute_audits] == [101, 102]
    assert all(str(audit.get("gpu_task_id", "")).startswith("gpu-task-") for audit in ctr.l1_reactor.compute_audits)

    gpu_diag = state.get_diagnostics()["gpu_compute_audit"]
    assert gpu_diag["l1_compute_runs"] == 2
    assert gpu_diag["duplicate_snapshot_skips"] >= 2
    assert str(gpu_diag["last_gpu_task_id"]).startswith("gpu-task-")
    active_input_diag = state.get_diagnostics()["active_options_input"]
    assert active_input_diag["updates"] == 2
    assert active_input_diag["valid"] is True
    assert active_input_diag["chain_size"] == 1
    assert active_input_diag["source_version"] == 102
    assert ctr.active_options_service.get_diagnostics()["latest_source_version"] == 102


@pytest.mark.asyncio
async def test_compute_loop_prefers_chain_arrow_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "websocket_update_interval", 0.001, raising=False)

    arrow_sentinel = object()
    ctr = _FakeContainer([_snapshot_with_arrow(201, arrow_sentinel)])
    state = SharedLoopState()

    task = asyncio.create_task(run_compute_loop(ctr, state))
    with pytest.raises(asyncio.CancelledError):
        await task

    assert ctr.l1_reactor.calls == 1
    assert ctr.option_chain_builder.fetch_include_chain_arrow
    assert all(ctr.option_chain_builder.fetch_include_chain_arrow)
    assert ctr.l1_reactor.chain_inputs[0] is arrow_sentinel
    active_input_diag = state.get_diagnostics()["active_options_input"]
    assert active_input_diag["updates"] == 1
    assert active_input_diag["valid"] is True
    assert ctr.active_options_service.get_diagnostics()["latest_source_version"] == 201


@pytest.mark.asyncio
async def test_compute_loop_stops_on_research_persistence_fatal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "websocket_update_interval", 0.001, raising=False)

    ctr = _FakeContainer([_snapshot(301)])
    ctr.l3_reactor = _FatalL3Reactor()
    state = SharedLoopState()

    with pytest.raises(ResearchPersistenceFatalError):
        await run_compute_loop(ctr, state)

    fatal = state.get_diagnostics()["fatal_runtime_error"]
    assert fatal["source"] == "research_persistence"
    assert "corrupt raw parquet" in fatal["message"]


@pytest.mark.asyncio
async def test_compute_loop_reconciles_l1_empty_snapshot_spot_before_l3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "websocket_update_interval", 0.001, raising=False)

    ctr = _FakeContainer([_snapshot(401)])
    ctr.l1_reactor = _FakeL1Reactor(returned_spot=0.0)
    ctr.l3_reactor = _CaptureL3Reactor()
    state = SharedLoopState()

    task = asyncio.create_task(run_compute_loop(ctr, state))
    with pytest.raises(asyncio.CancelledError):
        await task

    assert ctr.l1_reactor.calls == 1
    assert ctr.l3_reactor.snapshot_spots == [560.0]
