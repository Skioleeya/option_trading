"""Vanna Flow Analyzer for Agent B1 v2.0.

Computes Spot-Vol correlation and GEX regime classification.

Key features:
1. Dynamic window rolling Pearson correlation between Spot and ATM IV
2. GEX regime state machine (DAMPING / ACCELERATION / NEUTRAL)
3. Adaptive window sizing based on volatility regime (v2.1)
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

try:
    import ndm_rust
    _NDM_RUST_AVAILABLE = True
except ImportError:
    _NDM_RUST_AVAILABLE = False
    import logging
    logging.getLogger(__name__).warning("ndm_rust not installed, falling back to pure Python")

from app.config import settings
from app.models.microstructure import (
    GexRegime,
    VannaAccelerationState,
    VannaFlowResult,
    VannaFlowState,
)
from app.services.trackers.dynamic_thresholds import get_dynamic_threshold_service


# =============================================================================
# Internal Data Structures
# =============================================================================
class SpotIVPoint(NamedTuple):
    """Single observation for correlation calculation."""

    timestamp_mono: float
    spot: float
    iv: float  # ATM IV (typically call IV or average)


@dataclass
class WelfordState:
    """Online statistics accumulator using Welford's algorithm."""

    n: int = 0
    mean_x: float = 0.0
    mean_y: float = 0.0
    m2_x: float = 0.0
    m2_y: float = 0.0
    c: float = 0.0  # Co-moment for covariance


# =============================================================================
# Vanna Flow Analyzer
# =============================================================================
class VannaFlowAnalyzer:
    """Analyzes Spot-Vol correlation and GEX regime.

    Uses Welford's online algorithm for efficient rolling correlation.
    Enhanced with dynamic window sizing (v2.1).

    Includes Vanna Acceleration to detect IV rate-of-change acceleration,
    which signals "double whammy" effects: Dealer Short Gamma losses +
    Vanna-driven Delta changes during IV spikes.
    """

    # Vanna Acceleration thresholds (percentage points per 5 min)
    IV_ROC_ACCEL_THRESHOLD = 2.0  # Acceleration > 2 pp/5min² = significant
    IV_ROC_HIGH_THRESHOLD = 5.0     # IV ROC > 5 pp/5min = high fear
    IV_ROC_LOW_THRESHOLD = -5.0    # IV ROC < -5 pp/5min = vol crush
    ROLLING_WINDOW_SIZE = 120  # Rolling window size for correlation

    def __init__(self, window_seconds: float = 300.0):  # Default 5-minute window
        self._base_window_seconds = window_seconds
        self._window_seconds = window_seconds  # Actual window (can be dynamic)
        self._history: deque[SpotIVPoint] = deque(maxlen=500)
        self._last_result: VannaFlowResult | None = None
        self._dynamic_thresholds = get_dynamic_threshold_service()

        # IV ROC history for acceleration calculation
        self._iv_roc_history: deque[tuple[float, float]] = deque(maxlen=10)
        self._last_iv: float | None = None
        self._last_iv_time: float | None = None

        # Correlation history for "Vanna Flip" detection
        self._corr_history: deque[tuple[float, float]] = deque(maxlen=120)  # ~2 min at 1Hz

        # Bridge IV gaps
        self._last_valid_iv: float | None = None

        # Persistence (v2.1)
        self._redis = None

    async def set_redis_client(self, client: Any) -> None:
        """Inject shared Redis client."""
        self._redis = client
        await self._load_state()

    async def _save_state(self) -> None:
        """Save current state to Redis (Fire-and-forget)."""
        if not self._redis:
            return

        try:
            today = datetime.now(ZoneInfo("US/Eastern")).date().isoformat()
            key = f"vanna_analyzer:state:{today}"

            # Serialize
            data = self.to_dict()
            import json
            json_str = json.dumps(data)

            # Set with 24h TTL
            await self._redis.setex(key, 86400, json_str)
        except Exception:
            pass

    async def _load_state(self) -> None:
        """Load state from Redis on init."""
        if not self._redis:
            return

        try:
            today = datetime.now(ZoneInfo("US/Eastern")).date().isoformat()
            key = f"vanna_analyzer:state:{today}"

            json_str = await self._redis.get(key)
            if json_str:
                import json
                data = json.loads(json_str)
                self.from_dict(data)
        except Exception:
            pass

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
        """Update analyzer with new market data.

        Args:
            spot: Current spot price
            atm_iv: ATM implied volatility (for correlation calculation)
            net_gex: Net GEX value
            spy_atm_iv: SPY 0DTE ATM IV for dynamic thresholds
            as_of: Wall clock timestamp
            sim_clock_mono: Simulated monotonic time
        """
        now_mono = sim_clock_mono if sim_clock_mono is not None else time.monotonic()

        if as_of is None:
            as_of = datetime.now(ZoneInfo("US/Eastern"))

        # Update dynamic thresholds
        threshold_state = self._dynamic_thresholds.update(net_gex, spy_atm_iv, as_of)
        self._window_seconds = threshold_state.vanna_window_seconds

        # GEX regime
        gex_regime = self._classify_gex_regime(net_gex, threshold_state)

        # Fallback to last valid IV if current is zero/missing
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

        # Add to history
        self._history.append(SpotIVPoint(now_mono, spot, atm_iv))

        # Prune old
        cutoff = now_mono - self._window_seconds
        while self._history and self._history[0].timestamp_mono < cutoff:
            self._history.popleft()

        # Differentiate "Warming Up" from "Unavailable"
        history_count = len(self._history)
        if history_count < self.ROLLING_WINDOW_SIZE:
            return VannaFlowResult(
                state=VannaFlowState.UNAVAILABLE,
                gex_regime=gex_regime,
                net_gex=net_gex,
                correlation=None,
                history_count=history_count,
            )

        # Calculate correlation
        correlation = self._calculate_correlation()

        # Update correlation history for Flip detection
        if correlation is not None:
            self._corr_history.append((now_mono, correlation))

        # Detect VANNA_FLIP (Instantaneous slope shift)
        is_flip = self._detect_vanna_flip(now_mono, correlation)

        # Classify state
        state = self._classify_vanna_state(correlation, is_flip)

        # Vanna Acceleration
        iv_roc, iv_roc_prev, iv_accel, accel_state = self._calculate_vanna_acceleration(
            atm_iv, now_mono
        )

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

        # Persist state
        import asyncio
        asyncio.create_task(self._save_state())

        return result

    def _calculate_correlation(self) -> float | None:
        """Calculate Spot-Vol correlation (Vanna Flow)."""
        if len(self._history) < self.ROLLING_WINDOW_SIZE:
            return None

        # Extract recent history
        recent = list(self._history)[-self.ROLLING_WINDOW_SIZE:]
        spots = [d.spot for d in recent]
        ivs = [d.iv for d in recent]

        if len(spots) < 2 or len(ivs) < 2:
            return None

        if _NDM_RUST_AVAILABLE:
            try:
                # O(N) compiled Rust SIMD-friendly extension
                return ndm_rust.pearson_r(spots, ivs)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Rust math_engine error: {e}")

        # Fallback: Basic Pearson Correlation Implementation (Python)
        n = len(spots)
        sum_x = sum(spots)
        sum_y = sum(ivs)
        sum_x2 = sum(x * x for x in spots)
        sum_y2 = sum(y * y for y in ivs)
        sum_xy = sum(x * y for x, y in zip(spots, ivs))

        numerator = n * sum_xy - sum_x * sum_y
        denominator_x = n * sum_x2 - sum_x**2
        denominator_y = n * sum_y2 - sum_y**2

        if denominator_x <= 0 or denominator_y <= 0:
            return None

        return numerator / (math.sqrt(denominator_x) * math.sqrt(denominator_y))

    def _detect_vanna_flip(self, now_mono: float, current_corr: float | None) -> bool:
        """Detect rapid correlation shift (Vanna Flip).

        Logic: If correlation jumped > 0.6 within the last 2 minutes.
        Example: -0.9 -> -0.2 (Delta 0.7) = FLIP.
        """
        if current_corr is None or len(self._corr_history) < 10:
            return False

        if _NDM_RUST_AVAILABLE:
            try:
                # O(1) compiled Rust scanner
                return ndm_rust.detect_vanna_flip(now_mono, current_corr, list(self._corr_history))
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Rust detect_vanna_flip error: {e}")

        # Fallback: Python implementation
        # Find correlation from ~2 minutes ago
        two_min_ago = now_mono - 120
        past_corr = None
        for ts, corr in self._corr_history:
            if ts >= two_min_ago:
                past_corr = corr
                break

        if past_corr is None:
            return False

        delta = current_corr - past_corr
        return delta > 0.6

    def _classify_vanna_state(self, correlation: float | None, is_flip: bool = False) -> VannaFlowState:
        """Classify Vanna flow state with Flip detection."""
        if correlation is None:
            return VannaFlowState.NORMAL

        # Priority 1: Instantaneous Flip
        if is_flip:
            return VannaFlowState.VANNA_FLIP

        # Priority 2: Absolute Zones
        if correlation > settings.vanna_danger_zone_threshold:
            return VannaFlowState.DANGER_ZONE
        elif correlation < settings.vanna_grind_stable_threshold:
            return VannaFlowState.GRIND_STABLE
        else:
            return VannaFlowState.NORMAL

    def _calculate_vanna_acceleration(
        self,
        iv: float,
        now_mono: float,
    ) -> tuple[float | None, float | None, float | None, VannaAccelerationState]:
        """Calculate Vanna Acceleration (IV rate-of-change acceleration).

        IV ROC = d(IV)/dt (percentage points per unit time)
        IV Acceleration = d(IV ROC)/dt (how fast fear is accelerating)

        Returns:
            (iv_roc, iv_roc_prev, iv_acceleration, acceleration_state)
        """
        iv_roc = None
        iv_roc_prev = None
        iv_accel = None
        accel_state = VannaAccelerationState.UNAVAILABLE

        # Calculate current IV ROC
        if self._last_iv is not None and self._last_iv_time is not None:
            time_delta = now_mono - self._last_iv_time
            if time_delta > 0:
                iv_roc = (iv - self._last_iv) / time_delta * 60  # Convert to pp/min
                iv_roc = iv_roc * 5  # Scale to pp per 5-min for readability

                # Store in history
                self._iv_roc_history.append((now_mono, iv_roc))

                # Calculate acceleration (change in IV ROC)
                if len(self._iv_roc_history) >= 2:
                    for ts, roc in reversed(list(self._iv_roc_history)[:-1]):
                        iv_roc_prev = roc
                        time_diff = now_mono - ts
                        if time_diff > 30:  # At least 30 seconds between readings
                            iv_accel = (iv_roc - iv_roc_prev)
                            break

                # Classify acceleration state
                accel_state = self._classify_acceleration_state(iv_roc, iv_roc_prev, iv_accel)

        # Update for next iteration
        self._last_iv = iv
        self._last_iv_time = now_mono

        return iv_roc, iv_roc_prev, iv_accel, accel_state

    def _classify_acceleration_state(
        self,
        iv_roc: float | None,
        iv_roc_prev: float | None,
        iv_accel: float | None,
    ) -> VannaAccelerationState:
        """Classify Vanna Acceleration state."""
        if iv_roc is None:
            return VannaAccelerationState.UNAVAILABLE

        if iv_accel is None or iv_roc_prev is None:
            if iv_roc > self.IV_ROC_HIGH_THRESHOLD:
                return VannaAccelerationState.ACCELERATING_FEAR
            elif iv_roc < self.IV_ROC_LOW_THRESHOLD:
                return VannaAccelerationState.ACCELERATING_CALM
            return VannaAccelerationState.STABLE

        # Have both current and previous IV ROC
        if iv_roc > 0 and iv_roc_prev > 0:
            if iv_accel > self.IV_ROC_ACCEL_THRESHOLD:
                return VannaAccelerationState.ACCELERATING_FEAR
            elif iv_accel < -self.IV_ROC_ACCEL_THRESHOLD:
                return VannaAccelerationState.DECELERATING_FEAR
            return VannaAccelerationState.STABLE
        elif iv_roc < 0 and iv_roc_prev < 0:
            if iv_accel < -self.IV_ROC_ACCEL_THRESHOLD:
                return VannaAccelerationState.ACCELERATING_CALM
            elif iv_accel > self.IV_ROC_ACCEL_THRESHOLD:
                return VannaAccelerationState.DECELERATING_CALM
            return VannaAccelerationState.STABLE
        elif iv_roc > 0 and iv_roc_prev < 0:
            return VannaAccelerationState.REVERSING_UP
        elif iv_roc < 0 and iv_roc_prev > 0:
            return VannaAccelerationState.REVERSING_DOWN

        return VannaAccelerationState.STABLE

    def _classify_gex_regime(
        self,
        net_gex: float | None,
        threshold_state: Any | None = None
    ) -> GexRegime:
        """Classify GEX regime.

        Logic:
        - SUPER_PIN:   |GEX| >= 1000M (Frozen)
        - DAMPING:     200M <= |GEX| < 500M (positive only)
        - NEUTRAL:     |GEX| < 200M
        - ACCELERATION: net_gex < 0 (any negative)
        """
        if net_gex is None:
            return GexRegime.NEUTRAL

        # Any negative GEX -> ACCELERATION
        if net_gex < 0:
            return GexRegime.ACCELERATION

        # Positive GEX - use absolute value for thresholds
        abs_gex = abs(net_gex)

        neutral_threshold = settings.gex_neutral_threshold  # 200M
        super_pin_threshold = settings.gex_super_pin_threshold  # 1000M

        if abs_gex >= super_pin_threshold:
            return GexRegime.SUPER_PIN
        elif abs_gex >= neutral_threshold:
            return GexRegime.DAMPING
        else:
            return GexRegime.NEUTRAL

    def get_confidence(self) -> float:
        """Calculate vanna flow signal confidence.

        PP-3 FIX: When correlation sits near the DANGER_ZONE threshold, linearly
        interpolate confidence within a ±BOUNDARY_BAND window instead of hard-jumping
        0.4 → 0.9. This eliminates the confidence oscillation that occurred when
        correlation hovered just above/below vanna_danger_zone_threshold.
        """
        if self._last_result is None or self._last_result.state == VannaFlowState.UNAVAILABLE:
            return 0.0

        corr = abs(self._last_result.correlation or 0.0)
        sample_count = len(self._history)
        sample_factor = min(1.0, sample_count / 20)

        if self._last_result.state == VannaFlowState.DANGER_ZONE:
            # Smooth the 0.4→0.9 hard jump: linearly interpolate ±BOUNDARY_BAND around threshold
            BOUNDARY_BAND = 0.05
            danger_th = settings.vanna_danger_zone_threshold
            raw_corr = self._last_result.correlation or 0.0
            low = danger_th - BOUNDARY_BAND
            high = danger_th + BOUNDARY_BAND
            boundary_progress = (raw_corr - low) / (high - low)
            boundary_progress = max(0.0, min(1.0, boundary_progress))
            state_confidence = 0.4 + boundary_progress * 0.5  # 0.4 → 0.9 linear
        elif self._last_result.state == VannaFlowState.GRIND_STABLE:
            state_confidence = 0.7
        else:
            state_confidence = 0.4

        corr_factor = min(1.0, corr)
        confidence = (state_confidence * 0.5 + corr_factor * 0.3 + sample_factor * 0.2)
        return min(1.0, confidence)


    def reset(self) -> None:
        """Reset analyzer state. Call on day change."""
        self._history.clear()
        self._last_result = None
        self._iv_roc_history.clear()
        self._last_iv = None
        self._last_iv_time = None

    @property
    def data_points(self) -> int:
        """Return number of data points in current window."""
        return len(self._history)

    # =========================================================================
    # Persistence (v2.1)
    # =========================================================================

    def to_dict(self) -> dict[str, Any]:
        """Serialize state for persistence."""
        now_mono = time.monotonic()
        now_et = datetime.now(ZoneInfo("US/Eastern"))

        history_data = []
        for p in self._history:
            age_seconds = now_mono - p.timestamp_mono
            p_et = now_et.timestamp() - age_seconds
            history_data.append({
                "ts_et": p_et,
                "spot": p.spot,
                "iv": p.iv
            })

        corr_data = []
        for ts, corr in self._corr_history:
            age_seconds = now_mono - ts
            ts_et = now_et.timestamp() - age_seconds
            corr_data.append({"ts_et": ts_et, "corr": corr})

        return {
            "history": history_data,
            "corr_history": corr_data,
            "last_updated": now_et.isoformat(),
            "last_iv": self._last_iv,
            "last_iv_time_age": (now_mono - self._last_iv_time) if self._last_iv_time else None
        }

    def from_dict(self, data: dict[str, Any]) -> None:
        """Restore state from persistence."""
        try:
            now_mono = time.monotonic()
            now_et = datetime.now(ZoneInfo("US/Eastern")).timestamp()

            # Restore _history
            restored_history = []
            if "history" in data:
                for p_data in data["history"]:
                    ts_et = p_data["ts_et"]
                    age = now_et - ts_et

                    if age > (self.ROLLING_WINDOW_SIZE * 2):
                        continue

                    p_mono = now_mono - age
                    restored_history.append(SpotIVPoint(p_mono, p_data["spot"], p_data["iv"]))

            restored_history.sort(key=lambda x: x.timestamp_mono)
            self._history = deque(restored_history, maxlen=500)

            # Restore _corr_history
            restored_corr = []
            if "corr_history" in data:
                for c_data in data["corr_history"]:
                    ts_et = c_data["ts_et"]
                    age = now_et - ts_et
                    if age > 300:
                        continue
                    p_mono = now_mono - age
                    restored_corr.append((p_mono, c_data["corr"]))

            restored_corr.sort(key=lambda x: x[0])
            self._corr_history = deque(restored_corr, maxlen=120)

            # Restore IV state
            self._last_iv = data.get("last_iv")
            if data.get("last_iv_time_age") is not None:
                self._last_iv_time = now_mono - float(data["last_iv_time_age"])

        except Exception:
            pass
