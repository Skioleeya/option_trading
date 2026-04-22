"""Runtime providers for the L0 V2 source layer."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Literal

from longport.openapi import Config

from shared.config import settings
from ._native_helpers import build_gateway_config_native
from .bootstrap import (
    _build_openapi_endpoint_profiles,
    _longport_config_kwargs,
    _startup_connectivity_probe,
)
from .ipc import ArrowIpcReader
from .quote_runtime import L0QuoteRuntime, RustQuoteRuntime

logger = logging.getLogger(__name__)

LONGPORT_MAX_CALLS_PER_SEC = 10.0
LONGPORT_MAX_REQUEST_BURST = 10
LONGPORT_MAX_CONCURRENT = 5


class APIRateLimiter:
    """Async dual-token-bucket limiter for LongPort request and symbol budgets."""

    def __init__(
        self,
        rate: float = 10.0,
        burst: int = 10,
        max_concurrent: int = 5,
        symbol_rate: float = 240.0,
        symbol_burst: int = 50,
        startup_symbol_rate: float | None = None,
        startup_symbol_burst: int | None = None,
        steady_symbol_rate: float | None = None,
        steady_symbol_burst: int | None = None,
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

        steady_rate = float(symbol_rate if steady_symbol_rate is None else steady_symbol_rate)
        steady_burst = int(symbol_burst if steady_symbol_burst is None else steady_symbol_burst)
        startup_rate = float(steady_rate if startup_symbol_rate is None else startup_symbol_rate)
        startup_burst = int(steady_burst if startup_symbol_burst is None else startup_symbol_burst)

        self._startup_symbol_rate_per_sec = max(startup_rate, 1.0) / 60.0
        self._startup_symbol_burst = max(startup_burst, 1)
        self._steady_symbol_rate_per_sec = max(steady_rate, 1.0) / 60.0
        self._steady_symbol_burst = max(steady_burst, 1)

        self._tokens = float(self._burst)
        self._created_at = time.monotonic()
        self._symbol_profile: Literal["startup", "steady"] = "startup"
        self._symbol_rate_per_sec = self._startup_symbol_rate_per_sec
        self._symbol_burst = self._startup_symbol_burst
        self._symbol_tokens = float(self._symbol_burst)
        self._last_refill = self._created_at
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
        self._cooldown_until = 0.0
        self._last_cooldown_ts = self._created_at
        self._profile_entered_at = self._created_at
        self._cooldown_hits: deque[float] = deque()

    def _prune_cooldown_hits(self, now: float | None = None) -> None:
        current = time.monotonic() if now is None else now
        cutoff = current - 300.0
        while self._cooldown_hits and self._cooldown_hits[0] < cutoff:
            self._cooldown_hits.popleft()

    def _switch_symbol_profile(self, profile: Literal["startup", "steady"]) -> None:
        if profile == self._symbol_profile:
            return
        if profile == "steady":
            self._symbol_profile = "steady"
            self._symbol_rate_per_sec = self._steady_symbol_rate_per_sec
            self._symbol_burst = self._steady_symbol_burst
        else:
            self._symbol_profile = "startup"
            self._symbol_rate_per_sec = self._startup_symbol_rate_per_sec
            self._symbol_burst = self._startup_symbol_burst
        self._symbol_tokens = min(self._symbol_tokens, float(self._symbol_burst))
        self._profile_entered_at = time.monotonic()
        logger.info(
            "[RateLimiter] Symbol profile switched to %s (rate/min=%.1f burst=%d)",
            self._symbol_profile,
            self._symbol_rate_per_sec * 60.0,
            self._symbol_burst,
        )

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
    def symbol_profile(self) -> str:
        return self._symbol_profile

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @property
    def max_calls_per_sec(self) -> float:
        return self._rate

    @property
    def cooldown_active(self) -> bool:
        return time.monotonic() < self._cooldown_until

    @property
    def cooldown_hits_5m(self) -> int:
        now = time.monotonic()
        self._prune_cooldown_hits(now)
        return len(self._cooldown_hits)

    def seconds_since_last_cooldown(self) -> float:
        return max(0.0, time.monotonic() - self._last_cooldown_ts)

    def cooldown_stable_for(self, seconds: float) -> bool:
        return (not self.cooldown_active) and self.seconds_since_last_cooldown() >= max(seconds, 0.0)

    def force_startup_profile(self, reason: str = "manual") -> bool:
        if self._symbol_profile == "startup":
            return False
        self._switch_symbol_profile("startup")
        logger.warning("[RateLimiter] Startup profile enforced: reason=%s", reason)
        return True

    def maybe_promote_to_steady(
        self,
        *,
        warmup_done: bool,
        warming_up: bool,
        stable_for_sec: float = 120.0,
    ) -> bool:
        if self._symbol_profile == "steady":
            return False
        if not warmup_done or warming_up or self.cooldown_active:
            return False
        now = time.monotonic()
        stable_since = max(self._profile_entered_at, self._last_cooldown_ts)
        if (now - stable_since) < max(0.0, stable_for_sec):
            return False
        self._switch_symbol_profile("steady")
        return True

    def trigger_cooldown(self, seconds: int = 60) -> None:
        now = time.monotonic()
        new_until = now + seconds
        if new_until > self._cooldown_until:
            self._cooldown_until = new_until
            self._last_cooldown_ts = now
            self._cooldown_hits.append(now)
            self._prune_cooldown_hits(now)
            self.force_startup_profile(reason="cooldown")
            logger.warning("[RateLimiter] Global Cooldown triggered for %ss", seconds)

    async def _wait_for_tokens(self, num_symbols: int = 1) -> None:
        while True:
            now = time.monotonic()
            if now < self._cooldown_until:
                wait_sec = self._cooldown_until - now
                logger.debug("[RateLimiter] Cooldown active, waiting %.1fs", wait_sec)
                await asyncio.sleep(wait_sec)
                async with self._lock:
                    self._tokens = 1.0
                    self._symbol_tokens = 0.0
                    self._last_refill = time.monotonic()
                continue

            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(float(self._burst), self._tokens + elapsed * self._rate)
                self._symbol_tokens = min(
                    float(self._symbol_burst),
                    self._symbol_tokens + elapsed * self._symbol_rate_per_sec,
                )
                self._last_refill = now

                if self._tokens >= 1.0 and self._symbol_tokens >= num_symbols:
                    self._tokens -= 1.0
                    self._symbol_tokens -= num_symbols
                    return

                needed_req = 0.0 if self._tokens >= 1.0 else (1.0 - self._tokens) / self._rate
                needed_sym = (
                    0.0
                    if self._symbol_tokens >= num_symbols
                    else (num_symbols - self._symbol_tokens) / self._symbol_rate_per_sec
                )
                sleep_time = max(needed_req, needed_sym, 0.1)

            logger.debug(
                "[RateLimiter] Waiting %.2fs for tokens (reqs=%.1f, syms=%.1f)",
                sleep_time,
                self._tokens,
                self._symbol_tokens,
            )
            await asyncio.sleep(sleep_time)

    @asynccontextmanager
    async def acquire(self, weight: int = 1):
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


longport_limiter = APIRateLimiter(
    rate=settings.longport_api_rate_limit,
    burst=settings.longport_api_burst,
    max_concurrent=settings.longport_api_max_concurrent,
    symbol_rate=settings.longport_steady_symbol_rate_per_min,
    symbol_burst=settings.longport_steady_symbol_burst,
    startup_symbol_rate=settings.longport_startup_symbol_rate_per_min,
    startup_symbol_burst=settings.longport_startup_symbol_burst,
    steady_symbol_rate=settings.longport_steady_symbol_rate_per_min,
    steady_symbol_burst=settings.longport_steady_symbol_burst,
)


@dataclass(frozen=True)
class RuntimeBundle:
    config: Config
    quote_runtime: L0QuoteRuntime
    rate_limiter: APIRateLimiter


def _build_rust_gateway_config(cfg: object) -> dict[str, object]:
    return build_gateway_config_native(
        app_key=str(getattr(cfg, "longport_app_key")),
        app_secret=str(getattr(cfg, "longport_app_secret")),
        access_token=str(getattr(cfg, "longport_access_token")),
        http_url=getattr(cfg, "longport_http_url", None),
        quote_ws_url=getattr(cfg, "longport_quote_ws_url", None),
        trade_ws_url=getattr(cfg, "longport_trade_ws_url", None),
        language=getattr(cfg, "longport_language", None),
        enable_overnight=bool(getattr(cfg, "longport_enable_overnight", False)),
    )


def build_runtime_bundle() -> RuntimeBundle:
    endpoint_profiles = _build_openapi_endpoint_profiles(settings)
    config = Config(**_longport_config_kwargs(settings))
    gateway_config = _build_rust_gateway_config(settings)
    limiter = APIRateLimiter(
        rate=settings.longport_api_rate_limit,
        burst=settings.longport_api_burst,
        max_concurrent=settings.longport_api_max_concurrent,
        symbol_rate=settings.longport_steady_symbol_rate_per_min,
        symbol_burst=settings.longport_steady_symbol_burst,
        startup_symbol_rate=settings.longport_startup_symbol_rate_per_min,
        startup_symbol_burst=settings.longport_startup_symbol_burst,
        steady_symbol_rate=settings.longport_steady_symbol_rate_per_min,
        steady_symbol_burst=settings.longport_steady_symbol_burst,
    )
    runtime: L0QuoteRuntime = RustQuoteRuntime(
        config,
        endpoint_profiles=endpoint_profiles,
        gateway_config=gateway_config,
    )
    return RuntimeBundle(config=config, quote_runtime=runtime, rate_limiter=limiter)


__all__ = [
    "APIRateLimiter",
    "ArrowIpcReader",
    "L0QuoteRuntime",
    "RuntimeBundle",
    "RustQuoteRuntime",
    "_startup_connectivity_probe",
    "build_runtime_bundle",
    "longport_limiter",
]
