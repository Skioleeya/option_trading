"""Option Chain Builder — L0 ingest orchestrator."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from longport.openapi import Config, TradeDirection

from shared.config import settings

from l0_ingest.feeds.chain_state_store import ChainStateStore
from l0_ingest.feeds.feed_orchestrator import FeedOrchestrator
from l0_ingest.feeds.iv_baseline_sync import IVBaselineSync
from l0_ingest.feeds.quote_runtime import L0QuoteRuntime, PythonQuoteRuntime, RustQuoteRuntime
from l0_ingest.feeds.rate_limiter import APIRateLimiter
from l0_ingest.feeds.sanitization import (
    CleanQuoteEvent,
    EventType,
    SanitizationPipeline,
    _infer_opt_type,
)
from l0_ingest.feeds.tier2_poller import Tier2Poller
from l0_ingest.feeds.tier3_poller import Tier3Poller
from l0_ingest.subscription_manager import OptionSubscriptionManager

from l1_compute.analysis.depth_engine import DepthEngine
from l1_compute.analysis.entropy_filter import EntropyFilter
from l1_compute.analysis.greeks_engine import GreeksEngine
from l1_compute.rust_bridge import RustBridge

logger = logging.getLogger(__name__)


class OptionChainBuilder:
    """Institutional-grade coordinator of the L0 ingestion pipeline."""

    def __init__(self) -> None:
        self._store = ChainStateStore()
        self._depth_engine = DepthEngine(ewma_alpha=0.1)
        self._entropy_filter = EntropyFilter(min_entropy=0.05)
        self._sanitizer = SanitizationPipeline()

        config = Config(
            app_key=settings.longport_app_key,
            app_secret=settings.longport_app_secret,
            access_token=settings.longport_access_token,
        )

        self._rate_limiter = APIRateLimiter(
            rate=settings.longport_api_rate_limit,
            burst=settings.longport_api_burst,
            max_concurrent=settings.longport_api_max_concurrent,
            symbol_rate=settings.longport_symbol_rate_per_min,
            symbol_burst=settings.longport_symbol_burst,
        )

        runtime_mode = str(getattr(settings, "longport_runtime_mode", "rust_only")).strip().lower()
        if runtime_mode in {"python", "python_fallback"}:
            self._quote_runtime: L0QuoteRuntime = PythonQuoteRuntime(config)
        else:
            self._quote_runtime = RustQuoteRuntime(config)

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
        self._orchestrator = FeedOrchestrator(
            self._quote_runtime,
            self._store,
            self._sub_mgr,
            self._iv_sync,
            self._rate_limiter,
        )

        self._initialized = False
        self._consumer_task: asyncio.Task | None = None
        self._rust_consumer_task: asyncio.Task | None = None
        self._mgmt_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        if self._initialized:
            return

        try:
            await self._sub_mgr.connect()
            self._rust_bridge.connect()

            self._iv_sync.set_event_loop(asyncio.get_event_loop())
            self._consumer_task = asyncio.create_task(self._event_consumer_loop())
            self._rust_consumer_task = asyncio.create_task(self._rust_consumer_loop())

            today_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
            preloaded_count = self._iv_sync.preload_oi_from_disk(today_str)
            logger.info("[OptionChainBuilder] OI preloaded: %d symbols", preloaded_count)

            if preloaded_count > 0:
                for symbol, oi in self._iv_sync.oi_cache.items():
                    strike = self._sub_mgr.resolve_strike(symbol)
                    if strike:
                        self._store.apply_event(
                            CleanQuoteEvent(
                                seq_no=0,
                                event_type=EventType.REST,
                                symbol=symbol,
                                strike=strike,
                                opt_type=_infer_opt_type(symbol),
                                bid=None,
                                ask=None,
                                last_price=None,
                                volume=None,
                                open_interest=oi,
                                implied_volatility=None,
                                iv_timestamp=None,
                                delta=None,
                                gamma=None,
                                theta=None,
                                vega=None,
                                current_volume=None,
                                turnover=None,
                                arrival_mono=time.monotonic(),
                            )
                        )

            self._iv_sync.start(
                self._quote_runtime,
                get_symbols_fn=lambda: self._sub_mgr.subscribed_symbols,
                get_spot_fn=lambda: self._store.spot,
                on_update=self._handle_rest_update,
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
                    strike = self._sub_mgr.symbol_to_strike.get(event["symbol"])
                    if strike is None:
                        continue
                    clean = CleanQuoteEvent(
                        seq_no=event["seq_no"],
                        event_type=EventType(event["event_type"]),
                        symbol=event["symbol"],
                        strike=strike,
                        opt_type=_infer_opt_type(event["symbol"]),
                        bid=event["bid"] if event["bid"] > 0 else None,
                        ask=event["ask"] if event["ask"] > 0 else None,
                        last_price=event["last_price"] if event["last_price"] > 0 else None,
                        volume=event["volume"],
                        open_interest=None,
                        implied_volatility=None,
                        arrival_mono=event["arrival_mono_ns"] / 1e9,
                        impact_index=event["impact_index"],
                        is_sweep=event["is_sweep"],
                    )
                    self._store.apply_event(clean)
                await asyncio.sleep(0.001)
            except Exception as exc:
                logger.error("[OptionChainBuilder] Rust consumer loop error: %s", exc)
                await asyncio.sleep(0.1)

    async def fetch_chain(self) -> dict[str, Any]:
        if not self._initialized:
            return {
                "spot": None,
                "chain": [],
                "as_of": None,
                "as_of_utc": None,
                "version": self._store.version,
            }

        now = datetime.now(ZoneInfo("US/Eastern"))
        now_utc = now.astimezone(ZoneInfo("UTC"))
        try:
            target_set = self._sub_mgr.target_symbols
            snapshot = self._store.get_flow_merged_snapshot(
                self._depth_engine.get_flow_snapshot(),
                target_symbols=target_set,
            )
            agg = await self._greeks_engine.enrich(snapshot, self._store.spot or 0.0)

            data = {
                "spot": self._store.spot,
                "chain": snapshot,
                "version": self._store.version,
                "tier2_chain": self._tier2.cache,
                "tier3_chain": self._tier3.cache,
                "volume_map": self._store.volume_map,
                "aggregate_greeks": agg,
                "ttm_seconds": agg.get("ttm_seconds"),
                "as_of": now,
                "as_of_utc": now_utc.isoformat(),
                "rust_active": self._rust_bridge.mm is not None,
                "rust_shm_path": self._rust_bridge.mm_path if self._rust_bridge.mm else None,
                "shm_stats": {
                    "head": self._get_shm_val(self._rust_bridge.head_ptr),
                    "tail": self._get_shm_val(self._rust_bridge.tail_ptr),
                    "status": "OK" if self._rust_bridge.mm else "DISCONNECTED",
                },
                "governor_telemetry": {
                    "symbols_per_min": self._rate_limiter.symbol_tokens,
                    "cooldown_active": self._rate_limiter.cooldown_active,
                },
            }
            if not data["rust_active"]:
                logger.warning("[OptionChainBuilder] fetch_chain rust_active=FALSE")
            return data
        except Exception as exc:
            logger.error("[OptionChainBuilder] fetch_chain failure: %s", exc)
            return {
                "spot": self._store.spot,
                "chain": [],
                "as_of": now,
                "as_of_utc": now_utc.isoformat(),
                "version": self._store.version,
            }

    def _get_shm_val(self, ptr: int) -> int:
        if not self._rust_bridge.mm:
            return 0
        import struct

        return struct.unpack("Q", self._rust_bridge.mm[ptr : ptr + 8])[0]

    def _handle_rest_update(self, symbol: str, item: Any) -> None:
        strike = self._sub_mgr.resolve_strike(symbol)
        if strike is None:
            logger.warning("[OptionChainBuilder] REST update dropped: strike unresolved for %s", symbol)
            return
        clean = self._sanitizer.parse_rest_item(symbol, strike, item)
        if clean:
            self._store.apply_event(clean)
        else:
            logger.warning("[OptionChainBuilder] REST update sanitize failed for %s", symbol)

    async def _event_consumer_loop(self) -> None:
        logger.info("[OptionChainBuilder] Pipeline consumer loop active")
        queue = self._quote_runtime.event_queue
        while self._initialized:
            try:
                raw_event = await queue.get()

                if raw_event.symbol == "SPY.US" and raw_event.event_type == EventType.QUOTE:
                    price = float(getattr(raw_event.payload, "last_done", 0) or 0)
                    if price > 0:
                        self._store.update_spot(price)
                    queue.task_done()
                    continue

                if raw_event.event_type == EventType.QUOTE:
                    strike = self._sub_mgr.symbol_to_strike.get(raw_event.symbol)
                    if strike is None:
                        queue.task_done()
                        continue
                    clean = self._sanitizer.parse_quote(raw_event, strike)
                    if clean and self._entropy_filter.accept(clean.symbol, clean):
                        self._store.apply_event(clean)
                        if clean.open_interest is not None:
                            self._store.apply_oi_smooth(clean.symbol, clean.open_interest)

                elif raw_event.event_type == EventType.DEPTH:
                    clean_depth = self._sanitizer.parse_depth(raw_event)
                    if clean_depth:
                        bids = getattr(raw_event.payload, "bids", [])
                        asks = getattr(raw_event.payload, "asks", [])
                        self._depth_engine.update_depth(clean_depth.symbol, bids, asks)
                        self._store.apply_depth(clean_depth)
                        if hasattr(self, "on_depth") and self.on_depth is not None:
                            self.on_depth(clean_depth.symbol, bids, asks)

                elif raw_event.event_type == EventType.TRADE:
                    trades = getattr(raw_event.payload, "trades", [])
                    if trades:
                        trade_dicts: list[dict[str, Any]] = []
                        for trade in trades:
                            raw_dir = (
                                getattr(trade, "direction", 0)
                                if not isinstance(trade, dict)
                                else trade.get("dir", trade.get("direction", 0))
                            )
                            if raw_dir == TradeDirection.Up or str(raw_dir) == "2" or raw_dir == 2:
                                dir_sign = 1
                            elif raw_dir == TradeDirection.Down or str(raw_dir) == "1" or raw_dir == 1:
                                dir_sign = -1
                            else:
                                dir_sign = 0

                            if isinstance(trade, dict):
                                trade_dict = dict(trade)
                                trade_dict["vol"] = float(
                                    trade_dict.get("vol", 0.0) or trade_dict.get("volume", 0.0)
                                )
                                trade_dict["dir"] = dir_sign
                                trade_dicts.append(trade_dict)
                            else:
                                def _local_safe_float(value: Any, default: float = 0.0) -> float:
                                    try:
                                        return float(value)
                                    except (TypeError, ValueError):
                                        return default

                                def _local_safe_int(value: Any, default: int = 0) -> int:
                                    try:
                                        return int(float(value))
                                    except (TypeError, ValueError):
                                        return default

                                volume = _local_safe_float(getattr(trade, "volume", 0))
                                timestamp_val = getattr(trade, "timestamp", 0)

                                def to_ts_int(value: Any) -> int:
                                    if hasattr(value, "timestamp"):
                                        return int(value.timestamp())
                                    try:
                                        return int(float(value))
                                    except (TypeError, ValueError):
                                        return int(time.time())

                                trade_dicts.append(
                                    {
                                        "price": _local_safe_float(getattr(trade, "price", 0.0)),
                                        "vol": volume,
                                        "volume": volume,
                                        "timestamp": to_ts_int(timestamp_val),
                                        "dir": dir_sign,
                                        "direction": dir_sign,
                                        "trade_type": _local_safe_int(getattr(trade, "trade_type", 0)),
                                    }
                                )

                        self._depth_engine.update_trades(raw_event.symbol, trade_dicts)
                        if hasattr(self, "on_trade") and self.on_trade is not None:
                            self.on_trade(raw_event.symbol, trade_dicts)

                queue.task_done()
            except Exception as exc:
                logger.error("[OptionChainBuilder] Consumer loop exception: %s", exc)
                await asyncio.sleep(0.1)

    def set_mandatory_symbols(self, symbols: set[str]) -> None:
        self._orchestrator.set_mandatory_symbols(symbols)

    def get_diagnostics(self) -> dict[str, Any]:
        diagnostics = {
            "initialized": self._initialized,
            "gateway": self._quote_runtime.diagnostics(),
            "store": self._store.diagnostics(),
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
