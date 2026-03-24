"""L0 V2 facade with single-direction internal dependencies."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from shared.config import settings
from shared.system.rust_shm_bridge import RustBridge
from l0_ingest.v2.contracts import CallbackHooks, SnapshotRequest
from l0_ingest.v2.normalize.bridges import (
    dispatch_depth_event,
    dispatch_trade_event,
    parse_rust_event,
)
from l0_ingest.v2.normalize.events import StateEventProcessor
from l0_ingest.v2.normalize.pipeline import EventType
from l0_ingest.v2.projection import (
    build_error_snapshot_payload,
    build_snapshot_payload,
    build_uninitialized_snapshot_payload,
)
from l0_ingest.v2.services.orchestration.support import (
    apply_preloaded_oi_events,
    apply_rest_update,
)
from l0_ingest.v2.services.runtime.services import RuntimeServices
from l0_ingest.v2.source import build_runtime_bundle
from l0_ingest.v2.source.runtime.openapi_bootstrap import _startup_connectivity_probe
from l0_ingest.v2.state import LiveState

logger = logging.getLogger(__name__)


class OptionChainBuilder:
    """Hard-cut L0 facade that only owns ingest/runtime/state/output concerns."""

    def __init__(self) -> None:
        runtime_bundle = build_runtime_bundle()
        self._runtime_bundle = runtime_bundle
        self._state = LiveState()
        self._services = RuntimeServices.build(runtime_bundle=runtime_bundle, state=self._state)
        self._event_processor = StateEventProcessor(state=self._state, sub_mgr=self._services.sub_mgr)
        self._rust_bridge = RustBridge(self._services.sub_mgr.shm_path)
        self._hooks = CallbackHooks()
        self._initialized = False
        self._consumer_task: asyncio.Task | None = None
        self._rust_consumer_task: asyncio.Task | None = None
        self._mgmt_task: asyncio.Task | None = None
        self._last_trade_price: dict[str, float] = {}

    @property
    def on_depth(self) -> Any:
        return self._hooks.on_depth

    @on_depth.setter
    def on_depth(self, callback: Any) -> None:
        self._hooks.on_depth = callback

    @property
    def on_trade(self) -> Any:
        return self._hooks.on_trade

    @on_trade.setter
    def on_trade(self, callback: Any) -> None:
        self._hooks.on_trade = callback

    async def initialize(self) -> None:
        if self._initialized:
            return
        await self._services.sub_mgr.connect()
        await _startup_connectivity_probe(
            self._runtime_bundle.quote_runtime,
            strict_connectivity=bool(getattr(settings, "longport_startup_strict_connectivity", True)),
        )
        self._rust_bridge.connect()
        self._services.iv_sync.set_event_loop(asyncio.get_event_loop())

        today_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
        preloaded_count = self._services.iv_sync.preload_oi_from_disk(today_str)
        if preloaded_count > 0:
            apply_preloaded_oi_events(
                oi_cache=self._services.iv_sync.oi_cache,
                resolve_strike=self._services.sub_mgr.resolve_strike,
                store=self._state.store,
            )

        self._services.iv_sync.start(
            self._runtime_bundle.quote_runtime,
            get_symbols_fn=lambda: self._services.sub_mgr.subscribed_symbols,
            get_spot_fn=lambda: self._state.store.spot,
            on_update=self._apply_rest_item,
            get_price_repair_symbols_fn=lambda: self._services.orchestrator.mandatory_symbols,
            needs_price_repair_fn=self._state.store.needs_price_repair,
        )
        if settings.enable_tier2_polling:
            self._services.tier2.start(self._runtime_bundle.quote_runtime, get_spot_fn=lambda: self._state.store.spot)
        if settings.enable_tier3_polling:
            self._services.tier3.start(self._runtime_bundle.quote_runtime, get_spot_fn=lambda: self._state.store.spot)

        self._initialized = True
        self._consumer_task = asyncio.create_task(self._event_consumer_loop())
        self._rust_consumer_task = asyncio.create_task(self._rust_consumer_loop())
        self._mgmt_task = asyncio.create_task(self._services.orchestrator.run())
        logger.info("[OptionChainBuilderV2] L0 V2 pipeline initialized")

    def _apply_rest_item(self, symbol: str, item: Any) -> None:
        apply_rest_update(
            symbol=symbol,
            item=item,
            resolve_strike=self._services.sub_mgr.resolve_strike,
            sanitizer=self._state.sanitizer,
            store=self._state.store,
        )

    async def _event_consumer_loop(self) -> None:
        queue = self._runtime_bundle.quote_runtime.event_queue
        while self._initialized:
            raw_event: Any | None = None
            try:
                raw_event = await queue.get()
                self._event_processor.process(
                    raw_event,
                    on_depth=self._hooks.on_depth,
                    on_trade=self._hooks.on_trade,
                )
            except Exception as exc:
                logger.error("[OptionChainBuilderV2] Consumer loop exception: %s", exc)
                await asyncio.sleep(0.1)
            finally:
                if raw_event is not None:
                    queue.task_done()

    async def _rust_consumer_loop(self) -> None:
        while self._initialized:
            try:
                if not self._rust_bridge.mm:
                    self._rust_bridge.connect()
                if not self._rust_bridge.mm:
                    await asyncio.sleep(0.5)
                    continue
                for event in list(self._rust_bridge.poll()):
                    self._handle_rust_event(event)
                await asyncio.sleep(0.001)
            except Exception as exc:
                logger.error("[OptionChainBuilderV2] Rust consumer loop error: %s", exc)
                await asyncio.sleep(0.1)

    def _handle_rust_event(self, event: dict[str, Any]) -> None:
        clean = parse_rust_event(event, symbol_to_strike=self._services.sub_mgr.symbol_to_strike)
        if clean is None:
            return
        self._state.store.apply_event(clean)
        if clean.event_type == EventType.DEPTH:
            dispatch_depth_event(clean, on_depth=self._hooks.on_depth)
            return
        if clean.event_type == EventType.TRADE:
            dispatch_trade_event(
                clean,
                on_trade=self._hooks.on_trade,
                last_trade_price=self._last_trade_price,
            )

    async def fetch_snapshot(self, *, include_chain_arrow: bool = False) -> dict[str, Any]:
        if not self._initialized:
            return build_uninitialized_snapshot_payload(self._state.store.version)
        try:
            request = SnapshotRequest(include_chain_arrow=include_chain_arrow)
            return build_snapshot_payload(
                state=self._state,
                services=self._services,
                rate_limiter=self._runtime_bundle.rate_limiter,
                rust_bridge=self._rust_bridge,
                include_chain_arrow=request.include_chain_arrow,
            )
        except Exception as exc:
            logger.error("[OptionChainBuilderV2] fetch_snapshot failure: %s", exc)
            return build_error_snapshot_payload(
                spot=self._state.store.spot,
                version=self._state.store.version,
            )

    async def fetch_chain(self, include_legacy_greeks: bool = False, caller_tag: str = "unused", include_chain_arrow: bool = False) -> dict[str, Any]:
        del include_legacy_greeks, caller_tag
        return await self.fetch_snapshot(include_chain_arrow=include_chain_arrow)

    def get_startup_chain_snapshot(self) -> list[dict[str, Any]]:
        return self._state.snapshot_rows()

    def get_startup_bootstrap_context(self) -> tuple[float | None, list[dict[str, Any]]]:
        return self._state.store.spot, self.get_startup_chain_snapshot()

    def set_mandatory_symbols(self, symbols: set[str]) -> None:
        self._services.orchestrator.set_mandatory_symbols(symbols)

    async def repair_symbols_once(self, symbols: set[str], *, log_prefix: str = "[OptionChainBuilderV2]") -> int:
        return await self._services.orchestrator.repair_symbols_once(symbols, log_prefix=log_prefix)

    async def refresh_subscriptions_once(self, spot: float | None) -> set[str]:
        return await self._services.sub_mgr.refresh(spot, mandatory_symbols=self._services.orchestrator.mandatory_symbols)

    def get_iv_sync_context(self) -> tuple[dict[str, Any], dict[str, Any]]:
        return dict(self._services.iv_sync.iv_cache), dict(self._services.iv_sync.spot_at_sync)

    def get_diagnostics(self) -> dict[str, Any]:
        diagnostics = {
            "initialized": self._initialized,
            "gateway": self._runtime_bundle.quote_runtime.diagnostics(),
            "store": self._state.store.diagnostics(),
            "governor": {
                "limiter_profile": self._runtime_bundle.rate_limiter.symbol_profile,
                "cooldown_active": self._runtime_bundle.rate_limiter.cooldown_active,
                "cooldown_hits_5m": self._runtime_bundle.rate_limiter.cooldown_hits_5m,
                "pending_warmup_symbols": self._services.orchestrator.pending_warmup_count,
            },
            "subscription_metadata_cache": self._services.sub_mgr.metadata_cache_diagnostics(),
        }
        diagnostics.update(self._state.store.diagnostics())
        return diagnostics

    async def shutdown(self) -> None:
        self._initialized = False
        tasks = [task for task in [self._consumer_task, self._rust_consumer_task, self._mgmt_task] if task]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await self._runtime_bundle.quote_runtime.disconnect()
        await self._services.iv_sync.stop()
        await self._services.tier2.stop()
        await self._services.tier3.stop()
        logger.info("[OptionChainBuilderV2] L0 V2 pipeline shutdown complete")
