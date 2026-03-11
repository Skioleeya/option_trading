"""Wall dynamics state machine for MicroStats.

Pure classifier that maps call/put wall tracker states into a single
MicroStats wall-dynamics key.
"""

from __future__ import annotations

from typing import Any

from l3_assembly.presenters.ui.micro_stats import thresholds


URGENT_WALL_KEYS: set[str] = {"BREACH"}


def _norm_state(raw: str | None) -> str:
    s = str(raw or "")
    if "." in s:
        s = s.split(".")[-1]
    return s


def _extract_wall_context(raw: dict[str, Any] | None) -> tuple[str, float]:
    if not isinstance(raw, dict):
        return "NEUTRAL", 0.0

    gamma_regime = str(raw.get("gamma_regime", "NEUTRAL") or "NEUTRAL")
    try:
        intensity = float(raw.get("hedge_flow_intensity", 0.0) or 0.0)
    except (TypeError, ValueError):
        intensity = 0.0
    return gamma_regime, intensity


def classify_wall_key(
    call_state: str | None,
    put_state: str | None,
    wall_context: dict[str, Any] | None = None,
) -> str:
    """Collapse call/put wall states into one MicroStats key."""
    call_st = _norm_state(call_state)
    put_st = _norm_state(put_state)
    gamma_regime, hedge_flow_intensity = _extract_wall_context(wall_context)

    # Highest-priority hard-risk states.
    if call_st in thresholds.WALL_BREACH_STATES or put_st in thresholds.WALL_BREACH_STATES:
        return "BREACH"
    if call_st in thresholds.WALL_DECAY_STATES or put_st in thresholds.WALL_DECAY_STATES:
        return "DECAY"

    # Existing directional/structure hierarchy.
    if (
        call_st in thresholds.WALL_PINCH_CALL_STATES
        and put_st in thresholds.WALL_PINCH_PUT_STATES
    ):
        return "PINCH"
    if call_st in thresholds.WALL_SIEGE_STATES or put_st in thresholds.WALL_SIEGE_STATES:
        return "SIEGE"
    if (
        put_st in thresholds.WALL_COLLAPSE_STATES
        and gamma_regime in thresholds.WALL_COLLAPSE_GAMMA_REGIMES
        and hedge_flow_intensity >= thresholds.WALL_COLLAPSE_FLOW_INTENSITY_THRESHOLD
    ):
        return "COLLAPSE"
    call_retreat_up = call_st in thresholds.WALL_RETREAT_UP_STATES
    put_retreat_down = put_st in thresholds.WALL_RETREAT_DOWN_STATES
    if call_retreat_up and put_retreat_down:
        return "RETREAT"
    if put_retreat_down:
        return "RETREAT_DOWN"
    if call_retreat_up:
        return "RETREAT_UP"

    # Cold-start / data-gap state.
    if (
        call_st in thresholds.WALL_UNAVAILABLE_STATES
        and put_st in thresholds.WALL_UNAVAILABLE_STATES
    ):
        return "UNAVAILABLE"

    return "STABLE"
