"""Subscription Manager — Tier 1 WebSocket Subscription Logic.

Manages the asymmetric strike window (+25 Call / -35 Put) for 0DTE + 1DTE,
and handles dynamic promotion/demotion of symbols with micro-batch throttling.

All REST calls (option_chain_info_by_date) go through the shared APIRateLimiter.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from longport.openapi import QuoteContext, SubType
from shared.config import settings
from l0_ingest.feeds.rate_limiter import APIRateLimiter

logger = logging.getLogger(__name__)

# Asymmetric window constants (based on real market structure analysis)
CALL_WINDOW = 25.0   # Call concentration is tight around ATM
PUT_WINDOW = 35.0    # Put hedging extends further downside


class SubscriptionManager:
    """Manages Tier 1 WebSocket subscriptions with asymmetric windows.

    Responsibilities:
    - Collect 0DTE + 1DTE core symbols within the asymmetric window
    - Differential subscribe/unsubscribe with micro-batch throttling
    - Maintain the symbol-to-strike mapping for downstream use
    - All REST calls go through the shared APIRateLimiter
    """

    def __init__(self, rate_limiter: APIRateLimiter) -> None:
        self._subscribed_symbols: set[str] = set()
        self._depth_subscribed_symbols: set[str] = set()
        self._target_symbols: set[str] = set()
        self._symbol_to_strike: dict[str, float] = {}
        self._limiter = rate_limiter

    @property
    def subscribed_symbols(self) -> set[str]:
        return self._subscribed_symbols

    @property
    def target_symbols(self) -> set[str]:
        return self._target_symbols

    @property
    def symbol_to_strike(self) -> dict[str, float]:
        return self._symbol_to_strike

    def resolve_strike(self, symbol: str) -> float | None:
        """Resolve strike for a given symbol."""
        return self._symbol_to_strike.get(symbol)

    async def refresh(self, ctx: QuoteContext, spot: float | None, mandatory_symbols: set[str] | None = None) -> set[str]:
        """Collect core symbols and sync subscriptions. Returns the target set."""
        target_set = await self._collect_core_symbols(ctx, spot)
        
        # Ensure mandatory symbols (like ATM anchors) are in the target set
        if mandatory_symbols:
            target_set.update(mandatory_symbols)

        # Instantly update the intentional target set (used by payload builder)
        self._target_symbols = target_set

        # Slowly sync physical WebSocket status in the background
        await self._sync_subscriptions(ctx, target_set, spot, mandatory_symbols)
        return target_set


    async def _collect_core_symbols(self, ctx: QuoteContext, spot: float | None) -> set[str]:
        """
        Asymmetric Core Window: Collect 0DTE and 1DTE symbols via rate-limited REST.
        - CALL_WINDOW: +25pt (retail call concentration).
        - PUT_WINDOW: -35pt (institutional put hedging/panic).
        """
        if not ctx or not spot:
            return set()

        now_date = datetime.now(ZoneInfo("US/Eastern")).date()
        valid_dates = []

        # Detect next two valid expiries (0DTE and 1DTE), skipping weekends
        for i in range(7):
            check_date = now_date + timedelta(days=i)
            async with self._limiter.acquire():
                try:
                    chain_info = ctx.option_chain_info_by_date("SPY.US", check_date)
                except Exception as e:
                    logger.warning(f"[SubscriptionManager] Chain info fetch failed for {check_date}: {e}")
                    chain_info = None

            if chain_info and len(chain_info) > 0:
                valid_dates.append((check_date, chain_info))
                # Expanded to 3 expiries (0DTE, 1DTE, Weekly) under 500 sub limit
                if len(valid_dates) >= 3:
                    break

        target_symbols = set()
        new_symbol_to_strike = {}

        for _, chain_info in valid_dates:
            for s in chain_info:
                strike = float(s.price) if hasattr(s, 'price') else 0.0

                # Dynamic Sliding Window filtering (asymmetric)
                dist = strike - spot
                if dist > CALL_WINDOW or dist < -PUT_WINDOW:
                    continue

                if hasattr(s, 'call_symbol') and s.call_symbol:
                    target_symbols.add(s.call_symbol)
                    new_symbol_to_strike[s.call_symbol] = strike
                if hasattr(s, 'put_symbol') and s.put_symbol:
                    target_symbols.add(s.put_symbol)
                    new_symbol_to_strike[s.put_symbol] = strike

        self._symbol_to_strike = new_symbol_to_strike
        return target_symbols

    async def _sync_subscriptions(self, ctx: QuoteContext, target_set: set[str], spot: float | None, mandatory_symbols: set[str] | None = None) -> None:
        """
        Dynamic Promotion & Sliding:
        - Symbols leaving the core zone are dropped instantly.
        - Symbols entering the core zone are subscribed in micro-batches (5 per 50ms).
        - Manage SubType.Depth and SubType.Trade for ONLY the Top 10 closest strikes to Spot PLUS mandatory ones.
        """
        to_subscribe = list(target_set - self._subscribed_symbols)
        to_unsubscribe = list(self._subscribed_symbols - target_set)

        # 1. Drop targets slipping out of the window (Quote)
        if to_unsubscribe:
            try:
                ctx.unsubscribe(to_unsubscribe, [SubType.Quote])
                self._subscribed_symbols -= set(to_unsubscribe)
                logger.debug(f"[SubscriptionManager] Dropped {len(to_unsubscribe)} slipping symbols.")
            except Exception as e:
                logger.error(f"[SubscriptionManager] Unsubscribe error: {e}")

        # 2. Promote targets sliding into the window (Quote, micro-batched)
        if to_subscribe:
            if len(self._subscribed_symbols) + len(to_subscribe) > settings.subscription_max:
                logger.warning(
                    f"[SubscriptionManager] Sub limit breached! Cannot add {len(to_subscribe)} "
                    f"symbols to existing {len(self._subscribed_symbols)}."
                )
            else:
                batch_size = 10
                for i in range(0, len(to_subscribe), batch_size):
                    batch = to_subscribe[i:i + batch_size]
                    try:
                        ctx.subscribe(batch, [SubType.Quote])
                        self._subscribed_symbols |= set(batch)
                        await asyncio.sleep(1.5)  # Throttled WS sub delay
                    except Exception as e:
                        logger.error(f"[SubscriptionManager] Subscribe batch error: {e}")

        # 3. Synchronize SubType.Depth and SubType.Trade for Top 10 ATM contracts + SPY.US + Mandatory
        if spot is not None and self._subscribed_symbols:
            # Sort all subscribed options by distance to spot
            sorted_symbols = sorted(
                [s for s in self._subscribed_symbols if s != "SPY.US"],
                key=lambda s: abs(self._symbol_to_strike.get(s, float('inf')) - spot)
            )
            
            # Select top 10 (approx 5 Call + 5 Put ATM)
            target_depth_set = set(sorted_symbols[:10])
            
            # ALWAYS include mandatory symbols (ATM anchors) and SPY
            if mandatory_symbols:
                target_depth_set.update(mandatory_symbols)
            target_depth_set.add("SPY.US")

            to_sub_depth = list(target_depth_set - self._depth_subscribed_symbols)
            to_unsub_depth = list(self._depth_subscribed_symbols - target_depth_set)

            if to_unsub_depth:
                try:
                    ctx.unsubscribe(to_unsub_depth, [SubType.Depth, SubType.Trade])
                    self._depth_subscribed_symbols -= set(to_unsub_depth)
                except Exception as e:
                    logger.error(f"[SubscriptionManager] Unsubscribe depth/trade error: {e}")

            if to_sub_depth:
                try:
                    ctx.subscribe(to_sub_depth, [SubType.Depth, SubType.Trade])
                    self._depth_subscribed_symbols |= set(to_sub_depth)
                    logger.info(f"[SubscriptionManager] Subscribed Depth+Trade for ATM/Mandatory: {to_sub_depth}")
                except Exception as e:
                    logger.error(f"[SubscriptionManager] Subscribe depth/trade error: {e}")

        logger.info(f"[SubscriptionManager] Tier 1 Resynced. Actives: {len(self._subscribed_symbols)}, Depth: {len(self._depth_subscribed_symbols)}")

