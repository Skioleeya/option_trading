"""
L2 Depth & Order Flow Toxicity Engine (Option B)

Calculates running metrics for critical option contracts based on
Level 1 Depth (Top of Book) and Real-time Trades (Tick-by-Tick).

Metrics:
1. bbo_imbalance: Volume imbalance between highest Bid and lowest Ask.
   Range: [-1.0, 1.0]. Positive means more bid volume than ask volume.
2. toxicity_score: Exponential Moving Average of Trade Direction weighted by volume.
   Range: [-1.0, 1.0]. +1.0 means 100% of recent volume was "Take Ask" (Aggressive Buy).
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DepthEngine:
    def __init__(self, ewma_alpha: float = 0.1):
        """
        Args:
            ewma_alpha: Alpha smoothing factor for EWMA calculations.
                        A smaller alpha (e.g. 0.1) provides a smoother trend,
                        absorbing high-frequency tick noise.
        """
        self.ewma_alpha = ewma_alpha
        
        # State tracking per symbol
        # Schema: symbol -> { 
        #   "toxicity_score": float, 
        #   "bbo_imbalance": float, 
        #   "ema_volume": float, 
        #   "ema_dir_volume": float
        # }
        self._state: Dict[str, Dict[str, float]] = {}

    def _ensure_symbol(self, symbol: str):
        """Initializes empty state for a new symbol."""
        if symbol not in self._state:
            self._state[symbol] = {
                "toxicity_score": 0.0,
                "bbo_imbalance": 0.0,
                "ema_volume": 0.0,
                "ema_dir_volume": 0.0,
            }

    def update_depth(self, symbol: str, bids: list[Any], asks: list[Any]) -> None:
        """
        Updates Top-of-Book (BBO) Imbalance from a Depth Push event.
        Called asynchronously from the websocket callback via OptionChainBuilder.
        """
        self._ensure_symbol(symbol)

        # In LV1, we only get the Top Of Book (bids[0] and asks[0])
        bid_vol = getattr(bids[0], "volume", 0) if bids else 0
        ask_vol = getattr(asks[0], "volume", 0) if asks else 0

        total_vol = bid_vol + ask_vol
        if total_vol > 0:
            # -1.0 means all Ask volume, +1.0 means all Bid volume
            raw_imbalance = (bid_vol - ask_vol) / float(total_vol)
            
            # Smooth out the BBO jitter using EWMA
            prev_imb = self._state[symbol]["bbo_imbalance"]
            self._state[symbol]["bbo_imbalance"] = prev_imb + self.ewma_alpha * (raw_imbalance - prev_imb)

    def update_trades(self, symbol: str, trades: list[Any]) -> None:
        """
        Updates Order Flow Toxicity from a Trade Push event.
        A Trade event often packs multiple ticks simultaneously.
        """
        if not trades:
            return
            
        self._ensure_symbol(symbol)
        
        alpha = self.ewma_alpha
        
        for trade in trades:
            vol = getattr(trade, 'volume', 0)
            if vol <= 0:
                continue
                
            # direction: Longport TradeDirection enum
            # 0 = Neutral (Cross/Off-book)
            # 1 = Up (Take Ask -> Bullish aggressive)
            # 2 = Down (Hit Bid -> Bearish aggressive)
            direction = str(getattr(trade, 'direction', '0'))
            
            if direction == "1":
                dir_sign = 1.0
            elif direction == "2":
                dir_sign = -1.0
            else:
                # Ignore neutral/uncategorized trades for directional toxicity
                continue 
                
            # Volume-Weighted Directional EWMA
            prev_ema_v = self._state[symbol]["ema_volume"]
            prev_ema_dv = self._state[symbol]["ema_dir_volume"]
            
            new_ema_v = (1 - alpha) * prev_ema_v + alpha * vol
            new_ema_dv = (1 - alpha) * prev_ema_dv + alpha * (dir_sign * vol)
            
            self._state[symbol]["ema_volume"] = new_ema_v
            self._state[symbol]["ema_dir_volume"] = new_ema_dv
            
            if new_ema_v > 1e-8:
                self._state[symbol]["toxicity_score"] = new_ema_dv / new_ema_v

    def get_flow_snapshot(self) -> Dict[str, Dict[str, float]]:
        """
        Returns a copy of the current Flow Toxicity and BBO Imbalance state
        for all active symbols.
        """
        # Return a copy to prevent dict mutability issues in consumers
        return {
            sym: {
                "toxicity_score": data["toxicity_score"],
                "bbo_imbalance": data["bbo_imbalance"],
            }
            for sym, data in self._state.items()
        }
