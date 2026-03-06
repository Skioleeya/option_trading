import logging
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from longport.openapi import QuoteContext, SubType, Config
from shared.config import settings
from l0_ingest.feeds.market_data_gateway import MarketDataGateway
from l0_ingest.feeds.rate_limiter import APIRateLimiter

logger = logging.getLogger(__name__)
CALL_WINDOW = 25.0
PUT_WINDOW = 35.0

class OptionSubscriptionManager:
    """Unified manager for dual-stack ingestion (Python + Rust).
    
    Inherits logical windowing from legacy SubscriptionManager.
    """
    
    def __init__(self, config: Config, rate_limiter: Optional[APIRateLimiter] = None, primary_ctx: Any = None):
        """Unified manager for dual-stack ingestion (Python + Rust)."""
        print(f"==================================================")
        print(f"[SubscriptionManager] BOOTING (Dual-Stack Mode)")
        import sys, os
        print(f"[SubscriptionManager] Working Dir: {os.getcwd()}")
        print(f"[SubscriptionManager] Python Path: {sys.path[:3]}...")
        print(f"[SubscriptionManager] Longport Key Present: {bool(settings.longport_app_key)}")
        print(f"[SubscriptionManager] Primary Context Injected: {primary_ctx is not None}")
        print(f"==================================================")
        
        self.config = config
        self.py_gateway = MarketDataGateway(config, primary_ctx=primary_ctx)
        self._rust_gateway = None # Lazy load
        
        self.shm_path = "sentinel_shm_live"
        self.is_rust_started = False
        
        # State tracking
        self._subscribed_symbols: set[str] = set()
        self._depth_subscribed_symbols: set[str] = set()
        self._target_symbols: set[str] = set()
        self._symbol_to_strike: dict[str, float] = {}
        self._limiter = rate_limiter or APIRateLimiter(10, 20, 5) # Default if not provided
        
        # Routing map: symbol -> mode ('rust' or 'python')
        self._routing: Dict[str, str] = {}

    @property
    def rust_gateway(self) -> Any:
        if self._rust_gateway is None:
            print("[SubscriptionManager] Dynamically importing l0_rust...")
            import l0_rust
            self._rust_gateway = l0_rust.RustIngestGateway()
        return self._rust_gateway

    @property
    def subscribed_symbols(self) -> set[str]:
        return self._subscribed_symbols

    @property
    def target_symbols(self) -> set[str]:
        return self._target_symbols

    @property
    def symbol_to_strike(self) -> dict[str, float]:
        return self._symbol_to_strike

    def resolve_strike(self, symbol: str) -> float | None:
        return self._symbol_to_strike.get(symbol)

    async def connect(self):
        await self.py_gateway.connect()
        logger.info("[SubscriptionManager] Python Gateway connected.")

    async def refresh(self, ctx: QuoteContext, spot: float | None, mandatory_symbols: set[str] | None = None) -> set[str]:
        """Collect core symbols and sync subscriptions. Returns the target set."""
        print(f"[SubscriptionManager] REFRESH TRIGGERED | spot={spot} | mandatory={len(mandatory_symbols or [])}")
        target_set = await self._collect_core_symbols(ctx, spot)
        if mandatory_symbols:
            target_set.update(mandatory_symbols)

        self._target_symbols = target_set
        print(f"[SubscriptionManager] TARGET SET SIZE: {len(target_set)}")
        
        # Physical sync
        await self._sync_subscriptions(ctx, target_set, spot, mandatory_symbols)
        return target_set

    async def _collect_core_symbols(self, ctx: QuoteContext, spot: float | None) -> set[str]:
        if not ctx or not spot: 
            print("[SubscriptionManager] Skipping collection: ctx/spot missing.")
            return set()
        
        now_date = datetime.now(ZoneInfo("US/Eastern")).date()
        valid_dates = []
        for i in range(7):
            check_date = now_date + timedelta(days=i)
            async with self._limiter.acquire(weight=1):
                try:
                    chain_info = ctx.option_chain_info_by_date("SPY.US", check_date)
                    if chain_info:
                        valid_dates.append((check_date, chain_info))
                        if len(valid_dates) >= 3: break
                except: continue

        target_symbols = set()
        new_symbol_to_strike = {}
        for _, chain_info in valid_dates:
            for s in chain_info:
                strike = float(s.price) if hasattr(s, 'price') else 0.0
                dist = strike - spot
                if dist > CALL_WINDOW or dist < -PUT_WINDOW: continue
                
                if hasattr(s, 'call_symbol') and s.call_symbol:
                    target_symbols.add(s.call_symbol)
                    new_symbol_to_strike[s.call_symbol] = strike
                if hasattr(s, 'put_symbol') and s.put_symbol:
                    target_symbols.add(s.put_symbol)
                    new_symbol_to_strike[s.put_symbol] = strike
        
        self._symbol_to_strike = new_symbol_to_strike
        return target_symbols

    async def _sync_subscriptions(self, ctx: QuoteContext, target_set: set[str], spot: float | None, mandatory_symbols: set[str] | None = None) -> None:
        # For simplicity in Phase 16, we route everything in target_set to Rust 
        # unless explicitly overridden.
        rust_targets = target_set # Default everything to high-perf Rust path
        
        if not self.is_rust_started and rust_targets:
            print(f"\n[SubscriptionManager] >>> RUST GATEWAY START SEQUENCE INITIATED <<<")
            print(f"[SubscriptionManager] Target Symbols: {len(rust_targets)}")
            try:
                self.rust_gateway.start(list(rust_targets), self.shm_path, 1)
                self.is_rust_started = True
                self._subscribed_symbols = set(rust_targets)
                print(f"[SubscriptionManager] >>> RUST GATEWAY TASK SPAWNED SUCCESSFULLY <<<")
                logger.info(f"[SubscriptionManager] Rust Gateway started with {len(rust_targets)} symbols.")
            except Exception as e:
                print(f"[SubscriptionManager] !!! RUST GATEWAY FATAL ERROR: {e}")
                import traceback
                traceback.print_exc()
        elif self.is_rust_started:
            # Update tracked symbols for IVSync even if gateway already started
            self._subscribed_symbols = set(rust_targets)
            print(f"[SubscriptionManager] UPDATED SUBSCRIBED_SYMBOLS: {len(self._subscribed_symbols)}")
        
        # Standard Python Gateway handles SPY.US and any non-option metadata if needed
        # But OCB already handles SPY.US via _gateway.connect() internal callback registrations
        pass

    def subscribe(self, symbols: List[str], mode: str = "rust"):
        # Manual override/injection
        for s in symbols:
            self._routing[s] = mode
        
        if mode == "rust":
            if not self.is_rust_started:
                print(f"[SubscriptionManager] Manual Start (Rust): {len(symbols)} syms")
                self.rust_gateway.start(symbols, self.shm_path, 1)
                self.is_rust_started = True
            self._subscribed_symbols |= set(symbols)
        else:
            self.py_gateway.subscribe(symbols, [SubType.Quote, SubType.Depth, SubType.Trade])

    def stop(self):
        self.py_gateway.disconnect()
        if self.is_rust_started and self._rust_gateway:
            self._rust_gateway.stop()
        logger.info("[SubscriptionManager] All gateways stopped.")
