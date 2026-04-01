"""Vanna Flow Analyzer — thin orchestrator for Spot-Vol correlation and GEX analysis.

Delegates to focused sub-modules:
    - vanna.pearson_engine       → rolling Pearson correlation + flip detection
    - vanna.acceleration_engine  → IV ROC / acceleration state
    - vanna.gex_classifier       → GEX regime + Vanna state + confidence
    - vanna.persistence          → Redis save/load

Public API (unchanged):
    update(), get_confidence(), reset(), data_points, set_redis_client()

Layer:  L1
Deps:   l1_compute/trackers/vanna/*, l1_compute/trackers/dynamic_thresholds
"""

from __future__ import annotations

import time
from collections import deque
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import logging

from shared_rust.models import VannaFlowResult, VannaFlowState

from l1_compute.trackers.dynamic_thresholds import get_dynamic_threshold_service
from l1_compute.trackers.vanna.pearson_engine import PearsonEngine, SpotIVPoint
from l1_compute.trackers.vanna.acceleration_engine import IVAccelerationEngine
from l1_compute.trackers.vanna.gex_classifier import (
    VannaStateClassifier,
    classify_gex_regime,
    calculate_confidence,
)
from l1_compute.trackers.vanna.persistence import VannaStatePersistence

logger = logging.getLogger(__name__)

_ET = ZoneInfo("US/Eastern")

_HISTORY_MAXLEN     = 500
_CORR_HISTORY_LEN   = 120
_ROLLING_WINDOW     = 120


class VannaFlowAnalyzer:
    """Orchestrates Spot-Vol correlation analysis and GEX regime classification.

    Composes four single-responsibility sub-modules for high cohesion.
    This class is the sole public interface — all upstream callers (reactor.py)
    depend only on this class.
    """

    def __init__(self, window_seconds: float = 300.0) -> None:
        self._base_window_seconds = window_seconds
        self._window_seconds      = window_seconds

        # History deque — shared reference into PearsonEngine
        self._history: deque[SpotIVPoint] = deque(maxlen=_HISTORY_MAXLEN)

        # Sub-modules
        self._pearson     = PearsonEngine(self._history, _ROLLING_WINDOW, _CORR_HISTORY_LEN)
        self._accel       = IVAccelerationEngine()
        self._classifier  = VannaStateClassifier()
        self._persistence = VannaStatePersistence(rolling_window_size=_ROLLING_WINDOW)

        self._dynamic_thresholds = get_dynamic_threshold_service()
        self._last_result: VannaFlowResult | None = None

        # IV gap bridging
        self._last_valid_iv: float | None = None

    # ── Setup ─────────────────────────────────────────────────────────────────

    async def set_redis_client(self, client: Any) -> None:
        """Inject shared Redis client and restore persisted state."""
        await self._persistence.set_redis_client(client)
        history, corr_history, last_iv, last_iv_time = await self._persistence.load(
            history_maxlen=_HISTORY_MAXLEN, corr_maxlen=_CORR_HISTORY_LEN
        )
        self._history.clear()
        self._history.extend(history)
        self._pearson.corr_history = corr_history
        self._accel.last_iv        = last_iv
        self._accel.last_iv_time   = last_iv_time

    # ── Primary update ────────────────────────────────────────────────────────

    def update(
        self,
        *,
        spot: float | None,
        atm_iv: float | None,
        net_gex: float | None,
        spy_atm_iv: float | None = None,
        as_of: datetime | None = None,
        sim_clock_mono: float | None = None,
    ) -> VannaFlowResult:
        """Ingest one market tick; return the current VannaFlowResult."""
        now_mono = sim_clock_mono if sim_clock_mono is not None else time.monotonic()
        if as_of is None:
            as_of = datetime.now(_ET)

        # Dynamic threshold update → adaptive window
        threshold_state  = self._dynamic_thresholds.update(net_gex, spy_atm_iv, as_of)
        self._window_seconds = threshold_state.vanna_window_seconds

        # GEX regime (always available)
        gex_regime = classify_gex_regime(net_gex, threshold_state)

        # IV gap bridging
        if atm_iv and atm_iv > 0:
            self._last_valid_iv = atm_iv
        elif self._last_valid_iv is not None:
            atm_iv = self._last_valid_iv

        if spot is None or atm_iv is None or atm_iv <= 0:
            return VannaFlowResult(
                state=VannaFlowState.UNAVAILABLE,
                gex_regime=gex_regime,
                net_gex=net_gex,
            )

        # History + windowing
        self._history.append(SpotIVPoint(now_mono, spot, atm_iv))
        cutoff = now_mono - self._window_seconds
        while self._history and self._history[0].timestamp_mono < cutoff:
            self._history.popleft()

        history_count = len(self._history)
        if history_count < 2:
            return VannaFlowResult(
                state=VannaFlowState.UNAVAILABLE,
                gex_regime=gex_regime,
                net_gex=net_gex,
                correlation=None,
                history_count=history_count,
            )

        # Correlation
        correlation = self._pearson.calculate()
        self._pearson.push_correlation(now_mono, correlation)

        # State classification
        is_flip = self._pearson.detect_flip(now_mono, correlation)
        state   = self._classifier.classify(correlation, is_flip)

        # IV acceleration
        iv_roc, iv_roc_prev, iv_accel, accel_state = self._accel.update(atm_iv, now_mono)

        result = VannaFlowResult(
            state=state,
            correlation=correlation,
            gex_regime=gex_regime,
            net_gex=net_gex,
            vanna_acceleration_state=accel_state,
            iv_roc=iv_roc,
            iv_roc_prev=iv_roc_prev,
            iv_acceleration=iv_accel,
            history_count=len(self._history),
            wall_displacement_multiplier=threshold_state.wall_displacement_multiplier,
            momentum_slope_multiplier=threshold_state.momentum_slope_multiplier,
        )
        self._last_result = result

        # Persist state (fire-and-forget, thread-safe)
        self._persistence.schedule_save(
            self._history,
            self._pearson.corr_history,
            self._accel.last_iv,
            self._accel.last_iv_time,
        )

        return result

    # ── Accessors ─────────────────────────────────────────────────────────────

    def get_confidence(self) -> float:
        """Signal confidence in [0.0, 1.0]."""
        return calculate_confidence(self._last_result, len(self._history))

    @property
    def data_points(self) -> int:
        """Number of history points in current window."""
        return len(self._history)

    def reset(self) -> None:
        """Reset all state (call on day change)."""
        self._history.clear()
        self._last_result = None
        self._last_valid_iv = None
        self._classifier.reset()
        self._accel.reset()
