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
from app.config import settings, convert_to_market_time
from app.services.system.persistent_oi_store import PersistentOIStore
from app.services.analysis.bsm import get_trading_time_to_maturity, skew_adjust_iv
from app.services.analysis.bsm_fast import compute_greeks_batch, warmup as bsm_warmup

from app.services.feeds.subscription_manager import SubscriptionManager
from app.services.feeds.iv_baseline_sync import IVBaselineSync
from app.services.feeds.tier2_poller import Tier2Poller
from app.services.feeds.tier3_poller import Tier3Poller
from app.services.feeds.rate_limiter import APIRateLimiter
from app.services.analysis.depth_engine import DepthEngine
from app.services.analysis.entropy_filter import EntropyFilter

logger = logging.getLogger(__name__)



import asyncio
import logging
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from longport.openapi import Config

from app.config import settings
from app.services.feeds.market_data_gateway import MarketDataGateway
from app.services.feeds.sanitization import SanitizationPipeline, RawMarketEvent
from app.services.feeds.chain_state_store import ChainStateStore
from app.services.feeds.feed_orchestrator import FeedOrchestrator
from app.services.analysis.greeks_engine import GreeksEngine
from app.services.feeds.subscription_manager import SubscriptionManager
from app.services.feeds.iv_baseline_sync import IVBaselineSync
from app.services.feeds.tier2_poller import Tier2Poller
from app.services.feeds.tier3_poller import Tier3Poller
from app.services.analysis.depth_engine import DepthEngine
from app.services.analysis.entropy_filter import EntropyFilter

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

    def __init__(self) -> None:
        # 1. State Store (The Single Source of Truth)
        self._store = ChainStateStore()

        # 2. Logic Engines
        self._depth_engine = DepthEngine(ewma_alpha=0.1)
        self._entropy_filter = EntropyFilter(min_entropy=0.05)
        self._sanitizer = SanitizationPipeline()

        # 3. Connectivity Layer (L0)
        config = Config(
            app_key=settings.longport_app_key,
            app_secret=settings.longport_app_secret,
            access_token=settings.longport_access_token,
        )
        self._gateway = MarketDataGateway(config)

        # 4. Polling & Metadata Infrastructure
        # (Preserved shared rate limiter for REST calls)
        from app.services.feeds.rate_limiter import APIRateLimiter
        self._rate_limiter = APIRateLimiter(
            rate=settings.longport_api_rate_limit,
            burst=settings.longport_api_burst,
            max_concurrent=settings.longport_api_max_concurrent
        )
        self._sub_mgr = SubscriptionManager(self._rate_limiter)
        self._iv_sync = IVBaselineSync(self._rate_limiter)
        self._tier2 = Tier2Poller(self._rate_limiter)
        self._tier3 = Tier3Poller(self._rate_limiter)

        # 5. Domain Engines
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
            # Connect Gateway (captures loop and registers callbacks)
            await self._gateway.connect()

            # Shared loop config for IV sync hot-start
            self._iv_sync.set_event_loop(asyncio.get_event_loop())
            
            # OI hot-start from disk
            today_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
            preloaded = self._iv_sync.preload_oi_from_disk(today_str)
            logger.info(f"[OptionChainBuilder] OI preloaded: {preloaded} symbols")

            # Start Pollers
            self._iv_sync.start(
                self._gateway.quote_ctx,
                get_symbols_fn=lambda: self._sub_mgr.subscribed_symbols,
                get_spot_fn=lambda: self._store.spot,
            )
            if settings.enable_tier2_polling:
                self._tier2.start(self._gateway.quote_ctx, get_spot_fn=lambda: self._store.spot)
            if settings.enable_tier3_polling:
                self._tier3.start(self._gateway.quote_ctx, get_spot_fn=lambda: self._store.spot)

            # Start Pipeline Consumer (Processes the Queue)
            self._consumer_task = asyncio.create_task(self._event_consumer_loop())

            # Start Orchestrator Task
            self._mgmt_task = asyncio.create_task(self._orchestrator.run())

            from app.services.analysis.bsm_fast import warmup
            warmup()

            self._initialized = True
            logger.info("[OptionChainBuilder] Modular Pipeline INITIALIZED")
        except Exception as e:
            logger.error(f"[OptionChainBuilder] Initialization disaster: {e}")
            raise

    async def fetch_chain(self) -> dict[str, Any]:
        """Fetch current chain snapshot (Consumer Interface)."""
        if not self._initialized:
            return {"spot": None, "chain": [], "as_of": None}

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
                "tier2_chain": self._tier2.cache,
                "tier3_chain": self._tier3.cache,
                "volume_map": self._store.volume_map,
                "aggregate_greeks": agg,
                "as_of": now,
            }
        except Exception as e:
            logger.error(f"[OptionChainBuilder] fetch_chain failure: {e}")
            return {"spot": self._store.spot, "chain": [], "as_of": now}

    async def _event_consumer_loop(self) -> None:
        """The Pipeline Consumer: Raw Queue → Sanitizer → Entropy → Store."""
        logger.info("[OptionChainBuilder] Pipeline Consumer Loop ACTIVE")
        queue = self._gateway.event_queue
        while self._initialized:
            try:
                raw_event = await queue.get()
                
                # Type-specific processing
                from app.services.feeds.sanitization import EventType
                
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
                                vol = float(getattr(t, "volume", 0))
                                ts = getattr(t, "timestamp", 0)
                                def to_ts_int(val):
                                    if hasattr(val, "timestamp"): return int(val.timestamp())
                                    try: return int(float(val))
                                    except: return int(time.time())

                                ts_int = to_ts_int(ts)
                                trade_dicts.append({
                                    "price": float(getattr(t, "price", 0.0)),
                                    "vol": vol,
                                    "volume": vol,
                                    "timestamp": ts_int,
                                    "dir": dir_sign,
                                    "direction": dir_sign,
                                    "trade_type": int(getattr(t, "trade_type", 0))
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

