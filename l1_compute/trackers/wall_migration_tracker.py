"""Wall Migration Tracker for Agent B1 v2.0.

Tracks movement of Gamma walls (Call Wall and Put Wall) over time
to detect wall retreat, reinforcement, or stability.
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from datetime import datetime
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from shared.config import settings
from shared.models.microstructure import (
    WallMigrationCallState,
    WallMigrationPutState,
    WallMigrationResult,
)

logger = logging.getLogger(__name__)


class _WallSnapshot(NamedTuple):
    timestamp_mono: float
    call_wall: float | None
    put_wall: float | None
    call_volume: int
    put_volume: int


class WallMigrationTracker:
    """Tracks gamma wall migration over time.

    Detects:
    - RETREATING_RESISTANCE: Call wall moving higher (bullish)
    - REINFORCED_WALL: Call wall stable with increasing volume (bearish ceiling)
    - RETREATING_SUPPORT: Put wall moving lower (bearish)
    - REINFORCED_SUPPORT: Put wall stable with increasing volume (bullish floor)
    """

    def __init__(self) -> None:
        self._snapshots: deque[_WallSnapshot] = deque(maxlen=100)
        self._last_snapshot_time: float = 0.0
        self._last_result: WallMigrationResult | None = None

        # Persistence
        self._redis = None

    def set_redis_client(self, client: Any) -> None:
        """Inject shared Redis client."""
        self._redis = client

    @staticmethod
    def _normalize_wall_level(level: float | None) -> float | None:
        """Normalize wall strike from upstream layers.

        Upstream aggregation currently uses 0.0 as the "missing wall" sentinel.
        Treat non-positive / non-finite values as unavailable so breach logic
        cannot fire on invalid synthetic levels.
        """
        if level is None:
            return None
        try:
            value = float(level)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value) or value <= 0.0:
            return None
        return value

    def update(
        self,
        *,
        call_wall: float | None,
        put_wall: float | None,
        spot: float | None = None,
        call_wall_volume: int = 0,
        put_wall_volume: int = 0,
        sim_clock_mono: float | None = None,
        displacement_multiplier: float = 1.0,
    ) -> WallMigrationResult:
        """Update tracker with current wall positions."""
        now_mono = sim_clock_mono if sim_clock_mono is not None else time.monotonic()
        now_real = datetime.now(ZoneInfo("US/Eastern"))

        # Normalize sentinel/invalid levels early so all downstream branches
        # (throttle path + standard path) share identical semantics.
        call_wall = self._normalize_wall_level(call_wall)
        put_wall = self._normalize_wall_level(put_wall)

        # --- Pre-compute cross-cutting states (highest priority) ---
        # DECAYING: Late-day charm/gamma decay renders walls irrelevant after 14:00 ET
        is_decaying = now_real.hour >= 14

        # BREACHED: Spot has pierced through the wall
        # Calculate dynamic threshold based on settings percentage (e.g. 1% -> $5.00 on SPY 500)
        breakout_buffer = (spot * (settings.agent_g_wall_breakout_pct / 100.0)) if spot else 0.5
        hysteresis_buffer = breakout_buffer * 0.8  # Must fall back 80% of the buffer to un-breach
        
        was_call_breached = self._last_result and self._last_result.call_wall_state == WallMigrationCallState.BREACHED
        was_put_breached = self._last_result and self._last_result.put_wall_state == WallMigrationPutState.BREACHED

        call_breached = False
        if spot is not None and call_wall is not None:
            if was_call_breached:
                call_breached = spot > call_wall + (breakout_buffer - hysteresis_buffer)
            else:
                call_breached = spot > call_wall + breakout_buffer

        put_breached = False
        if spot is not None and put_wall is not None:
            if was_put_breached:
                put_breached = spot < put_wall - (breakout_buffer - hysteresis_buffer)
            else:
                put_breached = spot < put_wall - breakout_buffer

        # Only snapshot at configured interval
        elapsed = now_mono - self._last_snapshot_time
        if elapsed < settings.wall_snapshot_interval_seconds and self._snapshots:
            # Even on throttled return, overlay high-priority states on cached result
            if self._last_result:
                updates = {}
                if call_breached:
                    updates.update({"call_wall_state": WallMigrationCallState.BREACHED, "confidence": 0.95})
                elif is_decaying and self._last_result.call_wall_state != WallMigrationCallState.BREACHED:
                    updates["call_wall_state"] = WallMigrationCallState.DECAYING
                
                if put_breached:
                    updates.update({"put_wall_state": WallMigrationPutState.BREACHED, "confidence": 0.95})
                elif is_decaying and self._last_result.put_wall_state != WallMigrationPutState.BREACHED:
                    updates["put_wall_state"] = WallMigrationPutState.DECAYING

                # CRITICAL: Always inject live values into history tail for UI synchronization
                updates["call_wall_history"] = [s.call_wall for s in self._snapshots] + [call_wall]
                updates["put_wall_history"]  = [s.put_wall for s in self._snapshots] + [put_wall]

                return self._last_result.model_copy(update=updates)
            return WallMigrationResult()

        # If both walls are None (cold start / unwarmed chain), do NOT commit this
        # snapshot — refuse to advance _last_snapshot_time so the next valid
        # call immediately retries instead of waiting 900s.
        if call_wall is None and put_wall is None:
            logger.debug("[L3 WallTracker] Snapshot rejected: Both call_wall and put_wall are None (chain likely unwarmed).")
            # Still cache a minimal result for the UI so it shows '—' consistently
            if self._last_result is None:
                self._last_result = WallMigrationResult(
                    call_wall_state=WallMigrationCallState.STABLE,
                    put_wall_state=WallMigrationPutState.STABLE,
                    confidence=0.0,
                )
            return self._last_result

        self._last_snapshot_time = now_mono
        self._snapshots.append(_WallSnapshot(
            now_mono, call_wall, put_wall, call_wall_volume, put_wall_volume
        ))

        if len(self._snapshots) < 2:
            # First snapshot: history = [None, None, current_wall]
            # This ensures the 'current' box has data even if history is empty.
            call_hist = [None, None, call_wall]
            put_hist  = [None, None, put_wall]
            result = WallMigrationResult(
                call_wall_state=WallMigrationCallState.STABLE,
                put_wall_state=WallMigrationPutState.STABLE,
                call_wall_history=call_hist,
                put_wall_history=put_hist,
                confidence=0.5,
            )
            self._last_result = result
            return result

        # Compare current vs previous snapshot
        prev = self._snapshots[-2]
        curr = self._snapshots[-1]

        call_state = WallMigrationCallState.STABLE
        put_state = WallMigrationPutState.STABLE
        call_delta = None
        put_delta = None
        confidence = 0.0

        # Call wall analysis — BREACHED takes priority, then DECAYING
        threshold = settings.wall_displacement_threshold * displacement_multiplier
        if call_breached:
            call_state = WallMigrationCallState.BREACHED
            confidence = max(confidence, 0.95)
        elif is_decaying:
            call_state = WallMigrationCallState.DECAYING
            confidence = max(confidence, 0.3)
        elif curr.call_wall is not None and prev.call_wall is not None:
            call_delta = curr.call_wall - prev.call_wall
            if call_delta > threshold:
                call_state = WallMigrationCallState.RETREATING_RESISTANCE
                confidence = max(confidence, 0.7)
            elif call_delta < -threshold:
                call_state = WallMigrationCallState.REINFORCED_WALL
                confidence = max(confidence, 0.6)
            elif curr.call_volume > prev.call_volume + settings.volume_reinforcement_threshold:
                call_state = WallMigrationCallState.REINFORCED_WALL
                confidence = max(confidence, 0.5)

        # Put wall analysis — BREACHED takes priority, then DECAYING
        if put_breached:
            put_state = WallMigrationPutState.BREACHED
            confidence = max(confidence, 0.95)
        elif is_decaying:
            put_state = WallMigrationPutState.DECAYING
            confidence = max(confidence, 0.3)
        elif curr.put_wall is not None and prev.put_wall is not None:
            put_delta = curr.put_wall - prev.put_wall
            if put_delta < -threshold:
                put_state = WallMigrationPutState.RETREATING_SUPPORT
                confidence = max(confidence, 0.7)
            elif put_delta > threshold:
                put_state = WallMigrationPutState.REINFORCED_SUPPORT
                confidence = max(confidence, 0.6)
            elif curr.put_volume > prev.put_volume + settings.volume_reinforcement_threshold:
                put_state = WallMigrationPutState.REINFORCED_SUPPORT
                confidence = max(confidence, 0.5)

        # Build history list from snapshots PLUS THE CURRENT LIVE VALUE
        # Presenter expects total 3 slots (h1, h2, current). 
        # We supply all snapshots + the live value at the end.
        call_hist = [s.call_wall for s in self._snapshots] + [call_wall]
        put_hist  = [s.put_wall for s in self._snapshots] + [put_wall]

        result = WallMigrationResult(
            call_wall_state=call_state,
            put_wall_state=put_state,
            confidence=confidence,
            call_wall_delta=call_delta,
            put_wall_delta=put_delta,
            call_wall_history=call_hist,
            put_wall_history=put_hist,
        )
        self._last_result = result
        return result

    def get_confidence(self) -> float:
        """Return confidence of last result."""
        return self._last_result.confidence if self._last_result else 0.0

    def reset(self) -> None:
        """Reset tracker state."""
        self._snapshots.clear()
        self._last_snapshot_time = 0.0
        self._last_result = None
