"""Tier 2 Poller — 2DTE REST Polling.

Periodically fetches OI/Volume/IV data for the 2DTE expiry via REST.
All REST calls go through the shared APIRateLimiter.

配额优化：expiry metadata (option_chain_info_by_date) 在到期日滚动前只查一次，
避免每个 120s 周期消耗 14 次 REST 调用扫描日期。
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, date, timedelta
from typing import Any, Callable
from zoneinfo import ZoneInfo

from longport.openapi import CalcIndex

from l0_ingest.feeds.quote_runtime import L0QuoteRuntime
from l0_ingest.feeds.rate_limiter import APIRateLimiter

logger = logging.getLogger(__name__)

# 2DTE monitoring window (±30pt around spot)
TIER2_WINDOW = 30.0
# Polling interval in seconds
TIER2_INTERVAL = 120


class Tier2Poller:
    """Polls 2DTE option chain via REST at 120s intervals.

    Expiry metadata (which date is 2DTE, which symbols exist) is cached until
    the expiry date rolls over — eliminates 14 REST calls per cycle that were
    previously spent on option_chain_info_by_date date enumeration.
    """

    def __init__(self, rate_limiter: APIRateLimiter) -> None:
        self.cache: list[dict[str, Any]] = []
        self.expiry: date | None = None
        self._task: asyncio.Task | None = None
        self._syncing = False
        self._limiter = rate_limiter
        # ── Metadata cache ─────────────────────────────────────────────────────
        # Stores (expiry_date, {symbol: strike}) — refreshed only on rollover.
        self._meta_expiry: date | None = None
        self._meta_sym_to_strike: dict[str, float] = {}

    def start(self, runtime: L0QuoteRuntime, get_spot_fn: Callable[[], float | None]) -> None:
        """Start the background polling loop."""
        self._runtime = runtime
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
                if spot and not self._syncing:
                    await self._fetch(spot)
            except Exception as e:
                logger.error(f"[Tier2Poller] Sync error: {e}")
            await asyncio.sleep(TIER2_INTERVAL)

    async def _refresh_metadata(self) -> bool:
        """Scan option_chain_info_by_date to find the 2DTE expiry and build symbol map.

        Only called when metadata is stale (first run or expiry rolled over).
        Consumes up to 14 REST calls but amortized over many data cycles.

        Returns True if metadata was refreshed successfully.
        """
        now_date = datetime.now(ZoneInfo("US/Eastern")).date()
        valid_dates = []
        for i in range(14):
            check_date = now_date + timedelta(days=i)
            async with self._limiter.acquire(weight=1):
                try:
                    chain_info = await self._runtime.option_chain_info_by_date("SPY.US", check_date)
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
            logger.warning("[Tier2Poller] Could not find 2DTE expiry — skipping metadata refresh.")
            return False

        dte2_date, chain_info = valid_dates[2]
        spot = self._get_spot() or 0.0

        sym_to_strike: dict[str, float] = {}
        for s in chain_info:
            strike = float(s.price) if hasattr(s, "price") else 0.0
            if abs(strike - spot) > TIER2_WINDOW:
                continue
            if hasattr(s, "call_symbol") and s.call_symbol:
                sym_to_strike[s.call_symbol] = strike
            if hasattr(s, "put_symbol") and s.put_symbol:
                sym_to_strike[s.put_symbol] = strike

        self._meta_expiry = dte2_date
        self._meta_sym_to_strike = sym_to_strike
        self.expiry = dte2_date
        logger.info(
            f"[Tier2Poller] Metadata refreshed: 2DTE={dte2_date}, "
            f"{len(sym_to_strike)} symbols within ±{TIER2_WINDOW}pt"
        )
        return True

    async def _fetch(self, spot: float) -> None:
        """Fetch 2DTE chain via REST and cache locally."""
        self._syncing = True
        try:
            today = datetime.now(ZoneInfo("US/Eastern")).date()

            # ── 配额优化: 只在到期日滚动时重新扫描 metadata ──────────────────
            needs_refresh = (
                self._meta_expiry is None       # first run
                or self._meta_expiry < today    # expiry has passed → rollover
            )
            if needs_refresh:
                ok = await self._refresh_metadata()
                if not ok:
                    return
            else:
                logger.debug(
                    f"[Tier2Poller] Using cached metadata: 2DTE={self._meta_expiry}, "
                    f"{len(self._meta_sym_to_strike)} symbols"
                )

            symbols = list(self._meta_sym_to_strike.keys())
            if not symbols:
                return

            # ── Data fetch: IV / OI / Volume ──────────────────────────────────
            dte2_date = self._meta_expiry
            results_data: list[dict[str, Any]] = []
            batch_size = max(1, min(50, self._limiter.max_symbol_weight))
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                async with self._limiter.acquire(weight=len(batch)):
                    try:
                        results = await self._runtime.calc_indexes(
                            batch,
                            [CalcIndex.Volume, CalcIndex.OpenInterest, CalcIndex.ImpliedVolatility],
                        )
                        for r in results:
                            strike = self._meta_sym_to_strike.get(r.symbol, 0.0)
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
