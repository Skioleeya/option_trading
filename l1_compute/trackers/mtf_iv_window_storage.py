"""Cold-file persistence for MTF geometric-state snapshots."""

from __future__ import annotations

import json
import logging
import math
from collections import deque
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TF_KEYS = ("1m", "5m", "15m")
_LEGACY_WINDOW_MAXLEN = {"1m": 20, "5m": 12, "15m": 8}
_HISTORY_MAXLEN = 64


class MTFIVWindowStorage:
    """Append/read MTF snapshots as per-day JSONL files."""

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

        raw_state = data.get("state")
        if isinstance(raw_state, dict):
            state = MTFIVWindowStorage._sanitize_state(raw_state)
            if state is None:
                return None
            return {"timestamp": timestamp, "state": state}

        # Backward compatibility for old window-only records.
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
            cleaned = cleaned[-_LEGACY_WINDOW_MAXLEN[tf]:]
            windows[tf] = cleaned
            has_data = has_data or bool(cleaned)
        if not has_data:
            return None
        return {"timestamp": timestamp, "windows": windows}

    @staticmethod
    def _sanitize_state(state: dict[str, Any]) -> dict[str, Any] | None:
        raw_history = state.get("history")
        raw_frames = state.get("frames")
        raw_last_iv = state.get("last_iv")
        if not isinstance(raw_history, dict) or not isinstance(raw_frames, dict):
            return None

        history: dict[str, list[float]] = {}
        has_history = False
        for tf in _TF_KEYS:
            source = raw_history.get(tf, [])
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
            cleaned = cleaned[-_HISTORY_MAXLEN:]
            history[tf] = cleaned
            has_history = has_history or bool(cleaned)

        frames: dict[str, dict[str, Any]] = {}
        for tf in _TF_KEYS:
            raw = raw_frames.get(tf, {})
            if not isinstance(raw, dict):
                raw = {}
            frames[tf] = {
                "start_iv": MTFIVWindowStorage._coerce_positive(raw.get("start_iv"), 0.0),
                "end_iv": MTFIVWindowStorage._coerce_positive(raw.get("end_iv"), 0.0),
                "dt_seconds": MTFIVWindowStorage._coerce_positive(raw.get("dt_seconds"), 1.0),
                "support": MTFIVWindowStorage._coerce_positive(raw.get("support"), 0.0),
                "resistance": MTFIVWindowStorage._coerce_positive(raw.get("resistance"), 0.0),
                "state": MTFIVWindowStorage._coerce_state(raw.get("state")),
                "pending_state": MTFIVWindowStorage._coerce_state(raw.get("pending_state")),
                "entry_count": MTFIVWindowStorage._coerce_int(raw.get("entry_count")),
                "exit_count": MTFIVWindowStorage._coerce_int(raw.get("exit_count")),
                "relative_displacement": MTFIVWindowStorage._coerce_float(raw.get("relative_displacement"), 0.0),
                "pressure_gradient": MTFIVWindowStorage._coerce_float(raw.get("pressure_gradient"), 0.0),
                "distance_to_vacuum": MTFIVWindowStorage._coerce_positive(raw.get("distance_to_vacuum"), 0.0),
                "kinetic_level": MTFIVWindowStorage._coerce_unit(raw.get("kinetic_level")),
                "is_ready": bool(raw.get("is_ready", False)),
            }

        if not has_history:
            return None

        last_iv: dict[str, float] = {}
        if isinstance(raw_last_iv, dict):
            for tf in _TF_KEYS:
                last_iv[tf] = MTFIVWindowStorage._coerce_positive(raw_last_iv.get(tf), 0.0)
        else:
            for tf in _TF_KEYS:
                last_iv[tf] = history[tf][-1] if history[tf] else 0.0

        return {"frames": frames, "history": history, "last_iv": last_iv}

    @staticmethod
    def _coerce_float(value: Any, default: float = 0.0) -> float:
        try:
            out = float(value)
        except (TypeError, ValueError):
            return default
        if not math.isfinite(out):
            return default
        return out

    @staticmethod
    def _coerce_positive(value: Any, default: float = 0.0) -> float:
        out = MTFIVWindowStorage._coerce_float(value, default)
        return out if out >= 0.0 else default

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            out = int(value)
        except (TypeError, ValueError):
            return default
        return out if out >= 0 else default

    @staticmethod
    def _coerce_state(value: Any) -> int:
        try:
            out = int(value)
        except (TypeError, ValueError):
            return 0
        if out > 0:
            return 1
        if out < 0:
            return -1
        return 0

    @staticmethod
    def _coerce_unit(value: Any) -> float:
        out = MTFIVWindowStorage._coerce_float(value, 0.0)
        if out < 0.0:
            return 0.0
        if out > 1.0:
            return 1.0
        return out
