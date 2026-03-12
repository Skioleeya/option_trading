from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from l0_ingest.feeds.feed_orchestrator import FeedOrchestrator


class _StubStore:
    def __init__(self) -> None:
        self.spot = 100.0
        self._last_spot_update = datetime.now(ZoneInfo("US/Eastern"))


class _StubSubMgr:
    def __init__(self) -> None:
        self.subscribed_symbols: set[str] = set()
        self.refresh_calls = 0

    async def refresh(self, spot: float | None, mandatory_symbols: set[str] | None = None) -> set[str]:
        del spot, mandatory_symbols
        self.refresh_calls += 1
        if self.refresh_calls == 1:
            self.subscribed_symbols = {"A", "B"}
        elif self.refresh_calls == 2:
            self.subscribed_symbols = {"A", "B", "C"}
        return set(self.subscribed_symbols)


class _StubIVSync:
    def __init__(self) -> None:
        self.bootstrap_warmup_done = False
        self.warming_up = False
        self.calls: list[set[str]] = []

    async def warm_up(self, symbols: list[str]) -> None:
        self.calls.append(set(symbols))


class _StubLimiter:
    cooldown_active = False

    def maybe_promote_to_steady(self, **kwargs) -> bool:
        del kwargs
        return False

    def cooldown_stable_for(self, seconds: float) -> bool:
        del seconds
        return True


@pytest.mark.asyncio
async def test_orchestrator_throttles_refresh_and_merges_warmup_symbols() -> None:
    store = _StubStore()
    sub_mgr = _StubSubMgr()
    iv_sync = _StubIVSync()
    limiter = _StubLimiter()
    orchestrator = FeedOrchestrator(
        quote_runtime=object(),  # not used in this test
        store=store,
        sub_mgr=sub_mgr,
        iv_sync=iv_sync,
        rate_limiter=limiter,
    )

    async def _pass_spot(spot: float | None, now: datetime) -> float | None:
        del now
        return spot

    orchestrator._refresh_spot_if_needed = _pass_spot  # type: ignore[assignment]

    class _Clock:
        now = 100.0

    clock = _Clock()
    orchestrator._monotonic = lambda: clock.now

    await orchestrator._tick()  # refresh #1 -> queue A/B
    clock.now = 105.0
    await orchestrator._tick()  # no refresh
    clock.now = 121.0
    await orchestrator._tick()  # flush A/B after 20s merge window
    clock.now = 131.0
    await orchestrator._tick()  # refresh #2 -> queue C
    clock.now = 152.0
    await orchestrator._tick()  # flush C

    assert sub_mgr.refresh_calls == 2
    assert iv_sync.calls == [{"A", "B"}, {"C"}]
