"""GEX regime classification and Vanna state logic.

Responsibilities:
    - GEX regime → GexRegime enum (SUPER_PIN / DAMPING / NEUTRAL / ACCELERATION)
    - Vanna state → VannaFlowState enum (DANGER_ZONE / GRIND_STABLE / NORMAL / VANNA_FLIP)
    - Confidence score calculation

Layer:  L1
Deps:   shared/config, shared/models
"""

from __future__ import annotations

import logging
from typing import Any

from shared.config import settings
from shared.models.microstructure import GexRegime, VannaFlowState, VannaFlowResult

logger = logging.getLogger(__name__)

# Boundary band used for smooth danger-zone confidence interpolation
_CONFIDENCE_BOUNDARY_BAND = 0.05


# ── GEX Classifier ────────────────────────────────────────────────────────────

def classify_gex_regime(
    net_gex: float | None,
    _threshold_state: Any | None = None,
) -> GexRegime:
    """Classify GEX regime from net GEX value.

    Logic:
        - ACCELERATION : net_gex < 0 (any negative)
        - SUPER_PIN    : abs >= super_pin_threshold (e.g. 1000M)
        - DAMPING      : abs >= neutral_threshold   (e.g. 200M)
        - NEUTRAL      : otherwise
    """
    if net_gex is None:
        return GexRegime.NEUTRAL

    if net_gex < 0:
        return GexRegime.ACCELERATION

    abs_gex = abs(net_gex)
    neutral_threshold   = settings.gex_neutral_threshold
    super_pin_threshold = settings.gex_super_pin_threshold

    if abs_gex >= super_pin_threshold:
        return GexRegime.SUPER_PIN
    if abs_gex >= neutral_threshold:
        return GexRegime.DAMPING
    return GexRegime.NEUTRAL


# ── Vanna State Classifier ────────────────────────────────────────────────────

class VannaStateClassifier:
    """Stateful Vanna classification — owns the 'was_in_danger_zone' hysteresis flag.

    Design: single-responsibility for classification logic. The analyzer
    passes correlation + is_flip; this class returns the state enum and
    manages the hysteresis guard without touching history or math.
    """

    def __init__(self) -> None:
        self._was_in_danger_zone: bool = False
        self._warned_grind_sign: bool = False

    def classify(self, correlation: float | None, is_flip: bool = False) -> VannaFlowState:
        """Classify Vanna flow state.

        Priority:
            1. VANNA_FLIP  — instantaneous large correlation shift
            2. DANGER_ZONE — corr > danger threshold
            3. GRIND_STABLE — corr < -|grind threshold|
            4. NORMAL
        """
        if correlation is None:
            return VannaFlowState.NORMAL

        if is_flip:
            return VannaFlowState.VANNA_FLIP

        if correlation > settings.vanna_danger_zone_threshold:
            if not self._was_in_danger_zone:
                logger.debug(
                    "[L1 Vanna] Entering DANGER_ZONE. corr=%.2f > %.2f",
                    correlation,
                    settings.vanna_danger_zone_threshold,
                )
                self._was_in_danger_zone = True
            return VannaFlowState.DANGER_ZONE

        grind_threshold = settings.vanna_grind_stable_threshold
        if grind_threshold >= 0 and not self._warned_grind_sign:
            logger.warning(
                "[L1 Vanna] vanna_grind_stable_threshold=%.4f should be negative; using -abs().",
                grind_threshold,
            )
            self._warned_grind_sign = True
        grind_threshold = -abs(grind_threshold)

        if self._was_in_danger_zone:
            logger.debug("[L1 Vanna] Exiting DANGER_ZONE. corr=%.2f", correlation)
            self._was_in_danger_zone = False

        if correlation < grind_threshold:
            return VannaFlowState.GRIND_STABLE
        return VannaFlowState.NORMAL

    def reset(self) -> None:
        """Clear cross-day hysteresis state."""
        self._was_in_danger_zone = False


# ── Confidence Calculator ─────────────────────────────────────────────────────

def calculate_confidence(
    last_result: VannaFlowResult | None,
    sample_count: int,
) -> float:
    """Compute vanna signal confidence from [0.0, 1.0].

    PP-3 FIX: Uses linear interpolation around the DANGER_ZONE boundary
    (±BOUNDARY_BAND) instead of a hard 0.4 → 0.9 jump.
    """
    if last_result is None or last_result.state == VannaFlowState.UNAVAILABLE:
        return 0.0

    corr          = abs(last_result.correlation or 0.0)
    sample_factor = min(1.0, sample_count / 20)

    if last_result.state == VannaFlowState.DANGER_ZONE:
        danger_th   = settings.vanna_danger_zone_threshold
        raw_corr    = last_result.correlation or 0.0
        low         = danger_th - _CONFIDENCE_BOUNDARY_BAND
        high        = danger_th + _CONFIDENCE_BOUNDARY_BAND
        progress    = max(0.0, min(1.0, (raw_corr - low) / (high - low)))
        state_conf  = 0.4 + progress * 0.5   # [0.4, 0.9]
    elif last_result.state == VannaFlowState.GRIND_STABLE:
        state_conf = 0.7
    else:
        state_conf = 0.4

    corr_factor = min(1.0, corr)
    return min(1.0, state_conf * 0.5 + corr_factor * 0.3 + sample_factor * 0.2)
