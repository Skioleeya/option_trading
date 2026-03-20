"""IV Baseline Sync — Staggered REST IV/OI Polling.

REST API 是 IV 的唯一来源（长桥 WS 长连接不提供 IV）。
本模块负责：初次 warm_up + 定期 staggered sync（60s 周期）保持 iv_cache 新鲜。
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from longport.openapi import CalcIndex

from l0_ingest.feeds.iv_baseline_sync_support import (
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
    """

    def __init__(self, rate_limiter: APIRateLimiter) -> None:
        self.iv_cache: dict[str, float] = {}
        self.oi_cache: dict[str, int] = {}
        # per-symbol spot reference for sticky-strike correction.
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

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Inject the asyncio event loop reference (called from OptionChainBuilder.initialize)."""
        self._loop = loop

    def preload_oi_from_disk(self, date_str: str) -> int:
        """Hot-start: prime oi_cache from today's disk baseline BEFORE first REST warm_up."""
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
            "[IVBaselineSync] OI HOT-START: preloaded %d/%d entries from disk baseline %s. "
            "GEX will be non-zero from first tick.",
            loaded,
            len(baseline),
            date_str,
        )
        return loaded

    def _persist_oi_to_disk(self, date_str: str) -> None:
        """Write current oi_cache to disk so next restart can hot-start."""
        chain_like = [{"symbol": sym, "open_interest": oi} for sym, oi in self.oi_cache.items() if oi > 0]
        if not chain_like:
            return
        ok = self._oi_store.save_baseline(date_str, chain_like)
        if ok:
            logger.info("[IVBaselineSync] Persisted %d OI entries to disk for %s.", len(chain_like), date_str)

    def apply_iv_update(self, symbol: str, iv: float | None, oi: int | None = None) -> None:
        """Controlled write point for iv_cache / oi_cache."""
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
    ) -> None:
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
        return safe_batch_size(self._limiter.max_symbol_weight)

    def _should_skip_warm_up(self, symbols: list[str], now_ts: float) -> bool:
        signature = frozenset(symbols)
        if self._last_warmup_signature != signature:
            return False
        if (now_ts - self._last_warmup_ts) >= self._warmup_dedupe_window_sec:
            return False
        logger.info(
            "[IVSync] Warm-up deduplicated: %d symbols within %.0fs window.",
            len(signature),
            self._warmup_dedupe_window_sec,
        )
        return True

    def _mark_warm_up_signature(self, symbols: list[str], now_ts: float) -> None:
        self._last_warmup_signature = frozenset(symbols)
        self._last_warmup_ts = now_ts

    def _apply_batch_items(
        self,
        *,
        results: list[Any] | None,
        spot_ref: float | None,
        track_any_update: bool,
    ) -> bool:
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
                return await self._runtime.calc_indexes(
                    batch,
                    [CalcIndex.ImpliedVolatility, CalcIndex.OpenInterest],
                )
            except Exception as exc:
                await self._handle_batch_exception(exc, warm_up_mode)
                return None

    async def _handle_batch_exception(self, exc: Exception, warm_up_mode: bool) -> None:
        if warm_up_mode:
            logger.warning("[IVSync] Warm-up batch failed: %s", exc)
        else:
            logger.warning("[IVBaselineSync] Batch failed: %s", exc)
        if not is_rate_limit_error(exc):
            return
        if warm_up_mode:
            self._limiter.trigger_cooldown(seconds=WARMUP_COOLDOWN_SECONDS)
            await asyncio.sleep(WARMUP_COOLDOWN_SLEEP_SECONDS)
            return
        self._limiter.trigger_cooldown()
        await asyncio.sleep(SYNC_COOLDOWN_SLEEP_SECONDS)

    async def _sync_batches(
        self,
        *,
        symbols: list[str],
        spot_provider: Callable[[], float | None],
        warm_up_mode: bool,
        warm_up_batch_offset: int = 0,
    ) -> bool:
        any_update = False
        batch_size = self._safe_batch_size()
        for batch_index, batch in enumerate(iter_batches(symbols, batch_size), start=1):
            if warm_up_mode:
                logger.warning(
                    "[IVSync] Warm-up batch %d STARTING (batch size %d)...",
                    warm_up_batch_offset + batch_index,
                    len(batch),
                )
            spot_ref_now = spot_provider()
            results = await self._fetch_batch_results(batch, warm_up_mode)
            if results is None:
                continue
            if warm_up_mode:
                logger.warning("[IVSync] Batch SUCCESS: Received %d results.", len(results or []))
            updated = self._apply_batch_items(
                results=results,
                spot_ref=spot_ref_now,
                track_any_update=warm_up_mode,
            )
            if updated:
                any_update = True
        return any_update

    async def warm_up(self, symbols: list[str]) -> None:
        """Initial baseline sync for freshly subscribed symbols (ATM-first)."""
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
            any_update = await self._sync_batches(
                symbols=symbols,
                spot_provider=lambda: warm_up_spot,
                warm_up_mode=True,
            )
        except Exception as exc:
            logger.info("[IVBaselineSync] Warm-up session error: %s", exc)
        finally:
            self._warming_up = False
            if any_update:
                self._bootstrap_warmup_done = True
            today_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
            self._persist_oi_to_disk(today_str)

    async def _loop_task(self) -> None:
        """Background loop: initial warm-up, then staggered sync every 60s."""
        logger.warning("[IVSync] Background loop task STARTED.")

        await asyncio.sleep(3.0)
        try:
            symbols = list(self._get_symbols())
            if symbols and not self._bootstrap_warmup_done and not self.iv_cache:
                logger.info("[IVSync] Triggering initial warm_up for %d symbols.", len(symbols))
                await self.warm_up(symbols)
            elif symbols:
                logger.info(
                    "[IVSync] Initial warm_up skipped: already bootstrapped (symbols=%d iv_cache=%d).",
                    len(symbols),
                    len(self.iv_cache),
                )
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
        logger.warning(
            "[IVSync] chunk %d/%d START: %d syms, iv_cache_size=%d, spot=%s",
            chunk_index,
            SYNC_CHUNK_COUNT,
            len(chunk),
            iv_before,
            self._get_spot(),
        )
        await self._sync_batches(
            symbols=chunk,
            spot_provider=self._get_spot,
            warm_up_mode=False,
        )
        iv_after = len(self.iv_cache)
        logger.warning(
            "[IVSync] chunk %d/%d END: iv_cache_size=%d (+%d added), spot_at_sync_entries=%d",
            chunk_index,
            SYNC_CHUNK_COUNT,
            iv_after,
            iv_after - iv_before,
            len(self.spot_at_sync),
        )

    async def _staggered_sync(self, symbols: list[str]) -> None:
        """2-chunk staggered sync: ATM chunk first, then OTM chunk."""
        symbols = self._sort_by_proximity(symbols)
        total = len(symbols)
        logger.warning(
            "[IVSync] FULL CYCLE START: %d symbols, iv_cache_size=%d, spot=%s",
            total,
            len(self.iv_cache),
            self._get_spot(),
        )

        for idx, chunk in enumerate(split_sync_chunks(symbols), start=1):
            await self._sync_chunk(chunk, idx)

        logger.warning("[IVSync] FULL CYCLE END: iv_cache_size=%d", len(self.iv_cache))
        today_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
        self._persist_oi_to_disk(today_str)

    def _sort_by_proximity(
        self,
        symbols: list[str],
        symbol_to_strike: dict[str, float] | None = None,
    ) -> list[str]:
        """Sort symbols by distance from current spot price.

        P1-6 FIX: Uses symbol_to_strike dict lookup (from SubscriptionManager) when available,
        falling back to hardcoded character-offset parsing only if the dict misses.
        """
        spot = self._get_spot()
        if not spot:
            return symbols

        def get_dist(symbol: str) -> float:
            # Prefer dict lookup (reliable, no format assumptions)
            if symbol_to_strike and symbol in symbol_to_strike:
                return abs(symbol_to_strike[symbol] - spot)
            # Fallback: LongPort-specific format symbol[10:].split(".")[0] / 1000.0
            # (fragile if symbol format changes — TODO: remove once dict is always available)
            try:
                strike_part = symbol[10:].split(".")[0]
                strike_val = float(strike_part) / 1000.0
                logger.debug("[IVSync] _sort_by_proximity: dict miss for %s, using string parse", symbol)
                return abs(strike_val - spot)
            except (ValueError, IndexError):
                return 999.0

        return sorted(symbols, key=get_dist)
