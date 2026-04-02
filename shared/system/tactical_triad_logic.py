"""Rust-backed tactical-triad normalization helpers."""

from __future__ import annotations

import math
from typing import Any

from shared.services.l0_runtime._native_generated import l0_rust

_SPEC = dict(l0_rust.tactical_triad_spec())
DEFAULT_VRP_BASELINE_HV_PCT = float(_SPEC["DEFAULT_VRP_BASELINE_HV_PCT"])
_VALID_SVOL_STATES = {str(value) for value in _SPEC["VALID_SVOL_STATES"]}


def _to_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def normalize_iv_percent(atm_iv: Any) -> float | None:
    return l0_rust.tactical_normalize_iv_percent(_to_float(atm_iv))


def normalize_vrp_baseline_hv_pct(raw_baseline_hv: Any) -> float:
    return float(l0_rust.tactical_normalize_vrp_baseline_hv_pct(_to_float(raw_baseline_hv)))


def normalize_guard_vrp_threshold_pct(raw_threshold: Any, default_pct: float) -> float:
    return float(
        l0_rust.tactical_normalize_guard_vrp_threshold_pct(_to_float(raw_threshold), float(default_pct))
    )


def compute_vrp(atm_iv: Any, baseline_hv: Any) -> float | None:
    return l0_rust.tactical_compute_vrp(_to_float(atm_iv), _to_float(baseline_hv))


def compute_guard_vrp_proxy_pct(atm_iv: Any, vol_accel_ratio: Any) -> float | None:
    return l0_rust.tactical_compute_guard_vrp_proxy_pct(_to_float(atm_iv), _to_float(vol_accel_ratio))


def classify_vrp_state(
    vrp: float | None,
    cheap_threshold: Any,
    expensive_threshold: Any,
    trap_threshold: Any,
) -> str:
    return str(
        l0_rust.tactical_classify_vrp_state(
            _to_float(vrp),
            _to_float(cheap_threshold),
            _to_float(expensive_threshold),
            _to_float(trap_threshold),
        )
    )


def normalize_svol_state(raw_state: Any) -> str:
    if raw_state is None:
        return "UNAVAILABLE"
    value = str(raw_state)
    state = str(l0_rust.tactical_normalize_svol_state(value))
    return state if state in _VALID_SVOL_STATES else "NORMAL"


def resolve_svol_fields(vanna_result: Any) -> tuple[float | None, str]:
    if vanna_result is None:
        return None, "UNAVAILABLE"
    state_obj = getattr(vanna_result, "state", None)
    raw_state = getattr(state_obj, "value", state_obj)
    state = normalize_svol_state(raw_state)
    corr = _to_float(getattr(vanna_result, "correlation", None))
    if corr is None:
        return None, "UNAVAILABLE"
    return corr, state
