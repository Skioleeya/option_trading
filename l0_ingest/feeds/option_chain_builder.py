"""Option Chain Builder — Longport API integration.

Thin orchestrator that composes modular components:
- SubscriptionManager: Tier 1 WS subscription (0DTE + 1DTE, asymmetric window)
- IVBaselineSync: Staggered IV/OI REST polling (120s, 2-chunk)
- Tier2Poller: 2DTE REST polling (120s, ±30pt)
- Tier3Poller: Weekly REST polling (10min, Top 20 OI)

All Greeks are computed locally via BSM using WebSocket price ticks
and REST-sourced IV baseline, with Sticky-Strike correction.
"""

from __future__ import annotations

import asyncio
import logging
import math
import threading
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from longport.openapi import QuoteContext, Config, SubType
from shared.config import settings, convert_to_market_time
from shared.system.persistent_oi_store import PersistentOIStore

from l0_ingest.feeds.market_data_gateway import MarketDataGateway
from l0_ingest.feeds.sanitization import (
    SanitizationPipeline, RawMarketEvent, CleanQuoteEvent, EventType, _infer_opt_type
)
from l0_ingest.feeds.chain_state_store import ChainStateStore
from l0_ingest.feeds.feed_orchestrator import FeedOrchestrator
from l0_ingest.feeds.iv_baseline_sync import IVBaselineSync
from l0_ingest.feeds.tier2_poller import Tier2Poller
from l0_ingest.feeds.tier3_poller import Tier3Poller
from l0_ingest.feeds.rate_limiter import APIRateLimiter
from l0_ingest.subscription_manager import OptionSubscriptionManager

from l1_compute.analysis.bsm import get_trading_time_to_maturity, skew_adjust_iv
from l1_compute.analysis.bsm_fast import compute_greeks_batch, warmup as bsm_warmup
from l1_compute.analysis.depth_engine import DepthEngine
from l1_compute.analysis.entropy_filter import EntropyFilter
from l1_compute.analysis.greeks_engine import GreeksEngine
from l1_compute.rust_bridge import RustBridge

logger = logging.getLogger(__name__)

class OptionChainBuilder:
    """Institutional-grade Orchestrator for the Option Chain Feed.

    Refactored from God Object into a lean coordinator of specialized modules:
    - MarketDataGateway: L0-L1 WS Queue (Thread-safe)
    - SanitizationPipeline: L1A Data Cleaning (NaN/Inf filter)
    - ChainStateStore: L1B State Management (Sequence-ordered)
    - FeedOrchestrator: Management & Research Scheduler
    - GreeksEngine: Off-thread BSM Compute (Non-blocking)
    """

    def __init__(self, primary_ctx: Any = None) -> None:
        """Initialize all ingestion components with unified rate control."""
        # 1. State Store (The Single Source of Truth)
        self._store = ChainStateStore()

        # 2. Logic Engines
        self._depth_engine = DepthEngine(ewma_alpha=0.1)
        self._entropy_filter = EntropyFilter(min_entropy=0.05)
        self._sanitizer = SanitizationPipeline()

        # 3. Connectivity & Metadata Infrastructure (L0)
        # 1. Configuration & Key Loading
        config = Config(
            app_key=settings.longport_app_key,
            app_secret=settings.longport_app_secret,
            access_token=settings.longport_access_token,
        )
        
        # 2. Shared Rate Limiter (Institutional Safeguard: 10/s, 5 concurrent)
        self._rate_limiter = APIRateLimiter(
            rate=settings.longport_api_rate_limit,
            burst=settings.longport_api_burst,
            max_concurrent=settings.longport_api_max_concurrent
        )

        # 3. Component Instantiation
        self._sub_mgr = OptionSubscriptionManager(config, rate_limiter=self._rate_limiter, primary_ctx=primary_ctx)
        self._gateway = self._sub_mgr.py_gateway
        self._rust_bridge = RustBridge(self._sub_mgr.shm_path)

        self._iv_sync = IVBaselineSync(self._rate_limiter)
        self._tier2 = Tier2Poller(self._rate_limiter)
        self._tier3 = Tier3Poller(self._rate_limiter)

        # 4. Domain Engines
        self._greeks_engine = GreeksEngine(self._store, self._iv_sync)
        self._orchestrator = FeedOrchestrator(
            self._gateway, self._store, self._sub_mgr, self._iv_sync, self._rate_limiter
        )

        self._initialized = False
        self._consumer_task: asyncio.Task | None = None
        self._mgmt_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        """Startup entire modular pipeline."""
        if self._initialized:
            return

        try:
            print("[OptionChainBuilder] >>> INITIALIZE START <<<")
            # Connect Gateway (captures loop and registers callbacks)
            print("[OptionChainBuilder] Connecting SubMgr...")
            await self._sub_mgr.connect()
            print("[OptionChainBuilder] Connecting RustBridge...")
            self._rust_bridge.connect()

            # Shared loop config for IV sync hot-start
            self._iv_sync.set_event_loop(asyncio.get_event_loop())
            
            # Start Pipeline Consumers
            print("[OptionChainBuilder] Starting Event Consumer Loop...")
            self._consumer_task = asyncio.create_task(self._event_consumer_loop())
            print("[OptionChainBuilder] Starting Rust Consumer Loop...")
            self._rust_consumer_task = asyncio.create_task(self._rust_consumer_loop())

            # OI hot-start from disk
            print("[OptionChainBuilder] Preloading OI...")
            today_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
            preloaded_count = self._iv_sync.preload_oi_from_disk(today_str)
            logger.info(f"[OptionChainBuilder] OI preloaded: {preloaded_count} symbols")
            
            # Seed the store with hot-start data
            if preloaded_count > 0:
                for sym, oi in self._iv_sync.oi_cache.items():
                    strike = self._sub_mgr.resolve_strike(sym)
                    if strike:
                        # Use apply_oi_smooth or direct? 
                        # Direct update to ensure it's there for n_valid check
                        self._store.apply_event(CleanQuoteEvent(
                            seq_no=0, event_type=EventType.REST, symbol=sym, strike=strike,
                            opt_type=_infer_opt_type(sym),
                            bid=None, ask=None, last_price=None, volume=None,
                            open_interest=oi, implied_volatility=None, iv_timestamp=None,
                            delta=None, gamma=None, theta=None, vega=None,
                            current_volume=None, turnover=None, arrival_mono=time.monotonic()
                        ))
                logger.info("[OptionChainBuilder] ChainStateStore seeded with preloaded OI.")

            # Start Pollers
            self._iv_sync.start(
                self._gateway.quote_ctx,
                get_symbols_fn=lambda: self._sub_mgr.subscribed_symbols,
                get_spot_fn=lambda: self._store.spot,
                on_update=self._handle_rest_update
            )
            if settings.enable_tier2_polling:
                self._tier2.start(self._gateway.quote_ctx, get_spot_fn=lambda: self._store.spot)
            if settings.enable_tier3_polling:
                self._tier3.start(self._gateway.quote_ctx, get_spot_fn=lambda: self._store.spot)

            # Start Orchestrator Task
            self._mgmt_task = asyncio.create_task(self._orchestrator.run())

            from l1_compute.analysis.bsm_fast import warmup
            warmup()

            self._initialized = True
            logger.info("[OptionChainBuilder] Modular Pipeline INITIALIZED & READY")
            print("[OptionChainBuilder] >>> ALL CONSUMER LOOPS READY <<<")
        except Exception as e:
            logger.error(f"[OptionChainBuilder] Initialization disaster: {e}")
            raise

    async def _rust_consumer_loop(self) -> None:
        """The High-Perf Consumer: Shared Memory → RustBridge → Store."""
        logger.info("[OptionChainBuilder] Rust Consumer Loop ACTIVE")
        while self._initialized:
            try:
                if not self._rust_bridge.mm:
                    self._rust_bridge.connect()
                
                if not self._rust_bridge.mm:
                    await asyncio.sleep(0.5) # Try again later
                    continue

                events = list(self._rust_bridge.poll())
                if events:
                    # Convert to Arrow for high-speed enrichment (future enhancement)
                    # batch = self._rust_bridge.to_arrow_batch(events)
                    
                    for ev in events:
                        # Map Rust struct to CleanQuoteEvent
                        strike = self._sub_mgr.symbol_to_strike.get(ev["symbol"])
                        if strike is None: continue
                        
                        clean = CleanQuoteEvent(
                            seq_no=ev["seq_no"],
                            event_type=EventType(ev["event_type"]),
                            symbol=ev["symbol"],
                            strike=strike,
                            opt_type=_infer_opt_type(ev["symbol"]),
                            bid=ev["bid"] if ev["bid"] > 0 else None,
                            ask=ev["ask"] if ev["ask"] > 0 else None,
                            last_price=ev["last_price"] if ev["last_price"] > 0 else None,
                            volume=ev["volume"],
                            open_interest=None, # Pulled from REST
                            implied_volatility=None,
                            arrival_mono=ev["arrival_mono_ns"] / 1e9,
                            impact_index=ev["impact_index"],
                            is_sweep=ev["is_sweep"]
                        )
                        self._store.apply_event(clean)
                
                await asyncio.sleep(0.001) # Ultra-fast poll
            except Exception as e:
                logger.error(f"[OptionChainBuilder] Rust Consumer Loop Error: {e}")
                await asyncio.sleep(0.1)

    async def fetch_chain(self) -> dict[str, Any]:
        """Fetch current chain snapshot (Consumer Interface)."""
        if not self._initialized:
            return {"spot": None, "chain": [], "as_of": None, "version": self._store.version}

        now = datetime.now(ZoneInfo("US/Eastern"))
        try:
            # 1. Get filtered snapshot (only target symbols)
            target_set = self._sub_mgr.target_symbols
            snapshot = self._store.get_flow_merged_snapshot(
                self._depth_engine.get_flow_snapshot(),
                target_symbols=target_set
            )

            # 2. Trigger non-blocking enrichment (off-thread compute)
            # This is the "pull-through" update for Greeks
            agg = await self._greeks_engine.enrich(snapshot, self._store.spot or 0.0)

            return {
                "spot": self._store.spot,
                "chain": snapshot,
                "version": self._store.version,
                "tier2_chain": self._tier2.cache,
                "tier3_chain": self._tier3.cache,
                "volume_map": self._store.volume_map,
                "aggregate_greeks": agg,
                "ttm_seconds": agg.get("ttm_seconds"),
                "as_of": now,
                "rust_active": self._rust_bridge.mm is not None,
                "rust_shm_path": self._rust_bridge.mm_path if self._rust_bridge.mm else None,
                "shm_stats": {
                    "head": self._get_shm_val(self._rust_bridge.head_ptr),
                    "tail": self._get_shm_val(self._rust_bridge.tail_ptr),
                    "status": "OK" if self._rust_bridge.mm else "DISCONNECTED"
                },
                "governor_telemetry": {
                    "symbols_per_min": self._rate_limiter.symbol_tokens,
                    "cooldown_active": self._rate_limiter.cooldown_active
                }
            }
            if not data["rust_active"]:
                logger.warning(f"[OptionChainBuilder] fetch_chain status: rust_active=FALSE (self._rust_bridge.mm={self._rust_bridge.mm})")
            return data
        except Exception as e:
            logger.error(f"[OptionChainBuilder] fetch_chain failure: {e}")
            return {"spot": self._store.spot, "chain": [], "as_of": now, "version": self._store.version}

    def _get_shm_val(self, ptr: int) -> int:
        """Helper to read a uint64 from shm without moving internal pointers."""
        if not self._rust_bridge.mm: return 0
        import struct
        return struct.unpack("Q", self._rust_bridge.mm[ptr:ptr+8])[0]

    def _handle_rest_update(self, symbol: str, item: Any) -> None:
        """Update store from REST-fetched metadata (IV/OI)."""
        strike = self._sub_mgr.resolve_strike(symbol)
        if strike:
            clean = self._sanitizer.parse_rest_item(symbol, strike, item)
            if clean:
                applied = self._store.apply_event(clean)
                logger.debug("[OptionChainBuilder] REST update for %s | strike=%s | applied=%s", symbol, strike, applied)
            else:
                logger.warning("[OptionChainBuilder] REST update for %s failed to sanitize", symbol)
        else:
            logger.warning("[OptionChainBuilder] REST update for %s dropped: strike UNRESOLVED", symbol)

    async def _event_consumer_loop(self) -> None:
        """The Pipeline Consumer: Raw Queue → Sanitizer → Entropy → Store."""
        logger.info("[OptionChainBuilder] Pipeline Consumer Loop ACTIVE")
        queue = self._gateway.event_queue
        while self._initialized:
            try:
                raw_event = await queue.get()
                
                # Type-specific processing
                from l0_ingest.feeds.sanitization import EventType
                
                # SPECIAL CASE: SPY spot handle
                if raw_event.symbol == "SPY.US" and raw_event.event_type == EventType.QUOTE:
                    price = float(getattr(raw_event.payload, 'last_done', 0) or 0)
                    if price > 0:
                        self._store.update_spot(price)
                    continue

                # Normal Option Processing
                if raw_event.event_type == EventType.QUOTE:
                    # Resolve strike from sub mgr
                    strike = self._sub_mgr.symbol_to_strike.get(raw_event.symbol)
                    if strike is None: continue

                    clean = self._sanitizer.parse_quote(raw_event, strike)
                    if clean and self._entropy_filter.accept(clean.symbol, clean):
                        self._store.apply_event(clean)
                        
                        # PP-4 Sync OI smoothing if present
                        if clean.open_interest is not None:
                            self._store.apply_oi_smooth(clean.symbol, clean.open_interest)
                
                elif raw_event.event_type == EventType.DEPTH:
                    clean_d = self._sanitizer.parse_depth(raw_event)
                    if clean_d:
                        self._depth_engine.update_depth(
                            clean_d.symbol, 
                            getattr(raw_event.payload, 'bids', []), 
                            getattr(raw_event.payload, 'asks', [])
                        )
                        self._store.apply_depth(clean_d)
                        
                        if hasattr(self, 'on_depth') and self.on_depth is not None:
                            self.on_depth(
                                clean_d.symbol,
                                getattr(raw_event.payload, 'bids', []),
                                getattr(raw_event.payload, 'asks', [])
                            )
                
                elif raw_event.event_type == EventType.TRADE:
                    trades = getattr(raw_event.payload, 'trades', [])
                    if trades:
                        # Convert Trade objects to dicts for VPINv2 which expects dicts
                        trade_dicts = []
                        from longport.openapi import TradeDirection
                        for t in trades:
                            # Extract and normalize direction
                            raw_dir = getattr(t, "direction", 0) if not isinstance(t, dict) else t.get("dir", t.get("direction", 0))
                            if raw_dir == TradeDirection.Up or str(raw_dir) == "2" or raw_dir == 2:
                                dir_sign = 1
                            elif raw_dir == TradeDirection.Down or str(raw_dir) == "1" or raw_dir == 1:
                                dir_sign = -1
                            else:
                                dir_sign = 0

                            if isinstance(t, dict):
                                d = dict(t)
                                d["vol"] = float(d.get("vol", 0.0) or d.get("volume", 0.0))
                                d["dir"] = dir_sign
                                trade_dicts.append(d)
                            else:
                                # Safe parsing for TRADE objects
                                def _local_safe_float(v, default=0.0):
                                    try: return float(v)
                                    except: return default
                                
                                def _local_safe_int(v, default=0):
                                    try: return int(float(v))
                                    except: return default

                                vol = _local_safe_float(getattr(t, "volume", 0))
                                ts = getattr(t, "timestamp", 0)
                                def to_ts_int(val):
                                    if hasattr(val, "timestamp"): return int(val.timestamp())
                                    try: return int(float(val))
                                    except: return int(time.time())

                                ts_int = to_ts_int(ts)
                                trade_dicts.append({
                                    "price": _local_safe_float(getattr(t, "price", 0.0)),
                                    "vol": vol,
                                    "volume": vol,
                                    "timestamp": ts_int,
                                    "dir": dir_sign,
                                    "direction": dir_sign,
                                    "trade_type": _local_safe_int(getattr(t, "trade_type", 0))
                                })
                        
                        self._depth_engine.update_trades(raw_event.symbol, trade_dicts)
                        if hasattr(self, 'on_trade') and self.on_trade is not None:
                            self.on_trade(raw_event.symbol, trade_dicts)

                queue.task_done()
            except Exception as e:
                logger.error(f"[OptionChainBuilder] Consumer Loop Exception: {e}")
                await asyncio.sleep(0.1)

    def set_mandatory_symbols(self, symbols: set[str]) -> None:
        self._orchestrator.set_mandatory_symbols(symbols)

    def get_diagnostics(self) -> dict[str, Any]:
        """Consolidate diagnostics from all components."""
        diag = {
            "initialized": self._initialized,
            "gateway": self._gateway.diagnostics(),
            "store": self._store.diagnostics(),
        }
        diag.update(self._store.diagnostics())
        return diag

    async def shutdown(self) -> None:
        """Controlled pipeline shutdown."""
        self._initialized = False
        if self._consumer_task: self._consumer_task.cancel()
        if self._mgmt_task: self._mgmt_task.cancel()
        await self._gateway.disconnect()
        await self._iv_sync.stop()
        await self._tier2.stop()
        await self._tier3.stop()
        logger.info("[OptionChainBuilder] Modular Pipeline SHUTDOWN COMPLETE")

