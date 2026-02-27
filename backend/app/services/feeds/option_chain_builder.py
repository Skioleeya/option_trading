"""Option Chain Builder — Longport API integration.

Subscribes to real-time option chain data from Longport
and builds the OptionChainSnapshot used by the computation engine.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, date
from typing import Any
from zoneinfo import ZoneInfo

from longport.openapi import QuoteContext, Config, SubType
from app.config import settings, convert_to_market_time
from app.services.system.persistent_oi_store import PersistentOIStore
from app.services.analysis.bsm import compute_greeks, get_trading_time_to_maturity


logger = logging.getLogger(__name__)


class OptionChainBuilder:
    """Builds option chain snapshots from Longport API data.

    Manages:
    - Quote subscription for SPY options
    - Real-time option data aggregation
    - Snapshot construction for downstream services
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
        self._subscribed_symbols: set[str] = set()  # Currently active WebSocket subscriptions
        self._symbol_to_strike: dict[str, float] = {}  # symbol -> strike

    async def initialize(self) -> None:
        """Initialize Longport quote context and subscribe to SPY options."""
        try:
            from longport.openapi import Config, QuoteContext

            config = Config(
                app_key=settings.longport_app_key,
                app_secret=settings.longport_app_secret,
                access_token=settings.longport_access_token,
            )
            self._quote_ctx = QuoteContext(config)
            
            # PHASE 33: Register callback for push data
            self._quote_ctx.set_on_quote(self._on_quote_callback)
            
            self._initialized = True
            logger.info("[OptionChainBuilder] Longport QuoteContext initialized with Push Callback")
        except Exception as e:
            logger.error(f"[OptionChainBuilder] Failed to initialize: {e}")
            self._initialized = False

    async def fetch_chain(self) -> dict[str, Any]:
        """Fetch current option chain snapshot.

        Returns:
            Dict with 'spot', 'chain' (list of option dicts), 'as_of'
        """
        if not self._initialized or not self._quote_ctx:
            logger.warning("[OptionChainBuilder] Not initialized")
            return {"spot": None, "chain": [], "as_of": None}

        try:
            now = datetime.now(ZoneInfo("US/Eastern"))

            # Fetch SPY spot price
            spot_quotes = self._quote_ctx.quote(["SPY.US"])
            if spot_quotes:
                self._spot = float(spot_quotes[0].last_done)

            # Fetch option chain (0DTE)
            today_str = now.strftime("%Y%m%d")
            
            # Periodic Research Scan (Phase 32)
            # Scan +/- 70 points every 15 mins to identify liquidity peaks
            if not self._last_research or (now - self._last_research).total_seconds() > 900:
                await self._run_volume_research(today_str, self._spot)
                self._last_research = now

            chain_data = self._get_option_chain(today_str, spot=self._spot)
            
            # --- LOCAL BSM ENRICHMENT ---
            chain_data = self._enrich_greeks(chain_data, self._spot, now)

            # --- OI PERSISTENCE (Phase 22) ---
            # If no baseline exists for today, capture this one as start-of-session
            if not self._oi_store.has_baseline(today_str):
                self._oi_store.save_baseline(today_str, chain_data)

            self._last_update = now

            return {
                "spot": self._spot,
                "chain": chain_data,
                "volume": float(spot_quotes[0].volume) if spot_quotes else 0,
                "volume_map": self._volume_map,
                "as_of": now,
            }

        except Exception as e:
            logger.error(f"[OptionChainBuilder] fetch_chain error: {e}")
            requested_count = len(self._chain) if self._chain else 122
            got_count = 0
            logger.warning(
                f"[OptionChainBuilder] Store partial miss: "
                f"requested {requested_count}, got {got_count}"
            )
            return {
                "spot": self._spot,
                "chain": list(self._chain.values()),
                "volume_map": self._volume_map,
                "as_of": self._last_update,
            }

    def _enrich_greeks(self, chain: list[dict[str, Any]], spot: float | None, now: datetime) -> list[dict[str, Any]]:
        """Compute local BSM Greeks if API doesn't provide them."""
        if not spot or spot <= 0:
            return chain
            
        t_years = get_trading_time_to_maturity(now)
        
        for opt in chain:
            gamma = opt.get("gamma", 0)
            if gamma == 0:
                iv = opt.get("implied_volatility", 0)
                if iv > 0:
                    greeks = compute_greeks(
                        spot=spot,
                        strike=opt.get("strike", 0),
                        iv=iv,
                        t_years=t_years,
                        opt_type=opt.get("type", "CALL")
                    )
                    opt["delta"] = greeks["delta"]
                    opt["gamma"] = greeks["gamma"]
                    opt["theta"] = greeks["theta"]
                    opt["vega"] = greeks["vega"]
                    opt["vanna"] = greeks["vanna"]
                    opt["charm"] = greeks["charm"]
        return chain

    def _get_option_chain(self, expiry_date: str, spot: float | None = None) -> list[dict[str, Any]]:
        """Fetch option chain for a given expiry date from Longport.
        
        Uses a dynamic strike window around 'spot' to reduce API load.
        """
        """Fetch option chain for a given expiry date from Longport."""
        if not self._quote_ctx:
            return []

        try:
            # Conversion: option_chain_info_by_date expects a 'date' object
            if isinstance(expiry_date, str):
                try:
                    exp_date_obj = date.fromisoformat(expiry_date)
                except ValueError:
                    # Fallback if string is not ISO format
                    from datetime import datetime
                    exp_date_obj = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            else:
                exp_date_obj = expiry_date

            # Get option chain info to find all possible symbols
            chain_info = self._quote_ctx.option_chain_info_by_date("SPY.US", exp_date_obj)

            if not chain_info:
                return []

            # PHASE 33: WebSocket Push Synchronization & Subscription Management
            window = settings.strike_window_size
            target_symbols = []
            
            # Map symbols to strikes for quick lookup in callback
            new_symbol_to_strike = {}
            for s in chain_info:
                strike = float(s.price) if hasattr(s, 'price') else 0.0
                if spot and abs(strike - spot) > window:
                    continue
                    
                if hasattr(s, 'call_symbol') and s.call_symbol:
                    target_symbols.append(s.call_symbol)
                    new_symbol_to_strike[s.call_symbol] = strike
                if hasattr(s, 'put_symbol') and s.put_symbol:
                    target_symbols.append(s.put_symbol)
                    new_symbol_to_strike[s.put_symbol] = strike

            self._symbol_to_strike = new_symbol_to_strike
            target_set = set(target_symbols)

            # --- Subscription Maintenance (Differential) ---
            to_subscribe = target_set - self._subscribed_symbols
            to_unsubscribe = self._subscribed_symbols - target_set

            if to_unsubscribe:
                try:
                    self._quote_ctx.unsubscribe(list(to_unsubscribe))
                    self._subscribed_symbols -= to_unsubscribe
                    logger.debug(f"[OptionChainBuilder] Unsubscribed {len(to_unsubscribe)} symbols outside window")
                except Exception as e:
                    logger.error(f"[OptionChainBuilder] Unsubscribe error: {e}")

            if to_subscribe:
                try:
                    # Longport limit check
                    if len(self._subscribed_symbols) + len(to_subscribe) <= 100:
                        self._quote_ctx.subscribe(list(to_subscribe), [SubType.Quote])
                        self._subscribed_symbols |= to_subscribe
                        logger.info(f"[OptionChainBuilder] Subscribed to {len(to_subscribe)} new symbols. Total: {len(self._subscribed_symbols)}")
                        
                        # "Warm up" first-time subscriptions with a REST quote so we don't wait for the first tick
                        warm_quotes = self._quote_ctx.option_quote(list(to_subscribe))
                        if warm_quotes:
                            for q in warm_quotes:
                                self._update_contract_in_memory(q.symbol, q)
                    else:
                        logger.warning(f"[OptionChainBuilder] Subscription limit reached! Cannot add {len(to_subscribe)} symbols")
                except Exception as e:
                    logger.error(f"[OptionChainBuilder] Subscribe error: {e}")

            # Return the latest memory snapshot (zero network latency for the runner)
            return [data for sym, data in self._chain.items() if sym in target_set]

        except Exception as e:
            logger.error(f"[OptionChainBuilder] Error in _get_option_chain: {e}")
            return []

    def _on_quote_callback(self, symbol: str, quote: Any) -> None:
        """Callback handler for Longport WebSocket pushes."""
        try:
            self._update_contract_in_memory(symbol, quote)
        except Exception as e:
            logger.error(f"[OptionChainBuilder] Push update error for {symbol}: {e}")

    def _update_contract_in_memory(self, symbol: str, q: Any) -> None:
        """Helper to synchronize a Quote object into the internal _chain dictionary."""
        strike = self._symbol_to_strike.get(symbol)
        if strike is None:
            return

        # Reuse existing entry or initialize new one
        entry = self._chain.get(symbol, {
            "symbol": symbol,
            "strike": strike,
            "type": "CALL" if hasattr(q, 'option_type') and "Call" in str(q.option_type) else ("CALL" if "C" in symbol else "PUT"),
            "bid": 0.0,
            "ask": 0.0,
            "last_price": 0.0,
            "volume": 0,
            "open_interest": 0,
            "iv": 0.0,
            "delta": 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
        })

        # Update core fields from tick
        if hasattr(q, 'bid') and float(q.bid) > 0: entry["bid"] = float(q.bid)
        if hasattr(q, 'ask') and float(q.ask) > 0: entry["ask"] = float(q.ask)
        if hasattr(q, 'last_done') and float(q.last_done) > 0: entry["last_price"] = float(q.last_done)
        if hasattr(q, 'volume'): entry["volume"] = int(q.volume)
        if hasattr(q, 'open_interest'): entry["open_interest"] = int(q.open_interest)
        
        # Update Greeks if provided in the push and non-zero
        if hasattr(q, 'implied_volatility') and q.implied_volatility: entry["implied_volatility"] = float(q.implied_volatility)
        if hasattr(q, 'delta') and q.delta: entry["delta"] = float(q.delta)
        if hasattr(q, 'gamma') and q.gamma: entry["gamma"] = float(q.gamma)
        if hasattr(q, 'theta') and q.theta: entry["theta"] = float(q.theta)
        if hasattr(q, 'vega') and q.vega: entry["vega"] = float(q.vega)
        
        entry["last_update"] = datetime.now()
        self._chain[symbol] = entry

    async def _run_volume_research(self, today_str: str, spot: float | None) -> None:
        """Perform a wide-window scan to identify volume distribution."""
        if not spot or not self._quote_ctx:
            return

        try:
            # We use the raw info from date to get symbols
            # and then fetch quotes for +/- 70 points
            chain_info = self._quote_ctx.option_chain_info_by_date("SPY.US", datetime.now().date())
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

            # Fetch in small safe batches
            batch_size = 50
            results = []
            for i in range(0, len(research_symbols), batch_size):
                batch = research_symbols[i:i+batch_size]
                try:
                    quotes = self._quote_ctx.option_quote(batch)
                    if quotes:
                        results.extend(quotes)
                    # Small yield to not block main thread
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"[OptionChainBuilder] Research batch failure: {e}")

            # Update internal volume map
            new_map = {}
            for q in results:
                strike = strike_lookup.get(q.symbol)
                if strike is not None:
                    new_map[strike] = new_map.get(strike, 0) + int(q.volume)
            
            self._volume_map = new_map
            logger.info(f"[OptionChainBuilder] Volume map updated: {len(self._volume_map)} strikes analyzed")

        except Exception as e:
            logger.error(f"[OptionChainBuilder] Volume research failed: {e}")

    def get_diagnostics(self) -> dict[str, Any]:
        """Return diagnostic info."""
        return {
            "initialized": self._initialized,
            "chain_size": len(self._chain),
            "spot": self._spot,
            "strike_window": settings.strike_window_size,
            "volume_map_size": len(self._volume_map),
            "last_research": self._last_research.isoformat() if self._last_research else None,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    async def shutdown(self) -> None:
        """Clean shutdown."""
        self._initialized = False
        logger.info("[OptionChainBuilder] Shutdown complete")
