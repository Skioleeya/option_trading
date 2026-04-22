from __future__ import annotations

import asyncio
import contextlib
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.loops.broadcast_loop import run_broadcast_loop
from app.loops.shared_state import SharedLoopState
from shared.config import settings


@dataclass
class _FakeReport:
    client_count: int = 1
    message_type: str = "dashboard_delta"
    payload_age_ms: float = 0.0
    is_stale: bool = False
    serialized_bytes: int = 1
    delta_ratio: float = 1.0
    broadcast_latency_ms: float = 0.0
    failed_clients: int = 0


class _FakeFrozen:
    def __init__(self, version: int, spot: float = 700.0) -> None:
        self.version = version
        self.spot = spot
        self.data_timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, int]:
        return {"version": self.version}

    def with_live_spot(
        self,
        *,
        spot: float,
        version: int,
        data_timestamp: str,
        broadcast_timestamp: str | None = None,
        quote_lane: dict[str, object] | None = None,
    ) -> "_FakeFrozen":
        del broadcast_timestamp, quote_lane
        updated = _FakeFrozen(version=version, spot=spot)
        updated.data_timestamp = data_timestamp
        return updated

    def with_governor_telemetry(self, patch: dict[str, object] | None) -> "_FakeFrozen":
        del patch
        updated = _FakeFrozen(version=self.version, spot=self.spot)
        updated.data_timestamp = self.data_timestamp
        return updated


class _FakeGovernor:
    def __init__(self) -> None:
        self.calls: list[dict[str, float | int | object]] = []

    async def broadcast(self, *, payload, clients, payload_time, compute_interval):
        self.calls.append(
            {
                "ts": time.monotonic(),
                "payload": payload,
                "clients": len(clients),
                "payload_time": payload_time,
                "compute_interval": compute_interval,
            }
        )
        return _FakeReport(client_count=len(clients))


async def _wait_for(predicate, timeout_sec: float) -> None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.001)
    raise AssertionError("condition not met before timeout")


@pytest.mark.asyncio
async def test_broadcast_loop_broadcasts_immediately_on_new_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ws_broadcast_interval", 0.2, raising=False)

    governor = _FakeGovernor()
    ctr = SimpleNamespace(l3_reactor=SimpleNamespace(governor=governor))
    ws_manager = SimpleNamespace(clients={object()})
    state = SharedLoopState()

    task = asyncio.create_task(run_broadcast_loop(ctr, ws_manager, state))
    try:
        await asyncio.sleep(0.02)
        start = time.monotonic()
        state.update(_FakeFrozen(version=1))
        await _wait_for(lambda: len(governor.calls) >= 1, timeout_sec=0.08)
        assert governor.calls[0]["ts"] - start < 0.08
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_broadcast_loop_rebroadcasts_on_heartbeat_without_new_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ws_broadcast_interval", 0.05, raising=False)

    governor = _FakeGovernor()
    ctr = SimpleNamespace(l3_reactor=SimpleNamespace(governor=governor))
    ws_manager = SimpleNamespace(clients={object()})
    state = SharedLoopState()
    state.update(_FakeFrozen(version=7))

    task = asyncio.create_task(run_broadcast_loop(ctr, ws_manager, state))
    try:
        await asyncio.sleep(0)
        await _wait_for(lambda: len(governor.calls) >= 1, timeout_sec=0.08)
        first_call_ts = float(governor.calls[0]["ts"])
        await _wait_for(lambda: len(governor.calls) >= 2, timeout_sec=0.15)
        second_call_ts = float(governor.calls[1]["ts"])
        assert second_call_ts - first_call_ts >= 0.04
        assert governor.calls[0]["payload"] is governor.calls[1]["payload"]
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_broadcast_loop_broadcasts_live_spot_overlay_without_waiting_for_compute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ws_broadcast_interval", 0.2, raising=False)

    governor = _FakeGovernor()
    ctr = SimpleNamespace(l3_reactor=SimpleNamespace(governor=governor))
    ws_manager = SimpleNamespace(clients={object()})
    state = SharedLoopState()
    state.update(_FakeFrozen(version=10, spot=705.0))

    task = asyncio.create_task(run_broadcast_loop(ctr, ws_manager, state))
    try:
        await asyncio.sleep(0)
        await _wait_for(lambda: len(governor.calls) >= 1, timeout_sec=0.08)
        baseline = len(governor.calls)
        start = time.monotonic()
        state.publish_live_spot(
            spot=705.25,
            version=11,
            data_timestamp="2026-04-21T17:30:00+00:00",
        )
        assert state.frozen is not None
        assert state.frozen.version == 11
        await _wait_for(lambda: len(governor.calls) > baseline, timeout_sec=0.08)
        assert governor.calls[-1]["ts"] - start < 0.08
        assert governor.calls[-1]["payload"].version == 11
        assert governor.calls[-1]["payload"].spot == pytest.approx(705.25)
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_broadcast_loop_broadcasts_quote_lane_overlay_without_waiting_for_compute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ws_broadcast_interval", 0.2, raising=False)

    governor = _FakeGovernor()
    ctr = SimpleNamespace(l3_reactor=SimpleNamespace(governor=governor))
    ws_manager = SimpleNamespace(clients={object()})
    state = SharedLoopState()
    state.update(_FakeFrozen(version=10, spot=705.0))

    task = asyncio.create_task(run_broadcast_loop(ctr, ws_manager, state))
    try:
        await asyncio.sleep(0)
        await _wait_for(lambda: len(governor.calls) >= 1, timeout_sec=0.08)
        baseline = len(governor.calls)
        start = time.monotonic()
        state.publish_quote_lane_telemetry({"last_source_timestamp_utc": "2026-04-21T17:30:00+00:00"})
        await _wait_for(lambda: len(governor.calls) > baseline, timeout_sec=0.08)
        assert governor.calls[-1]["ts"] - start < 0.08
        assert governor.calls[-1]["payload"].version == 10
        assert governor.calls[-1]["payload"].spot == pytest.approx(705.0)
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
