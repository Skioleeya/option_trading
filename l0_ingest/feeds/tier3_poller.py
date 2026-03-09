"""Tier 3 Poller — Weekly REST Polling.

Periodically fetches the Top N OI anchor nodes for the next Weekly expiry.
All REST calls go through the shared APIRateLimiter.

配额优化：expiry metadata (option_chain_info_by_date) 在到期日滚动前只查一次，
避免每个 600s 周期消耗 14 次 REST 调用扫描日期。
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

# Weekly monitoring window (±60pt around spot)
TIER3_WINDOW = 60.0
# Number of top OI nodes to retain
TOP_N = 20
# Polling interval in seconds (10 minutes)
TIER3_INTERVAL = 600


class Tier3Poller:
    """Polls next Weekly option chain via REST at 10-minute intervals.

    Expiry metadata (which Friday is the next weekly, which symbols exist) is
    cached until the expiry date rolls over — eliminates 14 REST calls per cycle
    that were previously spent on option_chain_info_by_date date enumeration.
    """

    def __init__(self, rate_limiter: APIRateLimiter) -> None:
        self.cache: list[dict[str, Any]] = []
        self.expiry: date | None = None
        self._task: asyncio.Task | None = None
        self._syncing = False
        self._limiter = rate_limiter
        # ── Metadata cache ─────────────────────────────────────────────────────
        # Stores (weekly_date, {symbol: strike}) — refreshed only on rollover.
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
        await asyncio.sleep(180)  # Stagger from Tier1/Tier2 convergence
        while True:
            try:
                spot = self._get_spot()
                if spot and not self._syncing:
                    await self._fetch(spot)
            except Exception as e:
                logger.error(f"[Tier3Poller] Sync error: {e}")
            await asyncio.sleep(TIER3_INTERVAL)

    async def _refresh_metadata(self) -> bool:
        """Scan option_chain_info_by_date to find the next Weekly expiry and build symbol map.

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
            logger.warning("[Tier3Poller] Could not find Weekly expiry — skipping metadata refresh.")
            return False

        spot = self._get_spot() or 0.0
        sym_to_strike: dict[str, float] = {}
        for s in weekly_chain:
            strike = float(s.price) if hasattr(s, "price") else 0.0
            if abs(strike - spot) > TIER3_WINDOW:
                continue
            if hasattr(s, "call_symbol") and s.call_symbol:
                sym_to_strike[s.call_symbol] = strike
            if hasattr(s, "put_symbol") and s.put_symbol:
                sym_to_strike[s.put_symbol] = strike

        self._meta_expiry = weekly_date
        self._meta_sym_to_strike = sym_to_strike
        self.expiry = weekly_date
        logger.info(
            f"[Tier3Poller] Metadata refreshed: Weekly={weekly_date}, "
            f"{len(sym_to_strike)} symbols within ±{TIER3_WINDOW}pt"
        )
        return True

    async def _fetch(self, spot: float) -> None:
        """Fetch next Weekly chain via REST, keep only Top N OI nodes."""
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
                    f"[Tier3Poller] Using cached metadata: Weekly={self._meta_expiry}, "
                    f"{len(self._meta_sym_to_strike)} symbols"
                )

            symbols = list(self._meta_sym_to_strike.keys())
            if not symbols:
                return

            # ── Data fetch: OI / Volume / IV ──────────────────────────────────
            weekly_date = self._meta_expiry
            all_data: list[dict[str, Any]] = []
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
                            oi = int(r.open_interest) if r.open_interest else 0
                            iv_raw = r.implied_volatility
                            iv_val = 0.0
                            if iv_raw:
                                try:
                                    f_iv = float(iv_raw)
                                    if math.isfinite(f_iv):
                                        iv_val = f_iv
                                except (ValueError, TypeError):
                                    pass

                            all_data.append({
                                "symbol": r.symbol,
                                "strike": strike,
                                "type": opt_type,
                                "expiry": str(weekly_date),
                                "tier": "T3",
                                "volume": int(r.volume) if r.volume else 0,
                                "open_interest": oi,
                                "implied_volatility": iv_val,
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
