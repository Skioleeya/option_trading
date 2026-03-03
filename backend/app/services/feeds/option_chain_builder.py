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


class OptionChainBuilder:
    """Builds option chain snapshots from Longport API data.

    Orchestrates:
    - SubscriptionManager (Tier 1 WS)
    - IVBaselineSync (IV/OI cache)
    - Tier2Poller (2DTE REST)
    - Tier3Poller (Weekly REST)
    - Local BSM Greeks enrichment
    - DepthEngine (L2 Flow Toxicity)
    - WebSocket callback handling
    """

    def __init__(self) -> None:
        self._chain: dict[str, dict[str, Any]] = {}  # symbol -> option data
        self._spot: float | None = None
        self._last_update: datetime | None = None
        self._quote_ctx = None
        self._initialized = False
        self._oi_store = PersistentOIStore()
        self._volume_map: dict[float, int] = {}  # strike -> total volume
        self._last_research: datetime | None = None
        self._last_spot_update: datetime | None = None

        # RACE FIX (Race 2): asyncio loop reference for thread-safe WS callback dispatch
        self._loop: asyncio.AbstractEventLoop | None = None
        # Off-thread call counter for RACE_PROBE logging (not a lock — just a counter)
        self._ws_offthread_calls: int = 0

        # PP-4 FIX: OI EMA state (alpha=0.2 smooths REST 5-min step-jumps)
        self._oi_smooth: dict[str, float] = {}   # symbol -> smoothed OI

        # Shared rate limiter — single token bucket for ALL REST callers
        # PP-LIMIT FIX: Longport 30req/30s limit is strict. Using 0.9/s with burst=1.
        self._rate_limiter = APIRateLimiter(rate=0.9, burst=1, max_concurrent=2)

        # Modular components (rate limiter injected into every REST user)
        self._sub_mgr = SubscriptionManager(self._rate_limiter)
        self._iv_sync = IVBaselineSync(self._rate_limiter)
        self._tier2 = Tier2Poller(self._rate_limiter)
        self._tier3 = Tier3Poller(self._rate_limiter)
        
        # Depth Engine for Order Flow Toxicity and BBO Imbalance
        self._depth_engine = DepthEngine(ewma_alpha=0.1)

        # Shannon Entropy pre-filter: drops zero-information ticks before BSM
        # min_entropy=0.05 means at least one field must change by ≥0.1% to pass
        self._entropy_filter = EntropyFilter(min_entropy=0.05)

    async def initialize(self) -> None:
        """Initialize Longport quote context and start all components."""
        try:
            # RACE FIX (Race 2): capture the running asyncio loop so WS callbacks
            # (fired from Longport SDK OS threads) can schedule writes safely.
            self._loop = asyncio.get_event_loop()

            # DEBUG TOKEN LENTH AND BOUNDS
            tk = settings.longport_access_token
            masked_tk = f"{tk[:5]}...{tk[-5:]}" if tk else "NONE"
            logger.info(f"[OptionChainBuilder] Token Diag: key={settings.longport_app_key} token={masked_tk} len={len(tk) if tk else 0}")

            config = Config(
                app_key=settings.longport_app_key,
                app_secret=settings.longport_app_secret,
                access_token=settings.longport_access_token,
            )
            self._quote_ctx = QuoteContext(config)

            # Register WS callbacks
            self._quote_ctx.set_on_quote(self._on_quote_callback)
            self._quote_ctx.set_on_depth(self._on_depth_callback)
            self._quote_ctx.set_on_trades(self._on_trades_callback)
            
            # Subscribe to SPY spot (Quote, Depth, Trade)
            self._quote_ctx.subscribe(["SPY.US"], [SubType.Quote, SubType.Depth, SubType.Trade])
            self._sub_mgr._depth_subscribed_symbols.add("SPY.US")

            self._initialized = True
            logger.info("[OptionChainBuilder] QuoteContext initialized")

            # Share the loop reference with IVBaselineSync for thread-safe iv_cache writes
            self._iv_sync.set_event_loop(self._loop)

            # Start all background components
            self._iv_sync.start(
                self._quote_ctx,
                get_symbols_fn=lambda: self._sub_mgr.subscribed_symbols,
                get_spot_fn=lambda: self._spot,
            )
            self._tier2.start(self._quote_ctx, get_spot_fn=lambda: self._spot)
            self._tier3.start(self._quote_ctx, get_spot_fn=lambda: self._spot)

            # Pre-compile Numba JIT kernel (one-time ~1600ms cost at startup)
            bsm_warmup()

            # Start administrative management loop (Subscriptions & Warm-ups)
            self._mgmt_task = asyncio.create_task(self._management_loop())

        except Exception as e:
            logger.error(f"[OptionChainBuilder] Failed to initialize: {e}")
            self._initialized = False

    async def fetch_chain(self) -> dict[str, Any]:
        """Fetch current option chain snapshot (Zero-Wait).

        Returns:
            Dict with 'spot', 'chain', 'tier2_chain', 'tier3_chain', 'as_of'
        """
        if not self._initialized:
            return {"spot": None, "chain": [], "as_of": None}

        try:
            now = datetime.now(ZoneInfo("US/Eastern"))
            
            # 1. Filter current in-memory chain to active subscriptions
            # Use `target_symbols` for stability, protecting against the WebSocket sync loop race
            target_set = self._sub_mgr.target_symbols
            chain_data = [data for sym, data in self._chain.items() if sym in target_set]

            # Incorporate flow snapshots from Depth engine
            flow_snap = self._depth_engine.get_flow_snapshot()
            for data in chain_data:
                sym = data["symbol"]
                if sym in flow_snap:
                    data["toxicity_score"] = flow_snap[sym]["toxicity_score"]
                    data["bbo_imbalance"] = flow_snap[sym]["bbo_imbalance"]
                else:
                    data["toxicity_score"] = 0.0
                    data["bbo_imbalance"] = 0.0
            
            # 2. Local Enrichment & Single-Pass Aggregation

            aggregate_greeks = self._enrich_chain_with_local_greeks(chain_data)

            self._last_update = now
            return {
                "spot": self._spot,
                "chain": chain_data,
                "tier2_chain": self._tier2.cache,
                "tier3_chain": self._tier3.cache,
                "volume_map": self._volume_map,
                "aggregate_greeks": aggregate_greeks,
                "as_of": now,
            }

        except Exception as e:
            logger.error(f"[OptionChainBuilder] fetch_chain error: {e}")
            return {
                "spot": self._spot,
                "chain": list(self._chain.values()),
                "volume_map": self._volume_map,
                "aggregate_greeks": {},
                "as_of": self._last_update,
            }

    async def _management_loop(self) -> None:
        """Background task for administrative work: sub refresh, warm-ups, research."""
        while self._initialized:
            try:
                now = datetime.now(ZoneInfo("US/Eastern"))
                today_str = now.strftime("%Y%m%d")

                # 1. Spot Fallback (REST if WS is silent) — rate-limited
                if self._spot is None or (self._last_spot_update and 
                                        (now - self._last_spot_update).total_seconds() > 10.0):
                    async with self._rate_limiter.acquire():
                        spot_quotes = self._quote_ctx.quote(["SPY.US"])
                    if spot_quotes:
                        self._spot = float(spot_quotes[0].last_done)
                        self._last_spot_update = now

                # 2. Refresh Subscriptions (Heavy REST)
                if self._spot:
                    target_set = await self._sub_mgr.refresh(self._quote_ctx, self._spot)
                    
                    # 3. Warm up IV cache for new symbols (Extremely Heavy REST)
                    if new_symbols:
                        logger.info(f"[OptionChainBuilder] Detected {len(new_symbols)} new symbols. Triggering sync warm-up...")
                        await self._iv_sync.warm_up(list(new_symbols))
                    else:
                        logger.debug("[OptionChainBuilder] No new symbols for IV sync.")

                # 4. Periodic Volume Research (Every 15 mins)
                if self._spot and (not self._last_research or 
                                (now - self._last_research).total_seconds() > 900):
                    await self._run_volume_research(today_str, self._spot)
                    self._last_research = now

            except Exception as e:
                logger.error(f"[OptionChainBuilder] Management loop error: {e}")
            
            # STARTUP BOOST: Run faster for the first 5 minutes (every 5s) to warm up chain
            if (datetime.now(ZoneInfo("US/Eastern")) - now).total_seconds() < 300:
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(60)

    # =========================================================================
    # Tier 1: Core Chain Retrieval (DEPRECATED - Moved to management loop)
    # =========================================================================

    async def _get_option_chain(self, spot: float | None = None) -> list[dict[str, Any]]:
        return []

    # =========================================================================
    # BSM Enrichment
    # =========================================================================

    def _enrich_chain_with_local_greeks(self, chain_data: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute Greeks for the whole chain in-place and return aggregates.

        FAST PATH: builds NumPy arrays for the entire chain, calls the Numba
        JIT batch engine (`compute_greeks_batch`), then writes results back in
        a second O(n) pass. This eliminates the inner-loop Python overhead and
        allows Numba to parallelise across CPU cores.

        PP-1 FIX: WS IV values older than WS_IV_TTL are treated as stale.
        PP-2 FIX: spot_ref looked up per-symbol from iv_sync.spot_at_sync.
        PP-4 FIX: OI smoothed with EMA(α=0.2).
        """
        if self._spot is None or self._spot <= 0:
            return {}

        WS_IV_TTL: float = 60.0

        now      = datetime.now(ZoneInfo("US/Eastern"))
        t_years  = get_trading_time_to_maturity(now)
        now_mono = time.monotonic()

        agg = {
            "net_gex": 0.0, "net_vanna": 0.0, "net_charm": 0.0,
            "total_call_gex": 0.0, "total_put_gex": 0.0,
            "call_wall": None, "put_wall": None,
            "max_call_gex": 0.0, "max_put_gex": 0.0, "atm_iv": 0.0,
        }
        min_strike_diff = float("inf")

        n = len(chain_data)
        if n == 0:
            return agg

        # ── Phase 1: build input arrays and resolve IVs ────────────────────────
        spots_arr   = np.empty(n, dtype=np.float64)
        strikes_arr = np.empty(n, dtype=np.float64)
        ivs_arr     = np.zeros(n,  dtype=np.float64)  # 0 = invalid / skip
        is_call_arr = np.empty(n,  dtype=np.bool_)
        adj_ivs     = np.zeros(n,  dtype=np.float64)  # skew-adjusted IV per entry
        ois_arr     = np.zeros(n,  dtype=np.float64)
        mults_arr   = np.zeros(n,  dtype=np.float64)
        vols_arr    = np.zeros(n,  dtype=np.float64)

        for idx, entry in enumerate(chain_data):
            symbol   = entry["symbol"]
            strike   = entry["strike"]
            opt_type = entry["type"].upper()

            spots_arr[idx]   = self._spot
            strikes_arr[idx] = strike
            is_call_arr[idx] = opt_type in ("CALL", "C")
            vols_arr[idx]    = float(entry.get("volume", 0))
            
            # OI resolution + EMA smoothing (PP-4)
            raw_oi     = self._iv_sync.oi_cache.get(symbol, 0)
            prev_smooth = self._oi_smooth.get(symbol, float(raw_oi))
            smoothed_oi = prev_smooth + 0.2 * (raw_oi - prev_smooth)
            self._oi_smooth[symbol] = smoothed_oi
            oi = int(smoothed_oi)
            entry["open_interest"] = oi
            
            ois_arr[idx] = float(oi)
            mults_arr[idx] = float(entry.get("contract_multiplier", 100))

            # IV resolution: WS real-time > REST cache (PP-1: TTL guard)
            ws_iv_raw = entry.get("implied_volatility")
            iv_age    = now_mono - entry.get("iv_timestamp", 0.0)
            ws_iv     = ws_iv_raw if (ws_iv_raw and ws_iv_raw > 0 and iv_age < WS_IV_TTL) else None
            rest_iv   = self._iv_sync.iv_cache.get(symbol)
            
            if ws_iv_raw is not None and ws_iv is None:
                logger.debug(f"[L1 Fallback] Stale WS IV for {symbol} (Age: {iv_age:.1f}s), falling back to REST cache.")
                
            raw_iv    = ws_iv if ws_iv is not None else rest_iv

            if raw_iv and raw_iv > 0:
                # PP-2: per-symbol spot reference
                spot_ref = self._iv_sync.spot_at_sync.get(symbol, self._spot)
                adj_iv   = skew_adjust_iv(
                    cached_iv=raw_iv,
                    spot_now=self._spot,
                    spot_ref=spot_ref,
                    opt_type=entry["type"],
                )
                ivs_arr[idx]  = adj_iv
                adj_ivs[idx]  = adj_iv

        # Vectorized Volume computation (OTM specific)
        otm_call_mask = is_call_arr & (strikes_arr > self._spot)
        otm_put_mask  = ~is_call_arr & (strikes_arr < self._spot)
        
        agg["otm_call_vol"] = int(np.sum(vols_arr[otm_call_mask]))
        agg["otm_put_vol"]  = int(np.sum(vols_arr[otm_put_mask]))
        agg["total_chain_vol"] = int(np.sum(vols_arr))

        # ── Phase 2: batch Greeks (single Numba/NumPy call for entire chain) ──
        batch, batch_agg = compute_greeks_batch(
            spots_arr, strikes_arr, ivs_arr, t_years, is_call_arr,
            r=settings.risk_free_rate,
            q=settings.bsm_dividend_yield,
            ois=ois_arr,
            mults=mults_arr,
        )

        # ── Phase 3: write results back + aggregate ────────────────────────────
        for idx, entry in enumerate(chain_data):
            if ivs_arr[idx] <= 0:
                continue  # no valid IV — skip

            symbol   = entry["symbol"]
            strike   = entry["strike"]
            adj_iv   = adj_ivs[idx]

            greeks = {
                "delta":            float(batch["delta"][idx]),
                "gamma":            float(batch["gamma"][idx]),
                "vega":             float(batch["vega"][idx]),
                "vanna":            float(batch["vanna"][idx]),
                "charm":            float(batch["charm"][idx]),
                "theta":            float(batch["theta"][idx]),
                "implied_volatility": adj_iv,
            }
            entry.update(greeks)

            # ATM IV tracking
            strike_diff = abs(strike - self._spot)
            if strike_diff < min_strike_diff:
                min_strike_diff = strike_diff
                agg["atm_iv"] = adj_iv

            if symbol in self._chain:
                self._chain[symbol].update(greeks)

        if batch_agg:
            agg.update(batch_agg)

        return agg

    # =========================================================================
    # WebSocket Callbacks
    # =========================================================================

    def _on_quote_callback(self, symbol: str, quote: Any) -> None:
        """Callback handler for Longport WebSocket pushes.

        RACE FIX (Race 2): This is called from the Longport SDK OS thread.
        We MUST NOT touch self._chain or self._iv_sync.iv_cache directly here.
        Instead route the update via call_soon_threadsafe so it executes on
        the asyncio event loop thread where all dict reads happen.
        """
        if self._loop is None:
            logger.warning("[RACE_PROBE] WS callback fired before loop initialized — dropped")
            return
        self._ws_offthread_calls += 1
        if self._ws_offthread_calls <= 5 or self._ws_offthread_calls % 100 == 0:
            logger.debug(
                f"[RACE_PROBE] WS OS-thread call #{self._ws_offthread_calls}: symbol={symbol}"
            )
        self._loop.call_soon_threadsafe(self._safe_on_quote, symbol, quote)

    def _safe_on_quote(self, symbol: str, quote: Any) -> None:
        """Executes on asyncio thread — safe to touch _chain and iv_cache."""
        try:
            if symbol == "SPY.US":
                if hasattr(quote, 'last_done') and float(quote.last_done) > 0:
                    self._spot = float(quote.last_done)
                    self._last_spot_update = datetime.now(ZoneInfo("US/Eastern"))
                return
            self._update_contract_in_memory(symbol, quote)
        except Exception as e:
            logger.error(f"[OptionChainBuilder] Safe push error for {symbol}: {e}")

    def _update_contract_in_memory(self, symbol: str, q: Any) -> None:
        """Sync a Quote push into the internal _chain dictionary.

        SAFETY: Must only be called from the asyncio thread (via _safe_on_quote).
        Direct calls from OS threads are prohibited after Race 2 fix.

        PP-1 FIX: Every WS IV update now stamps entry["iv_timestamp"] with
        time.monotonic(). The enrichment loop in _enrich_chain_with_local_greeks
        checks this timestamp and downgrades stale WS IV to the REST cache if
        it is older than WS_IV_TTL (60s), eliminating 'zombie IV' oscillation.

        FIELD PROTECTION: LongPort WebSocket Quotes for options often lack
        IV and OI. We MUST NOT default missing fields to 0, as it overwrites
        valid REST cache. We only update fields present in the quote object.
        """
        strike = self._sub_mgr.symbol_to_strike.get(symbol)
        if strike is None:
            return

        # 1. Build values safely — only include fields that exist in the push
        new_values = {}
        
        # Core Price/Volume (Usually present)
        for field, attr in [
            ("last_price", "last_done"),
            ("volume", "volume"),
            ("bid", "bid"),
            ("ask", "ask"),
            ("current_volume", "current_volume"),
            ("turnover", "turnover")
        ]:
            val = getattr(q, attr, None)
            if val is not None:
                new_values[field] = float(val)

        # Optional Greeks/OI (Nested in option_extend for LongPort)
        opt_ext = getattr(q, "option_extend", None)
        if opt_ext:
            iv_val = getattr(opt_ext, "implied_volatility", None)
            if iv_val is not None:
                try:
                    # Protobuf string to float, then scale from percent
                    new_values["implied_volatility"] = float(iv_val) / 100.0
                    new_values["iv_timestamp"] = time.monotonic()
                except (ValueError, TypeError):
                    pass

            oi_val = getattr(opt_ext, "open_interest", None)
            if oi_val is not None:
                new_values["open_interest"] = int(oi_val)
        else:
            # Fallback for flat structure or calc_indexes results
            iv_val = getattr(q, "implied_volatility", None)
            if iv_val is not None:
                new_values["implied_volatility"] = float(iv_val) / 100.0
                new_values["iv_timestamp"] = time.monotonic()

            oi_val = getattr(q, "open_interest", None)
            if oi_val is not None:
                new_values["open_interest"] = int(oi_val)

        if not new_values:
            return

        # Shannon entropy gate: discard zero-information ticks
        if not self._entropy_filter.accept(symbol, new_values):
            return

        entry = self._chain.get(symbol, {
            "symbol": symbol,
            "strike": strike,
            "type": "CALL" if "C" in symbol else "PUT",
            "bid": 0.0, "ask": 0.0, "last_price": 0.0,
            "volume": 0, "open_interest": 0, "iv": 0.0,
            "delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0,
        })

        if hasattr(q, 'bid') and float(q.bid) > 0: entry["bid"] = float(q.bid)
        if hasattr(q, 'ask') and float(q.ask) > 0: entry["ask"] = float(q.ask)
        if hasattr(q, 'last_done') and float(q.last_done) > 0: entry["last_price"] = float(q.last_done)
        if hasattr(q, 'volume'): entry["volume"] = int(q.volume)
        if hasattr(q, 'open_interest') and q.open_interest:
            oi_val = int(q.open_interest)
            entry["open_interest"] = oi_val
            # RACE FIX (Race 3): route iv_cache/oi_cache write through IVBaselineSync's
            # thread-safe method. Since _update_contract_in_memory now only runs on
            # the asyncio thread, this is a direct call (no extra thread handoff needed).
            self._iv_sync.apply_iv_update(symbol, None, oi_val)
        if hasattr(q, 'implied_volatility') and q.implied_volatility:
            iv_value = float(q.implied_volatility) / 100.0
            entry["implied_volatility"] = iv_value
            # PP-1 FIX: stamp the monotonic time so _enrich_ can detect stale WS IV
            entry["iv_timestamp"] = time.monotonic()
            self._iv_sync.apply_iv_update(symbol, iv_value)
        if hasattr(q, 'delta') and q.delta: entry["delta"] = float(q.delta)
        if hasattr(q, 'gamma') and q.gamma: entry["gamma"] = float(q.gamma)
        if hasattr(q, 'theta') and q.theta: entry["theta"] = float(q.theta)
        if hasattr(q, 'vega') and q.vega: entry["vega"] = float(q.vega)

        entry["last_update"] = datetime.now(ZoneInfo("US/Eastern"))
        self._chain[symbol] = entry

    def _on_depth_callback(self, symbol: str, event: Any) -> None:
        """Callback handler for Longport WebSocket Depth pushes (OS thread)."""
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._safe_on_depth, symbol, event)
        
    def _safe_on_depth(self, symbol: str, event: Any) -> None:
        """Execute on asyncio thread to safely update DepthEngine."""
        try:
            bids = getattr(event, 'bids', [])
            asks = getattr(event, 'asks', [])
            if bids or asks:
                self._depth_engine.update_depth(symbol, bids, asks)
        except Exception as e:
            logger.error(f"[OptionChainBuilder] Safe depth error for {symbol}: {e}")

    def _on_trades_callback(self, symbol: str, event: Any) -> None:
        """Callback handler for Longport WebSocket Trade pushes (OS thread)."""
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._safe_on_trades, symbol, event)
        
    def _safe_on_trades(self, symbol: str, event: Any) -> None:
        """Execute on asyncio thread to safely update DepthEngine."""
        try:
            trades = getattr(event, 'trades', [])
            if trades:
                self._depth_engine.update_trades(symbol, trades)
        except Exception as e:
            logger.error(f"[OptionChainBuilder] Safe trade error for {symbol}: {e}")

    # =========================================================================
    # Volume Research (Wide-window discovery)
    # =========================================================================

    async def _run_volume_research(self, today_str: str, spot: float | None) -> None:
        """Wide-window scan to identify volume distribution."""
        if not spot or not self._quote_ctx:
            return
        try:
            async with self._iv_sync._limiter.acquire():
                try:
                    chain_info = self._quote_ctx.option_chain_info_by_date("SPY.US", datetime.now().date())
                except Exception as e:
                    if "301607" in str(e):
                        self._iv_sync._limiter.trigger_cooldown()
                    logger.warning(f"[OptionChainBuilder] Volume research metadata failed: {e}")
                    return

            if not chain_info:
                return

            window = settings.research_window_size
            research_symbols = []
            strike_lookup = {}
            for s in chain_info:
                strike = float(s.price) if hasattr(s, 'price') else 0.0
                if abs(strike - spot) <= window:
                    if hasattr(s, 'call_symbol') and s.call_symbol:
                        research_symbols.append(s.call_symbol)
                        strike_lookup[s.call_symbol] = strike
                    if hasattr(s, 'put_symbol') and s.put_symbol:
                        research_symbols.append(s.put_symbol)
                        strike_lookup[s.put_symbol] = strike

            batch_size = 50
            results = []
            for i in range(0, len(research_symbols), batch_size):
                batch = research_symbols[i:i + batch_size]
                async with self._rate_limiter.acquire():  # Rate-limited — no more naked sleep
                    try:
                        quotes = self._quote_ctx.option_quote(batch)
                        if quotes:
                            results.extend(quotes)
                    except Exception as e:
                        logger.error(f"[OptionChainBuilder] Research batch failure: {e}")

            new_map = {}
            for q in results:
                strike = strike_lookup.get(q.symbol)
                if strike is not None:
                    new_map[strike] = new_map.get(strike, 0) + int(q.volume)

            self._volume_map = new_map
            logger.info(f"[OptionChainBuilder] Volume map: {len(self._volume_map)} strikes")

        except Exception as e:
            logger.error(f"[OptionChainBuilder] Volume research failed: {e}")

    # =========================================================================
    # Diagnostics & Lifecycle
    # =========================================================================

    def get_diagnostics(self) -> dict[str, Any]:
        """Return diagnostic info."""
        # Defensive Log: Check for stale data indicating WS drop
        now_mono = time.monotonic()
        if self._chain:
            # Get the first entry to check its timestamp
            first_symbol = next(iter(self._chain))
            first_entry = self._chain[first_symbol]
            first_timestamp = first_entry.get("iv_timestamp", 0) # Use iv_timestamp for freshness
            if first_timestamp > 0:
                age_ms = (now_mono - first_timestamp) * 1000
                if age_ms > 3000: # 3 seconds
                    logger.warning(f"[L0 Feed] Stale Quote Data detected. Age: {age_ms:.0f}ms. WS might be disconnected.")

        return {
            "initialized": self._initialized,
            "chain_size": len(self._chain),
            "tier1_subscribed": len(self._sub_mgr.subscribed_symbols),
            "tier2_size": len(self._tier2.cache),
            "tier2_expiry": str(self._tier2.expiry) if self._tier2.expiry else None,
            "tier3_size": len(self._tier3.cache),
            "tier3_expiry": str(self._tier3.expiry) if self._tier3.expiry else None,
            "spot": self._spot,
            "strike_window": settings.strike_window_size,
            "volume_map_size": len(self._volume_map),
            "last_research": self._last_research.isoformat() if self._last_research else None,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    async def shutdown(self) -> None:
        """Clean shutdown of all components."""
        self._initialized = False
        await self._iv_sync.stop()
        await self._tier2.stop()
        await self._tier3.stop()
        logger.info("[OptionChainBuilder] Shutdown complete")
