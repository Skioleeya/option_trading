"""IV Baseline Sync — Staggered REST IV/OI Polling.

Uses the shared APIRateLimiter for all calc_indexes calls.
Now operates as a fallback/initial warmup layer — primary IV now comes
from WebSocket OptionQuote push (see OptionChainBuilder._update_contract_in_memory).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from longport.openapi import QuoteContext, CalcIndex

from app.services.feeds.rate_limiter import APIRateLimiter

logger = logging.getLogger(__name__)


class IVBaselineSync:
    """Manages IV/OI baseline synchronization for Tier 1 symbols.

    Responsibilities:
    - Initial warm_up: batch-fetch IV/OI for all new symbols (ATM-first).
    - Periodic staggered sync (120s cycle) to keep iv_cache fresh as fallback.
    - All REST calls go through the shared APIRateLimiter.

    RACE FIX (Race 3): iv_cache and oi_cache are only written through
    apply_iv_update(), which is safe to call from the asyncio thread.
    The WS callback in OptionChainBuilder calls this method after being
    routed to the asyncio thread via call_soon_threadsafe (Race 2 fix).
    """

    def __init__(self, rate_limiter: APIRateLimiter) -> None:
        self.iv_cache: dict[str, float] = {}        # symbol -> implied_volatility
        self.oi_cache: dict[str, int] = {}            # symbol -> open_interest
        # PP-2/3 FIX: per-symbol spot reference (replaces single global float).
        # Each symbol now records the spot price at the moment its IV was
        # fetched from REST, so skew_adjust_iv always uses the correct baseline.
        self.spot_at_sync: dict[str, float] = {}     # symbol -> spot @ IV-sync time
        self._task: asyncio.Task | None = None
        self._warming_up = False
        self._limiter = rate_limiter
        self._loop: asyncio.AbstractEventLoop | None = None  # set by OptionChainBuilder.initialize()

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Inject the asyncio event loop reference (called from OptionChainBuilder.initialize)."""
        self._loop = loop

    def apply_iv_update(self, symbol: str, iv: float | None, oi: int | None = None) -> None:
        """Controlled write point for iv_cache / oi_cache.

        Called from the asyncio thread only (either from _staggered_sync or from
        _update_contract_in_memory after call_soon_threadsafe routing).
        Plain dict writes are safe because this always runs on the event loop thread.
        """
        if iv is not None:
            self.iv_cache[symbol] = iv
        if oi is not None:
            self.oi_cache[symbol] = oi

    def start(self, ctx: QuoteContext, get_symbols_fn: Callable[[], set[str]],
              get_spot_fn: Callable[[], float | None]) -> None:
        """Start the background sync loop."""
        self._ctx = ctx
        self._get_symbols = get_symbols_fn
        self._get_spot = get_spot_fn
        if self._task is None:
            self._task = asyncio.create_task(self._loop_task())

    async def stop(self) -> None:
        """Cancel the background task."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def warm_up(self, symbols: list[str]) -> None:
        """Initial baseline sync for freshly subscribed symbols (ATM-first)."""
        if not symbols or self._warming_up:
            return

        self._warming_up = True
        try:
            logger.info(f"[IVBaselineSync] Warming up {len(symbols)} symbols.")

            # Prioritize ATM strikes for immediate chart population
            symbols = self._sort_by_proximity(symbols)
            spot = self._get_spot()  # Fetch here so it's in scope for spot_at_sync below

            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                logger.warning(f"[IVSync] Warm-up batch {i//batch_size + 1}/{len(symbols)//batch_size + 1} starting...")
                async with self._limiter.acquire():
                    try:
                        logger.warning(f"[IVSync] Calling calc_indexes for {len(batch)} symbols...")
                        results = self._ctx.calc_indexes(
                            batch, [CalcIndex.ImpliedVolatility, CalcIndex.OpenInterest]
                        )
                        logger.warning(f"[IVSync] Received {len(results or [])} items.")
                        for item in results:
                            iv = float(item.implied_volatility) / 100.0 if item.implied_volatility else None
                            oi = int(item.open_interest) if item.open_interest else None
                            self.apply_iv_update(item.symbol, iv, oi)
                            if spot is not None:
                                self.spot_at_sync[item.symbol] = spot
                    except Exception as e:
                        logger.warning(f"[IVSync] Warm-up batch failed: {e}")
                        if "301607" in str(e):
                            await asyncio.sleep(10.0)
                
                await asyncio.sleep(1.1)
        except Exception as e:
            logger.info(f"[IVBaselineSync] Warm-up session error: {e}")
        finally:
            self._warming_up = False

    # --- Internal ---

    async def _loop_task(self) -> None:
        """Background loop: staggered sync then sleep."""
        while True:
            try:
                symbols = self._get_symbols()
                if symbols:
                    await self._staggered_sync(list(symbols))
            except Exception as e:
                logger.error(f"[IVBaselineSync] Loop error: {e}")
            await asyncio.sleep(300)  # Reduced from 5s to 300s (5-min cycle)

    async def _staggered_sync(self, symbols: list[str]) -> None:
        """2-chunk staggered sync: ATM chunk first, then OTM chunk.

        RACE FIX (Race 3): iv_cache writes use apply_iv_update() (the controlled
        write point).
        PP-2/3 FIX: spot_at_sync is written per-symbol at the moment the REST
        call completes for that specific batch, preventing the 15s stagger window
        from causing ATM symbols to inherit the OTM chunk's spot reference.
        """
        # CONTINUOUS ASSURANCE: re-sort every cycle against latest spot
        symbols = self._sort_by_proximity(symbols)
        total = len(symbols)
        logger.warning(
            f"[IVSync] FULL CYCLE START: {total} symbols, "
            f"iv_cache_size={len(self.iv_cache)}, spot={self._get_spot()}"
        )

        half = total // 2
        chunks = [symbols[:half], symbols[half:]]

        for idx, chunk in enumerate(chunks):
            if not chunk:
                continue

            iv_before = len(self.iv_cache)
            logger.warning(
                f"[IVSync] chunk {idx+1}/2 START: {len(chunk)} syms, "
                f"iv_cache_size={iv_before}, spot={self._get_spot()}"
            )

            batch_size = 50
            for i in range(0, len(chunk), batch_size):
                batch = chunk[i:i + batch_size]
                # PP-3 FIX: capture spot immediately before each REST call so
                # each batch's symbols get the most precise spot reference.
                spot_ref_now = self._get_spot()
                async with self._limiter.acquire():
                    try:
                        results = self._ctx.calc_indexes(
                            batch, [CalcIndex.ImpliedVolatility, CalcIndex.OpenInterest]
                        )
                        for item in results:
                            iv = float(item.implied_volatility) / 100.0 if item.implied_volatility else None
                            oi = int(item.open_interest) if item.open_interest else None
                            self.apply_iv_update(item.symbol, iv, oi)
                            # PP-2/3 FIX: per-symbol spot ref recorded at batch time
                            if spot_ref_now is not None:
                                self.spot_at_sync[item.symbol] = spot_ref_now
                    except Exception as e:
                        if "301607" in str(e):
                            self._limiter.trigger_cooldown()
                            await asyncio.sleep(5.0) # Local pause
                        logger.warning(f"[IVBaselineSync] Batch failed: {e}")

                await asyncio.sleep(1.1)  # Respect 1-sec per-call cadence

            iv_after = len(self.iv_cache)
            logger.warning(
                f"[IVSync] chunk {idx+1}/2 END: iv_cache_size={iv_after} "
                f"(+{iv_after - iv_before} added), spot_at_sync_entries={len(self.spot_at_sync)}"
            )

            # Stagger between ATM and OTM chunks to give other callers breathing room
            if idx == 0 and len(chunks) > 1:
                logger.warning(
                    "[IVSync] ATM chunk done. Stalling 15s before OTM batch — "
                    "each symbol already has its own spot_at_sync (PP-3 fixed)."
                )
                await asyncio.sleep(15.0)

        logger.warning(f"[IVSync] FULL CYCLE END: iv_cache_size={len(self.iv_cache)}")

    def _sort_by_proximity(self, symbols: list[str]) -> list[str]:
        """Sort symbols by distance from current spot price."""
        spot = self._get_spot()
        if not spot:
            return symbols

        def get_dist(s: str) -> float:
            try:
                # LONGPORT FORMAT: SPY + YYMMDD + C/P + 6+ digit strike (.US)
                # Example: SPY260304C673000.US
                # index 0-2 (SPY), 3-8 (date), 9 (C/P), 10+ (strike)
                strike_part = s[10:].split('.')[0]
                return abs(float(strike_part) / 1000.0 - spot)
            except (ValueError, IndexError):
                return 999.0

        return sorted(symbols, key=get_dist)
