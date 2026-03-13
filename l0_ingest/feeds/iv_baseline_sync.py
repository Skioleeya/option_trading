"""IV Baseline Sync — Staggered REST IV/OI Polling.

REST API 是 IV 的唯一来源（长桥 WS 长连接不提供 IV）。
本模块负责：初次 warm_up + 定期 staggered sync（60s 周期）保持 iv_cache 新鲜。
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from longport.openapi import CalcIndex

from l0_ingest.feeds.rate_limiter import APIRateLimiter
from l0_ingest.feeds.quote_runtime import L0QuoteRuntime
from shared.config import settings
from shared.system.persistent_oi_store import PersistentOIStore

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
        self.spot_at_sync: dict[str, float] = {}     # symbol -> spot @ IV-sync time
        self._on_update: Callable[[str, Any], None] | None = None
        self._task: asyncio.Task | None = None
        self._warming_up = False
        self._bootstrap_warmup_done = False
        self._last_warmup_signature: frozenset[str] | None = None
        self._last_warmup_ts: float = 0.0
        self._warmup_dedupe_window_sec = 120.0
        self._limiter = rate_limiter
        self._loop: asyncio.AbstractEventLoop | None = None  # set by OptionChainBuilder.initialize()
        self._oi_store = PersistentOIStore()          # disk persistence for OI hotstart

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Inject the asyncio event loop reference (called from OptionChainBuilder.initialize)."""
        self._loop = loop

    def preload_oi_from_disk(self, date_str: str) -> int:
        """Hot-start: prime oi_cache from today's disk baseline BEFORE first REST warm_up.

        Call this immediately after set_event_loop() in OptionChainBuilder.initialize().
        Each entry only fills symbols NOT already in oi_cache (REST values always win).
        Returns the number of symbols preloaded (0 = no baseline for today yet).
        """
        baseline = self._oi_store.get_baseline(date_str)
        if not baseline:
            logger.info(f"[IVBaselineSync] No disk OI baseline for {date_str} — cold start, GEX=0 until warm_up.")
            return 0
        loaded = 0
        for symbol, oi in baseline.items():
            if symbol not in self.oi_cache and isinstance(oi, int) and oi > 0:
                self.oi_cache[symbol] = oi
                loaded += 1
        logger.warning(
            f"[IVBaselineSync] OI HOT-START: preloaded {loaded}/{len(baseline)} entries from "
            f"disk baseline {date_str}. GEX will be non-zero from first tick."
        )
        return loaded

    def _persist_oi_to_disk(self, date_str: str) -> None:
        """Write current oi_cache to disk so next restart can hot-start."""
        chain_like = [
            {"symbol": sym, "open_interest": oi}
            for sym, oi in self.oi_cache.items() if oi > 0
        ]
        if chain_like:
            ok = self._oi_store.save_baseline(date_str, chain_like)
            if ok:
                logger.info(f"[IVBaselineSync] Persisted {len(chain_like)} OI entries to disk for {date_str}.")

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

    def start(self, runtime: L0QuoteRuntime, get_symbols_fn: Callable[[], set[str]],
              get_spot_fn: Callable[[], float | None],
              on_update: Callable[[str, Any], None] | None = None) -> None:
        """Start the background sync loop."""
        self._runtime = runtime
        self._get_symbols = get_symbols_fn
        self._get_spot = get_spot_fn
        self._on_update = on_update
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

    @property
    def warming_up(self) -> bool:
        return self._warming_up

    @property
    def bootstrap_warmup_done(self) -> bool:
        return self._bootstrap_warmup_done

    def _safe_batch_size(self) -> int:
        return max(1, min(50, self._limiter.max_symbol_weight))

    async def warm_up(self, symbols: list[str]) -> None:
        """Initial baseline sync for freshly subscribed symbols (ATM-first)."""
        if not symbols or self._warming_up:
            return
        subscription_cap = max(1, min(int(settings.subscription_max), 500))
        if len(symbols) > subscription_cap:
            logger.warning(
                "[IVSync] Warm-up symbols exceed cap: %d -> %d",
                len(symbols),
                subscription_cap,
            )
            symbols = self._sort_by_proximity(symbols)[:subscription_cap]
        signature = frozenset(symbols)
        now_ts = time.monotonic()
        if (
            self._last_warmup_signature == signature
            and (now_ts - self._last_warmup_ts) < self._warmup_dedupe_window_sec
        ):
            logger.info(
                "[IVSync] Warm-up deduplicated: %d symbols within %.0fs window.",
                len(signature),
                self._warmup_dedupe_window_sec,
            )
            return
        self._last_warmup_signature = signature
        self._last_warmup_ts = now_ts

        self._warming_up = True
        any_update = False
        try:
            logger.info(f"[IVBaselineSync] Warming up {len(symbols)} symbols.")

            # Prioritize ATM strikes for immediate chart population
            symbols = self._sort_by_proximity(symbols)
            spot = self._get_spot()  # Fetch here so it's in scope for spot_at_sync below

            batch_size = self._safe_batch_size()
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                logger.warning(f"[IVSync] Warm-up batch {i//batch_size + 1} STARTING (batch size {len(batch)})...")
                async with self._limiter.acquire(weight=len(batch)):
                    try:
                        results = await self._runtime.calc_indexes(
                            batch,
                            [CalcIndex.ImpliedVolatility, CalcIndex.OpenInterest],
                        )
                        n_res = len(results or [])
                        logger.warning(f"[IVSync] Batch SUCCESS: Received {n_res} results.")
                        for item in results:
                            iv = None
                            iv_normalized = getattr(item, "implied_volatility_decimal", None)
                            if iv_normalized is not None:
                                try:
                                    f_iv = float(iv_normalized)
                                    if math.isfinite(f_iv):
                                        iv = f_iv
                                except (ValueError, TypeError):
                                    pass
                            elif item.implied_volatility:
                                try:
                                    f_iv = float(item.implied_volatility)
                                    if math.isfinite(f_iv):
                                        iv = f_iv / 100.0 if f_iv > 1.0 else f_iv
                                except (ValueError, TypeError):
                                    pass
                                
                            oi_raw = item.open_interest
                            oi = None
                            if oi_raw:
                                try:
                                    oi = int(oi_raw)
                                except (ValueError, TypeError): pass
                                
                            self.apply_iv_update(item.symbol, iv, oi)
                            if iv is not None or oi is not None:
                                any_update = True
                            if self._on_update:
                                self._on_update(item.symbol, item)
                            # BUG-3 FIX: IV 有效才记录 spot ref，防止 Sticky Strike 矫正使用错误基准
                            if iv is not None and spot is not None:
                                self.spot_at_sync[item.symbol] = spot
                    except Exception as e:
                        logger.warning(f"[IVSync] Warm-up batch failed: {e}")
                        if "301607" in str(e):
                            self._limiter.trigger_cooldown(seconds=60)
                            await asyncio.sleep(10.0)
                
                # Removed redundant 1.1s sleep: pacing is now handled solely by self._limiter.acquire()
        except Exception as e:
            logger.info(f"[IVBaselineSync] Warm-up session error: {e}")
        finally:
            self._warming_up = False
            if any_update:
                self._bootstrap_warmup_done = True
            # OI-PERSIST FIX: write REST-fetched OI to disk so next restart hot-starts
            today_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
            self._persist_oi_to_disk(today_str)

    # --- Internal ---

    async def _loop_task(self) -> None:
        """Background loop: initial warm-up, then staggered sync every 60s."""
        logger.warning("[IVSync] Background loop task STARTED.")
        
        # ── Initial warm-up: populate iv_cache before the first L1 tick ──
        # Wait briefly for subscriptions to arrive before fetching IV
        await asyncio.sleep(3.0)
        try:
            symbols = list(self._get_symbols())
            if symbols and not self._bootstrap_warmup_done and not self.iv_cache:
                logger.info("[IVSync] Triggering initial warm_up for %d symbols.", len(symbols))
                await self.warm_up(symbols)
            elif symbols:
                logger.info(
                    "[IVSync] Initial warm_up skipped: already bootstrapped "
                    "(symbols=%d iv_cache=%d).",
                    len(symbols),
                    len(self.iv_cache),
                )
            else:
                logger.warning("[IVSync] No symbols yet for initial warm_up — will retry in 60s loop.")
        except Exception as e:
            logger.error("[IVSync] Initial warm_up failed: %s", e)
        
        while True:
            try:
                symbols = self._get_symbols()
                if symbols:
                    await self._staggered_sync(list(symbols))
                else:
                    logger.debug("[IVSync] No symbols to sync.")
            except Exception as e:
                logger.error(f"[IVBaselineSync] Loop error: {e}")
            await asyncio.sleep(60)  # Refresh every 60s

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

            batch_size = self._safe_batch_size()
            for i in range(0, len(chunk), batch_size):
                batch = chunk[i:i + batch_size]
                # PP-3 FIX: capture spot immediately before each REST call so
                # each batch's symbols get the most precise spot reference.
                spot_ref_now = self._get_spot()
                async with self._limiter.acquire(weight=len(batch)):
                    try:
                        results = await self._runtime.calc_indexes(
                            batch,
                            [CalcIndex.ImpliedVolatility, CalcIndex.OpenInterest],
                        )
                        for item in results:
                            iv = None
                            iv_normalized = getattr(item, "implied_volatility_decimal", None)
                            if iv_normalized is not None:
                                try:
                                    f_iv = float(iv_normalized)
                                    if math.isfinite(f_iv):
                                        iv = f_iv
                                except (ValueError, TypeError):
                                    pass
                            elif item.implied_volatility:
                                try:
                                    f_iv = float(item.implied_volatility)
                                    if math.isfinite(f_iv):
                                        iv = f_iv / 100.0 if f_iv > 1.0 else f_iv
                                except (ValueError, TypeError):
                                    pass
                                
                            oi_raw = item.open_interest
                            oi = None
                            if oi_raw:
                                try:
                                    oi = int(oi_raw)
                                except (ValueError, TypeError): pass
                                
                            self.apply_iv_update(item.symbol, iv, oi)
                            if self._on_update:
                                self._on_update(item.symbol, item)
                            # BUG-3 FIX: IV 有效才记录 spot ref，防止 Sticky Strike 矫正使用错误基准
                            if iv is not None and spot_ref_now is not None:
                                self.spot_at_sync[item.symbol] = spot_ref_now
                    except Exception as e:
                        if "301607" in str(e):
                            self._limiter.trigger_cooldown()
                            await asyncio.sleep(5.0) # Local pause
                        logger.warning(f"[IVBaselineSync] Batch failed: {e}")

                # Removed redundant 1.1s sleep: pacing is now handled solely by self._limiter.acquire()

            iv_after = len(self.iv_cache)
            logger.warning(
                f"[IVSync] chunk {idx+1}/2 END: iv_cache_size={iv_after} "
                f"(+{iv_after - iv_before} added), spot_at_sync_entries={len(self.spot_at_sync)}"
            )

            # Removed 15s stall: all batches now use centralized rate limiter for concurrency safety.

        logger.warning(f"[IVSync] FULL CYCLE END: iv_cache_size={len(self.iv_cache)}")

        # BUG-3 FIX: Persist OI after every staggered sync cycle, not just after warm_up.
        # If the process crashes between warm_up and the next restart, the latest REST
        # OI values (fetched by each _staggered_sync call) would otherwise be lost.
        today_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
        self._persist_oi_to_disk(today_str)

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
