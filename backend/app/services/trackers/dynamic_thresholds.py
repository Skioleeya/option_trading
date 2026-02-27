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
    
    # MM Pulse Adaptive Scaling
    wall_displacement_multiplier: float = 1.0
    momentum_slope_multiplier: float = 1.0
    
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
        # Thresholds derived from post-2020 Markov Regime-Switching (MS) models
        # and rolling percentile literature:
        # Regime 1 (Low): < 18
        # Regime 2 (Medium): 18 to 23
        # Regime 3 (High): 23 to 30
        # Panic State: > 30
        iv_mult = 1.0
        if spy_atm_iv is not None:
            # Baseline IV for scaling based on MS regime mid-point
            iv_ref = 18.0
            
            vix_regime_low = 18.0
            vix_regime_med = 23.0
            vix_regime_panic = 30.0
            
            # Base multiplier relative to structural normal
            iv_mult = max(0.5, spy_atm_iv / iv_ref)
            
            if spy_atm_iv >= vix_regime_panic:
                window = 120.0  # 2 min (Fast) - Panic state
                self._state.iv_regime = "PANIC"
                iv_mult *= 1.5  # Increase displacement filter drastically in panic
            elif spy_atm_iv >= vix_regime_med:
                window = 180.0  # 3 min - High Volatility
                self._state.iv_regime = "HIGH"
            elif spy_atm_iv >= vix_regime_low:
                window = 300.0  # 5 min - Medium Volatility
                self._state.iv_regime = "ELEVATED"
            else:
                window = 480.0  # 8 min - Low Volatility
                self._state.iv_regime = "LOW"

        # Adjust multipliers based on GEX intensity (Market Tension)
        # Academic basis:
        # 1. Ni et al. (RFS 2021) & Baltussen et al. (JFE 2021) "Hedging demand and market intraday momentum":
        #    Option dealers' hedging of negative gamma (ACCELERATION) forces trading in direction of price,
        #    creating fragility and intraday momentum. Wall breaks require much LESS displacement to be real.
        # 2. Barbon & Buraschi (2020) "Gamma Fragility":
        #    Positive gamma (SUPER PIN) leads to liquidity provisioning, fading momentum. Wall breaks need MASSIVE flow.
        # 3. Spina (RFS 2023) on "Dealer Vanna":
        #    Dealers are structurally long Vanna. A highly pinned (positive) market masks true momentum, so we raise slope requirements.
        wall_mult = iv_mult
        mom_mult = iv_mult ** 0.5  # Sub-linear baseline for VWAP slope

        if net_gex is not None:
            abs_gex = abs(net_gex)
            if abs_gex >= settings.gex_super_pin_threshold:
                # SUPER_PIN: Market is deep in liquidity. Absorb flow.
                window = max(window, 600.0)
                self._state.gex_regime = "SUPER_PIN"
                wall_mult = iv_mult * 2.0  # Massive volume needed to displace a pinned wall
                mom_mult = iv_mult * 1.5   # High slope threshold to filter out the tight range chop
            elif net_gex < 0:
                # ACCELERATION: Negative GEX. Dealer hedging amplifies momentum (Gamma Squeeze).
                window = min(window, 120.0)
                self._state.gex_regime = "ACCELERATION"
                wall_mult = iv_mult * 0.4  # Extremely fragile walls; slight displacement = real break
                mom_mult = iv_mult * 0.5   # Less slope needed; mechanical delta hedging guarantees following
            else:
                self._state.gex_regime = "DAMPING"

        self._state.vanna_window_seconds = window
        self._state.wall_displacement_multiplier = wall_mult
        self._state.momentum_slope_multiplier = mom_mult
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
