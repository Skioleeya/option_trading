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

LONGPORT_MAX_CALLS_PER_SEC = 10.0
LONGPORT_MAX_REQUEST_BURST = 10
LONGPORT_MAX_CONCURRENT = 5


class APIRateLimiter:
    """Async Dual-Token Bucket Rate Limiter.
    
    Controls:
    1. Request Frequency (Reqs/Sec): Max 10/s.
    2. Symbol Volume (Symbols/Min): conservative cap (default 240/min) to avoid 301607.
    3. Concurrency (In-flight): Max 5.
    """

    def __init__(
        self,
        rate: float = 8.0,            # requests per second
        burst: int = 10,              # max request burst
        max_concurrent: int = 4,      # max in-flight
        symbol_rate: float = 240.0,   # symbols per 60 seconds (conservative startup quota)
        symbol_burst: int = 50        # max symbol burst
    ) -> None:
        requested_rate = float(rate)
        requested_burst = int(burst)
        requested_concurrency = int(max_concurrent)

        self._rate = max(0.1, min(requested_rate, LONGPORT_MAX_CALLS_PER_SEC))
        self._burst = max(1, min(requested_burst, LONGPORT_MAX_REQUEST_BURST))
        self._max_concurrent = max(1, min(requested_concurrency, LONGPORT_MAX_CONCURRENT))
        if (
            self._rate != requested_rate
            or self._burst != requested_burst
            or self._max_concurrent != requested_concurrency
        ):
            logger.warning(
                "[RateLimiter] Requested limits (rate=%.2f, burst=%d, concurrent=%d) "
                "were clamped to official Quote API caps (rate=%.2f, burst=%d, concurrent=%d).",
                requested_rate,
                requested_burst,
                requested_concurrency,
                self._rate,
                self._burst,
                self._max_concurrent,
            )

        safe_symbol_rate = max(float(symbol_rate), 1.0)
        safe_symbol_burst = max(int(symbol_burst), 1)
        self._tokens = float(self._burst)
        
        self._symbol_rate_per_sec = safe_symbol_rate / 60.0
        self._symbol_burst = safe_symbol_burst
        self._symbol_tokens = float(self._symbol_burst)
        
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
        self._cooldown_until = 0.0

    @property
    def tokens(self) -> float:
        return self._tokens

    @property
    def symbol_tokens(self) -> float:
        return self._symbol_tokens

    @property
    def max_symbol_weight(self) -> int:
        return self._symbol_burst

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @property
    def max_calls_per_sec(self) -> float:
        return self._rate

    @property
    def cooldown_active(self) -> bool:
        return time.monotonic() < self._cooldown_until

    def trigger_cooldown(self, seconds: int = 60) -> None:
        """Triggers a global quiet period."""
        new_until = time.monotonic() + seconds
        if new_until > self._cooldown_until:
            self._cooldown_until = new_until
            logger.warning(f"[RateLimiter] Global Cooldown triggered for {seconds}s")

    async def _wait_for_tokens(self, num_symbols: int = 1) -> None:
        """Block until both request and symbol tokens are available."""
        while True:
            now = time.monotonic()
            if now < self._cooldown_until:
                wait_sec = self._cooldown_until - now
                logger.debug(f"[RateLimiter] Cooldown active, waiting {wait_sec:.1f}s")
                await asyncio.sleep(wait_sec)
                async with self._lock:
                    self._tokens = 1.0 # Reset to 1 to prevent burst after cooldown
                    self._symbol_tokens = 0.0
                    self._last_refill = time.monotonic()
                continue

            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                
                # Refill Req tokens
                self._tokens = min(float(self._burst), self._tokens + elapsed * self._rate)
                # Refill Symbol tokens
                self._symbol_tokens = min(float(self._symbol_burst), 
                                        self._symbol_tokens + elapsed * self._symbol_rate_per_sec)
                self._last_refill = now

                if self._tokens >= 1.0 and self._symbol_tokens >= num_symbols:
                    self._tokens -= 1.0
                    self._symbol_tokens -= num_symbols
                    return 
                
                # Calculate sleep time based on which token is missing
                needed_req = 0.0 if self._tokens >= 1.0 else (1.0 - self._tokens) / self._rate
                needed_sym = 0.0 if self._symbol_tokens >= num_symbols else (num_symbols - self._symbol_tokens) / self._symbol_rate_per_sec
                sleep_time = max(needed_req, needed_sym, 0.1)

            logger.debug(f"[RateLimiter] Waiting {sleep_time:.2f}s for tokens (reqs={self._tokens:.1f}, syms={self._symbol_tokens:.1f})")
            await asyncio.sleep(sleep_time)

    @asynccontextmanager
    async def acquire(self, weight: int = 1):
        """wait for tokens based on request weight (number of symbols)."""
        normalized_weight = max(int(weight), 1)
        if normalized_weight > self._symbol_burst:
            raise ValueError(
                f"acquire(weight={normalized_weight}) exceeds symbol_burst={self._symbol_burst}; "
                "split request into smaller batches"
            )
        await self._wait_for_tokens(normalized_weight)
        async with self._semaphore:
            yield

    def get_dynamic_interval(self) -> int:
        return 1

from shared.config import settings

longport_limiter = APIRateLimiter(
    rate=settings.longport_api_rate_limit,
    burst=settings.longport_api_burst,
    max_concurrent=settings.longport_api_max_concurrent,
    symbol_rate=settings.longport_symbol_rate_per_min,
    symbol_burst=settings.longport_symbol_burst,
)
