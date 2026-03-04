"""Phase 25C — 0DTE Time Decay Factor.

Calculates a decay factor based on market hours to adjust microstructure signal weights 
as expiration approaches. In 0DTE, gamma risk and vanna flow sensitivity explode 
near the close (Paper 5: Aura et al.).
"""

from datetime import datetime
from zoneinfo import ZoneInfo


class TimeDecayFactor:
    """Calculates 0DTE end-of-day exponential decay factor."""

    def __init__(self, market_close_hour: int = 16, market_close_minute: int = 0):
        self.market_close_hour = market_close_hour
        self.market_close_minute = market_close_minute
        self.tz = ZoneInfo("US/Eastern")

    def get_decay_factor(self, current_time: datetime | None = None) -> float:
        """
        Returns a factor from 0.0 to 1.0.
        0.0 = Market open / Early day
        1.0 = Market close
        
        The factor starts increasing meaningfully after 14:00 ET.
        """
        if current_time is None:
            current_time = datetime.now(self.tz)
        else:
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=self.tz)

        # Calculate time remaining in minutes
        close_time = current_time.replace(
            hour=self.market_close_hour, 
            minute=self.market_close_minute, 
            second=0, 
            microsecond=0
        )
        
        # If after hours, return 1.0 (or clamp)
        if current_time >= close_time:
            return 1.0
            
        total_seconds = (close_time - current_time).total_seconds()
        total_minutes = total_seconds / 60.0
        
        # We focus on the last 120 minutes (2 hours)
        # Factor = max(0, (120 - total_minutes) / 120)
        # But we use a curve: factor = clamp(0, 1, (120 - total_minutes) / 120)
        
        if total_minutes > 120:
            return 0.0
            
        # Linear decay for simplicity in v1, can be changed to exponential (1 - exp(-k*t))
        factor = (120.0 - total_minutes) / 120.0
        return max(0.0, min(1.0, factor))

    def is_pre_close(self, factor: float) -> bool:
        """Threshold for PRE-CLOSE label (e.g., last 30 mins)."""
        return factor > 0.75  # ~15:30 ET
