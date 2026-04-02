from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from longport.openapi import Config, SubType

from shared.config import settings
from shared.services.l0_runtime.source.runtime.quote_runtime import L0QuoteRuntime
from shared.services.l0_runtime.source.runtime.rate_limiter import APIRateLimiter
from shared.services.l0_runtime.services.native_support import (
    clamp_subscription_cap_native,
    collect_targets_native,
    enforce_cap_native,
)

logger = logging.getLogger(__name__)

CALL_WINDOW = 25.0
PUT_WINDOW = 35.0
LONGPORT_MAX_SUBSCRIPTIONS = 500


class OptionSubscriptionManager:
    """Unified manager for Rust-only ingestion with runtime abstraction."""

    def __init__(
        self,
        config: Config,
        quote_runtime: L0QuoteRuntime,
        rate_limiter: Optional[APIRateLimiter] = None,
    ):
        self.config = config
        self._runtime = quote_runtime

        self.shm_path = quote_runtime.shm_path
        self.is_rust_started = False

        self._subscribed_symbols: set[str] = set()
        self._depth_subscribed_symbols: set[str] = set()
        self._target_symbols: set[str] = set()
        self._symbol_to_strike: dict[str, float] = {}
        self._limiter = rate_limiter or APIRateLimiter(
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
        configured_cap = int(getattr(settings, "subscription_max", LONGPORT_MAX_SUBSCRIPTIONS))
        self._subscription_cap = clamp_subscription_cap_native(configured_cap)
        if self._subscription_cap != configured_cap:
            logger.warning(
                "[SubscriptionManager] subscription_max=%d clamped to official cap=%d",
                configured_cap,
                self._subscription_cap,
            )

        self._routing: dict[str, str] = {}
        self._metadata_weight = max(1, int(getattr(settings, "longport_metadata_weight", 5)))
        self._metadata_ttl_sec = max(1.0, float(getattr(settings, "longport_metadata_ttl_sec", 30)))
        self._metadata_cache: dict[date, tuple[float, list[Any]]] = {}
        self._metadata_cache_hits = 0
        self._metadata_cache_misses = 0

    @property
    def subscribed_symbols(self) -> set[str]:
        return self._subscribed_symbols

    @property
    def target_symbols(self) -> set[str]:
        return self._target_symbols

    @property
    def subscription_cap(self) -> int:
        return self._subscription_cap

    @property
    def symbol_to_strike(self) -> dict[str, float]:
        return self._symbol_to_strike

    def resolve_strike(self, symbol: str) -> float | None:
        return self._symbol_to_strike.get(symbol)

    @property
    def metadata_cache_hit_rate(self) -> float:
        total = self._metadata_cache_hits + self._metadata_cache_misses
        if total <= 0:
            return 0.0
        return self._metadata_cache_hits / float(total)

    def metadata_cache_diagnostics(self) -> dict[str, float | int]:
        return {
            "hit_rate": self.metadata_cache_hit_rate,
            "hits": self._metadata_cache_hits,
            "misses": self._metadata_cache_misses,
            "entries": len(self._metadata_cache),
            "ttl_sec": self._metadata_ttl_sec,
            "weight": self._metadata_weight,
        }

    def _prune_metadata_cache(self, now_mono: float) -> None:
        stale_dates = [
            d
            for d, (cached_at, _) in self._metadata_cache.items()
            if (now_mono - cached_at) > self._metadata_ttl_sec
        ]
        for d in stale_dates:
            self._metadata_cache.pop(d, None)

    async def _option_chain_info_by_date_cached(
        self,
        symbol: str,
        check_date: date,
    ) -> list[Any]:
        now_mono = time.monotonic()
        self._prune_metadata_cache(now_mono)
        cached = self._metadata_cache.get(check_date)
        if cached is not None:
            self._metadata_cache_hits += 1
            return cached[1]

        self._metadata_cache_misses += 1
        async with self._limiter.acquire(weight=self._metadata_weight):
            chain_info = await self._runtime.option_chain_info_by_date(
                symbol,
                check_date,
            )
        cached_rows = list(chain_info or [])
        self._metadata_cache[check_date] = (time.monotonic(), cached_rows)
        return cached_rows

    async def connect(self) -> None:
        await self._runtime.connect()
        logger.info("[SubscriptionManager] Quote runtime connected.")

    async def refresh(
        self,
        spot: float | None,
        mandatory_symbols: set[str] | None = None,
    ) -> set[str]:
        target_set = await self._collect_core_symbols(spot)
        if mandatory_symbols:
            target_set.update(mandatory_symbols)
        target_set = self._enforce_subscription_cap(
            target_set,
            mandatory_symbols=mandatory_symbols,
            spot=spot,
        )

        self._target_symbols = target_set
        await self._sync_subscriptions(target_set)
        return target_set

    async def _collect_core_symbols(self, spot: float | None) -> set[str]:
        if not spot:
            logger.info("[SubscriptionManager] Skipping collection: spot missing.")
            return set()

        now_date = datetime.now(ZoneInfo("US/Eastern")).date()
        valid_dates: list[tuple[date, list[Any]]] = []
        for i in range(7):
            check_date = now_date + timedelta(days=i)
            try:
                chain_info = await self._option_chain_info_by_date_cached("SPY.US", check_date)
                if chain_info:
                    valid_dates.append((check_date, chain_info))
                    if len(valid_dates) >= 3:
                        break
            except Exception as exc:
                logger.debug(
                    "[SubscriptionManager] option_chain_info_by_date failed for %s: %s",
                    check_date,
                    exc,
                )

        target_symbols = set()
        new_symbol_to_strike: dict[str, float] = {}
        for _, chain_info in valid_dates:
            native = collect_targets_native(list(chain_info), float(spot))
            target_symbols.update(native["targets"])
            new_symbol_to_strike.update(native["symbol_to_strike"])

        self._symbol_to_strike = new_symbol_to_strike
        return target_symbols

    def _symbol_distance_to_spot(self, symbol: str, spot: float | None) -> float:
        if spot is None:
            return float("inf")
        strike = self._symbol_to_strike.get(symbol)
        if strike is None:
            return float("inf")
        return abs(strike - spot)

    def _symbol_priority_key(self, symbol: str, spot: float | None) -> tuple[int, float, str]:
        import re
        expiry_date = 999999
        match = re.search(r"([A-Z]+)(\d{6})([C|P])(\d+)\.", symbol)
        if match:
            try:
                expiry_date = int(match.group(2))
            except ValueError:
                pass
        
        distance = self._symbol_distance_to_spot(symbol, spot)
        return (expiry_date, distance, symbol)

    def _enforce_subscription_cap(
        self,
        target_set: set[str],
        mandatory_symbols: set[str] | None,
        spot: float | None,
    ) -> set[str]:
        if len(target_set) <= self._subscription_cap:
            return target_set

        mandatory = set(mandatory_symbols or set())
        if len(mandatory) > self._subscription_cap:
            logger.warning(
                "[SubscriptionManager] Mandatory symbols exceed cap: kept %d of %d",
                self._subscription_cap,
                len(mandatory_symbols or set()),
            )
        native = enforce_cap_native(
            target_symbols=target_set,
            mandatory_symbols=mandatory,
            spot=spot,
            subscription_cap=self._subscription_cap,
            symbol_to_strike=self._symbol_to_strike,
        )
        kept = native["kept"]
        dropped = len(target_set) - len(kept)
        self._symbol_to_strike = native["symbol_to_strike"]
        logger.warning(
            "[SubscriptionManager] Subscription pool trimmed to %d/%d (dropped=%d, mandatory=%d)",
            len(kept),
            self._subscription_cap,
            dropped,
            len(mandatory),
        )
        return kept

    async def _sync_subscriptions(self, target_set: set[str]) -> None:
        rust_targets = target_set
        if not rust_targets:
            return
        await self._runtime.subscribe(
            sorted(rust_targets),
            [SubType.Quote, SubType.Depth, SubType.Trade],
        )
        self.is_rust_started = True
        self._subscribed_symbols = set(rust_targets)
        logger.info(
            "[SubscriptionManager] Rust runtime subscribed symbols=%d",
            len(self._subscribed_symbols),
        )

    async def stop(self) -> None:
        await self._runtime.disconnect()
        self.is_rust_started = False
        logger.info("[SubscriptionManager] Runtime disconnected.")

