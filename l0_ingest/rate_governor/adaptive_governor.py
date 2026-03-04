"""
AdaptiveRateGovernor — 4 层自适应速率控制器

Layer 1: Token Bucket           — 全局 burst 控制
Layer 2: Sliding Window         — per-endpoint 请求频率
Layer 3: Circuit Breaker        — 连续 429 触发熔断
Layer 4: Priority Queue         — 优先级路由

使用方式:
    governor = AdaptiveRateGovernor()
    async with governor.acquire("option_chain", priority=RequestPriority.OI):
        response = await api.get_option_chain(...)
"""
from __future__ import annotations

import asyncio
import time
import logging
from collections import deque
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Deque, Dict, Optional

from .priority_queue import RequestPriority

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
#  Layer 1: Token Bucket
# ─────────────────────────────────────────────────────────────────────
class _TokenBucket:
    """令牌桶（线程安全 via asyncio event loop 单线程）"""

    def __init__(self, rate: float, burst: int) -> None:
        self.rate = rate        # 每秒补充令牌数
        self.burst = burst      # 最大桶容量
        self._tokens = float(burst)
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_refill = now

    def consume(self) -> bool:
        self._refill()
        if self._tokens >= 1:
            self._tokens -= 1
            return True
        return False

    async def wait_for_token(self) -> None:
        while not self.consume():
            await asyncio.sleep(1.0 / self.rate)


# ─────────────────────────────────────────────────────────────────────
#  Layer 2: Sliding Window per-endpoint
# ─────────────────────────────────────────────────────────────────────
class _SlidingWindow:
    def __init__(self, limit: int, window_s: float = 1.0) -> None:
        self.limit = limit
        self.window_s = window_s
        self._timestamps: Deque[float] = deque()

    def check(self) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_s
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
        if len(self._timestamps) < self.limit:
            self._timestamps.append(now)
            return True
        return False

    async def wait(self) -> None:
        while not self.check():
            await asyncio.sleep(0.05)


# ─────────────────────────────────────────────────────────────────────
#  Layer 3: Circuit Breaker
# ─────────────────────────────────────────────────────────────────────
class _CircuitBreaker:
    def __init__(self, consecutive_fails: int = 3, reset_s: float = 30.0) -> None:
        self.consecutive_fails = consecutive_fails
        self.reset_s = reset_s
        self._fails: int = 0
        self._open_until: float = 0.0

    @property
    def is_open(self) -> bool:
        return time.monotonic() < self._open_until

    def record_success(self) -> None:
        self._fails = 0

    def record_failure(self) -> None:
        self._fails += 1
        if self._fails >= self.consecutive_fails:
            self._open_until = time.monotonic() + self.reset_s
            logger.warning(
                f"Circuit breaker OPEN for {self.reset_s}s "
                f"after {self._fails} consecutive failures"
            )
            self._fails = 0


# ─────────────────────────────────────────────────────────────────────
#  主类: AdaptiveRateGovernor
# ─────────────────────────────────────────────────────────────────────
class AdaptiveRateGovernor:
    """
    4 层自适应速率控制器。

    参数:
        rate_per_s      : Token Bucket 速率（默认 8 req/s）
        burst           : Token Bucket 最大 burst（默认 8）
        endpoint_limit  : Sliding Window per-endpoint 限制（默认 5 req/s）
        breaker_fails   : Circuit Breaker 连续失败阈值（默认 3）
        breaker_reset_s : Circuit Breaker 重置秒数（默认 30）
    """

    def __init__(
        self,
        rate_per_s: float = 8.0,
        burst: int = 8,
        endpoint_limit: int = 5,
        breaker_fails: int = 3,
        breaker_reset_s: float = 30.0,
    ) -> None:
        self._bucket = _TokenBucket(rate_per_s, burst)
        self._endpoint_limit = endpoint_limit
        self._windows: Dict[str, _SlidingWindow] = {}
        self._breaker = _CircuitBreaker(breaker_fails, breaker_reset_s)

        # 延迟度量
        self._latencies: Deque[float] = deque(maxlen=1000)
        self._rejected: int = 0

    @asynccontextmanager
    async def acquire(
        self,
        endpoint: str = "default",
        priority: RequestPriority = RequestPriority.OI,
    ) -> AsyncGenerator[None, None]:
        """
        异步上下文管理器：获取请求许可。

        用法:
            async with governor.acquire("snapshot_endpoint", priority=RequestPriority.QUOTE):
                data = await api.get_snapshot()
        """
        # Layer 3: Circuit Breaker
        if self._breaker.is_open:
            self._rejected += 1
            raise RuntimeError("Circuit breaker is open — request rejected")

        # Layer 4: Priority (隐含在 acquire 调用优先级上，调度由上层 PriorityQueue 保证)
        # 此处直接限流，不再重复入队

        # Layer 1: Token Bucket
        start = time.monotonic()
        await self._bucket.wait_for_token()

        # Layer 2: Sliding Window
        if endpoint not in self._windows:
            self._windows[endpoint] = _SlidingWindow(
                self._endpoint_limit, window_s=1.0
            )
        await self._windows[endpoint].wait()

        try:
            yield
            self._breaker.record_success()
        except Exception as exc:
            # 检测 429
            if "429" in str(exc) or "rate limit" in str(exc).lower():
                self._breaker.record_failure()
            raise
        finally:
            self._latencies.append((time.monotonic() - start) * 1000)

    def record_429(self) -> None:
        """手动报告 429 错误（由调用方在捕获异常后调用）"""
        self._breaker.record_failure()

    def metrics(self) -> Dict[str, float]:
        """实时统计指标"""
        lats = sorted(self._latencies) if self._latencies else [0.0]
        n = len(lats)
        p50 = lats[int(0.50 * n)] if n else 0.0
        p99 = lats[int(0.99 * n)] if n else 0.0
        return {
            "p50_wait_ms": p50,
            "p99_wait_ms": p99,
            "token_bucket_tokens": self._bucket._tokens,
            "rejected_total": self._rejected,
            "breaker_open": float(self._breaker.is_open),
        }
