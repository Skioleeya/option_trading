from __future__ import annotations

from types import SimpleNamespace

import pytest

from shared.services.l0_runtime.services.runtime.builder import OptionChainBuilder
from shared.services.l0_runtime.services.subscription import OptionSubscriptionManager


class _FakeRuntime:
    def __init__(self) -> None:
        self.shm_path = "sentinel_shm_live"
        self.subscribed: list[str] = []

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def subscribe(self, symbols, sub_types=None) -> None:
        del sub_types
        self.subscribed = list(symbols)

    async def option_chain_info_by_date(self, symbol, check_date):
        del symbol, check_date
        return []


@pytest.mark.asyncio
async def test_subscription_manager_wait_for_writer_ready_times_out() -> None:
    mgr = OptionSubscriptionManager(
        config=SimpleNamespace(),
        quote_runtime=_FakeRuntime(),
    )
    with pytest.raises(RuntimeError, match="writer_not_ready_timeout"):
        await mgr.wait_for_writer_ready(timeout_sec=0.01)


@pytest.mark.asyncio
async def test_subscription_manager_sets_writer_ready_after_subscribe() -> None:
    mgr = OptionSubscriptionManager(
        config=SimpleNamespace(),
        quote_runtime=_FakeRuntime(),
    )
    await mgr._sync_subscriptions({"SPY.TEST.C"})
    assert mgr.writer_ready is True


@pytest.mark.asyncio
async def test_builder_await_arrow_writer_ready_surfaces_subscription_timeout() -> None:
    class _TimeoutSubMgr:
        async def wait_for_writer_ready(self, timeout_sec: float) -> None:
            del timeout_sec
            raise RuntimeError("writer_not_ready_timeout")

    builder = OptionChainBuilder.__new__(OptionChainBuilder)
    builder._services = SimpleNamespace(sub_mgr=_TimeoutSubMgr())

    with pytest.raises(RuntimeError, match="writer_not_ready_timeout"):
        await builder._await_arrow_writer_ready_or_fail(timeout_sec=0.01)
