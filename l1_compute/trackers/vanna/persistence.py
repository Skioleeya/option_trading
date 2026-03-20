"""Redis persistence for VannaFlowAnalyzer state.

Responsibilities:
    - Serialize analyzer history to Redis (fire-and-forget)
    - Restore history from Redis on startup
    - Isolated from correlation math and classification logic

Layer:  L1
Deps:   stdlib, asyncio, zoneinfo
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from l1_compute.trackers.vanna.pearson_engine import SpotIVPoint

logger = logging.getLogger(__name__)

_ET = ZoneInfo("US/Eastern")
_REDIS_KEY_PREFIX = "vanna_analyzer:state"
_REDIS_TTL_SECONDS = 86400          # 24h
_MAX_HISTORY_AGE_FACTOR = 2         # keep point if age <= window_size * 2
_CORR_HISTORY_MAX_AGE = 300         # seconds


class VannaStatePersistence:
    """Manages Redis-backed state persistence for VannaFlowAnalyzer.

    Usage:
        persistence = VannaStatePersistence(rolling_window_size=120)
        await persistence.set_redis_client(client)
        # On each update that changes state:
        persistence.schedule_save(history, corr_history, last_iv, last_iv_time)
        # On restore:
        history, corr_history, last_iv, last_iv_time = await persistence.load()
    """

    def __init__(self, rolling_window_size: int = 120) -> None:
        self._rolling_window_size = rolling_window_size
        self._redis: Any | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # ── Setup ──────────────────────────────────────────────────────────────────

    async def set_redis_client(self, client: Any) -> None:
        """Inject shared Redis async client and load any existing state."""
        self._redis = client
        self._loop = asyncio.get_running_loop()

    # ── Save ───────────────────────────────────────────────────────────────────

    def schedule_save(
        self,
        history: deque[SpotIVPoint],
        corr_history: deque[tuple[float, float]],
        last_iv: float | None,
        last_iv_time: float | None,
    ) -> None:
        """Schedule an async fire-and-forget Redis save (thread-safe)."""
        if not self._redis or not self._loop:
            return
        data = self._serialize(history, corr_history, last_iv, last_iv_time)
        try:
            self._loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self._async_save(data))
            )
        except Exception as exc:
            logger.debug("[VannaStatePersistence] schedule_save failed (non-critical): %s", exc)

    async def _async_save(self, data: dict[str, Any]) -> None:
        if not self._redis:
            return
        try:
            today = datetime.now(_ET).date().isoformat()
            key   = f"{_REDIS_KEY_PREFIX}:{today}"
            await self._redis.setex(key, _REDIS_TTL_SECONDS, json.dumps(data))
        except Exception as exc:
            logger.debug("[VannaStatePersistence] _async_save failed (non-critical): %s", exc)

    # ── Load ───────────────────────────────────────────────────────────────────

    async def load(
        self,
        history_maxlen: int = 500,
        corr_maxlen: int = 120,
    ) -> tuple[
        deque[SpotIVPoint],
        deque[tuple[float, float]],
        float | None,
        float | None,
    ]:
        """Load state from Redis; returns empty state if not available."""
        empty = (
            deque(maxlen=history_maxlen),
            deque(maxlen=corr_maxlen),
            None,
            None,
        )
        if not self._redis:
            return empty
        try:
            today   = datetime.now(_ET).date().isoformat()
            key     = f"{_REDIS_KEY_PREFIX}:{today}"
            raw     = await self._redis.get(key)
            if not raw:
                return empty
            return self._deserialize(
                json.loads(raw),
                history_maxlen=history_maxlen,
                corr_maxlen=corr_maxlen,
            )
        except Exception as exc:
            logger.debug("[VannaStatePersistence] load failed (non-critical): %s", exc)
            return empty

    # ── (De)Serialization ─────────────────────────────────────────────────────

    @staticmethod
    def _serialize(
        history: deque[SpotIVPoint],
        corr_history: deque[tuple[float, float]],
        last_iv: float | None,
        last_iv_time: float | None,
    ) -> dict[str, Any]:
        now_mono = time.monotonic()
        now_et   = datetime.now(_ET)

        hist_data = []
        for p in history:
            age   = now_mono - p.timestamp_mono
            ts_et = now_et.timestamp() - age
            hist_data.append({"ts_et": ts_et, "spot": p.spot, "iv": p.iv})

        corr_data = []
        for ts, corr in corr_history:
            age   = now_mono - ts
            ts_et = now_et.timestamp() - age
            corr_data.append({"ts_et": ts_et, "corr": corr})

        return {
            "history":          hist_data,
            "corr_history":     corr_data,
            "last_updated":     now_et.isoformat(),
            "last_iv":          last_iv,
            "last_iv_time_age": (now_mono - last_iv_time) if last_iv_time else None,
        }

    def _deserialize(
        self,
        data: dict[str, Any],
        history_maxlen: int,
        corr_maxlen: int,
    ) -> tuple[
        deque[SpotIVPoint],
        deque[tuple[float, float]],
        float | None,
        float | None,
    ]:
        now_mono = time.monotonic()
        now_et   = datetime.now(_ET).timestamp()
        max_age  = self._rolling_window_size * _MAX_HISTORY_AGE_FACTOR

        restored_hist: list[SpotIVPoint] = []
        for p in data.get("history", []):
            age = now_et - p["ts_et"]
            if age > max_age:
                continue
            restored_hist.append(SpotIVPoint(now_mono - age, p["spot"], p["iv"]))
        restored_hist.sort(key=lambda x: x.timestamp_mono)

        restored_corr: list[tuple[float, float]] = []
        for c in data.get("corr_history", []):
            age = now_et - c["ts_et"]
            if age > _CORR_HISTORY_MAX_AGE:
                continue
            restored_corr.append((now_mono - age, c["corr"]))
        restored_corr.sort(key=lambda x: x[0])

        last_iv: float | None = data.get("last_iv")
        last_iv_time: float | None = None
        if data.get("last_iv_time_age") is not None:
            last_iv_time = now_mono - float(data["last_iv_time_age"])

        return (
            deque(restored_hist, maxlen=history_maxlen),
            deque(restored_corr, maxlen=corr_maxlen),
            last_iv,
            last_iv_time,
        )
