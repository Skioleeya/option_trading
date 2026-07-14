from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from typing import Any

import pytest

from app.loops.compute_loop import run_compute_loop
from app.loops.shared_state import SharedLoopState
from l3_assembly.events.active_options_contract import active_option_row_from_dict
from l3_assembly.events.payload_events import FrozenPayload, SignalData, UIState
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
        del chain_snapshot, iv_cache, spot_at_sync
        self.calls += 1
        return _FakeL1Snapshot(version=l0_version, spot=spot, extra_metadata=extra_metadata)


class _FakeDecision:
    direction = "NEUTRAL"
    confidence = 0.0
    latency_ms = 0.0
    version = 101
    computed_at = "2026-03-25T14:00:00+00:00"
    signal_summary: dict[str, Any] = {}
    data: dict[str, Any] = {"spy_atm_iv": 0.22}


class _FakeL2Reactor:
    async def decide(self, snapshot: Any) -> _FakeDecision:
        del snapshot
        return _FakeDecision()

    def flush_audit(self) -> int:
        return 0


class _FakeL3Reactor:
    async def tick(self, **kwargs: Any) -> FrozenPayload:
        snapshot = kwargs["snapshot"]
        atm_decay = kwargs["atm_decay"]
        active_options = tuple(
            active_option_row_from_dict(row)
            for row in (kwargs.get("active_options") or [])
            if isinstance(row, dict)
        )
        return FrozenPayload(
            data_timestamp="2026-03-25T14:00:00+00:00",
            broadcast_timestamp="2026-03-25T14:00:00+00:00",
            spot=float(snapshot.spot),
            version=int(snapshot.version),
            drift_ms=0.0,
            drift_warning=False,
            signal=SignalData.neutral(),
            ui_state=replace(UIState.zero_state(), active_options=active_options),
            atm=atm_decay,
        )


class _FakeAtmDecayTracker:
    def __init__(self) -> None:
        self.calls = 0

    def get_anchor_symbols(self) -> set[str]:
        return {"SPY.TEST.C", "SPY.TEST.P"}

    async def update(self, chain: list[dict[str, Any]], spot: float) -> dict[str, Any]:
        del chain, spot
        self.calls += 1
        return {
            "timestamp": f"2026-03-25T10:00:0{self.calls}-04:00",
            "call_pct": 0.01,
            "put_pct": 0.02,
            "straddle_pct": 0.03,
            "strike": 560.0,
            "strike_changed": False,
        }


class _FakeActiveOptionsService:
    def __init__(self) -> None:
        self.calls = 0
        self.update_calls = 0
        self._latest_source_version = 0

    async def update_background(self, **kwargs: Any) -> None:
        self.update_calls += 1
        source_version = int(kwargs.get("source_version", 0) or 0)
        if source_version > 0:
            self._latest_source_version = source_version

    def get_diagnostics(self) -> dict[str, Any]:
        return {"latest_source_version": self._latest_source_version}

    def get_latest(self) -> list[dict[str, Any]]:
        self.calls += 1
        return [_active_options_row(strike=560.0 + self.calls, flow=float(self.calls))]


class _FakeBuilder:
    def __init__(self, snapshots: list[dict[str, Any]]) -> None:
        self._snapshots = snapshots
        self._cursor = 0
        self.last_mandatory_symbols: set[str] | None = None
        self.refresh_calls = 0
        self.repair_calls = 0

    async def fetch_snapshot(self, *, include_chain_arrow: bool = False) -> dict[str, Any]:
        del include_chain_arrow
        if self._cursor >= len(self._snapshots):
            raise asyncio.CancelledError()
        snapshot = self._snapshots[self._cursor]
        self._cursor += 1
        await asyncio.sleep(0)
        return snapshot

    def get_iv_sync_context(self) -> tuple[dict[str, float], dict[str, float]]:
        return {}, {}

    def set_mandatory_symbols(self, symbols: set[str]) -> None:
        self.last_mandatory_symbols = set(symbols)

    async def refresh_subscriptions_once(self, spot: float | None) -> set[str]:
        del spot
        self.refresh_calls += 1
        return {"SPY.US", *(self.last_mandatory_symbols or set())}

    async def repair_symbols_once(self, symbols: set[str], *, log_prefix: str) -> int:
        del log_prefix
        self.repair_calls += 1
        return len(symbols)


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


def _active_options_row(*, strike: float, flow: float) -> dict[str, Any]:
    return {
        "symbol": "SPY",
        "option_type": "CALL",
        "strike": strike,
        "implied_volatility": 0.22,
        "volume": 1000,
        "turnover": 100000.0,
        "flow": flow,
        "flow_score": flow,
        "impact_index": 1.0,
        "is_sweep": False,
        "flow_deg_formatted": "$1",
        "flow_volume_label": "1K",
        "flow_color": "text-accent-red",
        "flow_glow": "",
        "flow_intensity": "LOW",
        "flow_direction": "BULLISH",
        "flow_d_z": 0.0,
        "flow_e_z": 0.0,
        "flow_g_z": 0.0,
        "is_placeholder": False,
        "slot_index": 1,
        "row_quality": "REAL",
        "fallback_reason": None,
        "is_synthetic_fallback": False,
        "flow_signal_state": "LIVE",
        "flow_signal_reason": None,
    }


@pytest.mark.asyncio
async def test_duplicate_snapshot_tick_keeps_atm_live_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "websocket_update_interval", 0.001, raising=False)

    ctr = _FakeContainer([_snapshot(101), _snapshot(101), _snapshot(101)])
    state = SharedLoopState()

    task = asyncio.create_task(run_compute_loop(ctr, state))
    with pytest.raises(asyncio.CancelledError):
        await task

    assert ctr.l1_reactor.calls == 1
    assert ctr.atm_decay_tracker.calls == 3
    assert ctr.active_options_service.update_calls == 1
    assert ctr.option_chain_builder.refresh_calls == 1
    assert ctr.option_chain_builder.repair_calls == 1
    assert state.frozen is not None
    assert state.frozen.atm is not None
    assert state.frozen.atm["timestamp"] == "2026-03-25T10:00:03-04:00"
    assert state.total_computations == 3

    gpu_diag = state.get_diagnostics()["gpu_compute_audit"]
    assert gpu_diag["duplicate_snapshot_skips"] >= 2
    assert gpu_diag["l1_compute_runs"] == 1


@pytest.mark.asyncio
async def test_duplicate_snapshot_tick_keeps_active_options_live_updates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "websocket_update_interval", 0.001, raising=False)

    ctr = _FakeContainer([_snapshot(101), _snapshot(101), _snapshot(101)])
    state = SharedLoopState()

    task = asyncio.create_task(run_compute_loop(ctr, state))
    with pytest.raises(asyncio.CancelledError):
        await task

    assert ctr.l1_reactor.calls == 1
    assert ctr.active_options_service.calls == 3
    assert ctr.active_options_service.update_calls == 1
    assert ctr.option_chain_builder.refresh_calls == 1
    assert state.frozen is not None
    assert state.frozen.ui_state.active_options
    assert state.frozen.ui_state.active_options[0].strike == pytest.approx(563.0)
    assert state.frozen.ui_state.active_options[0].flow == pytest.approx(3.0)
