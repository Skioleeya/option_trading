from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from app.loops.housekeeping_loop import _sync_anchor_symbols, run_housekeeping_loop
from app.loops.shared_state import ActiveOptionsInputSnapshot, SharedLoopState
from shared.config import settings


class _FakeActiveOptionsService:
    def __init__(self) -> None:
        self.calls = 0
        self.last_kwargs: dict[str, Any] = {}

    async def update_background(self, **kwargs: Any) -> None:
        self.calls += 1
        self.last_kwargs = dict(kwargs)


class _FakeAtmDecayTracker:
    def __init__(self, symbols: set[str] | None = None) -> None:
        self._symbols = set(symbols or set())

    def get_anchor_symbols(self) -> set[str]:
        return set(self._symbols)


class _FakeBuilder:
    def __init__(self) -> None:
        self.fetch_calls = 0
        self.last_mandatory_symbols: set[str] | None = None

    async def fetch_snapshot(self, *, include_chain_arrow: bool = False) -> dict[str, Any]:
        del include_chain_arrow
        self.fetch_calls += 1
        return {"chain": [], "spot": 0.0}

    def set_mandatory_symbols(self, symbols: set[str]) -> None:
        self.last_mandatory_symbols = set(symbols)


class _FakeContainer:
    def __init__(self) -> None:
        self.option_chain_builder = _FakeBuilder()
        self.active_options_service = _FakeActiveOptionsService()
        self.atm_decay_tracker = _FakeAtmDecayTracker()
        self.redis_service = SimpleNamespace(client=None)


@pytest.mark.asyncio
async def test_housekeeping_consumes_shared_active_options_input_and_dedups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "websocket_update_interval", 0.001, raising=False)

    ctr = _FakeContainer()
    state = SharedLoopState()
    state.update_active_options_input(
        ActiveOptionsInputSnapshot(
            chain=[{"symbol": "SPY.TEST.C", "strike": 560.0, "type": "CALL", "volume": 500}],
            spot=561.0,
            atm_iv=0.22,
            gex_regime="NEUTRAL",
            ttm_seconds=900.0,
            source_version=777,
            source_timestamp_utc="2026-03-19T15:40:00+00:00",
            valid=True,
            invalid_reason=None,
        )
    )

    task = asyncio.create_task(run_housekeeping_loop(ctr, state))
    await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert ctr.option_chain_builder.fetch_calls == 0
    assert ctr.active_options_service.calls == 1
    assert ctr.active_options_service.last_kwargs.get("spot") == pytest.approx(561.0)
    assert ctr.active_options_service.last_kwargs.get("atm_iv") == pytest.approx(0.22)
    assert ctr.active_options_service.last_kwargs.get("gex_regime") == "NEUTRAL"
    assert ctr.active_options_service.last_kwargs.get("chain")


@pytest.mark.asyncio
async def test_housekeeping_degrades_when_shared_input_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "websocket_update_interval", 0.001, raising=False)

    ctr = _FakeContainer()
    state = SharedLoopState()
    state.update_active_options_input(
        ActiveOptionsInputSnapshot(
            chain=[],
            spot=0.0,
            atm_iv=0.0,
            gex_regime="NEUTRAL",
            ttm_seconds=None,
            source_version=1001,
            source_timestamp_utc="2026-03-19T15:40:00+00:00",
            valid=False,
            invalid_reason="empty_chain",
        )
    )

    task = asyncio.create_task(run_housekeeping_loop(ctr, state))
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert ctr.option_chain_builder.fetch_calls == 0
    assert ctr.active_options_service.calls >= 1
    assert ctr.active_options_service.last_kwargs.get("chain") == []
    assert ctr.active_options_service.last_kwargs.get("spot") == pytest.approx(0.0)


def test_sync_anchor_symbols_clears_mandatory_symbols_when_anchor_is_empty() -> None:
    ctr = _FakeContainer()

    _sync_anchor_symbols(ctr)

    assert ctr.option_chain_builder.last_mandatory_symbols == set()
