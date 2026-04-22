from __future__ import annotations

import pytest

from shared.services.l0_runtime.services.subscription import (
    OptionSubscriptionManager,
    UNDERLYING_SPOT_SYMBOL,
)


class _FakeRuntime:
    shm_path = "test_shm"

    def __init__(self) -> None:
        self.subscriptions: list[tuple[list[str], list[object] | None]] = []

    async def connect(self) -> None:
        return None

    async def subscribe(self, symbols, sub_types=None) -> None:
        self.subscriptions.append((list(symbols), sub_types))


@pytest.mark.asyncio
async def test_refresh_always_subscribes_underlying_spot_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _FakeRuntime()
    manager = OptionSubscriptionManager(config=object(), quote_runtime=runtime)

    async def _fake_collect_core_symbols(spot: float | None) -> set[str]:
        assert spot == 706.5
        return {"SPY260421C00707000.US"}

    monkeypatch.setattr(manager, "_collect_core_symbols", _fake_collect_core_symbols)

    target = await manager.refresh(706.5)

    assert UNDERLYING_SPOT_SYMBOL in target
    assert UNDERLYING_SPOT_SYMBOL in manager.subscribed_symbols
    assert runtime.subscriptions
    assert UNDERLYING_SPOT_SYMBOL in runtime.subscriptions[-1][0]
