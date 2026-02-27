"""Wall Migration Tracker for Agent B1 v2.0.

Tracks movement of Gamma walls (Call Wall and Put Wall) over time
to detect wall retreat, reinforcement, or stability.
"""

from __future__ import annotations

import time
from collections import deque
from datetime import datetime
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from app.config import settings
from app.models.microstructure import (
    WallMigrationCallState,
    WallMigrationPutState,
    WallMigrationResult,
)


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
        if settings.redis_url:
            try:
                import redis
                self._redis = redis.Redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=1
                )
            except Exception:
                pass

    def update(
        self,
        *,
        call_wall: float | None,
        put_wall: float | None,
        call_wall_volume: int = 0,
        put_wall_volume: int = 0,
        sim_clock_mono: float | None = None,
    ) -> WallMigrationResult:
        """Update tracker with current wall positions."""
        now_mono = sim_clock_mono if sim_clock_mono is not None else time.monotonic()

        # Only snapshot at configured interval
        elapsed = now_mono - self._last_snapshot_time
        if elapsed < settings.wall_snapshot_interval_seconds and self._snapshots:
            return self._last_result or WallMigrationResult()

        self._last_snapshot_time = now_mono
        self._snapshots.append(_WallSnapshot(
            now_mono, call_wall, put_wall, call_wall_volume, put_wall_volume
        ))

        if len(self._snapshots) < 2:
            return WallMigrationResult()

        # Compare current vs previous snapshot
        prev = self._snapshots[-2]
        curr = self._snapshots[-1]

        call_state = WallMigrationCallState.STABLE
        put_state = WallMigrationPutState.STABLE
        call_delta = None
        put_delta = None
        confidence = 0.0

        # Call wall analysis
        if curr.call_wall is not None and prev.call_wall is not None:
            call_delta = curr.call_wall - prev.call_wall
            if call_delta > settings.wall_displacement_threshold:
                call_state = WallMigrationCallState.RETREATING_RESISTANCE
                confidence = max(confidence, 0.7)
            elif call_delta < -settings.wall_displacement_threshold:
                call_state = WallMigrationCallState.REINFORCED_WALL
                confidence = max(confidence, 0.6)
            elif curr.call_volume > prev.call_volume + settings.volume_reinforcement_threshold:
                call_state = WallMigrationCallState.REINFORCED_WALL
                confidence = max(confidence, 0.5)

        # Put wall analysis
        if curr.put_wall is not None and prev.put_wall is not None:
            put_delta = curr.put_wall - prev.put_wall
            if put_delta < -settings.wall_displacement_threshold:
                put_state = WallMigrationPutState.RETREATING_SUPPORT
                confidence = max(confidence, 0.7)
            elif put_delta > settings.wall_displacement_threshold:
                put_state = WallMigrationPutState.REINFORCED_SUPPORT
                confidence = max(confidence, 0.6)
            elif curr.put_volume > prev.put_volume + settings.volume_reinforcement_threshold:
                put_state = WallMigrationPutState.REINFORCED_SUPPORT
                confidence = max(confidence, 0.5)

        result = WallMigrationResult(
            call_wall_state=call_state,
            put_wall_state=put_state,
            confidence=confidence,
            call_wall_delta=call_delta,
            put_wall_delta=put_delta,
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
