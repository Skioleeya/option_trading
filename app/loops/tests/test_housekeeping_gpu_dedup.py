from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from app.loops.housekeeping_loop import run_housekeeping_loop
from app.loops.shared_state import SharedLoopState
from shared.config import settings


@dataclass
class _FakeAggregates:
    atm_iv: float = 0.21


class _FakeL1Snapshot:
    def __init__(self) -> None:
        self.version = 777
        self.spot = 561.0
        self.ttm_seconds = 900.0
        self.aggregates = _FakeAggregates()
        self.chain = [
            {
                "symbol": "SPY.TEST.C",
                "strike": 560.0,
                "type": "CALL",
                "volume": 500,
                "turnover": 100000.0,
                "implied_volatility": 0.0,
                "computed_iv": 0.22,
                "delta": 0.0,
                "computed_delta": 0.31,
                "gamma": 0.0,
                "computed_gamma": 0.018,
                "vanna": 0.0,
                "computed_vanna": -0.01,
                "open_interest": 1000,
            }
        ]


class _FakeActiveOptionsService:
    def __init__(self) -> None:
        self.calls = 0
        self.last_chain: list[dict[str, Any]] = []

    async def update_background(self, **kwargs: Any) -> None:
        self.calls += 1
        self.last_chain = kwargs.get("chain", [])


class _FakeAtmDecayTracker:
    def get_anchor_symbols(self) -> set[str]:
        return set()


class _FakeBuilder:
    def __init__(self) -> None:
        self.fetch_calls = 0

    async def fetch_chain(
        self,
        include_legacy_greeks: bool = False,
        caller_tag: str = "unspecified",
    ) -> dict[str, Any]:
        del include_legacy_greeks, caller_tag
        self.fetch_calls += 1
        return {"chain": [], "spot": 0.0, "ttm_seconds": 0.0}

    def set_mandatory_symbols(self, symbols: set[str]) -> None:
        del symbols


class _FakeContainer:
    def __init__(self) -> None:
        self.option_chain_builder = _FakeBuilder()
        self.active_options_service = _FakeActiveOptionsService()
        self.atm_decay_tracker = _FakeAtmDecayTracker()
        self.redis_service = SimpleNamespace(client=None)


@pytest.mark.asyncio
async def test_housekeeping_reuses_latest_l1_snapshot_and_dedups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "websocket_update_interval", 0.001, raising=False)

    ctr = _FakeContainer()
    state = SharedLoopState()
    state.latest_l1_snapshot = _FakeL1Snapshot()

    task = asyncio.create_task(run_housekeeping_loop(ctr, state))
    await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert ctr.option_chain_builder.fetch_calls == 0
    assert ctr.active_options_service.calls == 1
    assert ctr.active_options_service.last_chain
    row = ctr.active_options_service.last_chain[0]
    assert row["option_type"] == "CALL"
    assert row["implied_volatility"] == pytest.approx(0.22)
    assert row["delta"] == pytest.approx(0.31)
    assert row["gamma"] == pytest.approx(0.018)
    assert row["vanna"] == pytest.approx(-0.01)
