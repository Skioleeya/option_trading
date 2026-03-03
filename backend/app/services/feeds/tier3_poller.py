"""Tier 3 Poller — Weekly REST Polling.

Periodically fetches the Top N OI anchor nodes for the next Weekly expiry.
All REST calls go through the shared APIRateLimiter.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Any, Callable
from zoneinfo import ZoneInfo

from longport.openapi import QuoteContext, CalcIndex

from app.services.feeds.rate_limiter import APIRateLimiter

logger = logging.getLogger(__name__)

# Weekly monitoring window (±60pt around spot)
TIER3_WINDOW = 60.0
# Number of top OI nodes to retain
TOP_N = 20
# Polling interval in seconds (10 minutes)
TIER3_INTERVAL = 600


class Tier3Poller:
    """Polls next Weekly option chain via REST at 10-minute intervals."""

    def __init__(self, rate_limiter: APIRateLimiter) -> None:
        self.cache: list[dict[str, Any]] = []
        self.expiry: date | None = None
        self._task: asyncio.Task | None = None
        self._syncing = False
        self._limiter = rate_limiter

    def start(self, ctx: QuoteContext, get_spot_fn: Callable[[], float | None]) -> None:
        """Start the background polling loop."""
        self._ctx = ctx
        self._get_spot = get_spot_fn
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Cancel the background task."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        """Background loop with initial stagger delay."""
        await asyncio.sleep(180)  # Stagger from Tier1/Tier2 convergence
        while True:
            try:
                spot = self._get_spot()
                if spot and self._ctx and not self._syncing:
                    await self._fetch(spot)
            except Exception as e:
                logger.error(f"[Tier3Poller] Sync error: {e}")
            await asyncio.sleep(TIER3_INTERVAL)

    async def _fetch(self, spot: float) -> None:
        """Fetch next Weekly chain via REST, keep only Top N OI nodes."""
        self._syncing = True
        try:
            now_date = datetime.now(ZoneInfo("US/Eastern")).date()

            # Scan for valid expiry dates
            valid_dates = []
            for i in range(14):
                check_date = now_date + timedelta(days=i)
                async with self._limiter.acquire():
                    try:
                        chain_info = self._ctx.option_chain_info_by_date("SPY.US", check_date)
                    except Exception as e:
                        if "301607" in str(e):
                            self._limiter.trigger_cooldown()
                        logger.warning(f"[Tier3Poller] Metadata fetch failed: {e}")
                        continue

                if chain_info and len(chain_info) > 0:
                    valid_dates.append((check_date, chain_info))

            # Weekly = first Friday beyond the first 2 expiries
            weekly_date = None
            weekly_chain = None
            for d, info in valid_dates[2:]:
                if d.weekday() == 4:  # Friday
                    weekly_date = d
                    weekly_chain = info
                    break

            if not weekly_date or not weekly_chain:
                return

            self.expiry = weekly_date

            # Filter to ±60pt window
            symbols = []
            sym_to_strike: dict[str, float] = {}
            for s in weekly_chain:
                strike = float(s.price) if hasattr(s, 'price') else 0.0
                if abs(strike - spot) > TIER3_WINDOW:
                    continue
                if hasattr(s, 'call_symbol') and s.call_symbol:
                    symbols.append(s.call_symbol)
                    sym_to_strike[s.call_symbol] = strike
                if hasattr(s, 'put_symbol') and s.put_symbol:
                    symbols.append(s.put_symbol)
                    sym_to_strike[s.put_symbol] = strike

            if not symbols:
                return

            # Fetch OI via calc_indexes through the shared rate limiter
            all_data: list[dict[str, Any]] = []
            batch_size = 50  # Was 10 — safe under rate limiter control
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                async with self._limiter.acquire():
                    try:
                        results = self._ctx.calc_indexes(
                            batch, [CalcIndex.Volume, CalcIndex.OpenInterest,
                                    CalcIndex.ImpliedVolatility]
                        )
                        for r in results:
                            strike = sym_to_strike.get(r.symbol, 0.0)
                            opt_type = "CALL" if "C" in r.symbol else "PUT"
                            oi = int(r.open_interest) if r.open_interest else 0
                            all_data.append({
                                "symbol": r.symbol,
                                "strike": strike,
                                "type": opt_type,
                                "expiry": str(weekly_date),
                                "tier": "T3",
                                "volume": int(r.volume) if r.volume else 0,
                                "open_interest": oi,
                                "implied_volatility": float(r.implied_volatility) if r.implied_volatility else 0.0,
                            })
                    except Exception as e:
                        if "301607" in str(e):
                            self._limiter.trigger_cooldown()
                        logger.info(f"[Tier3Poller] Batch recovery active: {e}")

            # Retain only Top N OI nodes (structural anchors)
            all_data.sort(key=lambda x: x["open_interest"], reverse=True)
            self.cache = all_data[:TOP_N]
            logger.info(
                f"[Tier3Poller] Synced Top {TOP_N} OI anchors "
                f"(Weekly={weekly_date}, ±{TIER3_WINDOW}pt)"
            )
        finally:
            self._syncing = False
