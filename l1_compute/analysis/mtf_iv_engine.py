"""MTF IV geometric engine.

This module exposes a stateful multi-timeframe engine that operates on
relative displacement vectors instead of distributional statistics.
Output schema is intentionally physics-like:
- state: -1 | 0 | 1
- relative_displacement
- pressure_gradient
- distance_to_vacuum
- kinetic_level
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_TF_KEYS = ("1m", "5m", "15m")
_HISTORY_MAXLEN = 64
_ENTRY_TICKS = 2
_EXIT_TICKS = 2

# Thresholds operate on relative displacement.
_THRESHOLDS = {
    "1m": {"entry": 0.0030, "exit": 0.0015},
    "5m": {"entry": 0.0045, "exit": 0.0020},
    "15m": {"entry": 0.0060, "exit": 0.0025},
}


@dataclass
class TFGeomFrame:
    start_iv: float = 0.0
    end_iv: float = 0.0
    dt_seconds: float = 1.0
    support: float = 0.0
    resistance: float = 0.0
    state: int = 0
    pending_state: int = 0
    entry_count: int = 0
    exit_count: int = 0
    relative_displacement: float = 0.0
    pressure_gradient: float = 0.0
    distance_to_vacuum: float = 0.0
    kinetic_level: float = 0.0
    is_ready: bool = False


class MTFIVEngine:
    """Multi-timeframe geometric IV state engine."""

    def __init__(self) -> None:
        self._frames: dict[str, TFGeomFrame] = {tf: TFGeomFrame() for tf in _TF_KEYS}
        self._history: dict[str, deque[float]] = {
            tf: deque(maxlen=_HISTORY_MAXLEN) for tf in _TF_KEYS
        }
        self._last_iv: dict[str, float] = {tf: 0.0 for tf in _TF_KEYS}

    def update(self, tf: str, atm_iv: float) -> None:
        """Legacy-compatible update using unit-time displacement."""
        if tf not in self._frames:
            return
        try:
            value = float(atm_iv)
        except (TypeError, ValueError):
            return
        if not math.isfinite(value) or value <= 0.0:
            return
        prev = self._last_iv.get(tf, 0.0)
        if prev <= 0.0:
            self._last_iv[tf] = value
            self._history[tf].append(value)
            return
        self.update_frame(tf, start_iv=prev, end_iv=value, dt_seconds=1.0)
        self._last_iv[tf] = value

    def update_frame(self, tf: str, *, start_iv: float, end_iv: float, dt_seconds: float) -> None:
        """Update a timeframe with a finalized geometric frame."""
        if tf not in self._frames:
            return
        try:
            start = float(start_iv)
            end = float(end_iv)
            dt = float(dt_seconds)
        except (TypeError, ValueError):
            return
        if not (math.isfinite(start) and math.isfinite(end) and math.isfinite(dt)):
            return
        if start <= 0.0 or end <= 0.0 or dt <= 0.0:
            return

        frame = self._frames[tf]
        frame.start_iv = start
        frame.end_iv = end
        frame.dt_seconds = dt
        frame.is_ready = True

        self._last_iv[tf] = end
        hist = self._history[tf]
        hist.append(end)
        frame.support = min(hist) if hist else end
        frame.resistance = max(hist) if hist else end

        frame.relative_displacement = (end - start) / max(start, 1e-6)
        frame.pressure_gradient = frame.relative_displacement / max(dt, 1e-6)
        frame.distance_to_vacuum = min(abs(end - frame.support), abs(frame.resistance - end))
        span = max(abs(frame.resistance - frame.support), 1e-6)
        frame.kinetic_level = max(0.0, min(1.0, abs(frame.relative_displacement) / span))

        self._apply_hysteresis(tf, frame)

    def export_state(self) -> dict[str, Any]:
        """Export engine state for cold persistence."""
        frames: dict[str, dict[str, Any]] = {}
        for tf, frame in self._frames.items():
            frames[tf] = {
                "start_iv": frame.start_iv,
                "end_iv": frame.end_iv,
                "dt_seconds": frame.dt_seconds,
                "support": frame.support,
                "resistance": frame.resistance,
                "state": frame.state,
                "pending_state": frame.pending_state,
                "entry_count": frame.entry_count,
                "exit_count": frame.exit_count,
                "relative_displacement": frame.relative_displacement,
                "pressure_gradient": frame.pressure_gradient,
                "distance_to_vacuum": frame.distance_to_vacuum,
                "kinetic_level": frame.kinetic_level,
                "is_ready": frame.is_ready,
            }
        return {
            "frames": frames,
            "history": {tf: list(hist) for tf, hist in self._history.items()},
            "last_iv": dict(self._last_iv),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        """Restore engine state from sanitized external snapshot."""
        self.reset()
        if not isinstance(state, dict):
            return

        # Compatibility path for legacy snapshot format: {"windows": {"1m": [...]}}
        legacy_windows = state.get("windows")
        if isinstance(legacy_windows, dict):
            for tf in _TF_KEYS:
                values = legacy_windows.get(tf, [])
                if not isinstance(values, list):
                    continue
                for raw in values:
                    self.update(tf, raw)
            return

        history_raw = state.get("history")
        if isinstance(history_raw, dict):
            for tf in _TF_KEYS:
                values = history_raw.get(tf, [])
                if not isinstance(values, list):
                    continue
                for raw in values:
                    try:
                        iv = float(raw)
                    except (TypeError, ValueError):
                        continue
                    if not math.isfinite(iv) or iv <= 0.0:
                        continue
                    self._history[tf].append(iv)
                if self._history[tf]:
                    self._last_iv[tf] = self._history[tf][-1]

        frames_raw = state.get("frames")
        if isinstance(frames_raw, dict):
            for tf in _TF_KEYS:
                raw_frame = frames_raw.get(tf, {})
                if not isinstance(raw_frame, dict):
                    continue
                frame = self._frames[tf]
                frame.start_iv = _as_pos(raw_frame.get("start_iv"), default=0.0)
                frame.end_iv = _as_pos(raw_frame.get("end_iv"), default=0.0)
                frame.dt_seconds = _as_pos(raw_frame.get("dt_seconds"), default=1.0)
                frame.support = _as_pos(raw_frame.get("support"), default=0.0)
                frame.resistance = _as_pos(raw_frame.get("resistance"), default=0.0)
                frame.state = _as_state(raw_frame.get("state"))
                frame.pending_state = _as_state(raw_frame.get("pending_state"))
                frame.entry_count = _as_int(raw_frame.get("entry_count"))
                frame.exit_count = _as_int(raw_frame.get("exit_count"))
                frame.relative_displacement = _as_float(raw_frame.get("relative_displacement"))
                frame.pressure_gradient = _as_float(raw_frame.get("pressure_gradient"))
                frame.distance_to_vacuum = _as_pos(raw_frame.get("distance_to_vacuum"), default=0.0)
                frame.kinetic_level = max(0.0, min(1.0, _as_float(raw_frame.get("kinetic_level"))))
                frame.is_ready = bool(raw_frame.get("is_ready", frame.end_iv > 0.0))
                if frame.end_iv > 0.0:
                    self._last_iv[tf] = frame.end_iv

    def reset(self) -> None:
        """Clear frame and history buffers."""
        for tf in _TF_KEYS:
            self._frames[tf] = TFGeomFrame()
            self._history[tf].clear()
            self._last_iv[tf] = 0.0

    def compute(self, current_iv_map: dict[str, float] | None = None) -> dict[str, Any]:
        """Return current geometric state for each timeframe.

        `current_iv_map` is accepted for backward signature compatibility but ignored.
        """
        out: dict[str, dict[str, Any]] = {}
        for tf, frame in self._frames.items():
            out[tf] = _pack_frame(frame)
        return {"timeframes": out}

    def _apply_hysteresis(self, tf: str, frame: TFGeomFrame) -> None:
        cfg = _THRESHOLDS[tf]
        entry_th = cfg["entry"]
        exit_th = cfg["exit"]
        disp = frame.relative_displacement

        target_state = 1 if disp >= entry_th else (-1 if disp <= -entry_th else 0)
        neutral_ready = abs(disp) <= exit_th

        if frame.state == 0:
            if target_state == 0:
                frame.pending_state = 0
                frame.entry_count = 0
                return
            if frame.pending_state != target_state:
                frame.pending_state = target_state
                frame.entry_count = 1
            else:
                frame.entry_count += 1
            if frame.entry_count >= _ENTRY_TICKS:
                frame.state = target_state
                frame.pending_state = 0
                frame.entry_count = 0
            return

        if neutral_ready:
            frame.exit_count += 1
            if frame.exit_count >= _EXIT_TICKS:
                frame.state = 0
                frame.pending_state = 0
                frame.exit_count = 0
            return

        frame.exit_count = 0
        if target_state != 0 and target_state != frame.state:
            if frame.pending_state != target_state:
                frame.pending_state = target_state
                frame.entry_count = 1
            else:
                frame.entry_count += 1
            if frame.entry_count >= _ENTRY_TICKS:
                frame.state = target_state
                frame.pending_state = 0
                frame.entry_count = 0
        else:
            frame.pending_state = 0
            frame.entry_count = 0


def _pack_frame(frame: TFGeomFrame) -> dict[str, Any]:
    return {
        "state": frame.state,
        "relative_displacement": round(frame.relative_displacement, 6),
        "pressure_gradient": round(frame.pressure_gradient, 6),
        "distance_to_vacuum": round(frame.distance_to_vacuum, 6),
        "kinetic_level": round(frame.kinetic_level, 6),
    }


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(out):
        return default
    return out


def _as_pos(value: Any, default: float = 0.0) -> float:
    out = _as_float(value, default)
    return out if out >= 0.0 else default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        out = int(value)
    except (TypeError, ValueError):
        return default
    return out if out >= 0 else default


def _as_state(value: Any) -> int:
    try:
        out = int(value)
    except (TypeError, ValueError):
        return 0
    if out > 0:
        return 1
    if out < 0:
        return -1
    return 0
