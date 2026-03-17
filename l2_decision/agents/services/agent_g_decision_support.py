from __future__ import annotations

import math
from typing import Any

ATM_STRIKE_WINDOW = 3.0
NEG_GEX_BBO_WEIGHT = 0.60
POS_GEX_BBO_WEIGHT = 0.40
MAX_SIGNAL_CONFIDENCE = 1.0
VOL_ACCEL_SQUEEZE_CONFIDENCE_BOOST = 1.25
VRP_VETO_EXIT_RATIO = 0.95


def safe_get_value(obj: Any, key: str, default: Any = None) -> Any:
    if hasattr(obj, key):
        return getattr(obj, key, default)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def extract_per_strike(snapshot: Any) -> list[Any]:
    per_strike = safe_get_value(snapshot, "per_strike_gex", []) or []
    if not hasattr(snapshot, "chain"):
        return per_strike
    try:
        import pyarrow as pa  # lazy import to avoid hard dependency at module load

        if isinstance(snapshot.chain, pa.RecordBatch):
            return snapshot.chain.to_pylist()
    except (ImportError, AttributeError, TypeError):
        return per_strike
    return per_strike


def _row_value(row: Any, key: str, default: Any = 0.0) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _extract_atm_row_metrics(row: Any, spot: float, strike_window: float) -> tuple[float, float, float | None] | None:
    row_strike = float(_row_value(row, "strike", 0.0) or 0.0)
    if abs(row_strike - spot) > strike_window:
        return None
    tox = float(_row_value(row, "toxicity_score", 0.0) or 0.0)
    bbo = float(_row_value(row, "bbo_imbalance", 0.0) or 0.0)
    raw_vpin = _row_value(row, "vpin_score", None)
    if raw_vpin is None:
        return tox, bbo, None
    vpin = float(raw_vpin)
    if vpin == 0.0:
        return tox, bbo, None
    return tox, bbo, vpin


def collect_atm_micro_metrics(
    *,
    per_strike: list[Any],
    spot: float,
    strike_window: float = ATM_STRIKE_WINDOW,
) -> tuple[float, float, float]:
    atm_tox_vals: list[float] = []
    atm_bbo_vals: list[float] = []
    atm_vpin_vals: list[float] = []

    for row in per_strike:
        metrics = _extract_atm_row_metrics(row, spot, strike_window)
        if metrics is None:
            continue
        tox, bbo, vpin = metrics
        if tox != 0.0:
            atm_tox_vals.append(tox)
        if bbo != 0.0:
            atm_bbo_vals.append(bbo)
        if vpin is not None:
            atm_vpin_vals.append(vpin)

    avg_tox = sum(atm_tox_vals) / len(atm_tox_vals) if atm_tox_vals else 0.0
    avg_bbo = sum(atm_bbo_vals) / len(atm_bbo_vals) if atm_bbo_vals else 0.0
    avg_vpin = sum(atm_vpin_vals) / len(atm_vpin_vals) if atm_vpin_vals else 0.0
    return avg_tox, avg_bbo, avg_vpin


def build_micro_flow_signal(
    *,
    avg_tox: float,
    avg_bbo: float,
    fallback_bbo: float,
    net_gex: float | None,
    threshold: float,
) -> tuple[dict[str, Any], float]:
    bbo = avg_bbo if avg_bbo != 0.0 else fallback_bbo
    bbo_weight = NEG_GEX_BBO_WEIGHT if (net_gex is not None and net_gex < 0) else POS_GEX_BBO_WEIGHT
    tox_weight = 1.0 - bbo_weight
    micro_score = tox_weight * avg_tox + bbo_weight * bbo

    if micro_score > threshold:
        direction = "BULLISH"
        confidence = min(abs(micro_score), MAX_SIGNAL_CONFIDENCE)
    elif micro_score < -threshold:
        direction = "BEARISH"
        confidence = min(abs(micro_score), MAX_SIGNAL_CONFIDENCE)
    else:
        direction = "NEUTRAL"
        confidence = 0.0

    signal = {
        "direction": direction,
        "confidence": confidence,
    }
    return signal, bbo


def extract_dealer_squeeze_alert(ms_state: Any, agent_b_data: dict[str, Any]) -> bool:
    if ms_state is not None and bool(getattr(ms_state, "dealer_squeeze_alert", False)):
        return True
    raw_micro_state = agent_b_data.get("micro_structure", {}).get("micro_structure_state", {})
    if isinstance(raw_micro_state, dict):
        return bool(raw_micro_state.get("dealer_squeeze_alert", False))
    return False


def parse_decimal_iv(raw_value: Any) -> float | None:
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return value
