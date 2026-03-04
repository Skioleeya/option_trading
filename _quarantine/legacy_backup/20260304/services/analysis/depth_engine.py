"""
L2 Depth & Order Flow Toxicity Engine (Option B)

Calculates running metrics for critical option contracts based on
Level 1 Depth (Top of Book) and Real-time Trades (Tick-by-Tick).

Metrics:
1. bbo_imbalance: Volume imbalance between highest Bid and lowest Ask.
   Range: [-1.0, 1.0]. Positive means more bid volume than ask volume.
2. toxicity_score: Volume-Synchronized VPIN (Practice 2 — Dynamic Alpha).
   Range: [-1.0, 1.0]. +1.0 means 100% of recent volume was "Take Ask" (Aggressive Buy).
   Dynamic alpha = min(1.0, volume / vpin_bucket_size) so that:
     - Low-volume ticks (noise) have near-zero alpha → minimal toxicity change.
     - High-volume ticks (institutional) get alpha ≈ 1.0 → immediate update.
3. vpin_score: Academic VPIN metric based on volume buckets.
   Range: [-1.0, 1.0]. Directional volume / total volume within a volume bucket.
"""

import logging
from typing import Dict, Any, Optional
from longport.openapi import TradeDirection
import ndm_rust
from app.config import settings

logger = logging.getLogger(__name__)


class DepthEngine:
    def __init__(self, ewma_alpha: float = 0.1):
        """
        Args:
            ewma_alpha: Fallback alpha for BBO imbalance smoothing.
                        NOTE: For toxicity_score, dynamic alpha based on volume
                        magnitude is used instead (Practice 2 — VPIN Dynamic Alpha).
        """
        self.ewma_alpha = ewma_alpha

        # State tracking per symbol
        # Schema: symbol -> {
        #   "toxicity_score": float,
        #   "bbo_imbalance": float,
        #   "ema_volume": float,
        #   "ema_dir_volume": float,
        #   --- Practice 2: VPIN bucket state ---
        #   "volume_bucket_accumulated": float,  # cumulative volume since last bucket reset
        #   "vpin_bucket_threshold": float,       # = settings.vpin_bucket_size
        #   "vpin_dir_volume": float,             # directional (signed) volume within bucket
        #   "vpin_total_volume": float,           # unsigned volume within bucket
        #   "vpin_score": float,                  # VPIN metric (dir_volume / total_volume)
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
                # Practice 2: VPIN bucket state
                "volume_bucket_accumulated": 0.0,
                "vpin_bucket_threshold": settings.vpin_bucket_size,
                "vpin_dir_volume": 0.0,
                "vpin_total_volume": 0.0,
                "vpin_score": 0.0,
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
        """Process incoming option sub_type.trades.
        
        Now offloads the high-frequency loop to the Rust `update_vpin_logic` kernel.
        """
        if not trades:
            return
            
        # Defensive Log: Trace physical arrival of trade ticks from Longport WS
        logger.debug(f"[L1 Feed] DepthEngine received {len(trades)} trades for {symbol}")

        self._ensure_symbol(symbol)

        # VPIN Alpha config
        bucket_size = self._state[symbol]["vpin_bucket_threshold"] # Corrected from _vpin_bucket_size to _state[symbol]["vpin_bucket_threshold"]
        # Prepare trade vector for Rust bridge: list of (vol, dir_sign)
        trade_data: list[tuple[float, float]] = []
        for trade in trades:
            vol = float(getattr(trade, 'volume', 0))
            if vol <= 0: continue
            
            trade_dir = getattr(trade, 'direction', 0)
            if trade_dir == TradeDirection.Up or trade_dir == 2 or str(trade_dir) == "2":
                dir_sign = 1.0
            elif trade_dir == TradeDirection.Down or trade_dir == 1 or str(trade_dir) == "1":
                dir_sign = -1.0
            else:
                dir_sign = 0.0
            trade_data.append((vol, dir_sign))

        if not trade_data:
            return

        s = self._state[symbol]
        
        # Call Rust kernel
        (
            new_ema_v, new_ema_dv, 
            new_b_accum, new_b_dv, new_b_tv, 
            toxicity_score, vpin_score
        ) = ndm_rust.update_vpin_logic(
            ema_v=s["ema_volume"],
            ema_dv=s["ema_dir_volume"],
            b_accum=s["volume_bucket_accumulated"],
            b_dv=s["vpin_dir_volume"],
            b_tv=s["vpin_total_volume"],
            bucket_size=bucket_size,
            trades=trade_data
        )

        # Update state with Rust results
        s.update({
            "ema_volume": new_ema_v,
            "ema_dir_volume": new_ema_dv,
            "volume_bucket_accumulated": new_b_accum,
            "vpin_dir_volume": new_b_dv,
            "vpin_total_volume": new_b_tv,
            "toxicity_score": toxicity_score,
            "vpin_score": vpin_score,
        })
        
        # Defensive Log: Catch NaN or Infinity from Rust
        if toxicity_score != toxicity_score or toxicity_score == float('inf') or toxicity_score == float('-inf'):
            logger.warning(f"[L1 Rust Engine] Invalid toxicity_score computed: {toxicity_score} for {symbol}. Inputs: {trade_data}")
        if vpin_score != vpin_score or vpin_score == float('inf') or vpin_score == float('-inf'):
            logger.warning(f"[L1 Rust Engine] Invalid vpin_score computed: {vpin_score} for {symbol}. Inputs: {trade_data}")

    def get_flow_snapshot(self) -> Dict[str, Dict[str, float]]:
        """
        Returns a copy of the current Flow Toxicity, BBO Imbalance, and VPIN score
        for all active symbols.

        Practice 2: vpin_score is now included as a diagnostic field, propagated
        downstream through AgentB1 → snapshot["per_strike_gex"] → AgentG.
        """
        # Return a copy to prevent dict mutability issues in consumers
        return {
            sym: {
                "toxicity_score": data["toxicity_score"],
                "bbo_imbalance": data["bbo_imbalance"],
                "vpin_score": data["vpin_score"],
            }
            for sym, data in self._state.items()
        }
