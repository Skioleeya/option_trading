"""Wall dynamics state machine for MicroStats.

Pure classifier that maps call/put wall tracker states into a single
MicroStats wall-dynamics key.
"""

from __future__ import annotations

from l3_assembly.presenters.ui.micro_stats import thresholds


URGENT_WALL_KEYS: set[str] = {"BREACH"}


def _norm_state(raw: str | None) -> str:
    s = str(raw or "")
    if "." in s:
        s = s.split(".")[-1]
    return s


def classify_wall_key(call_state: str | None, put_state: str | None) -> str:
    """Collapse call/put wall states into one MicroStats key."""
    call_st = _norm_state(call_state)
    put_st = _norm_state(put_state)

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
    if call_st in thresholds.WALL_RETREAT_STATES:
        return "RETREAT"
    if put_st in thresholds.WALL_COLLAPSE_STATES:
        return "COLLAPSE"

    # Cold-start / data-gap state.
    if (
        call_st in thresholds.WALL_UNAVAILABLE_STATES
        and put_st in thresholds.WALL_UNAVAILABLE_STATES
    ):
        return "UNAVAILABLE"

    return "STABLE"
