"""P5 — FeedOrchestrator: Multi-Tier REST Polling Scheduler.

Extracts the management loop and volume research from OptionChainBuilder,
leaving OCB as a thin ~80-line bootstrap/wiring layer.

Responsibilities:
  - Spot price fallback (REST poll when WS is silent)
  - Tier 1 subscription refresh (SubscriptionManager.refresh)
  - IV warm-up for newly subscribed symbols (IVBaselineSync.warm_up)
  - Volume research scan every 15 minutes (_run_volume_research)
  - Adaptive management cadence: 5s for first 5 min (startup boost), 60s after

All REST calls are rate-limited via the shared APIRateLimiter injected at init.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from shared.config import settings

if TYPE_CHECKING:
    from longport.openapi import QuoteContext
    from l0_ingest.feeds.market_data_gateway import MarketDataGateway
    from l0_ingest.feeds.chain_state_store import ChainStateStore
    from l0_ingest.feeds.subscription_manager import SubscriptionManager
    from l0_ingest.feeds.iv_baseline_sync import IVBaselineSync
    from l0_ingest.feeds.rate_limiter import APIRateLimiter

logger = logging.getLogger(__name__)


class FeedOrchestrator:
    """Schedules all REST polling activity for the option chain feed.

    Pure scheduler — does NOT own any data state. All state reads/writes
    go through ChainStateStore or the pollers' own caches.
    """

    def __init__(
        self,
        gateway: "MarketDataGateway",
        store: "ChainStateStore",
        sub_mgr: "SubscriptionManager",
        iv_sync: "IVBaselineSync",
        rate_limiter: "APIRateLimiter",
    ) -> None:
        self._gateway     = gateway
        self._store       = store
        self._sub_mgr     = sub_mgr
        self._iv_sync     = iv_sync
        self._limiter     = rate_limiter
        self._mandatory_symbols: set[str] = set()

        self._start_time    = datetime.now(ZoneInfo("US/Eastern"))
        self._last_research: datetime | None = None
        self._running       = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def run(self) -> None:
        """Main management loop — run as an asyncio Task."""
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
        """Symbols that must always have Depth+Trade subscriptions."""
        if symbols != self._mandatory_symbols:
            self._mandatory_symbols = symbols
            logger.info("[FeedOrchestrator] Mandatory symbols updated: %s", symbols)

    # ── Internal tick ─────────────────────────────────────────────────────────

    async def _tick(self) -> None:
        ctx = self._gateway.quote_ctx
        if ctx is None:
            return

        now     = datetime.now(ZoneInfo("US/Eastern"))
        today   = now.strftime("%Y%m%d")
        spot    = self._store.spot

        # 1. Spot fallback (REST when WS silent)
        spot = await self._refresh_spot_if_needed(ctx, spot, now)

        # 2. Refresh Tier 1 subscriptions
        if spot:
            prev_symbols = set(self._sub_mgr.subscribed_symbols)
            target_set   = await self._sub_mgr.refresh(
                ctx, spot, mandatory_symbols=self._mandatory_symbols
            )

            # 3. Warm-up IV cache for newly discovered symbols
            new_symbols = target_set - prev_symbols
            if new_symbols:
                logger.info(
                    "[FeedOrchestrator] %d new symbols detected — triggering IV warm-up.",
                    len(new_symbols),
                )
                await self._iv_sync.warm_up(list(new_symbols))

        # 4. Volume research every 15 min
        if spot and (
            not self._last_research
            or (now - self._last_research).total_seconds() > 900
        ):
            await self._run_volume_research(today, spot, ctx)
            self._last_research = now

    async def _refresh_spot_if_needed(
        self,
        ctx: "QuoteContext",
        spot: float | None,
        now: datetime,
    ) -> float | None:
        """Poll SPY spot via REST if WS is silent (>10s without update)."""
        last_spot_update = getattr(self._store, "_last_spot_update", None)
        needs_refresh = (
            spot is None
            or (last_spot_update and (now - last_spot_update).total_seconds() > 10.0)
        )
        if not needs_refresh:
            return spot

        async with self._limiter.acquire():
            try:
                quotes = ctx.quote(["SPY.US"])
                if quotes:
                    price = float(quotes[0].last_done)
                    import math
                    if math.isfinite(price) and price > 0:
                        self._store.update_spot(price)
                        return price
            except Exception as exc:
                logger.warning("[FeedOrchestrator] Spot REST fallback failed: %s", exc)
        return spot

    async def _run_volume_research(
        self,
        today_str: str,
        spot: float,
        ctx: "QuoteContext",
    ) -> None:
        """Wide-window scan to build the strike→volume map."""
        try:
            async with self._limiter.acquire():
                try:
                    chain_info = ctx.option_chain_info_by_date(
                        "SPY.US", datetime.now().date()
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

            for s in chain_info:
                import math
                strike = float(s.price) if hasattr(s, "price") else 0.0
                if not math.isfinite(strike) or abs(strike - spot) > window:
                    continue
                if hasattr(s, "call_symbol") and s.call_symbol:
                    research_symbols.append(s.call_symbol)
                    strike_lookup[s.call_symbol] = strike
                if hasattr(s, "put_symbol") and s.put_symbol:
                    research_symbols.append(s.put_symbol)
                    strike_lookup[s.put_symbol] = strike

            new_map: dict[float, int] = {}
            batch_size = 50
            for i in range(0, len(research_symbols), batch_size):
                batch = research_symbols[i : i + batch_size]
                async with self._limiter.acquire():
                    try:
                        quotes = ctx.option_quote(batch)
                        if quotes:
                            for q in quotes:
                                st = strike_lookup.get(q.symbol)
                                if st is not None:
                                    new_map[st] = new_map.get(st, 0) + int(q.volume)
                    except Exception as exc:
                        logger.error("[FeedOrchestrator] Research batch failed: %s", exc)

            self._store.update_volume_map(new_map)
            logger.info(
                "[FeedOrchestrator] Volume map updated: %d strikes", len(new_map)
            )

        except Exception as exc:
            logger.error("[FeedOrchestrator] Volume research failed: %s", exc)
