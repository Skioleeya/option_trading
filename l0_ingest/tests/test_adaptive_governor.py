"""
test_adaptive_governor.py — 4 层速率控制器测试

覆盖:
  - Token Bucket 耗尽阻塞
  - Circuit Breaker 熔断 + 恢复
  - 正常请求通过
"""
import asyncio
import pytest
import time
from l0_ingest.rate_governor.adaptive_governor import AdaptiveRateGovernor
from l0_ingest.rate_governor.priority_queue import PriorityRequestQueue, RequestPriority


class TestAdaptiveRateGovernor:

    # ── 正常流量通过 ──────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_normal_request_passes(self) -> None:
        governor = AdaptiveRateGovernor(rate_per_s=100.0, burst=10)
        results = []
        async with governor.acquire("test_endpoint", RequestPriority.QUOTE):
            results.append("ok")
        assert results == ["ok"]

    # ── Token Bucket 限流 ─────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_token_bucket_throttles_burst(self) -> None:
        """Token Bucket 应限制突发请求速率"""
        governor = AdaptiveRateGovernor(rate_per_s=10.0, burst=3, endpoint_limit=100)
        start = time.monotonic()
        for _ in range(5):
            async with governor.acquire("ep", RequestPriority.OI):
                pass
        elapsed = time.monotonic() - start
        # 5 个请求，burst=3，rate=10/s → 至少需要 0.2s
        assert elapsed >= 0.15, f"Token Bucket 应限制速率，elapsed={elapsed:.3f}s"

    # ── Circuit Breaker 熔断 ───────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self) -> None:
        """连续 3 次失败应触发熔断，后续请求被拒"""
        governor = AdaptiveRateGovernor(
            rate_per_s=100.0, burst=100,
            endpoint_limit=100,
            breaker_fails=3,
            breaker_reset_s=0.1,
        )
        # 触发 3 次 429 失败
        for _ in range(3):
            governor.record_429()

        # 熔断器打开后，acquire 应抛出 RuntimeError
        with pytest.raises(RuntimeError, match="Circuit breaker"):
            async with governor.acquire("ep"):
                pass

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovers(self) -> None:
        """熔断后等待 reset 时间自动恢复"""
        governor = AdaptiveRateGovernor(
            rate_per_s=100.0, burst=100,
            endpoint_limit=100,
            breaker_fails=3,
            breaker_reset_s=0.05,
        )
        for _ in range(3):
            governor.record_429()

        await asyncio.sleep(0.1)  # 等待重置

        # 应恢复正常
        done = False
        async with governor.acquire("ep"):
            done = True
        assert done

    # ── metrics() 统计 ────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_metrics_contains_expected_keys(self) -> None:
        governor = AdaptiveRateGovernor()
        async with governor.acquire("ep"):
            pass
        m = governor.metrics()
        assert "p50_wait_ms" in m
        assert "p99_wait_ms" in m
        assert "token_bucket_tokens" in m
        assert "rejected_total" in m
        assert "breaker_open" in m


class TestPriorityRequestQueue:

    @pytest.mark.asyncio
    async def test_put_and_get(self) -> None:
        q = PriorityRequestQueue(maxsize=10)
        await q.put("ep", payload={"x": 1}, priority=RequestPriority.OI)
        req = await q.get(timeout=1.0)
        assert req is not None
        assert req.endpoint == "ep"

    @pytest.mark.asyncio
    async def test_priority_ordering(self) -> None:
        """QUOTE 应比 HISTORY 先出队"""
        q = PriorityRequestQueue(maxsize=10)
        await q.put("history", priority=RequestPriority.HISTORY)
        await q.put("quote",   priority=RequestPriority.QUOTE)
        await q.put("oi",      priority=RequestPriority.OI)

        r1 = await q.get(timeout=1.0)
        r2 = await q.get(timeout=1.0)
        r3 = await q.get(timeout=1.0)

        assert r1.endpoint == "quote"
        assert r2.endpoint == "oi"
        assert r3.endpoint == "history"

    @pytest.mark.asyncio
    async def test_full_queue_rejects(self) -> None:
        q = PriorityRequestQueue(maxsize=2)
        assert await q.put("a", priority=RequestPriority.HISTORY)
        assert await q.put("b", priority=RequestPriority.HISTORY)
        # 第三个应被拒绝
        assert not await q.put("c", priority=RequestPriority.HISTORY)
        assert q.rejected_count == 1
