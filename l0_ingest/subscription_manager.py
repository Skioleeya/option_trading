from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from longport.openapi import Config, SubType

from l0_ingest.feeds.quote_runtime import L0QuoteRuntime
from l0_ingest.feeds.rate_limiter import APIRateLimiter
from shared.config import settings

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
            symbol_rate=settings.longport_symbol_rate_per_min,
            symbol_burst=settings.longport_symbol_burst,
        )
        configured_cap = int(getattr(settings, "subscription_max", LONGPORT_MAX_SUBSCRIPTIONS))
        self._subscription_cap = max(1, min(configured_cap, LONGPORT_MAX_SUBSCRIPTIONS))
        if self._subscription_cap != configured_cap:
            logger.warning(
                "[SubscriptionManager] subscription_max=%d clamped to official cap=%d",
                configured_cap,
                self._subscription_cap,
            )

        self._routing: dict[str, str] = {}

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
            async with self._limiter.acquire(weight=1):
                try:
                    chain_info = await self._runtime.option_chain_info_by_date(
                        "SPY.US",
                        check_date,
                    )
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
            for item in chain_info:
                strike = float(getattr(item, "price", 0.0) or 0.0)
                dist = strike - spot
                if dist > CALL_WINDOW or dist < -PUT_WINDOW:
                    continue
                call_symbol = getattr(item, "call_symbol", "")
                put_symbol = getattr(item, "put_symbol", "")
                if call_symbol:
                    target_symbols.add(call_symbol)
                    new_symbol_to_strike[call_symbol] = strike
                if put_symbol:
                    target_symbols.add(put_symbol)
                    new_symbol_to_strike[put_symbol] = strike

        self._symbol_to_strike = new_symbol_to_strike
        return target_symbols

    def _symbol_distance_to_spot(self, symbol: str, spot: float | None) -> float:
        if spot is None:
            return float("inf")
        strike = self._symbol_to_strike.get(symbol)
        if strike is None:
            return float("inf")
        return abs(strike - spot)

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
            ranked_mandatory = sorted(
                mandatory,
                key=lambda sym: (self._symbol_distance_to_spot(sym, spot), sym),
            )
            mandatory = set(ranked_mandatory[: self._subscription_cap])
            logger.warning(
                "[SubscriptionManager] Mandatory symbols exceed cap: kept %d of %d",
                len(mandatory),
                len(mandatory_symbols or set()),
            )

        kept = set(mandatory)
        remaining = self._subscription_cap - len(kept)
        if remaining > 0:
            ranked_candidates = sorted(
                (sym for sym in target_set if sym not in kept),
                key=lambda sym: (self._symbol_distance_to_spot(sym, spot), sym),
            )
            kept.update(ranked_candidates[:remaining])

        dropped = len(target_set) - len(kept)
        self._symbol_to_strike = {
            sym: strike
            for sym, strike in self._symbol_to_strike.items()
            if sym in kept
        }
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
