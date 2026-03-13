"""Microstructure analysis models for Agent B1 v2.0.

Contains enums for GEX regime classification, Vanna flow states,
IV velocity states, wall migration states, and their result containers.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from datetime import datetime

from pydantic import BaseModel, Field


# ============================================================================
# Volume Imbalance Classification (Phase 24)
# ============================================================================
class VIBTimeframeResult(BaseModel):
    """Result for a specific timeframe."""
    ratio: float = 0.0          # (CallVol - PutVol) / TotalVol
    direction: str = "NEUTRAL"  # BULLISH (ratio > threshold), BEARISH, NEUTRAL
    confidence: float = 0.0     # Normalized intensity [0, 1]
    call_vol: int = 0
    put_vol: int = 0


class VIBResult(BaseModel):
    """Aggregated VIB result across timeframes."""
    tf_1m: VIBTimeframeResult = Field(default_factory=VIBTimeframeResult)
    tf_5m: VIBTimeframeResult = Field(default_factory=VIBTimeframeResult)
    tf_15m: VIBTimeframeResult = Field(default_factory=VIBTimeframeResult)
    consensus: str = "NEUTRAL"
    strength: float = 0.0
    # Practice 3: Volume Acceleration Ratio (1s volume / 60s avg)
    vol_accel_ratio: float = 1.0


# ============================================================================
# Jump Detection Classification (Phase 27)
# ============================================================================
class JumpResult(BaseModel):
    """Result of jump detection analysis."""
    is_jump: bool = False
    z_score: float = 0.0
    magnitude_pct: float = 0.0
    direction: str = "NEUTRAL"
    timestamp: datetime | None = None


# ============================================================================
# GEX Regime Classification
# ============================================================================
class GexRegime(str, Enum):
    """GEX regime classification.

    Thresholds are expressed in Million USD (MMUSD) and sourced from config:
    - SUPER_PIN:   net_gex >= 100000M (100B+, strongest positive pinning proxy)
    - DAMPING:     20000M <= net_gex < 100000M (positive OI-based proxy damping)
    - NEUTRAL:     |net_gex| < 20000M
    - ACCELERATION: net_gex < 0 (negative OI-based proxy, trend-following risk)
    """

    SUPER_PIN = "SUPER_PIN"
    DAMPING = "DAMPING"
    NEUTRAL = "NEUTRAL"
    ACCELERATION = "ACCELERATION"


# ============================================================================
# Vanna Flow States
# ============================================================================
class VannaFlowState(str, Enum):
    """Vanna flow correlation state.

    Based on Spot-Vol Pearson correlation:
    - DANGER_ZONE:  correlation > 0.5 (crash risk, spot & vol moving together)
    - GRIND_STABLE: correlation < -0.8 (normal inverse relationship)
    - NORMAL:       between thresholds
    - VANNA_FLIP:   rapid correlation shift (> 0.6 delta in 2 min)
    - UNAVAILABLE:  insufficient data
    """

    DANGER_ZONE = "DANGER_ZONE"
    GRIND_STABLE = "GRIND_STABLE"
    NORMAL = "NORMAL"
    VANNA_FLIP = "VANNA_FLIP"
    UNAVAILABLE = "UNAVAILABLE"


class VannaAccelerationState(str, Enum):
    """Vanna acceleration state (IV rate-of-change acceleration).

    Classifies the second derivative of IV movement.
    """

    ACCELERATING_FEAR = "ACCELERATING_FEAR"      # IV rising AND acceleration positive
    DECELERATING_FEAR = "DECELERATING_FEAR"      # IV rising BUT acceleration negative
    REVERSING_UP = "REVERSING_UP"                # IV was falling, now rising
    REVERSING_DOWN = "REVERSING_DOWN"            # IV was rising, now falling
    ACCELERATING_CALM = "ACCELERATING_CALM"      # IV falling faster (vol crush)
    DECELERATING_CALM = "DECELERATING_CALM"      # IV falling but slowing
    STABLE = "STABLE"                            # No significant change
    UNAVAILABLE = "UNAVAILABLE"                  # Not enough data


# ============================================================================
# IV Velocity States
# ============================================================================
class IVVelocityState(str, Enum):
    """IV velocity classification.

    v3.0 FIX: Asian Style Color Alignment (红涨绿跌)
    - BULLISH states (🔴 Rose): PAID_MOVE, ORGANIC_GRIND, HOLLOW_RISE, HOLLOW_DROP, VOL_EXPANSION
    - BEARISH states (🟢 Emerald): PAID_DROP only
    - WARNING (🟡 Amber): EXHAUSTION
    """

    PAID_MOVE = "PAID_MOVE"           # Spot move + IV rise = real buying/selling
    ORGANIC_GRIND = "ORGANIC_GRIND"   # Spot move + IV stable = organic trend
    HOLLOW_RISE = "HOLLOW_RISE"       # Spot up + IV down = gamma-assisted grind
    HOLLOW_DROP = "HOLLOW_DROP"       # Spot down + IV down = fake breakdown
    PAID_DROP = "PAID_DROP"           # Spot down + IV up = panic selling
    VOL_EXPANSION = "VOL_EXPANSION"   # IV spike without spot move
    EXHAUSTION = "EXHAUSTION"         # Large spot move + IV collapse
    UNAVAILABLE = "UNAVAILABLE"       # Not enough data


# ============================================================================
# Wall Migration States
# ============================================================================
class WallMigrationCallState(str, Enum):
    """Call wall migration state."""

    RETREATING_RESISTANCE = "RETREATING_RESISTANCE"  # Call wall moving up (bullish)
    REINFORCED_WALL = "REINFORCED_WALL"              # Call wall holding (bearish ceiling)
    BREACHED = "BREACHED"                            # Spot pierced through call wall (gamma squeeze)
    DECAYING = "DECAYING"                            # End-of-day charm decay, wall no longer relevant
    STABLE = "STABLE"
    UNAVAILABLE = "UNAVAILABLE"


class WallMigrationPutState(str, Enum):
    """Put wall migration state."""

    RETREATING_SUPPORT = "RETREATING_SUPPORT"    # Put wall moving down (bearish)
    REINFORCED_SUPPORT = "REINFORCED_SUPPORT"    # Put wall holding (bullish floor)
    BREACHED = "BREACHED"                        # Spot broke below put wall (panic cascade)
    DECAYING = "DECAYING"                        # End-of-day charm decay, wall no longer relevant
    STABLE = "STABLE"
    UNAVAILABLE = "UNAVAILABLE"


class WallGammaRegime(str, Enum):
    """Gamma regime for contextual wall-risk interpretation."""

    LONG_GAMMA = "LONG_GAMMA"
    SHORT_GAMMA = "SHORT_GAMMA"
    NEUTRAL = "NEUTRAL"


class WallContext(BaseModel):
    """Contextual factors for wall-risk interpretation."""

    gamma_regime: WallGammaRegime = WallGammaRegime.NEUTRAL
    hedge_flow_intensity: float = 0.0
    counterfactual_vol_impact_bps: float = 0.0
    near_wall_hedge_notional_m: float = 0.0
    near_wall_liquidity: float = 0.0


# ============================================================================
# IV Regime Classification
# ============================================================================
class IVRegime(str, Enum):
    """IV regime based on SPY ATM Call IV %.

    LOW:      < 12% (crushed vol)
    NORMAL:   12-20% (typical)
    ELEVATED: 20-30% (fear)
    HIGH:     30-35% (decay zone)
    EXTREME:  > 35% (crisis)
    """

    LOW = "LOW"
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


# ============================================================================
# GEX Intensity Classification
# ============================================================================
class GexIntensity(str, Enum):
    """GEX intensity classification for UI display."""

    EXTREME_POSITIVE = "EXTREME_POSITIVE"   # Super Pin
    STRONG_POSITIVE = "STRONG_POSITIVE"     # Damping
    MODERATE = "MODERATE"
    NEUTRAL = "NEUTRAL"
    STRONG_NEGATIVE = "STRONG_NEGATIVE"     # Acceleration
    EXTREME_NEGATIVE = "EXTREME_NEGATIVE"


# ============================================================================
# Result Models
# ============================================================================
class VannaFlowResult(BaseModel):
    """Result from VannaFlowAnalyzer.update()."""

    state: VannaFlowState = VannaFlowState.UNAVAILABLE
    correlation: float | None = None
    gex_regime: GexRegime = GexRegime.NEUTRAL
    net_gex: float | None = None
    confidence: float = 0.0
    vanna_acceleration_state: VannaAccelerationState = VannaAccelerationState.UNAVAILABLE
    iv_roc: float | None = None
    iv_roc_prev: float | None = None
    iv_acceleration: float | None = None
    history_count: int = 0
    
    # MM Pulse Dynamic Multipliers
    wall_displacement_multiplier: float = 1.0
    momentum_slope_multiplier: float = 1.0


class IVVelocityResult(BaseModel):
    """Result from IV velocity tracker."""

    state: IVVelocityState = IVVelocityState.UNAVAILABLE
    confidence: float = 0.0
    iv_roc: float | None = None
    spot_roc: float | None = None
    divergence_score: float = 0.0


class WallMigrationResult(BaseModel):
    """Result from wall migration tracker."""

    call_wall_state: WallMigrationCallState = WallMigrationCallState.UNAVAILABLE
    put_wall_state: WallMigrationPutState = WallMigrationPutState.UNAVAILABLE
    confidence: float = 0.0
    call_wall_delta: float | None = None
    put_wall_delta: float | None = None
    call_wall_history: list[float | None] = Field(default_factory=list)
    put_wall_history: list[float | None] = Field(default_factory=list)
    wall_context: WallContext | None = None


class MicroStructureState(BaseModel):
    """Combined microstructure state from all trackers."""

    iv_velocity: IVVelocityResult | None = None
    wall_migration: WallMigrationResult | None = None
    vanna_flow_result: VannaFlowResult | None = None
    vanna_flow: VannaFlowResult | None = None  # alt key fallback
    mtf_consensus: dict[str, Any] = Field(default_factory=dict)
    volume_imbalance: VIBResult | None = None
    jump_detection: JumpResult | None = None
    wall_context: WallContext | None = None
    # Practice 3: Dealer Squeeze alert (vol_accel > threshold AND net_gex < 0)
    dealer_squeeze_alert: bool = False
    # Practice 2: VPIN score propagated from DepthEngine (ATM contracts average)
    avg_atm_vpin_score: float = 0.0


class MicroStructureAnalysis(BaseModel):
    """Wrapper for microstructure analysis output."""

    micro_structure_state: MicroStructureState | None = None


# ============================================================================
# Fused Signal Result (Phase 4: Decision Fusion)
# ============================================================================
class FusedSignalResult(BaseModel):
    """Result from DynamicWeightEngine.calculate_weights()."""

    direction: str = "NEUTRAL"
    confidence: float = 0.0
    weights: dict[str, float] = Field(default_factory=dict)
    regime: str = "UNKNOWN"
    iv_regime: IVRegime = IVRegime.NORMAL
    gex_intensity: GexIntensity = GexIntensity.NEUTRAL
    explanation: str = ""
    components: dict[str, Any] = Field(default_factory=dict)
