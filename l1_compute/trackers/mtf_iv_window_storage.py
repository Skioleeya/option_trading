"""Cold-file persistence for MTF IV rolling-window snapshots."""

from __future__ import annotations

import json
import logging
import math
from collections import deque
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TF_KEYS = ("1m", "5m", "15m")
_TF_MAXLEN = {"1m": 20, "5m": 12, "15m": 8}


class MTFIVWindowStorage:
    """Append/read MTF IV window snapshots as per-day JSONL files."""

    def __init__(self, cold_dir: str | Path) -> None:
        self._cold_dir = Path(cold_dir)
        self._cold_dir.mkdir(parents=True, exist_ok=True)

    def _series_path(self, date_str: str) -> Path:
        return self._cold_dir / f"mtf_iv_series_{date_str}.jsonl"

    def append_snapshot(self, date_str: str, snapshot: dict[str, Any]) -> None:
        record = self._sanitize_snapshot(snapshot)
        if record is None:
            return
        try:
            with self._series_path(date_str).open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record))
                fh.write("\n")
        except Exception as exc:
            logger.error("[MTFIVWindowStorage] append failed date=%s error=%s", date_str, exc)
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
                        logger.warning("[MTFIVWindowStorage] skip invalid json line path=%s", path.name)
                        continue
                    if not isinstance(payload, dict):
                        continue
                    record = self._sanitize_snapshot(payload)
                    if record is not None:
                        rows.append(record)
        except Exception as exc:
            logger.error("[MTFIVWindowStorage] load failed date=%s error=%s", date_str, exc)
            raise

        return list(rows)

    @staticmethod
    def _sanitize_snapshot(data: dict[str, Any]) -> dict[str, Any] | None:
        ts = data.get("timestamp")
        timestamp = str(ts).strip() if ts is not None else ""
        if not timestamp:
            return None

        raw_windows = data.get("windows")
        if not isinstance(raw_windows, dict):
            return None

        windows: dict[str, list[float]] = {}
        has_data = False
        for tf in _TF_KEYS:
            source = raw_windows.get(tf, [])
            if not isinstance(source, list):
                source = []
            cleaned: list[float] = []
            for item in source:
                try:
                    num = float(item)
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(num) or num <= 0.0:
                    continue
                cleaned.append(num)
            maxlen = _TF_MAXLEN[tf]
            cleaned = cleaned[-maxlen:]
            windows[tf] = cleaned
            if cleaned:
                has_data = True

        if not has_data:
            return None

        return {
            "timestamp": timestamp,
            "windows": windows,
        }
