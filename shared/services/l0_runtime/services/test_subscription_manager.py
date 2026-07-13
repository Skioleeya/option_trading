from __future__ import annotations

import pytest

from shared.services.l0_runtime.services.subscription import (
    OptionSubscriptionManager,
    UNDERLYING_SPOT_SYMBOL,
)
from shared.services.l0_runtime.services.subscription.selection import SubscriptionSelection
from shared.services.l0_runtime.services._native_helpers import enforce_cap_native, select_targets_native


class _FakeRuntime:
    shm_path = "test_shm"

    def __init__(self) -> None:
        self.subscriptions: list[tuple[list[str], list[object] | None]] = []

    async def connect(self) -> None:
        return None

    async def subscribe(self, symbols, sub_types=None) -> None:
        self.subscriptions.append((list(symbols), sub_types))

    async def disconnect(self) -> None:
        return None


@pytest.mark.asyncio
async def test_refresh_always_subscribes_underlying_spot_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _FakeRuntime()
    manager = OptionSubscriptionManager(config=object(), quote_runtime=runtime)

    async def _fake_collect_core_symbols(
        spot: float | None,
        *,
        chain_snapshot: list[dict[str, object]],
        first_source_seen_at_mono: float | None,
        now_mono: float,
    ) -> SubscriptionSelection:
        assert spot == 706.5
        assert chain_snapshot == []
        assert first_source_seen_at_mono is None
        assert now_mono > 0.0
        return SubscriptionSelection(
            targets={"SPY260421C00707000.US"},
            symbol_to_strike={"SPY260421C00707000.US": 707.0},
            priority_by_symbol={"SPY260421C00707000.US": 0},
            diagnostics={
                "phase": "initial",
                "call_phase": "initial",
                "put_phase": "initial",
                "call_core_range": (677.0, 737.0),
                "put_core_range": (677.0, 737.0),
                "call_core_step_range": (0, 60),
                "put_core_step_range": (0, 60),
            },
        )

    monkeypatch.setattr(manager, "_collect_core_symbols", _fake_collect_core_symbols)

    target = await manager.refresh(706.5)

    assert UNDERLYING_SPOT_SYMBOL in target
    assert UNDERLYING_SPOT_SYMBOL in manager.subscribed_symbols
    assert runtime.subscriptions
    assert UNDERLYING_SPOT_SYMBOL in runtime.subscriptions[-1][0]


def _chain_rows(start: int = 670, stop: int = 740) -> list[dict[str, object]]:
    return [
        {
            "price": float(strike),
            "call_symbol": f"SPY260710C{strike:08d}.US",
            "put_symbol": f"SPY260710P{strike:08d}.US",
        }
        for strike in range(start, stop + 1)
    ]


def test_native_selector_stays_initial_before_first_source_and_lock_window() -> None:
    rows = _chain_rows()
    for first_seen, now_mono in ((None, 700.0), (100.0, 699.0)):
        native = select_targets_native(
            rows,
            chain_snapshot=[],
            spot=705.0,
            first_source_seen_at_mono=first_seen,
            now_mono=now_mono,
            initial_steps=30,
            dynamic_after_sec=600.0,
            coverage=0.90,
            core_buffer_steps=5,
        )
        assert native["phase"] == "initial"
        assert native["call_phase"] == "initial"
        assert native["put_phase"] == "initial"
        assert native["call_core_range"] == (675.0, 735.0)
        assert native["put_core_range"] == (675.0, 735.0)
        assert native["call_core_step_range"] == (5, 65)
        assert native["put_core_step_range"] == (5, 65)


def test_native_selector_dynamic_ranges_and_sentinels() -> None:
    rows = _chain_rows()
    snapshot = [
        {"symbol": "SPY260710C00000700.US", "strike": 700.0, "opt_type": "C", "volume": 100},
        {"symbol": "SPY260710C00000701.US", "strike": 701.0, "opt_type": "C", "volume": 100},
        {"symbol": "SPY260710C00000702.US", "strike": 702.0, "opt_type": "C", "volume": 800},
        {"symbol": "SPY260710P00000710.US", "strike": 710.0, "opt_type": "P", "volume": 900},
        {"symbol": "SPY260710P00000740.US", "strike": 740.0, "opt_type": "P", "open_interest": 9999},
    ]

    native = select_targets_native(
        rows,
        chain_snapshot=snapshot,
        spot=705.0,
        first_source_seen_at_mono=0.0,
        now_mono=600.0,
        initial_steps=30,
        dynamic_after_sec=600.0,
        coverage=0.90,
        core_buffer_steps=5,
    )

    assert native["phase"] == "dynamic"
    assert native["call_phase"] == "dynamic"
    assert native["put_phase"] == "dynamic"
    assert native["call_raw_range"] == (701.0, 702.0)
    assert native["call_core_range"] == (696.0, 707.0)
    assert native["call_core_step_range"] == (26, 37)
    assert native["put_raw_range"] == (710.0, 710.0)
    assert native["put_core_range"] == (705.0, 715.0)
    assert native["put_core_step_range"] == (35, 45)
    assert "SPY260710P00000740.US" in native["sentinel_targets"]


def test_native_selector_side_guard_keeps_initial_when_volume_missing() -> None:
    rows = _chain_rows()
    snapshot = [
        {"symbol": "SPY260710P00000710.US", "strike": 710.0, "opt_type": "P", "volume": 900},
    ]

    native = select_targets_native(
        rows,
        chain_snapshot=snapshot,
        spot=705.0,
        first_source_seen_at_mono=0.0,
        now_mono=600.0,
        initial_steps=30,
        dynamic_after_sec=600.0,
        coverage=0.90,
        core_buffer_steps=5,
    )

    assert native["phase"] == "dynamic"
    assert native["call_phase"] == "dynamic_guard_initial"
    assert native["put_phase"] == "dynamic"
    assert native["call_raw_range"] is None
    assert native["call_core_range"] == (675.0, 735.0)
    assert native["call_core_step_range"] == (5, 65)
    assert native["put_raw_range"] == (710.0, 710.0)


@pytest.mark.asyncio
async def test_dynamic_small_shift_requires_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _FakeRuntime()
    manager = OptionSubscriptionManager(config=object(), quote_runtime=runtime)
    selections = [
        SubscriptionSelection({"A"}, {"A": 700.0}, {"A": 2}, {"phase": "initial", "call_core_step_range": (0, 60), "put_core_step_range": (0, 60)}),
        SubscriptionSelection({"B"}, {"B": 701.0}, {"B": 2}, {"phase": "dynamic", "call_core_step_range": (10, 20), "put_core_step_range": (10, 20)}),
        SubscriptionSelection({"C"}, {"C": 702.0}, {"C": 2}, {"phase": "dynamic", "call_core_step_range": (11, 20), "put_core_step_range": (10, 21)}),
        SubscriptionSelection({"C"}, {"C": 702.0}, {"C": 2}, {"phase": "dynamic", "call_core_step_range": (11, 20), "put_core_step_range": (10, 21)}),
    ]

    async def _fake_collect_core_symbols(*_: object, **__: object) -> SubscriptionSelection:
        return selections.pop(0)

    monkeypatch.setattr(manager, "_collect_core_symbols", _fake_collect_core_symbols)

    assert await manager.refresh(705.0, now_mono=1.0) == {"A", UNDERLYING_SPOT_SYMBOL}
    assert await manager.refresh(705.0, now_mono=600.0) == {"B", UNDERLYING_SPOT_SYMBOL}
    assert await manager.refresh(705.0, now_mono=660.0) == {"B", UNDERLYING_SPOT_SYMBOL}
    assert await manager.refresh(705.0, now_mono=720.0) == {"C", UNDERLYING_SPOT_SYMBOL}
    assert len(runtime.subscriptions) == 3


@pytest.mark.asyncio
async def test_refresh_resubscribes_same_targets_after_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _FakeRuntime()
    manager = OptionSubscriptionManager(config=object(), quote_runtime=runtime)

    async def _fake_collect_core_symbols(*_: object, **__: object) -> SubscriptionSelection:
        return SubscriptionSelection(
            {"A"},
            {"A": 700.0},
            {"A": 2},
            {"phase": "initial", "call_core_step_range": (0, 10), "put_core_step_range": (0, 10)},
        )

    monkeypatch.setattr(manager, "_collect_core_symbols", _fake_collect_core_symbols)

    await manager.refresh(705.0, now_mono=1.0)
    await manager.stop()
    await manager.refresh(705.0, now_mono=2.0)

    assert len(runtime.subscriptions) == 2
    assert manager.writer_ready


def test_cap_trim_keeps_mandatory_and_near_spot_before_core() -> None:
    native = enforce_cap_native(
        target_symbols={"CORE1", "CORE2", "NEAR", "MAND"},
        mandatory_symbols={"MAND"},
        subscription_cap=3,
        symbol_to_strike={"CORE1": 705.0, "CORE2": 704.0, "NEAR": 720.0, "MAND": 740.0},
        symbol_priority={"CORE1": 2, "CORE2": 2, "NEAR": 1, "MAND": 9},
        spot=705.0,
    )

    assert "MAND" in native["kept"]
    assert "NEAR" in native["kept"]
    assert len(native["kept"]) == 3
