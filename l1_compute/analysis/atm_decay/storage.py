"""Persistence layer for ATM decay (Redis + cold JSON)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class AtmDecayStorage:
    """Encapsulates Redis and cold-file operations for ATM decay state."""

    def __init__(
        self,
        redis_client: Redis | None,
        cold_dir: str | Path,
        redis_key_tpl: str,
        series_key_tpl: str,
    ) -> None:
        self._redis = redis_client
        self._cold_dir = Path(cold_dir)
        self._cold_dir.mkdir(parents=True, exist_ok=True)
        self._redis_key_tpl = redis_key_tpl
        self._series_key_tpl = series_key_tpl

    @property
    def redis(self) -> Redis | None:
        return self._redis

    @redis.setter
    def redis(self, client: Redis | None) -> None:
        self._redis = client

    @property
    def cold_dir(self) -> Path:
        return self._cold_dir

    def _anchor_cold_path(self, date_str: str) -> Path:
        return self._cold_dir / f"atm_{date_str}.json"

    def _series_cold_path(self, date_str: str) -> Path:
        return self._cold_dir / f"atm_series_{date_str}.json"

    async def load_anchor_from_redis(self, date_str: str) -> dict[str, Any] | None:
        if not self._redis:
            return None
        raw = await self._redis.get(self._redis_key_tpl.format(date=date_str))
        if not raw:
            return None
        return json.loads(raw)

    def load_anchor_from_cold(self, date_str: str) -> dict[str, Any] | None:
        p = self._anchor_cold_path(date_str)
        if not p.exists():
            return None
        return json.loads(p.read_text())

    async def save_anchor(self, date_str: str, data: dict[str, Any], ttl_seconds: int) -> None:
        if self._redis:
            key = self._redis_key_tpl.format(date=date_str)
            await self._redis.set(key, json.dumps(data), ex=ttl_seconds)
        try:
            self._anchor_cold_path(date_str).write_text(json.dumps(data, indent=2))
        except Exception as exc:
            logger.error(f"[AtmDecayStorage] Cold JSON write failed: {exc}")

    async def recover_series_from_cold_if_needed(self, date_str: str, ttl_seconds: int) -> None:
        if not self._redis:
            return
        cold_history_file = self._series_cold_path(date_str)
        if not cold_history_file.exists():
            return

        try:
            history_points = json.loads(cold_history_file.read_text())
            if not history_points or not isinstance(history_points, list):
                return

            series_key = self._series_key_tpl.format(date=date_str)
            current_len = await self._redis.llen(series_key)
            if current_len != 0:
                return

            pipe = self._redis.pipeline()
            for point in history_points:
                pipe.rpush(series_key, json.dumps(point))
            pipe.expire(series_key, ttl_seconds)
            await pipe.execute()
            logger.info(f"[AtmDecayStorage] Recovered {len(history_points)} cold tracking points into Redis.")
        except Exception as exc:
            logger.error(f"[AtmDecayStorage] Cold JSON timeseries restore failed: {exc}")

    async def get_history(self, date_str: str) -> list[dict[str, Any]]:
        if not self._redis:
            return []
        key = self._series_key_tpl.format(date=date_str)
        raw = await self._redis.lrange(key, 0, -1)
        return [json.loads(r) for r in raw]

    async def flush_series(self, date_str: str) -> None:
        if self._redis:
            await self._redis.delete(self._series_key_tpl.format(date=date_str))
        cold_history_file = self._series_cold_path(date_str)
        if cold_history_file.exists():
            try:
                cold_history_file.unlink()
            except Exception as exc:
                logger.error(f"[AtmDecayStorage] Failed to flush cold JSON history: {exc}")

    async def append_series(self, date_str: str, data: dict[str, Any]) -> None:
        if not self._redis:
            logger.warning("[AtmDecayStorage] CANNOT STORE SERIES: redis client is NONE")
            return
        key = self._series_key_tpl.format(date=date_str)
        await self._redis.rpush(key, json.dumps(data))

        # Keep cold mirror updated asynchronously via caller fire-and-forget.
        try:
            raw_history = await self._redis.lrange(key, 0, -1)
            parsed_history = [json.loads(pt) for pt in raw_history]
            self._series_cold_path(date_str).write_text(json.dumps(parsed_history))
        except Exception as exc:
            logger.error(f"[AtmDecayStorage] Async JSON flush fail: {exc}")
