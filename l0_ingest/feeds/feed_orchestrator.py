"""P5 — FeedOrchestrator: Multi-Tier REST Polling Scheduler."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from shared.config import settings

if TYPE_CHECKING:
    from l0_ingest.feeds.chain_state_store import ChainStateStore
    from l0_ingest.feeds.iv_baseline_sync import IVBaselineSync
    from l0_ingest.feeds.quote_runtime import L0QuoteRuntime
    from l0_ingest.feeds.rate_limiter import APIRateLimiter
    from l0_ingest.subscription_manager import OptionSubscriptionManager

logger = logging.getLogger(__name__)


class FeedOrchestrator:
    """Schedules REST polling and subscription refresh using runtime abstraction."""

    def __init__(
        self,
        quote_runtime: "L0QuoteRuntime",
        store: "ChainStateStore",
        sub_mgr: "OptionSubscriptionManager",
        iv_sync: "IVBaselineSync",
        rate_limiter: "APIRateLimiter",
    ) -> None:
        self._quote_runtime = quote_runtime
        self._store = store
        self._sub_mgr = sub_mgr
        self._iv_sync = iv_sync
        self._limiter = rate_limiter
        self._mandatory_symbols: set[str] = set()

        self._start_time = datetime.now(ZoneInfo("US/Eastern"))
        self._last_research: datetime | None = None
        self._running = False

    async def run(self) -> None:
        self._running = True
        logger.info("[FeedOrchestrator] Management loop started.")
        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                logger.error("[FeedOrchestrator] Management loop error: %s", exc)

            elapsed = (datetime.now(ZoneInfo("US/Eastern")) - self._start_time).total_seconds()
            cadence = 5.0 if elapsed < 300.0 else 60.0
            await asyncio.sleep(cadence)

    async def stop(self) -> None:
        self._running = False

    def set_mandatory_symbols(self, symbols: set[str]) -> None:
        if symbols != self._mandatory_symbols:
            self._mandatory_symbols = symbols
            logger.info("[FeedOrchestrator] Mandatory symbols updated: %s", symbols)

    async def _tick(self) -> None:
        now = datetime.now(ZoneInfo("US/Eastern"))
        today = now.strftime("%Y%m%d")
        spot = self._store.spot

        spot = await self._refresh_spot_if_needed(spot, now)

        if spot:
            prev_symbols = set(self._sub_mgr.subscribed_symbols)
            target_set = await self._sub_mgr.refresh(spot, mandatory_symbols=self._mandatory_symbols)
            new_symbols = target_set - prev_symbols
            if new_symbols:
                logger.info(
                    "[FeedOrchestrator] %d new symbols detected — triggering IV warm-up.",
                    len(new_symbols),
                )
                await self._iv_sync.warm_up(list(new_symbols))

        can_run_research = self._iv_sync.bootstrap_warmup_done and not self._iv_sync.warming_up
        if spot and can_run_research and (
            not self._last_research
            or (now - self._last_research).total_seconds() > 900
        ):
            await self._run_volume_research(today, spot)
            self._last_research = now

    async def _refresh_spot_if_needed(
        self,
        spot: float | None,
        now: datetime,
    ) -> float | None:
        last_spot_update = getattr(self._store, "_last_spot_update", None)
        needs_refresh = (
            spot is None
            or (last_spot_update and (now - last_spot_update).total_seconds() > 10.0)
        )
        if not needs_refresh:
            return spot

        async with self._limiter.acquire(weight=1):
            try:
                quotes = await self._quote_runtime.quote(["SPY.US"])
                if quotes:
                    price = float(getattr(quotes[0], "last_done", 0.0) or 0.0)
                    if price > 0:
                        self._store.update_spot(price)
                        return price
            except Exception as exc:
                logger.warning("[FeedOrchestrator] Spot REST fallback failed: %s", exc)
        return spot

    async def _run_volume_research(
        self,
        today_str: str,
        spot: float,
    ) -> None:
        del today_str
        try:
            async with self._limiter.acquire():
                try:
                    chain_info = await self._quote_runtime.option_chain_info_by_date(
                        "SPY.US",
                        datetime.now().date(),
                    )
                except Exception as exc:
                    if "301607" in str(exc):
                        self._limiter.trigger_cooldown()
                    logger.warning("[FeedOrchestrator] Volume research metadata failed: %s", exc)
                    return

            if not chain_info:
                return

            window = settings.research_window_size
            research_symbols: list[str] = []
            strike_lookup: dict[str, float] = {}

            for item in chain_info:
                strike = float(getattr(item, "price", 0.0) or 0.0)
                if abs(strike - spot) > window:
                    continue
                call_symbol = getattr(item, "call_symbol", "")
                put_symbol = getattr(item, "put_symbol", "")
                if call_symbol:
                    research_symbols.append(call_symbol)
                    strike_lookup[call_symbol] = strike
                if put_symbol:
                    research_symbols.append(put_symbol)
                    strike_lookup[put_symbol] = strike

            new_map: dict[float, int] = {}
            batch_size = max(1, min(50, self._limiter.max_symbol_weight))
            for i in range(0, len(research_symbols), batch_size):
                batch = research_symbols[i : i + batch_size]
                async with self._limiter.acquire(weight=len(batch)):
                    try:
                        quotes = await self._quote_runtime.option_quote(batch)
                        if quotes:
                            for quote in quotes:
                                symbol = getattr(quote, "symbol", "")
                                strike = strike_lookup.get(symbol)
                                if strike is not None:
                                    vol = int(getattr(quote, "volume", 0) or 0)
                                    new_map[strike] = new_map.get(strike, 0) + vol
                    except Exception as exc:
                        logger.error("[FeedOrchestrator] Research batch failed: %s", exc)

            self._store.update_volume_map(new_map)
            logger.info("[FeedOrchestrator] Volume map updated: %d strikes", len(new_map))

        except Exception as exc:
            logger.error("[FeedOrchestrator] Volume research failed: %s", exc)
