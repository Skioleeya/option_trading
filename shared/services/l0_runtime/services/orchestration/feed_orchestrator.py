"""Feed orchestrator owner for L0 service orchestration."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any, Callable
from zoneinfo import ZoneInfo

from shared.config import settings
from shared.services.l0_runtime.services.orchestration import build_header_volatility_aux
from shared.services.l0_runtime.services.repair import repair_symbol_prices

if TYPE_CHECKING:
    from shared.services.l0_runtime.services.subscription import OptionSubscriptionManager
    from shared.services.l0_runtime.services.sync import IVBaselineSync
    from shared.services.l0_runtime.source.runtime import APIRateLimiter
    from shared.services.l0_runtime.source.runtime.quote_runtime import L0QuoteRuntime
    from shared.services.l0_runtime.state import ChainStateStore

logger = logging.getLogger(__name__)


class FeedOrchestrator:
    """Schedules REST polling and subscription refresh using runtime abstraction."""

    def __init__(
        self,
        quote_runtime: "L0QuoteRuntime",
        store: "ChainStateStore",
        sub_mgr: "OptionSubscriptionManager",
        iv_sync: "IVBaselineSync",
        rate_limiter: "APIRateLimiter",
        on_price_repair_update: Callable[[str, Any], None] | None = None,
        needs_price_repair_fn: Callable[[str], bool] | None = None,
    ) -> None:
        self._quote_runtime = quote_runtime
        self._store = store
        self._sub_mgr = sub_mgr
        self._iv_sync = iv_sync
        self._limiter = rate_limiter
        self._mandatory_symbols: set[str] = set()
        self._on_price_repair_update = on_price_repair_update
        self._needs_price_repair = needs_price_repair_fn
        self._price_repair_last_ts: dict[str, float] = {}
        self._start_time = datetime.now(ZoneInfo("US/Eastern"))
        self._last_research: datetime | None = None
        self._running = False
        self._monotonic = time.monotonic
        self._last_refresh_mono = 0.0
        self._refresh_min_interval_sec = 30.0
        self._warmup_merge_window_sec = max(
            1.0,
            float(getattr(settings, "longport_warmup_merge_window_sec", 20)),
        )
        self._research_startup_stable_sec = max(
            1.0,
            float(getattr(settings, "longport_research_startup_stable_sec", 120)),
        )
        self._pending_warmup_symbols: set[str] = set()
        self._pending_warmup_since_mono: float | None = None
        self._official_hv_decimal: float | None = None
        self._official_hv_sample_count: int = 0
        self._official_hv_synced_at_utc: str | None = None
        self._header_volatility_aux: dict[str, Any] = {}
        self._header_volatility_aux_synced_at_utc: str | None = None
        self._header_volatility_aux_last_mono = 0.0
        self._header_volatility_aux_ttl_sec = 60.0
        self._spot_stale_after_sec = 10.0
        self._source_stale = False

    async def run(self) -> None:
        self._running = True
        logger.info("[FeedOrchestrator] Management loop started.")
        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                logger.error("[FeedOrchestrator] Management loop error: %s", exc)
            elapsed = (datetime.now(ZoneInfo("US/Eastern")) - self._start_time).total_seconds()
            cadence = 5.0 if elapsed < 300.0 else 60.0
            await asyncio.sleep(cadence)

    async def stop(self) -> None:
        self._running = False

    def set_mandatory_symbols(self, symbols: set[str]) -> None:
        if symbols != self._mandatory_symbols:
            self._mandatory_symbols = symbols
            logger.info("[FeedOrchestrator] Mandatory symbols updated: %s", symbols)

    @property
    def pending_warmup_count(self) -> int:
        return len(self._pending_warmup_symbols)

    @property
    def mandatory_symbols(self) -> set[str]:
        return set(self._mandatory_symbols)

    @property
    def official_hv_diagnostics(self) -> dict[str, float | int | str | None]:
        return {
            "official_hv_decimal": self._official_hv_decimal,
            "official_hv_sample_count": self._official_hv_sample_count,
            "official_hv_synced_at_utc": self._official_hv_synced_at_utc,
        }

    @property
    def header_volatility_aux_diagnostics(self) -> dict[str, Any]:
        payload = dict(self._header_volatility_aux)
        payload["synced_at_utc"] = self._header_volatility_aux_synced_at_utc
        return payload

    def _subscription_refresh_due(self, now_mono: float) -> bool:
        return (now_mono - self._last_refresh_mono) >= self._refresh_min_interval_sec

    def _queue_warmup_symbols(self, symbols: set[str], now_mono: float) -> None:
        if not symbols:
            return
        if not self._pending_warmup_symbols:
            self._pending_warmup_since_mono = now_mono
        self._pending_warmup_symbols.update(symbols)

    async def _flush_warmup_if_due(self, now_mono: float) -> None:
        if not self._pending_warmup_symbols or self._iv_sync.warming_up:
            return
        pending_since = self._pending_warmup_since_mono
        if pending_since is None:
            self._pending_warmup_since_mono = now_mono
            return
        is_first_startup_flush = not getattr(self, "_first_flush_done", False)
        if not is_first_startup_flush and (now_mono - pending_since) < self._warmup_merge_window_sec:
            return
        self._first_flush_done = True
        batch = sorted(self._pending_warmup_symbols)
        self._pending_warmup_symbols.clear()
        self._pending_warmup_since_mono = None
        logger.info(
            "[FeedOrchestrator] Flushing warm-up queue: symbols=%d merge_window=%.0fs (fast_track=%s)",
            len(batch),
            self._warmup_merge_window_sec,
            is_first_startup_flush,
        )
        await self._iv_sync.warm_up(batch)

    async def _tick(self) -> None:
        now = datetime.now(ZoneInfo("US/Eastern"))
        today = now.strftime("%Y%m%d")
        now_mono = self._monotonic()
        spot = self._store.spot
        self._limiter.maybe_promote_to_steady(
            warmup_done=self._iv_sync.bootstrap_warmup_done,
            warming_up=self._iv_sync.warming_up,
            stable_for_sec=self._research_startup_stable_sec,
        )
        if spot is None or spot <= 0.0:
            logger.warning(
                "[FeedOrchestrator] Live spot missing; waiting for subscribed %s quote.",
                "SPY.US",
            )
            return
        quote_lane = self._store.diagnostics().get("quote_lane", {})
        source_timestamp_utc = self._source_timestamp_utc(quote_lane)
        allow_bootstrap_refresh = self._allow_bootstrap_refresh(source_timestamp_utc)
        is_source_fresh, source_age_sec = self._source_freshness(now, source_timestamp_utc)
        if not is_source_fresh:
            if allow_bootstrap_refresh:
                logger.info(
                    "[FeedOrchestrator] bootstrap refresh path active: startup spot present but raw source not observed yet; permitting initial subscription refresh only."
                )
                await self._refresh_subscriptions(spot=spot, now_mono=now_mono)
                return
            if not self._source_stale:
                logger.warning(
                    "[FeedOrchestrator] source stale gate active: age=%.3fs threshold=%.1fs last_source=%s; skipping header aux, subscription refresh, and research.",
                    source_age_sec or -1.0,
                    self._spot_stale_after_sec,
                    source_timestamp_utc,
                )
            self._source_stale = True
            return
        if self._source_stale:
            logger.info(
                "[FeedOrchestrator] source stale gate cleared: age=%.3fs last_source=%s",
                source_age_sec or 0.0,
                source_timestamp_utc,
            )
        self._source_stale = False
        await self._refresh_header_volatility_aux(
            spot=spot,
            now_mono=now_mono,
            trade_day=now.date(),
        )
        await self._refresh_subscriptions(spot=spot, now_mono=now_mono)
        await self._repair_mandatory_prices(now_mono)
        await self._flush_warmup_if_due(now_mono)
        can_run_research = self._iv_sync.bootstrap_warmup_done and not self._iv_sync.warming_up
        startup_stable = self._limiter.cooldown_stable_for(self._research_startup_stable_sec)
        if spot and can_run_research and (
            not self._last_research or (now - self._last_research).total_seconds() > 900
        ) and startup_stable:
            await self._run_volume_research(today, spot)
            self._last_research = now

    async def _refresh_subscriptions(self, *, spot: float, now_mono: float) -> None:
        if not self._subscription_refresh_due(now_mono):
            return
        prev_symbols = set(self._sub_mgr.subscribed_symbols)
        target_set = await self._sub_mgr.refresh(spot, mandatory_symbols=self._mandatory_symbols)
        self._last_refresh_mono = now_mono
        new_symbols = target_set - prev_symbols
        if new_symbols:
            logger.info(
                "[FeedOrchestrator] %d new symbols detected — queued for IV warm-up.",
                len(new_symbols),
            )
            self._queue_warmup_symbols(new_symbols, now_mono)

    @staticmethod
    def _source_timestamp_utc(quote_lane: dict[str, Any]) -> str | None:
        source_timestamp_utc = quote_lane.get("last_source_timestamp_utc")
        if not isinstance(source_timestamp_utc, str) or not source_timestamp_utc:
            return None
        return source_timestamp_utc

    def _allow_bootstrap_refresh(self, source_timestamp_utc: str | None) -> bool:
        return source_timestamp_utc is None and not self._sub_mgr.writer_ready

    def _source_freshness(
        self,
        now: datetime,
        source_timestamp_utc: str | None,
    ) -> tuple[bool, float | None]:
        if source_timestamp_utc is None:
            return False, None
        try:
            source_dt = datetime.fromisoformat(source_timestamp_utc)
        except ValueError:
            return False, None
        if source_dt.tzinfo is None:
            source_dt = source_dt.replace(tzinfo=timezone.utc)
        else:
            source_dt = source_dt.astimezone(timezone.utc)
        age_sec = max(0.0, (now.astimezone(timezone.utc) - source_dt).total_seconds())
        return age_sec <= self._spot_stale_after_sec, age_sec

    async def _repair_mandatory_prices(self, now_mono: float) -> None:
        if not self._mandatory_symbols or not self._on_price_repair_update or not self._needs_price_repair:
            return
        await repair_symbol_prices(
            batch=sorted(self._mandatory_symbols),
            repair_symbols=self._mandatory_symbols,
            needs_price_repair=self._needs_price_repair,
            last_repair_at=self._price_repair_last_ts,
            now_mono=now_mono,
            runtime=self._quote_runtime,
            limiter=self._limiter,
            on_update=self._on_price_repair_update,
            log_prefix="[FeedOrchestrator]",
        )

    async def repair_symbols_once(
        self,
        symbols: set[str],
        *,
        now_mono: float | None = None,
        log_prefix: str = "[FeedOrchestrator]",
    ) -> int:
        if not symbols or not self._on_price_repair_update or not self._needs_price_repair:
            return 0
        repair_now = self._monotonic() if now_mono is None else now_mono
        return await repair_symbol_prices(
            batch=sorted(symbols),
            repair_symbols=set(symbols),
            needs_price_repair=self._needs_price_repair,
            last_repair_at=self._price_repair_last_ts,
            now_mono=repair_now,
            runtime=self._quote_runtime,
            limiter=self._limiter,
            on_update=self._on_price_repair_update,
            log_prefix=log_prefix,
        )

    async def _run_volume_research(self, today_str: str, spot: float) -> None:
        del today_str
        try:
            async with self._limiter.acquire():
                try:
                    chain_info = await self._quote_runtime.option_chain_info_by_date(
                        "SPY.US",
                        datetime.now().date(),
                    )
                except Exception as exc:
                    if "301607" in str(exc):
                        self._limiter.trigger_cooldown()
                    logger.warning("[FeedOrchestrator] Volume research metadata failed: %s", exc)
                    return
            if not chain_info:
                return
            window = settings.research_window_size
            research_symbols: list[str] = []
            strike_lookup: dict[str, float] = {}
            for item in chain_info:
                strike = float(getattr(item, "price", 0.0) or 0.0)
                if abs(strike - spot) > window:
                    continue
                call_symbol = getattr(item, "call_symbol", "")
                put_symbol = getattr(item, "put_symbol", "")
                if call_symbol:
                    research_symbols.append(call_symbol)
                    strike_lookup[call_symbol] = strike
                if put_symbol:
                    research_symbols.append(put_symbol)
                    strike_lookup[put_symbol] = strike
            new_map: dict[float, int] = {}
            hv_samples: list[float] = []
            batch_size = max(1, min(50, self._limiter.max_symbol_weight))
            for i in range(0, len(research_symbols), batch_size):
                batch = research_symbols[i : i + batch_size]
                async with self._limiter.acquire(weight=len(batch)):
                    try:
                        quotes = await self._quote_runtime.option_quote(batch)
                        if quotes:
                            for quote in quotes:
                                symbol = getattr(quote, "symbol", "")
                                strike = strike_lookup.get(symbol)
                                if strike is not None:
                                    vol = int(getattr(quote, "volume", 0) or 0)
                                    new_map[strike] = new_map.get(strike, 0) + vol
                                hv_decimal = self._extract_hv_decimal(quote)
                                if hv_decimal is not None:
                                    hv_samples.append(hv_decimal)
                    except Exception as exc:
                        logger.error("[FeedOrchestrator] Research batch failed: %s", exc)
            self._store.update_volume_map(new_map)
            self._update_official_hv_diagnostics(hv_samples)
            logger.info("[FeedOrchestrator] Volume map updated: %d strikes", len(new_map))
        except Exception as exc:
            logger.error("[FeedOrchestrator] Volume research failed: %s", exc)

    @staticmethod
    def _extract_hv_decimal(quote: object) -> float | None:
        raw = getattr(quote, "historical_volatility_decimal", None)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value) or value <= 0.0:
            return None
        if value <= 0.0 or value > 3.0:
            return None
        return value

    def _update_official_hv_diagnostics(self, hv_samples: list[float]) -> None:
        if not hv_samples:
            if self._official_hv_decimal is None:
                self._official_hv_sample_count = 0
                self._official_hv_synced_at_utc = None
            return
        self._official_hv_decimal = sum(hv_samples) / len(hv_samples)
        self._official_hv_sample_count = len(hv_samples)
        self._official_hv_synced_at_utc = datetime.now(timezone.utc).isoformat()

    async def _refresh_header_volatility_aux(
        self,
        *,
        spot: float | None,
        now_mono: float,
        trade_day: date,
    ) -> None:
        if spot is None or spot <= 0.0:
            return
        if (now_mono - self._header_volatility_aux_last_mono) < self._header_volatility_aux_ttl_sec:
            return
        self._header_volatility_aux = await build_header_volatility_aux(
            quote_runtime=self._quote_runtime,
            limiter=self._limiter,
            spot=spot,
            trade_day=trade_day,
            logger=logger,
        )
        self._header_volatility_aux_synced_at_utc = datetime.now(timezone.utc).isoformat()
        self._header_volatility_aux_last_mono = now_mono
        logger.info(
            "[FeedOrchestrator] header volatility aux refreshed: spot=%.2f next_expiry=%s atm_iv_1dte=%s atm_iv_1dte_strike=%s vix_iv_decimal=%s",
            spot,
            self._header_volatility_aux.get("next_expiry"),
            self._header_volatility_aux.get("atm_iv_1dte"),
            self._header_volatility_aux.get("atm_iv_1dte_strike"),
            self._header_volatility_aux.get("vix_iv_decimal"),
        )
