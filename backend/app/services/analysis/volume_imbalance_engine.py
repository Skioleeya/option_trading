"""Volume Imbalance Engine (VIB) — Phase 24.

Based on Muravyev, Pearson & Pollet (2022/2024) SSRN #4019647.
Core discovery: OTM Call-Put Volume Imbalance is a strong short-term return predictor.
"""

from collections import deque
from datetime import datetime
from typing import Any

from app.models.microstructure import VIBResult, VIBTimeframeResult


class VolumeImbalanceEngine:
    """Calculates intraday Call/Put volume imbalance for OTM options."""

    def __init__(self, thresholds: dict[str, float] | None = None):
        # Academic threshold: 0.1 (10% imbalance) is often significant
        self.threshold = (thresholds or {}).get("vib_threshold", 0.1)
        
        # History for timeframes (rolling windows of ticks or seconds)
        self.history: deque[dict[str, Any]] = deque(maxlen=2000) # Increased for 15M covering

    def update(self, chain: list[dict[str, Any]], spot: float) -> VIBResult:
        """Update with new chain data and return imbalance analysis."""
        
        # 1. Filter OTM and calculate current cumulative volume
        otm_call_vol = 0
        otm_put_vol = 0
        
        for contract in chain:
            strike = contract.get("strike", 0)
            vol = contract.get("volume", 0)
            option_type = contract.get("option_type") # "CALL" or "PUT"
            
            if option_type == "CALL" and strike > spot:
                otm_call_vol += vol
            elif option_type == "PUT" and strike < spot:
                otm_put_vol += vol

        now = datetime.now()
        data_point = {
            "timestamp": now,
            "call_vol": otm_call_vol,
            "put_vol": otm_put_vol,
            "total_vol": otm_call_vol + otm_put_vol
        }
        self.history.append(data_point)

        # 2. Calculate for 1M, 5M, 15M (based on history)
        result = VIBResult()
        
        result.tf_1m = self._calculate_tf(60)   # 60s
        result.tf_5m = self._calculate_tf(300)  # 300s
        result.tf_15m = self._calculate_tf(900) # 900s

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
