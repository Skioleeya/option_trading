"""Phase 27.1 — Jump Detector Engine.

Based on Paper 5: Aura et al. (2024/2025) — "Intraday Option Volume and Stock Return Jumps".
Identifies price shocks (|Z| > 3.0) that trigger non-linear 0DTE hedging flash-risks.
"""

import math
from collections import deque
from datetime import datetime
from typing import NamedTuple

from pydantic import BaseModel


class JumpResult(BaseModel):
    """Result of jump detection analysis."""
    is_jump: bool = False
    z_score: float = 0.0
    magnitude_pct: float = 0.0
    direction: str = "NEUTRAL" # BULLISH_JUMP, BEARISH_JUMP
    timestamp: datetime | None = None


class JumpDetector:
    """Detects price jumps using rolling Z-Score of log returns."""

    def __init__(self, window_size: int = 60, z_threshold: float = 3.0):
        self.window_size = window_size  # Roughly 1M if 1 tick/sec
        self.z_threshold = z_threshold
        self.prices: deque[float] = deque(maxlen=window_size + 1)
        self.returns: deque[float] = deque(maxlen=window_size)
        
        # Cooldown management
        self.last_jump_time: datetime | None = None
        self.cooldown_seconds: int = 60

    def update(self, spot: float) -> JumpResult:
        """Update with new price and check for jumps."""
        now = datetime.now()
        
        if not self.prices:
            self.prices.append(spot)
            return JumpResult(timestamp=now)

        prev_spot = self.prices[-1]
        self.prices.append(spot)
        
        # Calculate log return
        if spot > 0 and prev_spot > 0:
            ret = math.log(spot / prev_spot)
            self.returns.append(ret)
        else:
            return JumpResult(timestamp=now)

        # Need at least 20 returns for a stable SD
        if len(self.returns) < 20: 
            return JumpResult(timestamp=now)

        # Calculate Mean and StdDev
        mean_ret = sum(self.returns) / len(self.returns)
        sq_sum = sum((r - mean_ret) ** 2 for r in self.returns)
        stdev = math.sqrt(sq_sum / len(self.returns))

        if stdev == 0:
            return JumpResult(timestamp=now)

        current_ret = self.returns[-1]
        z_score = (current_ret - mean_ret) / stdev
        
        is_jump = abs(z_score) > self.z_threshold
        magnitude = (spot / prev_spot - 1) * 100.0
        
        # Handle Cooldown
        if is_jump:
            self.last_jump_time = now
            
        is_in_cooldown = False
        if self.last_jump_time:
            elapsed = (now - self.last_jump_time).total_seconds()
            if elapsed < self.cooldown_seconds:
                is_in_cooldown = True

        direction = "NEUTRAL"
        if is_jump:
            direction = "BULLISH_JUMP" if z_score > 0 else "BEARISH_JUMP"

        return JumpResult(
            is_jump=is_jump or is_in_cooldown, # Safety valve stays active during cooldown
            z_score=z_score,
            magnitude_pct=magnitude,
            direction=direction,
            timestamp=now
        )

    def reset(self):
        self.prices.clear()
        self.returns.clear()
        self.last_jump_time = None
