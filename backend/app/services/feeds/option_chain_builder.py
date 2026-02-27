"""Option Chain Builder — Longport API integration.

Subscribes to real-time option chain data from Longport
and builds the OptionChainSnapshot used by the computation engine.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.config import settings, convert_to_market_time


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
            self._initialized = True
            logger.info("[OptionChainBuilder] Longport QuoteContext initialized")
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
            chain_data = self._get_option_chain(today_str)

            self._last_update = now

            return {
                "spot": self._spot,
                "chain": chain_data,
                "volume": float(spot_quotes[0].volume) if spot_quotes else 0,
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
                "as_of": self._last_update,
            }

    def _get_option_chain(self, expiry_date: str) -> list[dict[str, Any]]:
        """Fetch option chain for a given expiry date from Longport."""
        if not self._quote_ctx:
            return []

        try:
            # Get option chain info
            chain_info = self._quote_ctx.option_chain_info_by_date("SPY.US", expiry_date)

            if not chain_info:
                return []

            # Collect all option symbols
            symbols = []
            for strike_info in chain_info:
                if hasattr(strike_info, 'call_symbol') and strike_info.call_symbol:
                    symbols.append(strike_info.call_symbol)
                if hasattr(strike_info, 'put_symbol') and strike_info.put_symbol:
                    symbols.append(strike_info.put_symbol)

            if not symbols:
                return []

            # Fetch quotes for all options
            option_quotes = self._quote_ctx.option_quote(symbols)

            chain = []
            for q in option_quotes:
                opt_data = {
                    "symbol": q.symbol,
                    "option_type": "CALL" if hasattr(q, 'option_type') and "Call" in str(q.option_type) else "PUT",
                    "strike": float(q.strike_price) if hasattr(q, 'strike_price') else 0,
                    "last_price": float(q.last_done) if hasattr(q, 'last_done') else 0,
                    "volume": int(q.volume) if hasattr(q, 'volume') else 0,
                    "turnover": float(q.turnover) if hasattr(q, 'turnover') else 0,
                    "open": float(q.open) if hasattr(q, 'open') else 0,
                    "open_interest": int(q.open_interest) if hasattr(q, 'open_interest') else 0,
                    "contract_multiplier": int(q.contract_multiplier) if hasattr(q, 'contract_multiplier') else 100,
                    "implied_volatility": float(q.implied_volatility) if hasattr(q, 'implied_volatility') else 0,
                    "delta": float(q.delta) if hasattr(q, 'delta') else 0,
                    "gamma": float(q.gamma) if hasattr(q, 'gamma') else 0,
                    "theta": float(q.theta) if hasattr(q, 'theta') else 0,
                    "vega": float(q.vega) if hasattr(q, 'vega') else 0,
                    "rho": float(q.rho) if hasattr(q, 'rho') else 0,
                    "timestamp": convert_to_market_time(
                        datetime.fromtimestamp(q.timestamp.timestamp())
                    ).isoformat() if hasattr(q, 'timestamp') else None,
                    "charm": 0,  # Computed separately
                    "vanna": 0,  # Computed separately
                }
                chain.append(opt_data)
                self._chain[q.symbol] = opt_data

            return chain

        except Exception as e:
            logger.error(f"[OptionChainBuilder] _get_option_chain error: {e}")
            return list(self._chain.values())

    def get_diagnostics(self) -> dict[str, Any]:
        """Return diagnostic info."""
        return {
            "initialized": self._initialized,
            "chain_size": len(self._chain),
            "spot": self._spot,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    async def shutdown(self) -> None:
        """Clean shutdown."""
        self._initialized = False
        logger.info("[OptionChainBuilder] Shutdown complete")
