"""Polling services for L0 V2."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any, Callable
from zoneinfo import ZoneInfo

from longport.openapi import CalcIndex

from shared.services.l0_runtime.services._native_helpers import (
    build_symbol_metadata_native,
    normalize_calc_rows_native,
    top_open_interest_native,
)
from shared.services.l0_runtime.source.runtime import APIRateLimiter
from shared.services.l0_runtime.source.runtime.quote_runtime import L0QuoteRuntime

logger = logging.getLogger(__name__)

TIER2_WINDOW = 30.0
TIER2_INTERVAL = 120
TIER3_WINDOW = 60.0
TOP_N = 20
TIER3_INTERVAL = 600


class Tier2Poller:
    """Polls 2DTE option chain via REST at 120s intervals."""

    def __init__(self, rate_limiter: APIRateLimiter) -> None:
        self.cache: list[dict[str, Any]] = []
        self.expiry: date | None = None
        self._task: asyncio.Task | None = None
        self._syncing = False
        self._limiter = rate_limiter
        self._meta_expiry: date | None = None
        self._meta_sym_to_strike: dict[str, float] = {}
        self._meta_standard_by_symbol: dict[str, bool] = {}

    def start(self, runtime: L0QuoteRuntime, get_spot_fn: Callable[[], float | None]) -> None:
        self._runtime = runtime
        self._get_spot = get_spot_fn
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        await asyncio.sleep(180)
        while True:
            try:
                spot = self._get_spot()
                if self._limiter.cooldown_active:
                    logger.info("[Tier2Poller] Startup/stagger sync paused: global cooldown active.")
                elif spot and not self._syncing:
                    await self._fetch(spot)
            except Exception as exc:
                logger.error("[Tier2Poller] Sync error: %s", exc)
            await asyncio.sleep(TIER2_INTERVAL)

    async def _refresh_metadata(self) -> bool:
        now_date = datetime.now(ZoneInfo("US/Eastern")).date()
        valid_dates = []
        for i in range(14):
            check_date = now_date + timedelta(days=i)
            async with self._limiter.acquire(weight=1):
                try:
                    chain_info = await self._runtime.option_chain_info_by_date("SPY.US", check_date)
                except Exception as exc:
                    if "301607" in str(exc):
                        self._limiter.trigger_cooldown()
                    logger.warning("[Tier2Poller] Metadata fetch failed: %s", exc)
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
        sym_to_strike, standard_by_symbol, kept = build_symbol_metadata_native(
            list(chain_info),
            spot=spot,
            window=TIER2_WINDOW,
        )
        self._meta_expiry = dte2_date
        self._meta_sym_to_strike = sym_to_strike
        self._meta_standard_by_symbol = standard_by_symbol
        self.expiry = dte2_date
        logger.info(
            "[Tier2Poller] Metadata refreshed: 2DTE=%s, %d symbols within ±%spt",
            dte2_date,
            kept,
            TIER2_WINDOW,
        )
        return True

    async def _fetch(self, spot: float) -> None:
        self._syncing = True
        try:
            today = datetime.now(ZoneInfo("US/Eastern")).date()
            needs_refresh = self._meta_expiry is None or self._meta_expiry < today
            if needs_refresh:
                if not await self._refresh_metadata():
                    return
            else:
                logger.debug(
                    "[Tier2Poller] Using cached metadata: 2DTE=%s, %d symbols",
                    self._meta_expiry,
                    len(self._meta_sym_to_strike),
                )
            symbols = list(self._meta_sym_to_strike.keys())
            if not symbols:
                return
            dte2_date = self._meta_expiry
            results_data: list[dict[str, Any]] = []
            batch_size = max(1, min(50, self._limiter.max_symbol_weight))
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i : i + batch_size]
                async with self._limiter.acquire(weight=len(batch)):
                    try:
                        results = await self._runtime.calc_indexes(
                            batch,
                            [CalcIndex.Volume, CalcIndex.OpenInterest, CalcIndex.ImpliedVolatility, CalcIndex.Premium],
                        )
                        results_data.extend(
                            normalize_calc_rows_native(
                                list(results),
                                expiry=str(dte2_date),
                                tier="T2",
                                sym_to_strike=self._meta_sym_to_strike,
                                standard_by_symbol=self._meta_standard_by_symbol,
                            )
                        )
                    except Exception as exc:
                        if "301607" in str(exc):
                            self._limiter.trigger_cooldown()
                        logger.info("[Tier2Poller] Batch recovery active: %s", exc)
            self.cache = results_data
            logger.info("[Tier2Poller] Synced %d contracts (2DTE=%s, ±%spt)", len(results_data), dte2_date, TIER2_WINDOW)
        finally:
            self._syncing = False


class Tier3Poller:
    """Polls next Weekly option chain via REST at 10-minute intervals."""

    def __init__(self, rate_limiter: APIRateLimiter) -> None:
        self.cache: list[dict[str, Any]] = []
        self.expiry: date | None = None
        self._task: asyncio.Task | None = None
        self._syncing = False
        self._limiter = rate_limiter
        self._meta_expiry: date | None = None
        self._meta_sym_to_strike: dict[str, float] = {}
        self._meta_standard_by_symbol: dict[str, bool] = {}

    def start(self, runtime: L0QuoteRuntime, get_spot_fn: Callable[[], float | None]) -> None:
        self._runtime = runtime
        self._get_spot = get_spot_fn
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        await asyncio.sleep(300)
        while True:
            try:
                spot = self._get_spot()
                if self._limiter.cooldown_active:
                    logger.info("[Tier3Poller] Startup/stagger sync paused: global cooldown active.")
                elif spot and not self._syncing:
                    await self._fetch(spot)
            except Exception as exc:
                logger.error("[Tier3Poller] Sync error: %s", exc)
            await asyncio.sleep(TIER3_INTERVAL)

    async def _refresh_metadata(self) -> bool:
        now_date = datetime.now(ZoneInfo("US/Eastern")).date()
        valid_dates = []
        for i in range(14):
            check_date = now_date + timedelta(days=i)
            async with self._limiter.acquire(weight=1):
                try:
                    chain_info = await self._runtime.option_chain_info_by_date("SPY.US", check_date)
                except Exception as exc:
                    if "301607" in str(exc):
                        self._limiter.trigger_cooldown()
                    logger.warning("[Tier3Poller] Metadata fetch failed: %s", exc)
                    continue
            if chain_info and len(chain_info) > 0:
                valid_dates.append((check_date, chain_info))
        weekly_date = None
        weekly_chain = None
        for check_date, info in valid_dates[2:]:
            if check_date.weekday() == 4:
                weekly_date = check_date
                weekly_chain = info
                break
        if not weekly_date or not weekly_chain:
            logger.warning("[Tier3Poller] Could not find Weekly expiry — skipping metadata refresh.")
            return False
        spot = self._get_spot() or 0.0
        sym_to_strike, standard_by_symbol, kept = build_symbol_metadata_native(
            list(weekly_chain),
            spot=spot,
            window=TIER3_WINDOW,
        )
        self._meta_expiry = weekly_date
        self._meta_sym_to_strike = sym_to_strike
        self._meta_standard_by_symbol = standard_by_symbol
        self.expiry = weekly_date
        logger.info(
            "[Tier3Poller] Metadata refreshed: Weekly=%s, %d symbols within ±%spt",
            weekly_date,
            kept,
            TIER3_WINDOW,
        )
        return True

    async def _fetch(self, spot: float) -> None:
        self._syncing = True
        try:
            today = datetime.now(ZoneInfo("US/Eastern")).date()
            needs_refresh = self._meta_expiry is None or self._meta_expiry < today
            if needs_refresh:
                if not await self._refresh_metadata():
                    return
            else:
                logger.debug(
                    "[Tier3Poller] Using cached metadata: Weekly=%s, %d symbols",
                    self._meta_expiry,
                    len(self._meta_sym_to_strike),
                )
            symbols = list(self._meta_sym_to_strike.keys())
            if not symbols:
                return
            weekly_date = self._meta_expiry
            all_data: list[dict[str, Any]] = []
            batch_size = max(1, min(50, self._limiter.max_symbol_weight))
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i : i + batch_size]
                async with self._limiter.acquire(weight=len(batch)):
                    try:
                        results = await self._runtime.calc_indexes(
                            batch,
                            [CalcIndex.Volume, CalcIndex.OpenInterest, CalcIndex.ImpliedVolatility, CalcIndex.Premium],
                        )
                        all_data.extend(
                            normalize_calc_rows_native(
                                list(results),
                                expiry=str(weekly_date),
                                tier="T3",
                                sym_to_strike=self._meta_sym_to_strike,
                                standard_by_symbol=self._meta_standard_by_symbol,
                            )
                        )
                    except Exception as exc:
                        if "301607" in str(exc):
                            self._limiter.trigger_cooldown()
                        logger.info("[Tier3Poller] Batch recovery active: %s", exc)
            self.cache = top_open_interest_native(all_data, limit=TOP_N)
            logger.info("[Tier3Poller] Synced Top %d OI anchors (Weekly=%s, ±%spt)", TOP_N, weekly_date, TIER3_WINDOW)
        finally:
            self._syncing = False


__all__ = ["Tier2Poller", "Tier3Poller"]
