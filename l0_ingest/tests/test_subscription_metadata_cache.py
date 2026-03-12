from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date

import pytest

from l0_ingest.subscription_manager import OptionSubscriptionManager


class _StubLimiter:
    def __init__(self) -> None:
        self.weights: list[int] = []

    @asynccontextmanager
    async def acquire(self, weight: int = 1):
        self.weights.append(weight)
        yield


class _StubRuntime:
    def __init__(self) -> None:
        self.calls = 0

    async def option_chain_info_by_date(self, symbol: str, expiry: date):
        del symbol, expiry
        self.calls += 1
        return []


@pytest.mark.asyncio
async def test_option_chain_metadata_cache_respects_ttl_and_weight() -> None:
    mgr = OptionSubscriptionManager.__new__(OptionSubscriptionManager)
    mgr._runtime = _StubRuntime()
    mgr._limiter = _StubLimiter()
    mgr._metadata_weight = 5
    mgr._metadata_ttl_sec = 30.0
    mgr._metadata_cache = {}
    mgr._metadata_cache_hits = 0
    mgr._metadata_cache_misses = 0

    d = date(2026, 3, 12)
    first = await mgr._option_chain_info_by_date_cached("SPY.US", d)
    second = await mgr._option_chain_info_by_date_cached("SPY.US", d)

    assert first == []
    assert second == []
    assert mgr._runtime.calls == 1
    assert mgr._limiter.weights == [5]
    assert mgr._metadata_cache_hits == 1
    assert mgr._metadata_cache_misses == 1
    assert mgr.metadata_cache_hit_rate == pytest.approx(0.5)

    cached_at, cached_rows = mgr._metadata_cache[d]
    mgr._metadata_cache[d] = (cached_at - 31.0, cached_rows)
    await mgr._option_chain_info_by_date_cached("SPY.US", d)

    assert mgr._runtime.calls == 2
    assert mgr._limiter.weights == [5, 5]
    assert mgr._metadata_cache_misses == 2
