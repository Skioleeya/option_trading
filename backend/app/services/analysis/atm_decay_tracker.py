"""ATM Decay Tracker Module.

Tracks the SPY ATM options price exactly at 9:30 AM ET and calculates real-time
premium decay (Call, Put, Straddle) relative to that anchor.
Provides dual-layer persistence (Redis + Local JSON) to survive fast-API restarts.
"""

import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

# Eastern Time Zone
ET = ZoneInfo("US/Eastern")

class AtmDecayTracker:
    """Manages the 9:30 AM ATM anchor and calculates real-time decay."""

    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client
        self.anchor: dict[str, Any] | None = None
        
        # Cold storage paths
        self.cold_storage_dir = Path(settings.opening_atm_cold_storage_root)
        self.cold_storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Key templates
        self.redis_key_template = "app:opening_atm:{date}"
        self.series_key_template = "app:atm_decay_series:{date}"
        
        self._current_date_str = datetime.now(ET).strftime("%Y%m%d")
        
        self.is_initialized = False

    async def initialize(self) -> None:
        """Attempt to restore today's anchor from Redis or fallback to local JSON."""
        now = datetime.now(ET)
        self._current_date_str = now.strftime("%Y%m%d")
        
        anchor_key = self.redis_key_template.format(date=self._current_date_str)
        fallback_file = self.cold_storage_dir / f"atm_{self._current_date_str}.json"
        
        # 1. Try Redis
        if self.redis:
            try:
                raw_data = await self.redis.get(anchor_key)
                if raw_data:
                    self.anchor = json.loads(raw_data)
                    logger.info(f"[AtmDecayTracker] Restored ATM anchor from Redis: {self.anchor}")
                    self.is_initialized = True
                    return
            except Exception as e:
                logger.error(f"[AtmDecayTracker] Failed reading Redis anchor: {e}")
                
        # 2. Fallback to Local JSON
        if fallback_file.exists():
            try:
                with open(fallback_file, "r") as f:
                    self.anchor = json.load(f)
                logger.info(f"[AtmDecayTracker] Restored ATM anchor from fallback JSON: {self.anchor}")
                self.is_initialized = True
                
                # Opportunistically heal Redis if it's connected now
                if self.redis:
                    try:
                        await self._save_to_redis(self.anchor, self._current_date_str)
                    except Exception:
                        pass
                return
            except Exception as e:
                logger.error(f"[AtmDecayTracker] Failed reading fallback JSON: {e}")
                
        # 3. No existing anchor found
        logger.info("[AtmDecayTracker] No existing anchor found for today. Waiting for 9:30 AM.")
        self.is_initialized = True

    async def _save_to_redis(self, data: dict[str, Any], date_str: str) -> None:
        """Save anchor to Redis with TTL."""
        if not self.redis:
            return
            
        key = self.redis_key_template.format(date=date_str)
        payload = json.dumps(data)
        await self.redis.set(key, payload, ex=settings.opening_atm_redis_ttl_seconds)

    async def _save_to_disk(self, data: dict[str, Any], date_str: str) -> None:
        """Save anchor to local JSON fallback."""
        fallback_file = self.cold_storage_dir / f"atm_{date_str}.json"
        try:
            with open(fallback_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"[AtmDecayTracker] Failed to write fallback JSON: {e}")

    async def _persist_anchor(self, anchor_data: dict[str, Any]) -> None:
        """Main method to persist to both layers."""
        self.anchor = anchor_data
        
        # Determine the trade date based on the timestamp inside the anchor
        dt = datetime.fromisoformat(anchor_data["timestamp"])
        date_str = dt.strftime("%Y%m%d")
        
        # Dual-write
        await self._save_to_redis(anchor_data, date_str)
        await self._save_to_disk(anchor_data, date_str)
        logger.info(f"[AtmDecayTracker] Persisted new anchor for {date_str}: {anchor_data}")

    async def update(self, chain: list[dict[str, Any]], spot: float) -> dict[str, Any] | None:
        """
        Process incoming option chain. 
        Will capture the anchor at 9:30 AM if not set.
        Returns the ui_state.atm dictionary.
        """
        if not self.is_initialized:
            return None
            
        now = datetime.now(ET)
        current_time = now.time()
        
        market_open_time = datetime.strptime("09:30:00", "%H:%M:%S").time()
        
        # Pre-market: Do nothing
        if current_time < market_open_time:
            return None
            
        # Time to capture anchor!
        if not self.anchor:
            await self._capture_anchor(chain, spot, now)
            
        if not self.anchor:
           # Capture failed (e.g., chain empty)
           return None

        # Calculate Decay
        return await self._calculate_decay(chain)

    async def _capture_anchor(self, chain: list[dict[str, Any]], spot: float, now: datetime) -> None:
        """Identify ATM strike and record opening premiums."""
        if not chain or spot <= 0:
            return
            
        # Find ATM strike
        # Note: Depending on SPX/SPY rules, it's typically the nearest strike
        closest_strike = min(set(opt["strike"] for opt in chain), key=lambda x: abs(x - spot))
        
        call_price = 0.0
        put_price = 0.0
        
        # Extract Ask or Mid prices (Assuming 'ask' or 'mid' field exists, fallback to 'last')
        for opt in chain:
            if opt["strike"] == closest_strike:
                # Prefer mid price if available, else last price
                price = opt.get("mid", opt.get("last_price", 0.0))
                opt_type = opt.get("option_type", opt.get("type", "")).upper()
                
                if opt_type in ("CALL", "C"):
                    call_price = price
                elif opt_type in ("PUT", "P"):
                    put_price = price
                    
        if call_price > 0 and put_price > 0:
            new_anchor = {
                "strike": closest_strike,
                "call_price": call_price,
                "put_price": put_price,
                "timestamp": now.isoformat()
            }
            await self._persist_anchor(new_anchor)
        else:
            logger.warning(f"[AtmDecayTracker] Failed to capture full straddle prices for ATM strike: {closest_strike}")

    async def _calculate_decay(self, chain: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Calculate percentage change from anchor."""
        if not self.anchor:
            return None
            
        target_strike = self.anchor["strike"]
        anchor_c = self.anchor["call_price"]
        anchor_p = self.anchor["put_price"]
        anchor_straddle = anchor_c + anchor_p
        
        curr_c = 0.0
        curr_p = 0.0
        
        for opt in chain:
            if opt["strike"] == target_strike:
                price = opt.get("mid", opt.get("last_price", 0.0))
                opt_type = opt.get("option_type", opt.get("type", "")).upper()
                
                if opt_type in ("CALL", "C"):
                    curr_c = price
                elif opt_type in ("PUT", "P"):
                    curr_p = price
                    
        if curr_c == 0.0 or curr_p == 0.0:
            return None
            
        curr_straddle = curr_c + curr_p
        
        call_pct = (curr_c - anchor_c) / anchor_c if anchor_c > 0 else 0.0
        put_pct = (curr_p - anchor_p) / anchor_p if anchor_p > 0 else 0.0
        straddle_pct = (curr_straddle - anchor_straddle) / anchor_straddle if anchor_straddle > 0 else 0.0
        
        timestamp = datetime.now(ET)
        
        result = {
            "strike": target_strike,
            "locked_at": datetime.fromisoformat(self.anchor["timestamp"]).strftime("%H:%M:%S"),
            "call_pct": round(call_pct, 4),
            "put_pct": round(put_pct, 4),
            "straddle_pct": round(straddle_pct, 4),
            "timestamp": timestamp.isoformat() # Added so frontend can plot the time series
        }
        
        # Append to Time-Series History
        await self._append_to_series(result, timestamp.strftime("%Y%m%d"))
        
        return result

    async def _append_to_series(self, data: dict[str, Any], date_str: str) -> None:
        """Append tick to Redis time-series list for Full Fetch."""
        if not self.redis:
            return
            
        key = self.series_key_template.format(date=date_str)
        # Using RPUSH to append to the list
        await self.redis.rpush(key, json.dumps(data))
        # Important: SET TTL on the list if it's new
        if await self.redis.llen(key) == 1:
            await self.redis.expire(key, settings.opening_atm_redis_ttl_seconds)

    async def get_history(self, date_str: str) -> list[dict[str, Any]]:
        """Retrieve full day's history for the frontend."""
        if not self.redis:
            return []
            
        key = self.series_key_template.format(date=date_str)
        raw_list = await self.redis.lrange(key, 0, -1)
        
        return [json.loads(item) for item in raw_list]
