"""P5 — FeedOrchestrator: Multi-Tier REST Polling Scheduler."""

from __future__ import annotations

import asyncio
import logging
import time
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
        self._monotonic = time.monotonic
        self._last_refresh_mono = 0.0
        self._refresh_min_interval_sec = 30.0
        self._warmup_merge_window_sec = max(
            1.0,
            float(getattr(settings, "longport_warmup_merge_window_sec", 20)),
        )
        self._research_startup_stable_sec = max(
            1.0,
            float(getattr(settings, "longport_research_startup_stable_sec", 120)),
        )
        self._pending_warmup_symbols: set[str] = set()
        self._pending_warmup_since_mono: float | None = None

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

    @property
    def pending_warmup_count(self) -> int:
        return len(self._pending_warmup_symbols)

    def _subscription_refresh_due(self, now_mono: float) -> bool:
        return (now_mono - self._last_refresh_mono) >= self._refresh_min_interval_sec

    def _queue_warmup_symbols(self, symbols: set[str], now_mono: float) -> None:
        if not symbols:
            return
        if not self._pending_warmup_symbols:
            self._pending_warmup_since_mono = now_mono
        self._pending_warmup_symbols.update(symbols)

    async def _flush_warmup_if_due(self, now_mono: float) -> None:
        if not self._pending_warmup_symbols or self._iv_sync.warming_up:
            return
        pending_since = self._pending_warmup_since_mono
        if pending_since is None:
            self._pending_warmup_since_mono = now_mono
            return
        if (now_mono - pending_since) < self._warmup_merge_window_sec:
            return
        batch = sorted(self._pending_warmup_symbols)
        self._pending_warmup_symbols.clear()
        self._pending_warmup_since_mono = None
        logger.info(
            "[FeedOrchestrator] Flushing warm-up queue: symbols=%d merge_window=%.0fs",
            len(batch),
            self._warmup_merge_window_sec,
        )
        await self._iv_sync.warm_up(batch)

    async def _tick(self) -> None:
        now = datetime.now(ZoneInfo("US/Eastern"))
        today = now.strftime("%Y%m%d")
        now_mono = self._monotonic()
        spot = self._store.spot

        self._limiter.maybe_promote_to_steady(
            warmup_done=self._iv_sync.bootstrap_warmup_done,
            warming_up=self._iv_sync.warming_up,
            stable_for_sec=self._research_startup_stable_sec,
        )

        spot = await self._refresh_spot_if_needed(spot, now)

        if spot and self._subscription_refresh_due(now_mono):
            prev_symbols = set(self._sub_mgr.subscribed_symbols)
            target_set = await self._sub_mgr.refresh(spot, mandatory_symbols=self._mandatory_symbols)
            self._last_refresh_mono = now_mono
            new_symbols = target_set - prev_symbols
            if new_symbols:
                logger.info(
                    "[FeedOrchestrator] %d new symbols detected — queued for IV warm-up.",
                    len(new_symbols),
                )
                self._queue_warmup_symbols(new_symbols, now_mono)

        await self._flush_warmup_if_due(now_mono)

        can_run_research = self._iv_sync.bootstrap_warmup_done and not self._iv_sync.warming_up
        startup_stable = self._limiter.cooldown_stable_for(self._research_startup_stable_sec)
        if spot and can_run_research and (
            not self._last_research
            or (now - self._last_research).total_seconds() > 900
        ) and startup_stable:
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
