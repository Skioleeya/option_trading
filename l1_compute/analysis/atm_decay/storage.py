"""Persistence layer for ATM decay (Redis + cold JSON/JSONL)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from redis.asyncio import Redis

from .series_sanitizer import SanitizedSeriesResult, sanitize_series_points

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

    def _series_cold_json_path(self, date_str: str) -> Path:
        return self._cold_dir / f"atm_series_{date_str}.json"

    def _series_cold_jsonl_path(self, date_str: str) -> Path:
        return self._cold_dir / f"atm_series_{date_str}.jsonl"

    def _diagnostic_cold_jsonl_path(self, date_str: str) -> Path:
        return self._cold_dir / f"atm_anchor_diag_{date_str}.jsonl"

    # Backward-compatible alias kept for external diagnostics/tests.
    def _series_cold_path(self, date_str: str) -> Path:
        return self._series_cold_json_path(date_str)

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

    async def delete_anchor(self, date_str: str) -> None:
        if self._redis:
            await self._redis.delete(self._redis_key_tpl.format(date=date_str))
        anchor_path = self._anchor_cold_path(date_str)
        if anchor_path.exists():
            try:
                anchor_path.unlink()
            except Exception as exc:
                logger.error(f"[AtmDecayStorage] Failed deleting cold anchor: {exc}")

    async def recover_series_from_cold_if_needed(self, date_str: str, ttl_seconds: int) -> None:
        if not self._redis:
            return

        try:
            history_points = self._sanitize_series(
                date_str,
                self._load_cold_series_points(date_str),
                source="cold_restore",
            )
            if not history_points.points:
                return
            if history_points.dropped_total > 0:
                self._rewrite_cold_series_jsonl(date_str, history_points.points)

            series_key = self._series_key_tpl.format(date=date_str)
            current_len = await self._redis.llen(series_key)
            if current_len != 0:
                return

            pipe = self._redis.pipeline()
            for point in history_points.points:
                pipe.rpush(series_key, json.dumps(point))
            pipe.expire(series_key, ttl_seconds)
            await pipe.execute()
            logger.info(
                "[AtmDecayStorage] Recovered %s cold tracking points into Redis.",
                len(history_points.points),
            )
        except Exception as exc:
            logger.error(f"[AtmDecayStorage] Cold series restore failed: {exc}")

    async def get_history(self, date_str: str) -> list[dict[str, Any]]:
        if self._redis:
            key = self._series_key_tpl.format(date=date_str)
            raw = await self._redis.lrange(key, 0, -1)
            if raw:
                result = self._sanitize_series(
                    date_str,
                    [json.loads(r) for r in raw],
                    source="redis_history",
                )
                return result.points
        result = self._sanitize_series(
            date_str,
            self._load_cold_series_points(date_str),
            source="cold_history",
        )
        return result.points

    async def get_latest_history_point(self, date_str: str) -> dict[str, Any] | None:
        if self._redis:
            key = self._series_key_tpl.format(date=date_str)
            raw = await self._redis.lrange(key, 0, -1)
            if raw:
                try:
                    points = [json.loads(entry) for entry in raw]
                except Exception as exc:
                    logger.error(f"[AtmDecayStorage] Failed decoding latest Redis history point: {exc}")
                else:
                    sanitized = self._sanitize_series(
                        date_str,
                        points,
                        source="redis_latest_history",
                    )
                    if sanitized.points:
                        return sanitized.points[-1]

        sanitized = self._sanitize_series(
            date_str,
            self._load_cold_series_points(date_str),
            source="cold_latest_history",
        )
        if not sanitized.points:
            return None
        latest = sanitized.points[-1]
        return latest if isinstance(latest, dict) else None

    async def flush_series(self, date_str: str) -> None:
        if self._redis:
            await self._redis.delete(self._series_key_tpl.format(date=date_str))
            await self._redis.delete(f"app:atm_anchor_diag:{date_str}")
        for cold_history_file in (
            self._series_cold_jsonl_path(date_str),
            self._series_cold_json_path(date_str),
            self._diagnostic_cold_jsonl_path(date_str),
        ):
            if cold_history_file.exists():
                try:
                    cold_history_file.unlink()
                except Exception as exc:
                    logger.error(f"[AtmDecayStorage] Failed to flush cold series history: {exc}")

    async def append_series(self, date_str: str, data: dict[str, Any]) -> None:
        sanitized = self._sanitize_series(date_str, [data], source="append_series")
        if not sanitized.points:
            return
        payload = json.dumps(sanitized.points[0])
        if self._redis:
            key = self._series_key_tpl.format(date=date_str)
            await self._redis.rpush(key, payload)
        else:
            logger.warning("[AtmDecayStorage] Redis unavailable, writing cold JSONL mirror only.")

        try:
            with self._series_cold_jsonl_path(date_str).open("a", encoding="utf-8") as fh:
                fh.write(payload)
                fh.write("\n")
        except Exception as exc:
            logger.error(f"[AtmDecayStorage] Cold JSONL append fail: {exc}")

    async def append_anchor_diagnostic(self, date_str: str, data: dict[str, Any]) -> None:
        payload = json.dumps(data)
        if self._redis:
            await self._redis.rpush(f"app:atm_anchor_diag:{date_str}", payload)
        try:
            with self._diagnostic_cold_jsonl_path(date_str).open("a", encoding="utf-8") as fh:
                fh.write(payload)
                fh.write("\n")
        except Exception as exc:
            logger.error(f"[AtmDecayStorage] Cold diagnostics append fail: {exc}")

    def _load_cold_series_points(self, date_str: str) -> list[dict[str, Any]]:
        """Load cold series, preferring JSONL and falling back to legacy JSON arrays."""
        points = self._load_cold_series_points_jsonl(date_str)
        if points:
            return points

        legacy_points = self._load_cold_series_points_legacy_json(date_str)
        if legacy_points:
            self._migrate_legacy_series_to_jsonl(date_str, legacy_points)
        return legacy_points

    def _load_cold_series_points_jsonl(self, date_str: str) -> list[dict[str, Any]]:
        path = self._series_cold_jsonl_path(date_str)
        if not path.exists():
            return []

        points: list[dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    raw = line.strip()
                    if not raw:
                        continue
                    obj = json.loads(raw)
                    if isinstance(obj, dict):
                        points.append(obj)
        except Exception as exc:
            logger.error(f"[AtmDecayStorage] Failed reading cold JSONL series: {exc}")
            return []
        return points

    def _load_cold_series_points_legacy_json(self, date_str: str) -> list[dict[str, Any]]:
        path = self._series_cold_json_path(date_str)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error(f"[AtmDecayStorage] Failed reading legacy cold JSON series: {exc}")
            return []
        if not isinstance(data, list):
            return []
        return [pt for pt in data if isinstance(pt, dict)]

    def _migrate_legacy_series_to_jsonl(self, date_str: str, points: list[dict[str, Any]]) -> None:
        """One-time compatibility bridge from legacy JSON array to JSONL."""
        jsonl_path = self._series_cold_jsonl_path(date_str)
        if jsonl_path.exists():
            return
        try:
            with jsonl_path.open("w", encoding="utf-8") as fh:
                for point in points:
                    fh.write(json.dumps(point))
                    fh.write("\n")
            logger.info("[AtmDecayStorage] Migrated legacy cold JSON series to JSONL: %s", jsonl_path.name)
        except Exception as exc:
            logger.error(f"[AtmDecayStorage] Failed migrating legacy JSON series to JSONL: {exc}")

    def _sanitize_series(
        self,
        date_str: str,
        points: list[dict[str, Any]],
        *,
        source: str,
    ) -> SanitizedSeriesResult:
        result = sanitize_series_points(points, date_str=date_str)
        if result.dropped_total > 0:
            logger.warning(
                "[AtmDecayStorage] Sanitized %s: date=%s input=%s kept=%s "
                "dropped_invalid=%s dropped_wrong_date=%s dropped_future=%s dropped_duplicate=%s",
                source,
                date_str,
                result.input_count,
                len(result.points),
                result.dropped_invalid,
                result.dropped_wrong_date,
                result.dropped_future,
                result.dropped_duplicate,
            )
        return result

    def _rewrite_cold_series_jsonl(self, date_str: str, points: list[dict[str, Any]]) -> None:
        path = self._series_cold_jsonl_path(date_str)
        try:
            with path.open("w", encoding="utf-8") as fh:
                for point in points:
                    fh.write(json.dumps(point))
                    fh.write("\n")
            logger.info("[AtmDecayStorage] Rewrote sanitized cold JSONL series: %s", path.name)
        except Exception as exc:
            logger.error(f"[AtmDecayStorage] Failed rewriting sanitized JSONL series: {exc}")
