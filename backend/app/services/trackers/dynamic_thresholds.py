"""Dynamic Threshold Service for adaptive regime detection.

Provides dynamic thresholds for Vanna window sizing based on
current market volatility state (ATM IV and Net GEX).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.config import settings


@dataclass
class ThresholdState:
    """Current dynamic threshold state."""

    vanna_window_seconds: float = 300.0  # Default 5 minutes
    iv_regime: str = "NORMAL"
    gex_regime: str = "NEUTRAL"
    last_updated: datetime | None = None


class DynamicThresholdService:
    """Computes dynamic thresholds based on market regime.

    Adjusts Vanna correlation window based on:
    - ATM IV level (higher IV = shorter window for faster reaction)
    - GEX intensity (extreme GEX = longer window for stability)
    """

    def __init__(self) -> None:
        self._state = ThresholdState()

    def update(
        self,
        net_gex: float | None,
        spy_atm_iv: float | None,
        as_of: datetime | None = None,
    ) -> ThresholdState:
        """Update thresholds based on current market state.

        Args:
            net_gex: Net GEX value in Millions
            spy_atm_iv: SPY ATM IV percentage
            as_of: Current timestamp

        Returns:
            Updated ThresholdState
        """
        window = 300.0  # Default 5 min

        # Adjust window based on IV regime
        if spy_atm_iv is not None:
            if spy_atm_iv > settings.iv_elevated_max:
                # High IV = shorter window (react faster to regime shifts)
                window = 180.0  # 3 min
                self._state.iv_regime = "HIGH"
            elif spy_atm_iv > settings.iv_normal_max:
                window = 240.0  # 4 min
                self._state.iv_regime = "ELEVATED"
            elif spy_atm_iv < settings.iv_low_max:
                # Low IV = longer window (stable, less noise)
                window = 420.0  # 7 min
                self._state.iv_regime = "LOW"
            else:
                self._state.iv_regime = "NORMAL"

        # Adjust window based on GEX intensity
        if net_gex is not None:
            abs_gex = abs(net_gex)
            if abs_gex >= settings.gex_super_pin_threshold:
                # Extreme GEX = longer window (market is pinned, less noise)
                window = min(window * 1.3, 600.0)
                self._state.gex_regime = "SUPER_PIN"
            elif net_gex < 0:
                # Negative GEX = shorter window (acceleration, need speed)
                window = min(window * 0.8, window)
                self._state.gex_regime = "ACCELERATION"
            else:
                self._state.gex_regime = "DAMPING"

        self._state.vanna_window_seconds = window
        self._state.last_updated = as_of
        return self._state


# ============================================================================
# Singleton accessor
# ============================================================================
_instance: DynamicThresholdService | None = None


def get_dynamic_threshold_service() -> DynamicThresholdService:
    """Get or create the singleton DynamicThresholdService."""
    global _instance
    if _instance is None:
        _instance = DynamicThresholdService()
    return _instance
