"""Option Chain Builder — L0 ingest orchestrator."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from longport.openapi import Config

from shared.config import settings

from l0_ingest.feeds.builder_orchestration_support import (
    apply_preloaded_oi_events,
    apply_rest_update,
    read_shm_u64,
)
from l0_ingest.feeds.chain_state_store import ChainStateStore
from l0_ingest.feeds.chain_event_processor import ChainEventProcessor
from l0_ingest.feeds.feed_orchestrator import FeedOrchestrator
from l0_ingest.feeds.fetch_chain_components import (
    LegacyGreeksAudit,
    aggregate_store_snapshot,
    build_error_snapshot,
    build_governor_telemetry,
    build_runtime_status,
    build_uninitialized_snapshot,
    compose_fetch_chain_payload,
)
from l0_ingest.feeds.iv_baseline_sync import IVBaselineSync
from l0_ingest.feeds.openapi_bootstrap import (
    _build_openapi_endpoint_profiles,
    _longport_config_kwargs,
    _startup_connectivity_probe,
    _sync_openapi_env_aliases,
)
from l0_ingest.feeds.quote_runtime import L0QuoteRuntime, PythonQuoteRuntime, RustQuoteRuntime
from l0_ingest.feeds.rate_limiter import APIRateLimiter
from l0_ingest.feeds.rust_event_bridge import (
    dispatch_depth_event,
    dispatch_trade_event,
    parse_rust_event,
)
from l0_ingest.feeds.sanitization import (
    EventType,
    SanitizationPipeline,
)
from l0_ingest.feeds.tier2_poller import Tier2Poller
from l0_ingest.feeds.tier3_poller import Tier3Poller
from l0_ingest.subscription_manager import OptionSubscriptionManager

from l1_compute.analysis.depth_engine import DepthEngine
from l1_compute.analysis.entropy_filter import EntropyFilter
from l1_compute.analysis.bsm import get_trading_time_to_maturity
from l1_compute.analysis.greeks_engine import GreeksEngine
from l1_compute.arrow.schema import dicts_to_record_batch
from l1_compute.rust_bridge import RustBridge

logger = logging.getLogger(__name__)


class OptionChainBuilder:
    """Institutional-grade coordinator of the L0 ingestion pipeline."""

    def __init__(self) -> None:
        self._store = ChainStateStore()
        self._depth_engine = DepthEngine(ewma_alpha=0.1)
        self._entropy_filter = EntropyFilter(min_entropy=0.05)
        self._sanitizer = SanitizationPipeline()

        endpoint_profiles = _build_openapi_endpoint_profiles(settings)
        _sync_openapi_env_aliases(settings)
        config_kwargs = _longport_config_kwargs(settings)
        config = Config(**config_kwargs)
        logger.info(
            "[OptionChainBuilder] OpenAPI endpoints: http=%s quote_ws=%s trade_ws=%s language=%s overnight=%s",
            config_kwargs.get("http_url"),
            config_kwargs.get("quote_ws_url"),
            config_kwargs.get("trade_ws_url"),
            config_kwargs.get("language"),
            config_kwargs.get("enable_overnight"),
        )

        self._rate_limiter = APIRateLimiter(
            rate=settings.longport_api_rate_limit,
            burst=settings.longport_api_burst,
            max_concurrent=settings.longport_api_max_concurrent,
            symbol_rate=settings.longport_steady_symbol_rate_per_min,
            symbol_burst=settings.longport_steady_symbol_burst,
            startup_symbol_rate=settings.longport_startup_symbol_rate_per_min,
            startup_symbol_burst=settings.longport_startup_symbol_burst,
            steady_symbol_rate=settings.longport_steady_symbol_rate_per_min,
            steady_symbol_burst=settings.longport_steady_symbol_burst,
        )

        runtime_mode = str(getattr(settings, "longport_runtime_mode", "rust_only")).strip().lower()
        if runtime_mode in {"python", "python_fallback"}:
            self._quote_runtime: L0QuoteRuntime = PythonQuoteRuntime(config)
        else:
            self._quote_runtime = RustQuoteRuntime(
                config,
                endpoint_profiles=endpoint_profiles,
            )

        self._sub_mgr = OptionSubscriptionManager(
            config=config,
            quote_runtime=self._quote_runtime,
            rate_limiter=self._rate_limiter,
        )
        self._rust_bridge = RustBridge(self._sub_mgr.shm_path)

        self._iv_sync = IVBaselineSync(self._rate_limiter)
        self._tier2 = Tier2Poller(self._rate_limiter)
        self._tier3 = Tier3Poller(self._rate_limiter)

        self._greeks_engine = GreeksEngine(self._store, self._iv_sync)
        self._legacy_greeks_audit = LegacyGreeksAudit()
        self._orchestrator = FeedOrchestrator(
            self._quote_runtime,
            self._store,
            self._sub_mgr,
            self._iv_sync,
            self._rate_limiter,
        )
        self._event_processor = ChainEventProcessor(
            store=self._store,
            sanitizer=self._sanitizer,
            entropy_filter=self._entropy_filter,
            depth_engine=self._depth_engine,
            sub_mgr=self._sub_mgr,
        )

        self._initialized = False
        self._consumer_task: asyncio.Task | None = None
        self._rust_consumer_task: asyncio.Task | None = None
        self._mgmt_task: asyncio.Task | None = None
        self._last_trade_price: dict[str, float] = {}

    async def initialize(self) -> None:
        if self._initialized:
            return

        try:
            await self._sub_mgr.connect()
            await _startup_connectivity_probe(
                self._quote_runtime,
                strict_connectivity=bool(
                    getattr(settings, "longport_startup_strict_connectivity", True)
                ),
            )
            self._rust_bridge.connect()

            self._iv_sync.set_event_loop(asyncio.get_event_loop())
            self._consumer_task = asyncio.create_task(self._event_consumer_loop())
            self._rust_consumer_task = asyncio.create_task(self._rust_consumer_loop())

            today_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
            preloaded_count = self._iv_sync.preload_oi_from_disk(today_str)
            logger.info("[OptionChainBuilder] OI preloaded: %d symbols", preloaded_count)

            if preloaded_count > 0:
                apply_preloaded_oi_events(
                    oi_cache=self._iv_sync.oi_cache,
                    resolve_strike=self._sub_mgr.resolve_strike,
                    store=self._store,
                )

            self._iv_sync.start(
                self._quote_runtime,
                get_symbols_fn=lambda: self._sub_mgr.subscribed_symbols,
                get_spot_fn=lambda: self._store.spot,
                on_update=lambda symbol, item: apply_rest_update(
                    symbol=symbol,
                    item=item,
                    resolve_strike=self._sub_mgr.resolve_strike,
                    sanitizer=self._sanitizer,
                    store=self._store,
                ),
            )
            if settings.enable_tier2_polling:
                self._tier2.start(self._quote_runtime, get_spot_fn=lambda: self._store.spot)
            if settings.enable_tier3_polling:
                self._tier3.start(self._quote_runtime, get_spot_fn=lambda: self._store.spot)

            self._mgmt_task = asyncio.create_task(self._orchestrator.run())

            from l1_compute.analysis.bsm_fast import warmup

            warmup()
            self._initialized = True
            logger.info("[OptionChainBuilder] Modular pipeline initialized")
        except Exception as exc:
            logger.error("[OptionChainBuilder] Initialization failure: %s", exc)
            raise

    async def _rust_consumer_loop(self) -> None:
        logger.info("[OptionChainBuilder] Rust consumer loop active")
        while self._initialized:
            try:
                if not self._rust_bridge.mm:
                    self._rust_bridge.connect()
                if not self._rust_bridge.mm:
                    await asyncio.sleep(0.5)
                    continue

                events = list(self._rust_bridge.poll())
                for event in events:
                    self._handle_rust_event(event)
                await asyncio.sleep(0.001)
            except Exception as exc:
                logger.error("[OptionChainBuilder] Rust consumer loop error: %s", exc)
                await asyncio.sleep(0.1)

    def _handle_rust_event(self, event: dict[str, Any]) -> None:
        clean = parse_rust_event(
            event,
            symbol_to_strike=self._sub_mgr.symbol_to_strike,
        )
        if clean is None:
            return

        self._store.apply_event(clean)

        if clean.event_type == EventType.DEPTH:
            dispatch_depth_event(
                clean,
                on_depth=getattr(self, "on_depth", None),
            )
            return
        if clean.event_type == EventType.TRADE:
            dispatch_trade_event(
                clean,
                on_trade=getattr(self, "on_trade", None),
                last_trade_price=self._last_trade_price,
            )

    async def fetch_chain(
        self,
        include_legacy_greeks: bool = False,
        caller_tag: str = "unspecified",
        include_chain_arrow: bool = False,
    ) -> dict[str, Any]:
        if not self._initialized:
            return build_uninitialized_snapshot(self._store.version)

        now = datetime.now(ZoneInfo("US/Eastern"))
        now_utc_iso = now.astimezone(ZoneInfo("UTC")).isoformat()
        try:
            target_set = self._sub_mgr.target_symbols
            chain_snapshot = aggregate_store_snapshot(
                store=self._store,
                depth_engine=self._depth_engine,
                target_symbols=target_set,
            )
            chain_arrow = dicts_to_record_batch(chain_snapshot) if include_chain_arrow else None
            ttm_seconds = get_trading_time_to_maturity(now) * (252 * 23400)
            agg: dict[str, Any] = {}
            if include_legacy_greeks:
                version = int(self._store.version)
                invocation = self._legacy_greeks_audit.record_dispatch(version, caller_tag)
                logger.info(
                    "[GPU-AUDIT] legacy_greeks_dispatch caller=%s snapshot_version=%s invocation=%s",
                    caller_tag,
                    version,
                    invocation,
                )
                agg = await self._greeks_engine.enrich(chain_snapshot, self._store.spot or 0.0)
                ttm_seconds = float(agg.get("ttm_seconds", ttm_seconds) or ttm_seconds)

            runtime_status = build_runtime_status(
                rust_bridge=self._rust_bridge,
                shm_reader=lambda ptr: read_shm_u64(self._rust_bridge.mm, ptr),
            )
            governor_telemetry = build_governor_telemetry(
                rate_limiter=self._rate_limiter,
                orchestrator=self._orchestrator,
                sub_mgr=self._sub_mgr,
            )
            data = compose_fetch_chain_payload(
                spot=self._store.spot,
                chain=chain_snapshot,
                chain_arrow=chain_arrow,
                version=self._store.version,
                tier2_chain=self._tier2.cache,
                tier3_chain=self._tier3.cache,
                volume_map=self._store.volume_map,
                aggregate_greeks=agg,
                ttm_seconds=ttm_seconds,
                now=now,
                now_utc_iso=now_utc_iso,
                runtime_status=runtime_status,
                governor_telemetry=governor_telemetry,
                official_hv_diagnostics=self._orchestrator.official_hv_diagnostics,
            )
            if not runtime_status["rust_active"]:
                logger.warning("[OptionChainBuilder] fetch_chain rust_active=FALSE")
            return data
        except Exception as exc:
            logger.error("[OptionChainBuilder] fetch_chain failure: %s", exc)
            return build_error_snapshot(
                spot=self._store.spot,
                version=self._store.version,
                now=now,
                now_utc_iso=now_utc_iso,
            )

    async def _event_consumer_loop(self) -> None:
        logger.info("[OptionChainBuilder] Pipeline consumer loop active")
        queue = self._quote_runtime.event_queue
        while self._initialized:
            raw_event: Any | None = None
            try:
                raw_event = await queue.get()
                self._event_processor.process_event(
                    raw_event,
                    on_depth=getattr(self, "on_depth", None),
                    on_trade=getattr(self, "on_trade", None),
                )
            except Exception as exc:
                logger.error("[OptionChainBuilder] Consumer loop exception: %s", exc)
                await asyncio.sleep(0.1)
            finally:
                if raw_event is not None:
                    queue.task_done()

    def set_mandatory_symbols(self, symbols: set[str]) -> None:
        self._orchestrator.set_mandatory_symbols(symbols)

    def get_iv_sync_context(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Expose IV sync caches via public API for app loop orchestration.

        App loops must not reach into private members like ``_iv_sync`` directly.
        """
        iv_cache = getattr(self._iv_sync, "iv_cache", {})
        spot_at_sync = getattr(self._iv_sync, "spot_at_sync", {})
        return dict(iv_cache or {}), dict(spot_at_sync or {})

    def get_diagnostics(self) -> dict[str, Any]:
        diagnostics = {
            "initialized": self._initialized,
            "gateway": self._quote_runtime.diagnostics(),
            "store": self._store.diagnostics(),
            "governor": {
                "limiter_profile": self._rate_limiter.symbol_profile,
                "cooldown_active": self._rate_limiter.cooldown_active,
                "cooldown_hits_5m": self._rate_limiter.cooldown_hits_5m,
                "pending_warmup_symbols": self._orchestrator.pending_warmup_count,
            },
            "subscription_metadata_cache": self._sub_mgr.metadata_cache_diagnostics(),
            "legacy_greeks_audit": self._legacy_greeks_audit.diagnostics(),
        }
        diagnostics.update(self._store.diagnostics())
        return diagnostics

    async def shutdown(self) -> None:
        self._initialized = False
        tasks = [t for t in [self._consumer_task, self._rust_consumer_task, self._mgmt_task] if t]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await self._quote_runtime.disconnect()
        await self._iv_sync.stop()
        await self._tier2.stop()
        await self._tier3.stop()
        logger.info("[OptionChainBuilder] Modular pipeline shutdown complete")
