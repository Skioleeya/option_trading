"""Tier 2 Poller — 2DTE REST Polling.

Periodically fetches OI/Volume/IV data for the 2DTE expiry via REST.
All REST calls go through the shared APIRateLimiter.
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, date, timedelta
from typing import Any, Callable
from zoneinfo import ZoneInfo

from longport.openapi import QuoteContext, CalcIndex

from app.services.feeds.rate_limiter import APIRateLimiter

logger = logging.getLogger(__name__)

# 2DTE monitoring window (±30pt around spot)
TIER2_WINDOW = 30.0
# Polling interval in seconds
TIER2_INTERVAL = 120


class Tier2Poller:
    """Polls 2DTE option chain via REST at 120s intervals."""

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
        await asyncio.sleep(60)  # Decouple from Tier 1 cold-start burst
        while True:
            try:
                spot = self._get_spot()
                if spot and self._ctx and not self._syncing:
                    await self._fetch(spot)
            except Exception as e:
                logger.error(f"[Tier2Poller] Sync error: {e}")
            await asyncio.sleep(TIER2_INTERVAL)

    async def _fetch(self, spot: float) -> None:
        """Fetch 2DTE chain via REST and cache locally."""
        self._syncing = True
        try:
            now_date = datetime.now(ZoneInfo("US/Eastern")).date()

            # Find 3rd valid expiry (index 2 = 2DTE)
            valid_dates = []
            for i in range(14):
                check_date = now_date + timedelta(days=i)
                async with self._limiter.acquire():
                    try:
                        chain_info = self._ctx.option_chain_info_by_date("SPY.US", check_date)
                    except Exception as e:
                        if "301607" in str(e):
                            self._limiter.trigger_cooldown()
                        logger.warning(f"[Tier2Poller] Metadata fetch failed: {e}")
                        continue

                if chain_info and len(chain_info) > 0:
                    valid_dates.append((check_date, chain_info))
                    if len(valid_dates) >= 3:
                        break

            if len(valid_dates) < 3:
                return

            dte2_date, chain_info = valid_dates[2]
            self.expiry = dte2_date

            # Filter to ±30pt window
            symbols = []
            sym_to_strike: dict[str, float] = {}
            for s in chain_info:
                strike = float(s.price) if hasattr(s, 'price') else 0.0
                if abs(strike - spot) > TIER2_WINDOW:
                    continue
                if hasattr(s, 'call_symbol') and s.call_symbol:
                    symbols.append(s.call_symbol)
                    sym_to_strike[s.call_symbol] = strike
                if hasattr(s, 'put_symbol') and s.put_symbol:
                    symbols.append(s.put_symbol)
                    sym_to_strike[s.put_symbol] = strike

            if not symbols:
                return

            # Fetch via calc_indexes through the shared rate limiter
            results_data: list[dict[str, Any]] = []
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
                            iv_raw = r.implied_volatility
                            iv_val = 0.0
                            if iv_raw:
                                try:
                                    f_iv = float(iv_raw)
                                    if math.isfinite(f_iv):
                                        iv_val = f_iv
                                except (ValueError, TypeError):
                                    pass

                            results_data.append({
                                "symbol": r.symbol,
                                "strike": strike,
                                "type": opt_type,
                                "expiry": str(dte2_date),
                                "tier": "T2",
                                "volume": int(r.volume) if r.volume else 0,
                                "open_interest": int(r.open_interest) if r.open_interest else 0,
                                "implied_volatility": iv_val,
                            })
                    except Exception as e:
                        if "301607" in str(e):
                            self._limiter.trigger_cooldown()
                        logger.info(f"[Tier2Poller] Batch recovery active: {e}")

            self.cache = results_data
            logger.info(
                f"[Tier2Poller] Synced {len(results_data)} contracts "
                f"(2DTE={dte2_date}, ±{TIER2_WINDOW}pt)"
            )
        finally:
            self._syncing = False
