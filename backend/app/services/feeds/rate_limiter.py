"""API Rate Limiter — Centralized Token Bucket + Concurrency Guard.

Enforces Longport's REST API limits across all callers:
- Token Bucket: 10 calls/sec (burst up to 10).
- Semaphore: max 5 concurrent in-flight requests.

Usage:
    limiter = APIRateLimiter()

    async with limiter.acquire():
        result = ctx.calc_indexes(batch, [...])
"""

from __future__ import annotations

import asyncio
import time
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class APIRateLimiter:
    """Async Token Bucket Rate Limiter with concurrency cap.

    Combines two controls:
    1. Token Bucket: ensures average call rate stays ≤ `rate` calls/sec.
    2. Semaphore: ensures at most `max_concurrent` calls are running at once.

    Both must be satisfied before a call is allowed to proceed.
    """

    def __init__(
        self,
        rate: float = 8.0,         # calls/sec — using 8 to give Longport's 10/s a safety margin
        burst: int = 8,             # max burst tokens available at any time
        max_concurrent: int = 4,    # max in-flight — using 4 to respect the 5-concurrency limit
    ) -> None:
        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._cooldown_until = 0.0

    def trigger_cooldown(self, seconds: int = 60) -> None:
        """Triggers a global quiet period across all REST callers."""
        new_until = time.monotonic() + seconds
        if new_until > self._cooldown_until:
            self._cooldown_until = new_until
            logger.warning(f"[RateLimiter] Global Cooldown triggered for {seconds}s")

    async def _wait_for_token(self) -> None:
        """Block until a token is available, then consume one."""
        while True:
            # Check global cooldown first
            now = time.monotonic()
            if now < self._cooldown_until:
                wait_sec = self._cooldown_until - now
                logger.debug(f"[RateLimiter] Enforcing cooldown, waiting {wait_sec:.1f}s")
                await asyncio.sleep(wait_sec)
                continue

            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                # Refill tokens based on elapsed time
                self._tokens = min(
                    float(self._burst),
                    self._tokens + elapsed * self._rate,
                )
                self._last_refill = now

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return  # Token acquired

            # No token available — sleep briefly and retry
            # Sleep = 1 / rate seconds to wait for the next token
            await asyncio.sleep(1.0 / self._rate)

    @asynccontextmanager
    async def acquire(self):
        """Context manager: waits for a token and acquires the semaphore.

        Usage:
            async with limiter.acquire():
                result = ctx.calc_indexes(...)
        """
        await self._wait_for_token()
        async with self._semaphore:
            yield

    def get_dynamic_interval(self) -> int:
        """Returns a suggested loop interval in seconds based on token load.
        
        - 1s: API is mostly idle (lots of tokens).
        - 2s: API is under moderate load.
        - 3s: API is heavily utilized (few tokens).
        """
        # Estimate current tokens without waiting
        now = time.monotonic()
        elapsed = now - self._last_refill
        estimated_tokens = min(
            float(self._burst),
            self._tokens + elapsed * self._rate,
        )

        if estimated_tokens >= 6.0:
            return 1
        elif estimated_tokens >= 3.0:
            return 2
        else:
            return 3
# Module-level singleton — shared across all REST callers in the same process
longport_limiter = APIRateLimiter(rate=8.0, burst=8, max_concurrent=4)
