"""Cold-file persistence for wall-migration snapshots."""

from __future__ import annotations

import json
import logging
import math
from collections import deque
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class WallMigrationStorage:
    """Append/read wall snapshots as per-day JSONL files."""

    def __init__(self, cold_dir: str | Path) -> None:
        self._cold_dir = Path(cold_dir)
        self._cold_dir.mkdir(parents=True, exist_ok=True)

    def _series_path(self, date_str: str) -> Path:
        return self._cold_dir / f"wall_series_{date_str}.jsonl"

    def append_snapshot(self, date_str: str, snapshot: dict[str, Any]) -> None:
        record = self._sanitize_snapshot(snapshot)
        if record is None:
            return
        try:
            with self._series_path(date_str).open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record))
                fh.write("\n")
        except Exception as exc:
            logger.error("[WallMigrationStorage] append failed date=%s error=%s", date_str, exc)
            raise

    def load_recent(self, date_str: str, limit: int) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        path = self._series_path(date_str)
        if not path.exists():
            return []

        rows: deque[dict[str, Any]] = deque(maxlen=limit)
        try:
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    raw = line.strip()
                    if not raw:
                        continue
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning("[WallMigrationStorage] skip invalid json line path=%s", path.name)
                        continue
                    if not isinstance(payload, dict):
                        continue
                    record = self._sanitize_snapshot(payload)
                    if record is not None:
                        rows.append(record)
        except Exception as exc:
            logger.error("[WallMigrationStorage] load failed date=%s error=%s", date_str, exc)
            raise

        return list(rows)

    @staticmethod
    def _sanitize_snapshot(data: dict[str, Any]) -> dict[str, Any] | None:
        call_wall = WallMigrationStorage._to_positive_float(data.get("call_wall"))
        put_wall = WallMigrationStorage._to_positive_float(data.get("put_wall"))
        if call_wall is None and put_wall is None:
            return None

        ts = data.get("timestamp")
        timestamp = str(ts).strip() if ts is not None else ""
        if not timestamp:
            return None

        return {
            "timestamp": timestamp,
            "call_wall": call_wall,
            "put_wall": put_wall,
            "call_volume": WallMigrationStorage._to_non_negative_int(data.get("call_volume")),
            "put_volume": WallMigrationStorage._to_non_negative_int(data.get("put_volume")),
        }

    @staticmethod
    def _to_positive_float(value: Any) -> float | None:
        try:
            num = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(num) or num <= 0.0:
            return None
        return num

    @staticmethod
    def _to_non_negative_int(value: Any) -> int:
        try:
            num = int(value)
        except (TypeError, ValueError):
            return 0
        return max(0, num)
