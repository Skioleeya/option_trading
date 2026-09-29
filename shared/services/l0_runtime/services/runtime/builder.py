"""L0 V2 facade with single-direction internal dependencies."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from shared_rust.contracts import (
    SHM_STATUS_DISCONNECTED,
    CallbackHooks,
    SnapshotRequest,
)
from shared.config import settings
from shared.services.l0_runtime.normalize.events import StateEventProcessor
from shared.services.l0_runtime.projection import (
    build_error_snapshot_payload,
    build_snapshot_payload,
    build_uninitialized_snapshot_payload,
)
from shared.services.l0_runtime.services import RuntimeServices, apply_preloaded_oi_events, apply_rest_update
from shared.services.l0_runtime.services.runtime.arrow_transport import ArrowTransportMixin
from shared.services.l0_runtime.source import build_runtime_bundle
from shared.services.l0_runtime.source.runtime import ArrowIpcReader, _startup_connectivity_probe
from shared.services.l0_runtime.state import LiveState

logger = logging.getLogger(__name__)


class OptionChainBuilder(ArrowTransportMixin):
    """Hard-cut L0 facade that only owns ingest/runtime/state/output concerns."""

    def __init__(self) -> None:
        runtime_bundle = build_runtime_bundle()
        self._runtime_bundle = runtime_bundle
        self._state = LiveState()
        self._services = RuntimeServices.build(runtime_bundle=runtime_bundle, state=self._state)
        self._event_processor = StateEventProcessor(state=self._state, sub_mgr=self._services.sub_mgr)
        self._hooks = CallbackHooks()
        self._initialized = False
        self._consumer_task: asyncio.Task | None = None
        self._arrow_consumer_task: asyncio.Task | None = None
        self._mgmt_task: asyncio.Task | None = None
        self._arrow_reader: ArrowIpcReader | None = None
        self._last_arrow_batch_id = 0
        self._transport_status = SHM_STATUS_DISCONNECTED
        self._transport_error: str | None = None
        self._arrow_decode_failures_total = 0
        self._arrow_decode_failures_streak = 0
        self._last_trade_price: dict[str, float] = {}
        self._last_trade_direction: dict[str, int] = {}
        self._top_of_book: dict[str, tuple[float | None, float | None]] = {}
        self._on_spot: Any = None
        self.on_quote_lane: Any = None
        self._arrow_startup_timeout_sec = max(
            1.0,
            float(getattr(settings, "longport_subscription_ready_timeout_sec", 60) or 60),
        )
        self._state.store.add_spot_listener(self._emit_spot_update)
        self._state.store.set_quote_lane_listener(self._emit_quote_lane_update)

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

    @property
    def on_spot(self) -> Any:
        return self._on_spot

    @on_spot.setter
    def on_spot(self, callback: Any) -> None:
        self._on_spot = callback

    async def initialize(self) -> None:
        if self._initialized:
            return
        await self._services.sub_mgr.connect()
        startup_spot = await _startup_connectivity_probe(
            self._runtime_bundle.quote_runtime,
            strict_connectivity=bool(settings.longport_startup_strict_connectivity),
            retry_attempts=int(settings.longport_connect_retries),
            retry_base_sec=float(settings.longport_connect_retry_base_sec),
        )
        self._state.store.update_spot(startup_spot)
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
        self._mgmt_task = asyncio.create_task(self._services.orchestrator.run())
        if not self._uses_arrow_transport():
            self._consumer_task = asyncio.create_task(self._event_consumer_loop())
        else:
            try:
                await self._await_arrow_writer_ready_or_fail(timeout_sec=self._arrow_startup_timeout_sec)
                self._connect_arrow_reader()
            except Exception as exc:
                self._transport_status = SHM_STATUS_ERROR
                self._transport_error = str(exc)
                logger.error("[OptionChainBuilderV2] Arrow startup gate failed: %s", exc)
                await self.shutdown()
                raise RuntimeError(f"arrow_startup_gate_failed: {exc}") from exc
            self._arrow_consumer_task = asyncio.create_task(self._arrow_consumer_loop())
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

    async def fetch_snapshot(self, *, include_chain_arrow: bool = False) -> dict[str, Any]:
        if not self._initialized:
            return build_uninitialized_snapshot_payload(self._state.store.version)
        try:
            request = SnapshotRequest(include_chain_arrow=include_chain_arrow)
            return build_snapshot_payload(
                state=self._state,
                services=self._services,
                rate_limiter=self._runtime_bundle.rate_limiter,
                runtime_status=self._build_runtime_status(),
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
            "transport": {
                "status": self._transport_status,
                "last_batch_id": self._last_arrow_batch_id,
                "error": self._transport_error,
                "decode_failures_total": self._arrow_decode_failures_total,
                "decode_failures_streak": self._arrow_decode_failures_streak,
                **(self._arrow_reader.transport_diagnostics() if self._arrow_reader is not None else {}),
                **(
                    getattr(self._runtime_bundle.quote_runtime, "transport_contract", lambda: {})()
                    or {}
                ),
            },
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
        tasks = [task for task in [self._consumer_task, self._arrow_consumer_task, self._mgmt_task] if task]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if self._arrow_reader is not None:
            self._arrow_reader.close()
            self._arrow_reader = None
        await self._runtime_bundle.quote_runtime.disconnect()
        await self._services.iv_sync.stop()
        await self._services.tier2.stop()
        await self._services.tier3.stop()
        self._state.store.remove_spot_listener(self._emit_spot_update)
        self._state.store.set_quote_lane_listener(None)
        self._on_spot = None
        self.on_quote_lane = None
        logger.info("[OptionChainBuilderV2] L0 V2 pipeline shutdown complete")

    def _emit_spot_update(self, spot: float, version: int, data_timestamp: str) -> None:
        callback = self._on_spot
        if callable(callback):
            callback(spot=spot, version=version, data_timestamp=data_timestamp)

    def _emit_quote_lane_update(self, quote_lane: dict[str, Any]) -> None:
        callback = self.on_quote_lane
        if callable(callback):
            callback(quote_lane)

