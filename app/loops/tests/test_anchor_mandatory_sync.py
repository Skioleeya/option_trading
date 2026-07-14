from __future__ import annotations

from typing import Any

import pytest

from app.loops.anchor_mandatory_sync import (
    sync_anchor_mandatory_symbols,
    update_atm_decay_and_sync_anchor,
)
from app.loops.shared_state import SharedLoopState


class _FakeAtmDecayTracker:
    def __init__(self, symbols: set[str]) -> None:
        self.symbols = set(symbols)
        self.update_calls = 0

    def get_anchor_symbols(self) -> set[str]:
        return set(self.symbols)

    async def update(self, chain: Any, spot: Any) -> dict[str, Any]:
        del chain, spot
        self.update_calls += 1
        return {"timestamp": "2026-07-14T11:04:00-04:00", "call_pct": 0.1}


class _FakeBuilder:
    def __init__(self) -> None:
        self.last_mandatory_symbols: set[str] | None = None
        self.refresh_calls: list[float] = []
        self.repair_calls: list[set[str]] = []

    def set_mandatory_symbols(self, symbols: set[str]) -> None:
        self.last_mandatory_symbols = set(symbols)

    async def refresh_subscriptions_once(self, spot: float | None) -> set[str]:
        self.refresh_calls.append(float(spot or 0.0))
        return {"SPY.US", *(self.last_mandatory_symbols or set())}

    async def repair_symbols_once(self, symbols: set[str], *, log_prefix: str) -> int:
        assert log_prefix == "[AnchorMandatorySync]"
        self.repair_calls.append(set(symbols))
        return len(symbols)


class _FakeContainer:
    def __init__(self, symbols: set[str]) -> None:
        self.atm_decay_tracker = _FakeAtmDecayTracker(symbols)
        self.option_chain_builder = _FakeBuilder()


@pytest.mark.asyncio
async def test_anchor_change_sets_mandatory_refreshes_and_repairs() -> None:
    ctr = _FakeContainer({"SPY.C752", "SPY.P752"})
    state = SharedLoopState()

    result = await sync_anchor_mandatory_symbols(
        ctr,
        state,
        spot=749.66,
        refresh_on_change=True,
        reason="compute_tick",
    )

    assert result.changed is True
    assert result.refreshed is True
    assert result.repaired_count == 2
    assert ctr.option_chain_builder.last_mandatory_symbols == {"SPY.C752", "SPY.P752"}
    assert ctr.option_chain_builder.refresh_calls == [pytest.approx(749.66)]
    assert ctr.option_chain_builder.repair_calls == [{"SPY.C752", "SPY.P752"}]
    assert state.last_anchor_mandatory_symbols == {"SPY.C752", "SPY.P752"}
    assert state.anchor_mandatory_sync_updates == 1


@pytest.mark.asyncio
async def test_unchanged_anchor_sets_mandatory_without_refresh_churn() -> None:
    ctr = _FakeContainer({"SPY.C752", "SPY.P752"})
    state = SharedLoopState()
    state.record_anchor_mandatory_sync({"SPY.C752", "SPY.P752"}, reason="seed")

    result = await sync_anchor_mandatory_symbols(
        ctr,
        state,
        spot=749.66,
        refresh_on_change=True,
        reason="duplicate_snapshot",
    )

    assert result.changed is False
    assert result.refreshed is False
    assert ctr.option_chain_builder.last_mandatory_symbols == {"SPY.C752", "SPY.P752"}
    assert ctr.option_chain_builder.refresh_calls == []
    assert ctr.option_chain_builder.repair_calls == []
    assert state.anchor_mandatory_sync_updates == 1


@pytest.mark.asyncio
async def test_invalid_spot_still_sets_mandatory_but_skips_refresh() -> None:
    ctr = _FakeContainer({"SPY.C752", "SPY.P752"})
    state = SharedLoopState()

    result = await sync_anchor_mandatory_symbols(
        ctr,
        state,
        spot=0.0,
        refresh_on_change=True,
        reason="compute_tick",
    )

    assert result.changed is True
    assert result.refreshed is False
    assert ctr.option_chain_builder.last_mandatory_symbols == {"SPY.C752", "SPY.P752"}
    assert ctr.option_chain_builder.refresh_calls == []
    assert ctr.option_chain_builder.repair_calls == []


@pytest.mark.asyncio
async def test_atm_update_path_syncs_anchor_after_tracker_update() -> None:
    ctr = _FakeContainer({"SPY.C754", "SPY.P754"})
    state = SharedLoopState()

    payload = await update_atm_decay_and_sync_anchor(
        ctr,
        state,
        [{"symbol": "SPY.C754"}],
        749.66,
        reason="duplicate_snapshot",
    )

    assert payload["timestamp"] == "2026-07-14T11:04:00-04:00"
    assert ctr.atm_decay_tracker.update_calls == 1
    assert ctr.option_chain_builder.last_mandatory_symbols == {"SPY.C754", "SPY.P754"}
    assert ctr.option_chain_builder.refresh_calls == [pytest.approx(749.66)]
