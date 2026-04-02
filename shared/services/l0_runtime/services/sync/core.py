"""IV/OI warm-up and staggered sync owner."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from longport.openapi import CalcIndex

from shared.config import settings
from shared.system.persistent_oi_store import PersistentOIStore
from shared.services.l0_runtime.services.sync import (
    SYNC_CHUNK_COUNT,
    SYNC_COOLDOWN_SLEEP_SECONDS,
    WARMUP_COOLDOWN_SECONDS,
    WARMUP_COOLDOWN_SLEEP_SECONDS,
    clamp_subscription_cap,
    is_rate_limit_error,
    iter_batches,
    parse_implied_volatility,
    parse_open_interest,
    safe_batch_size,
    split_sync_chunks,
)
from shared.services.l0_runtime.source.runtime import APIRateLimiter
from shared.services.l0_runtime.source.runtime.quote_runtime import L0QuoteRuntime

logger = logging.getLogger(__name__)


class IVBaselineSync:
    """Manage IV/OI baseline synchronization for Tier 1 symbols."""

    def __init__(self, rate_limiter: APIRateLimiter) -> None:
        self.iv_cache: dict[str, float] = {}
        self.oi_cache: dict[str, int] = {}
        self.spot_at_sync: dict[str, float] = {}
        self._on_update: Callable[[str, Any], None] | None = None
        self._task: asyncio.Task | None = None
        self._warming_up = False
        self._bootstrap_warmup_done = False
        self._last_warmup_signature: frozenset[str] | None = None
        self._last_warmup_ts: float = 0.0
        self._warmup_dedupe_window_sec = 120.0
        self._limiter = rate_limiter
        self._loop: asyncio.AbstractEventLoop | None = None
        self._oi_store = PersistentOIStore()
        self._get_price_repair_symbols: Callable[[], set[str]] | None = None
        self._needs_price_repair: Callable[[str], bool] | None = None
        self._price_repair_last_ts: dict[str, float] = {}

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def preload_oi_from_disk(self, date_str: str) -> int:
        baseline = self._oi_store.get_baseline(date_str)
        if not baseline:
            logger.info("[IVBaselineSync] No disk OI baseline for %s — cold start, GEX=0 until warm_up.", date_str)
            return 0
        loaded = 0
        for symbol, oi in baseline.items():
            if symbol not in self.oi_cache and isinstance(oi, int) and oi > 0:
                self.oi_cache[symbol] = oi
                loaded += 1
        logger.warning(
            "[IVBaselineSync] OI HOT-START: preloaded %d/%d entries from disk baseline %s. GEX will be non-zero from first tick.",
            loaded,
            len(baseline),
            date_str,
        )
        return loaded

    def _persist_oi_to_disk(self, date_str: str) -> None:
        chain_like = [{"symbol": sym, "open_interest": oi} for sym, oi in self.oi_cache.items() if oi > 0]
        if not chain_like:
            return
        if self._oi_store.save_baseline(date_str, chain_like):
            logger.info("[IVBaselineSync] Persisted %d OI entries to disk for %s.", len(chain_like), date_str)

    def apply_iv_update(self, symbol: str, iv: float | None, oi: int | None = None) -> None:
        if iv is not None:
            self.iv_cache[symbol] = iv
        if oi is not None:
            self.oi_cache[symbol] = oi

    def start(
        self,
        runtime: L0QuoteRuntime,
        get_symbols_fn: Callable[[], set[str]],
        get_spot_fn: Callable[[], float | None],
        on_update: Callable[[str, Any], None] | None = None,
        get_price_repair_symbols_fn: Callable[[], set[str]] | None = None,
        needs_price_repair_fn: Callable[[str], bool] | None = None,
    ) -> None:
        self._runtime = runtime
        self._get_symbols = get_symbols_fn
        self._get_spot = get_spot_fn
        self._on_update = on_update
        self._get_price_repair_symbols = get_price_repair_symbols_fn
        self._needs_price_repair = needs_price_repair_fn
        if self._task is None:
            self._task = asyncio.create_task(self._loop_task())

    async def stop(self) -> None:
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
        return safe_batch_size(self._limiter.max_symbol_weight)

    def _should_skip_warm_up(self, symbols: list[str], now_ts: float) -> bool:
        signature = frozenset(symbols)
        if self._last_warmup_signature != signature:
            return False
        if (now_ts - self._last_warmup_ts) >= self._warmup_dedupe_window_sec:
            return False
        logger.info("[IVSync] Warm-up deduplicated: %d symbols within %.0fs window.", len(signature), self._warmup_dedupe_window_sec)
        return True

    def _mark_warm_up_signature(self, symbols: list[str], now_ts: float) -> None:
        self._last_warmup_signature = frozenset(symbols)
        self._last_warmup_ts = now_ts

    def _apply_batch_items(self, *, results: list[Any] | None, spot_ref: float | None, track_any_update: bool) -> bool:
        any_update = False
        for item in results or []:
            iv = parse_implied_volatility(item)
            oi = parse_open_interest(item)
            self.apply_iv_update(item.symbol, iv, oi)
            if iv is not None or oi is not None:
                any_update = True
            if self._on_update:
                self._on_update(item.symbol, item)
            if iv is not None and spot_ref is not None:
                self.spot_at_sync[item.symbol] = spot_ref
        return any_update if track_any_update else False

    async def _fetch_batch_results(self, batch: list[str], warm_up_mode: bool) -> list[Any] | None:
        async with self._limiter.acquire(weight=len(batch)):
            try:
                return await self._runtime.calc_indexes(batch, [CalcIndex.ImpliedVolatility, CalcIndex.OpenInterest])
            except Exception as exc:
                await self._handle_batch_exception(exc, warm_up_mode)
                return None

    async def _handle_batch_exception(self, exc: Exception, warm_up_mode: bool) -> None:
        logger.warning("[IVSync] Warm-up batch failed: %s", exc) if warm_up_mode else logger.warning("[IVBaselineSync] Batch failed: %s", exc)
        if not is_rate_limit_error(exc):
            return
        if warm_up_mode:
            self._limiter.trigger_cooldown(seconds=WARMUP_COOLDOWN_SECONDS)
            await asyncio.sleep(WARMUP_COOLDOWN_SLEEP_SECONDS)
            return
        self._limiter.trigger_cooldown()
        await asyncio.sleep(SYNC_COOLDOWN_SLEEP_SECONDS)

    async def _sync_batches(self, *, symbols: list[str], spot_provider: Callable[[], float | None], warm_up_mode: bool, warm_up_batch_offset: int = 0) -> bool:
        any_update = False
        batch_size = self._safe_batch_size()
        for batch_index, batch in enumerate(iter_batches(symbols, batch_size), start=1):
            if warm_up_mode:
                logger.warning("[IVSync] Warm-up batch %d STARTING (batch size %d)...", warm_up_batch_offset + batch_index, len(batch))
            spot_ref_now = spot_provider()
            results = await self._fetch_batch_results(batch, warm_up_mode)
            if results is None:
                continue
            if warm_up_mode:
                logger.warning("[IVSync] Batch SUCCESS: Received %d results.", len(results or []))
            updated = self._apply_batch_items(results=results, spot_ref=spot_ref_now, track_any_update=warm_up_mode)
            await self._repair_batch_prices(batch)
            if updated:
                any_update = True
        return any_update

    async def _repair_batch_prices(self, batch: list[str]) -> None:
        if not self._on_update or not self._get_price_repair_symbols or not self._needs_price_repair:
            return
        from shared.services.l0_runtime.services.repair import repair_symbol_prices

        await repair_symbol_prices(
            batch=batch,
            repair_symbols=self._get_price_repair_symbols(),
            needs_price_repair=self._needs_price_repair,
            last_repair_at=self._price_repair_last_ts,
            now_mono=time.monotonic(),
            runtime=self._runtime,
            limiter=self._limiter,
            on_update=self._on_update,
            log_prefix="[IVSync]",
        )

    async def warm_up(self, symbols: list[str]) -> None:
        if not symbols or self._warming_up:
            return
        subscription_cap = clamp_subscription_cap(settings.subscription_max)
        if len(symbols) > subscription_cap:
            logger.warning("[IVSync] Warm-up symbols exceed cap: %d -> %d", len(symbols), subscription_cap)
            symbols = self._sort_by_proximity(symbols)[:subscription_cap]
        now_ts = time.monotonic()
        if self._should_skip_warm_up(symbols, now_ts):
            return
        self._mark_warm_up_signature(symbols, now_ts)
        self._warming_up = True
        any_update = False
        try:
            logger.info("[IVBaselineSync] Warming up %d symbols.", len(symbols))
            symbols = self._sort_by_proximity(symbols)
            warm_up_spot = self._get_spot()
            any_update = await self._sync_batches(symbols=symbols, spot_provider=lambda: warm_up_spot, warm_up_mode=True)
        except Exception as exc:
            logger.info("[IVBaselineSync] Warm-up session error: %s", exc)
        finally:
            self._warming_up = False
            if any_update:
                self._bootstrap_warmup_done = True
            self._persist_oi_to_disk(datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d"))

    async def _loop_task(self) -> None:
        logger.warning("[IVSync] Background loop task STARTED.")
        await asyncio.sleep(3.0)
        try:
            symbols = list(self._get_symbols())
            if symbols and not self._bootstrap_warmup_done and not self.iv_cache:
                logger.info("[IVSync] Triggering initial warm_up for %d symbols.", len(symbols))
                await self.warm_up(symbols)
            elif symbols:
                logger.info("[IVSync] Initial warm_up skipped: already bootstrapped (symbols=%d iv_cache=%d).", len(symbols), len(self.iv_cache))
            else:
                logger.warning("[IVSync] No symbols yet for initial warm_up — will retry in 60s loop.")
        except Exception as exc:
            logger.error("[IVSync] Initial warm_up failed: %s", exc)
        while True:
            try:
                symbols = self._get_symbols()
                if symbols:
                    await self._staggered_sync(list(symbols))
                else:
                    logger.debug("[IVSync] No symbols to sync.")
            except Exception as exc:
                logger.error("[IVBaselineSync] Loop error: %s", exc)
            await asyncio.sleep(60)

    async def _sync_chunk(self, chunk: list[str], chunk_index: int) -> None:
        if not chunk:
            return
        iv_before = len(self.iv_cache)
        logger.warning("[IVSync] chunk %d/%d START: %d syms, iv_cache_size=%d, spot=%s", chunk_index, SYNC_CHUNK_COUNT, len(chunk), iv_before, self._get_spot())
        await self._sync_batches(symbols=chunk, spot_provider=self._get_spot, warm_up_mode=False)
        iv_after = len(self.iv_cache)
        logger.warning("[IVSync] chunk %d/%d END: iv_cache_size=%d (+%d added), spot_at_sync_entries=%d", chunk_index, SYNC_CHUNK_COUNT, iv_after, iv_after - iv_before, len(self.spot_at_sync))

    async def _staggered_sync(self, symbols: list[str]) -> None:
        symbols = self._sort_by_proximity(symbols)
        logger.warning("[IVSync] FULL CYCLE START: %d symbols, iv_cache_size=%d, spot=%s", len(symbols), len(self.iv_cache), self._get_spot())
        for idx, chunk in enumerate(split_sync_chunks(symbols), start=1):
            await self._sync_chunk(chunk, idx)
        logger.warning("[IVSync] FULL CYCLE END: iv_cache_size=%d", len(self.iv_cache))
        self._persist_oi_to_disk(datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d"))

    def _sort_by_proximity(self, symbols: list[str], symbol_to_strike: dict[str, float] | None = None) -> list[str]:
        spot = self._get_spot()
        if not spot:
            return symbols

        def get_dist(symbol: str) -> float:
            if symbol_to_strike and symbol in symbol_to_strike:
                return abs(symbol_to_strike[symbol] - spot)
            try:
                strike_part = symbol[10:].split(".")[0]
                strike_val = float(strike_part) / 1000.0
                logger.debug("[IVSync] _sort_by_proximity: dict miss for %s, using string parse", symbol)
                return abs(strike_val - spot)
            except (ValueError, IndexError):
                return 999.0

        return sorted(symbols, key=get_dist)
