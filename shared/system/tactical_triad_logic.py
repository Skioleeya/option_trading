"""Shared tactical-triad normalization helpers.

Centralizes VRP/S-VOL state normalization so L2/L3 stay semantically aligned.
"""

from __future__ import annotations

import math
from typing import Any


DEFAULT_VRP_BASELINE_HV_PCT = 13.5
_VALID_SVOL_STATES = {"DANGER_ZONE", "GRIND_STABLE", "VANNA_FLIP", "NORMAL", "UNAVAILABLE"}


def _to_float(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return f


def normalize_iv_percent(atm_iv: Any) -> float | None:
    """Normalize ATM IV to percentage points.

    Contract in this project is mostly decimal IV (e.g. 0.15), but a few
    legacy paths can emit already-percent values (e.g. 15.0). Keep both safe.
    """
    iv = _to_float(atm_iv)
    if iv is None:
        return None
    return iv * 100.0 if abs(iv) <= 3.0 else iv


def normalize_vrp_baseline_hv_pct(raw_baseline_hv: Any) -> float:
    """Normalize VRP baseline HV to percentage points.

    If a decimal-like value slips in (<= 1.0), interpret it as fraction.
    This keeps `0.15` and `15.0` semantically identical for Phase A.
    """
    baseline = _to_float(raw_baseline_hv)
    if baseline is None or baseline <= 0:
        return DEFAULT_VRP_BASELINE_HV_PCT
    return baseline * 100.0 if baseline <= 1.0 else baseline


def normalize_guard_vrp_threshold_pct(raw_threshold: Any, default_pct: float) -> float:
    """Normalize guard VRP thresholds to percentage points.

    Compatibility rule: legacy decimal thresholds like `0.15` are interpreted as
    `15.0` percent points.
    """
    threshold = _to_float(raw_threshold)
    if threshold is None or threshold <= 0:
        return default_pct
    return threshold * 100.0 if threshold <= 1.0 else threshold


def compute_vrp(atm_iv: Any, baseline_hv: Any) -> float | None:
    """Compute VRP = ATM_IV(%) - baseline_HV(%).

    Return value is always in percentage points, not decimal fraction.
    """
    atm_iv_pct = normalize_iv_percent(atm_iv)
    if atm_iv_pct is None:
        return None
    baseline_pct = normalize_vrp_baseline_hv_pct(baseline_hv)
    return atm_iv_pct - baseline_pct


def compute_guard_vrp_proxy_pct(atm_iv: Any, vol_accel_ratio: Any) -> float | None:
    """Compute the guard-only VRP proxy in percentage points.

    The guard preserves its historical idea of `ATM IV - realized vol proxy`,
    where the realized-vol leg is still derived from `|vol_accel_ratio| * 0.10`
    in decimal terms. This helper only normalizes the result to `% points`.
    """
    atm_iv_pct = normalize_iv_percent(atm_iv)
    vol_accel = _to_float(vol_accel_ratio)
    if atm_iv_pct is None or vol_accel is None:
        return None
    realized_vol_proxy_pct = abs(vol_accel) * 10.0
    return atm_iv_pct - realized_vol_proxy_pct


def classify_vrp_state(
    vrp: float | None,
    cheap_threshold: Any,
    expensive_threshold: Any,
    trap_threshold: Any,
) -> str:
    """Classify VRP regime with stable fallbacks."""
    if vrp is None:
        return "FAIR"

    cheap = _to_float(cheap_threshold)
    expensive = _to_float(expensive_threshold)
    trap = _to_float(trap_threshold)

    # Defensive defaults if config is invalid.
    if cheap is None:
        cheap = -2.0
    if expensive is None:
        expensive = 2.0
    if trap is None:
        trap = 5.0

    if vrp > trap:
        return "TRAP"
    if vrp > expensive:
        return "EXPENSIVE"
    if vrp < cheap * 3.0:
        return "BARGAIN"
    if vrp < cheap:
        return "CHEAP"
    return "FAIR"


def normalize_svol_state(raw_state: Any) -> str:
    """Normalize Vanna state to TacticalTriad S-VOL state domain."""
    if raw_state is None:
        return "UNAVAILABLE"
    state = str(raw_state)
    if "." in state:
        state = state.split(".")[-1]
    return state if state in _VALID_SVOL_STATES else "NORMAL"


def resolve_svol_fields(vanna_result: Any) -> tuple[float | None, str]:
    """Extract (svol_corr, svol_state) from VannaFlowResult-like object."""
    if vanna_result is None:
        return None, "UNAVAILABLE"

    state_obj = getattr(vanna_result, "state", None)
    raw_state = getattr(state_obj, "value", state_obj)
    state = normalize_svol_state(raw_state)

    corr = _to_float(getattr(vanna_result, "correlation", None))
    if corr is None:
        return None, "UNAVAILABLE"
    return corr, state
