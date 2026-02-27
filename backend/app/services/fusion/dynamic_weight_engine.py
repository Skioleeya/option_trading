"""Dynamic Weight Engine — Phase 4 Decision Fusion.

Calculates weighted directional signals from multiple microstructure
components (IV velocity, wall dynamics, vanna flow, MTF consensus).

Adjusts weights dynamically based on IV regime and GEX intensity.
"""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.models.microstructure import (
    FusedSignalResult,
    GexIntensity,
    IVRegime,
)
from app.services.analysis.time_decay_factor import TimeDecayFactor


class DynamicWeightEngine:
    """Fuses multiple microstructure signals into a single directional signal.

    Base weights (from config):
    - IV Velocity:  25%
    - Wall Dynamics: 30%
    - Vanna Flow:   20%
    - MTF Consensus: 25%

    These are dynamically adjusted based on:
    - IV Regime (LOW/NORMAL/ELEVATED/HIGH/EXTREME)
    - GEX Intensity (strength of gamma field)
    """

    def __init__(self) -> None:
        self._iv_regime = IVRegime.NORMAL
        self._gex_intensity = GexIntensity.NEUTRAL
        self._time_decay = TimeDecayFactor()

    def update_market_state(
        self,
        spy_atm_iv: float | None,
        net_gex: float | None,
    ) -> None:
        """Update internal market state for weight adjustment."""
        # Classify IV regime
        if spy_atm_iv is not None:
            if spy_atm_iv < settings.iv_low_max:
                self._iv_regime = IVRegime.LOW
            elif spy_atm_iv < settings.iv_normal_max:
                self._iv_regime = IVRegime.NORMAL
            elif spy_atm_iv < settings.iv_elevated_max:
                self._iv_regime = IVRegime.ELEVATED
            elif spy_atm_iv < settings.iv_high_max:
                self._iv_regime = IVRegime.HIGH
            else:
                self._iv_regime = IVRegime.EXTREME

        # Classify GEX intensity
        if net_gex is not None:
            abs_gex = abs(net_gex)
            if net_gex >= settings.gex_super_pin_threshold:
                self._gex_intensity = GexIntensity.EXTREME_POSITIVE
            elif net_gex >= settings.gex_strong_positive:
                self._gex_intensity = GexIntensity.STRONG_POSITIVE
            elif net_gex <= settings.gex_strong_negative:
                self._gex_intensity = GexIntensity.EXTREME_NEGATIVE
            elif net_gex < 0:
                self._gex_intensity = GexIntensity.STRONG_NEGATIVE
            elif abs_gex >= settings.gex_moderate_threshold:
                self._gex_intensity = GexIntensity.MODERATE
            else:
                self._gex_intensity = GexIntensity.NEUTRAL

    def calculate_weights(
        self,
        iv_signal: dict[str, Any],
        wall_signal: dict[str, Any],
        vanna_signal: dict[str, Any],
        mtf_signal: dict[str, Any],
        vib_signal: dict[str, Any],
    ) -> FusedSignalResult:
        """Calculate fused directional signal.

        Args:
            iv_signal: {"direction": str, "confidence": float}
            wall_signal: {"direction": str, "confidence": float}
            vanna_signal: {"direction": str, "confidence": float}
            mtf_signal: {"direction": str, "confidence": float}

        Returns:
            FusedSignalResult with direction, confidence, weights, etc.
        """
        # Base weights from config
        w_iv = settings.agent_g_iv_weight
        w_wall = settings.agent_g_wall_weight
        w_vanna = settings.agent_g_vanna_weight
        w_mtf = settings.agent_g_mtf_weight
        w_vib = 0.20 # Phase 24 — C/P Volume Imbalance (Paper 3)

        # Dynamic weight adjustments based on regime
        if self._iv_regime in (IVRegime.HIGH, IVRegime.EXTREME):
            # In high IV, IV velocity and vanna become more important
            w_iv *= 1.3
            w_vanna *= 1.3
            w_wall *= 0.7
        elif self._iv_regime == IVRegime.LOW:
            # In low IV, walls are dominant (gamma pinning)
            w_wall *= 1.4
            w_iv *= 0.7

        if self._gex_intensity in (GexIntensity.EXTREME_POSITIVE, GexIntensity.STRONG_POSITIVE):
            # Strong positive GEX = walls matter more
            w_wall *= 1.2
        elif self._gex_intensity in (GexIntensity.EXTREME_NEGATIVE, GexIntensity.STRONG_NEGATIVE):
            # Negative GEX = vanna matters more (crash risk)
            w_vanna *= 1.3
            w_wall *= 0.8

        # Dynamic weight adjustments based on Time Decay (Phase 25C)
        # 0DTE Gamma/Vanna risk explodes near close (Paper 1 & 5)
        decay = self._time_decay.get_decay_factor()
        if decay > 0:
            # Shift weight towards high-leverage microstructure (Vanna/VIB)
            w_vanna *= (1.0 + decay * 0.5)  # +50% weight at close
            w_vib *= (1.0 + decay * 0.4)    # +40% weight at close
            w_wall *= (1.0 - decay * 0.3)   # -30% weight at close (pinning risk dissipates)
            w_iv *= (1.0 - decay * 0.2)     # -20% weight at close (historical relevance drops)

        # Normalize weights
        total_w = w_iv + w_wall + w_vanna + w_mtf + w_vib
        if total_w > 0:
            w_iv /= total_w
            w_wall /= total_w
            w_vanna /= total_w
            w_mtf /= total_w
            w_vib /= total_w

        # Calculate directional score
        # +1 = BULLISH, -1 = BEARISH, 0 = NEUTRAL
        direction_map = {"BULLISH": 1.0, "BEARISH": -1.0, "NEUTRAL": 0.0}

        components = {
            "iv": {"direction": iv_signal["direction"], "confidence": iv_signal["confidence"], "weight": w_iv},
            "wall": {"direction": wall_signal["direction"], "confidence": wall_signal["confidence"], "weight": w_wall},
            "vanna": {"direction": vanna_signal["direction"], "confidence": vanna_signal["confidence"], "weight": w_vanna},
            "mtf": {"direction": mtf_signal["direction"], "confidence": mtf_signal["confidence"], "weight": w_mtf},
            "vib": {"direction": vib_signal["direction"], "confidence": vib_signal["confidence"], "weight": w_vib},
        }

        weighted_score = 0.0
        weighted_confidence = 0.0

        for key, comp in components.items():
            d = direction_map.get(comp["direction"], 0.0)
            c = comp["confidence"]
            w = comp["weight"]
            weighted_score += d * c * w
            weighted_confidence += c * w

        # Determine fused direction
        if weighted_score > 0.15:
            direction = "BULLISH"
        elif weighted_score < -0.15:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        # Determine regime label
        regime = f"{self._gex_intensity.value}_{self._iv_regime.value}"

        # Build explanation
        top_driver = max(components.items(), key=lambda x: x[1]["weight"] * x[1]["confidence"])
        
        pre_close_tag = "[PRE-CLOSE] " if self._time_decay.is_pre_close(decay) else ""
        
        explanation = (
            f"{pre_close_tag}Fused: {direction} (score={weighted_score:.2f}). "
            f"Regime: {regime}. "
            f"Primary: {top_driver[0]} ({top_driver[1]['direction']}, "
            f"conf={top_driver[1]['confidence']:.0%}, w={top_driver[1]['weight']:.0%})"
        )

        return FusedSignalResult(
            direction=direction,
            confidence=abs(weighted_confidence),
            weights={"iv": w_iv, "wall": w_wall, "vanna": w_vanna, "mtf": w_mtf, "vib": w_vib},
            regime=regime,
            iv_regime=self._iv_regime,
            gex_intensity=self._gex_intensity,
            explanation=explanation,
            components=components,
        )
