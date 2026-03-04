"""Volume Imbalance Engine (VIB) — Phase 24.

Based on Muravyev, Pearson & Pollet (2022/2024) SSRN #4019647.
Core discovery: OTM Call-Put Volume Imbalance is a strong short-term return predictor.

Practice 3 — Volume Acceleration Ratio:
Tracks per-tick total volume against a 60-tick EMA baseline.
vol_accel_ratio = current_tick_vol / max(60tick_ema, 1)
Ratio ≥ 3.0 on negative GEX → Dealer Squeeze alert in AgentB1.
"""

from collections import deque
from datetime import datetime
from typing import Any, Optional
import logging
import rust_kernel

from shared.models.microstructure import VIBResult, VIBTimeframeResult

logger = logging.getLogger(__name__)

# Practice 3: EMA decay factor for 60-tick rolling volume average.
# alpha = 2 / (N+1) where N=60 → alpha ≈ 0.032.
_VOL_ACCEL_EMA_ALPHA: float = 2.0 / (60.0 + 1.0)


class VolumeImbalanceEngine:
    """Calculates intraday Call/Put volume imbalance for OTM options."""

    def __init__(self, thresholds: dict[str, float] | None = None):
        # Academic threshold: 0.1 (10% imbalance) is often significant
        self.threshold = (thresholds or {}).get("vib_threshold", 0.1)

        # History for timeframes (rolling windows of ticks or seconds)
        self.history: deque[dict[str, Any]] = deque(maxlen=2000)  # Increased for 15M covering

        # Practice 3: 60-tick EMA of per-tick total volume for Vol Accel Ratio.
        # Initialized to None; defaults to current tick volume on first update.
        self._vol_ema_60tick: float = 0.0
        self._prev_total_vol: Optional[int] = None

    def update(
        self, 
        chain: list[dict[str, Any]], 
        spot: float,
        otm_call_vol: int = 0,
        otm_put_vol: int = 0,
        current_cumulative_total_chain_vol: int = 0,
    ) -> VIBResult:
        """Update with new chain data and return imbalance analysis.
        
        Now heavily optimized: OTM volumes are pre-calculated via NumPy/GPU 
        in OptionChainBuilder and passed down directly.
        """
        # (The loop over `chain` is removed because caller pre-calculates this via NumPy)

        now = datetime.now()
        data_point = {
            "timestamp": now,
            "call_vol": otm_call_vol,
            "put_vol": otm_put_vol,
            "total_vol": otm_call_vol + otm_put_vol,
        }
        self.history.append(data_point)

        # 2. Calculate for 1M, 5M, 15M (based on history)
        result = VIBResult()

        result.tf_1m = self._calculate_tf(60)    # 60s
        result.tf_5m = self._calculate_tf(300)   # 300s
        result.tf_15m = self._calculate_tf(900)  # 900s

        # 3. Aggregation
        directions = [result.tf_1m.direction, result.tf_5m.direction, result.tf_15m.direction]
        bull_count = directions.count("BULLISH")
        bear_count = directions.count("BEARISH")

        if bull_count >= 2:
            result.consensus = "BULLISH"
            result.strength = (result.tf_1m.confidence + result.tf_5m.confidence + result.tf_15m.confidence) / 3
        elif bear_count >= 2:
            result.consensus = "BEARISH"
            result.strength = (result.tf_1m.confidence + result.tf_5m.confidence + result.tf_15m.confidence) / 3
        else:
            result.consensus = "NEUTRAL"
            result.strength = 0.0

        # ── Practice 3: Volume Acceleration Ratio ─────────────────────────────
        # Practice 3: Volume Acceleration Ratio (based on delta volume)
        # 1. Total volume across the chain (cumulative daily)
        # This is already calculated as current_cumulative_total_chain_vol
        
        # 2. Derive tick volume (delta)
        if self._prev_total_vol is None:
            # First tick: assume zero activity before and use current as delta
            tick_volume = float(current_cumulative_total_chain_vol)
        else:
            tick_volume = float(max(0, current_cumulative_total_chain_vol - self._prev_total_vol))
        
        self._prev_total_vol = current_cumulative_total_chain_vol

        # ── Migration: Calculation moved to Rust (rust_kernel) ──────────────────
        # Call Rust kernel for EMA and Ratio
        new_ema, vol_accel_ratio = rust_kernel.compute_vol_accel(
            tick_volume=tick_volume,
            current_ema=self._vol_ema_60tick,
            alpha=_VOL_ACCEL_EMA_ALPHA
        )
        
        self._vol_ema_60tick = new_ema
        result.vol_accel_ratio = vol_accel_ratio
        
        # Defensive Log: Track high Vol Accel Ratio
        if vol_accel_ratio >= 2.0:
            logger.debug(f"[L1 Rust Engine] High Vol Accel Ratio detected: {vol_accel_ratio:.2f} (Tick Vol: {tick_volume:.1f}, Prev EMA: {self._vol_ema_60tick:.1f})")

        return result

    def _calculate_tf(self, seconds: int) -> VIBTimeframeResult:
        if not self.history:
            return VIBTimeframeResult()

        now = self.history[-1]["timestamp"]
        start_data = None
        for p in reversed(self.history):
            if (now - p["timestamp"]).total_seconds() >= seconds:
                start_data = p
                break
        
        # If we don't have enough history, use the earliest point
        if not start_data:
            start_data = self.history[0]

        end_data = self.history[-1]
        
        # Calculate Delta (Current Cumulative - Start Cumulative)
        d_call = max(0, end_data["call_vol"] - start_data["call_vol"])
        d_put = max(0, end_data["put_vol"] - start_data["put_vol"])
        total = d_call + d_put

        if total == 0:
            return VIBTimeframeResult()

        ratio = (d_call - d_put) / total
        
        direction = "NEUTRAL"
        if ratio > self.threshold:
            direction = "BULLISH"
        elif ratio < -self.threshold:
            direction = "BEARISH"

        return VIBTimeframeResult(
            ratio=ratio,
            direction=direction,
            confidence=min(abs(ratio) / (self.threshold * 3), 1.0), # Normalized
            call_vol=d_call,
            put_vol=d_put
        )
