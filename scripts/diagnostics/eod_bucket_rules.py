from __future__ import annotations

from typing import Any


def _sign(v: float) -> int:
    if v > 0:
        return 1
    if v < 0:
        return -1
    return 0


def _cfg(thresholds: dict[str, Any], key: str) -> dict[str, Any]:
    if key in thresholds:
        return thresholds[key]
    raise KeyError(key)


def _trend_path_passes(metrics: dict[str, Any], trend: dict[str, Any]) -> bool:
    return (
        abs(metrics["net_return"]) >= float(trend["abs_ret_threshold"])
        and metrics["directional_efficiency"] >= float(trend["directional_efficiency_min"])
        and metrics["open_side_persistence"] >= float(trend["open_side_persistence_min"])
        and metrics["close_to_extreme"] <= float(trend["close_to_extreme_max"])
        and metrics["state_switch_rate"] <= float(trend["state_switch_rate_max"])
    )


def _reversal_path_passes(metrics: dict[str, Any], reversal: dict[str, Any]) -> bool:
    midday_return = float(metrics.get("midday_return", 0.0))
    afternoon_return = float(metrics.get("afternoon_return", 0.0))
    net_return = float(metrics["net_return"])
    return (
        abs(midday_return) >= float(reversal["opening_leg_abs_min"])
        and abs(afternoon_return) >= float(reversal["reversal_leg_abs_min"])
        and abs(net_return) >= float(reversal["net_return_abs_min"])
        and _sign(midday_return) != 0
        and _sign(midday_return) == -_sign(afternoon_return)
        and _sign(afternoon_return) == _sign(net_return)
        and metrics["state_switch_rate"] <= float(reversal["state_switch_rate_max"])
    )


def _balance_path_passes(metrics: dict[str, Any], balance: dict[str, Any]) -> bool:
    return (
        abs(metrics["net_return"]) <= float(balance["net_return_cap"])
        and metrics["directional_efficiency"] <= float(balance["directional_efficiency_max"])
    )


def _close_profile(metrics: dict[str, Any], thresholds: dict[str, Any]) -> str:
    close_cfg = _cfg(thresholds, "close_profile")
    close_to_extreme = float(metrics["close_to_extreme"])
    if close_to_extreme <= float(close_cfg["strong_close_max"]):
        return "strong_close"
    if close_to_extreme <= float(close_cfg["mid_close_max"]):
        return "mid_close"
    return "weak_close"


def _context_modifiers(metrics: dict[str, Any], thresholds: dict[str, Any], hits: list[str]) -> list[str]:
    modifiers: list[str] = []

    high = _cfg(thresholds, "high_vol_open")
    if metrics["open_rv_1m"] >= float(high["open_rv_1m_threshold"]):
        modifiers.append("high_vol_open")
        hits.append("high_vol_open: open_rv_1m >= threshold")

    gap = _cfg(thresholds, "gap_open")
    if metrics["overnight_gap_available"] and abs(metrics["overnight_gap"]) >= float(gap["overnight_gap_abs_min"]):
        modifiers.append("gap_open")
        hits.append("gap_open: overnight_gap_abs >= threshold")

    crush = _cfg(thresholds, "vol_crush")
    if (
        metrics["atm_iv_available"]
        and metrics["atm_iv_change_pct"] <= float(crush["atm_iv_change_pct_max"])
        and abs(metrics["net_return"]) <= float(crush["net_return_cap"])
        and metrics["realized_range"] <= float(crush["realized_range_cap"])
    ):
        modifiers.append("vol_crush")
        hits.append("vol_crush: iv crush threshold passed")

    pin = _cfg(thresholds, "pinning")
    if (
        metrics["key_level_coverage"] > 0
        and metrics["close_to_key_level"] <= float(pin["close_to_key_level_max"])
        and metrics["pin_band_ratio"] >= float(pin["pin_band_ratio_min"])
        and metrics["realized_range"] <= float(pin["realized_range_cap"])
    ):
        modifiers.append("pinning")
        hits.append("pinning: spot clustered near key level")

    return modifiers


def classify_metrics(
    metrics: dict[str, Any], thresholds: dict[str, Any], primary_priority: list[str]
) -> dict[str, Any]:
    hits: list[str] = []
    primary_candidates: list[str] = []
    context_modifiers = _context_modifiers(metrics, thresholds, hits)

    whipsaw = _cfg(thresholds, "whipsaw_day")
    if (
        metrics["state_switch_rate"] >= float(whipsaw["state_switch_rate_min"])
        and metrics["realized_range"] >= float(whipsaw["realized_range_min"])
        and abs(metrics["net_return"]) <= float(whipsaw["net_return_cap"])
    ):
        primary_candidates.append("whipsaw_day")
        hits.append("whipsaw_day: high switching and high range with low drift")

    reversal = _cfg(thresholds, "reversal_day")
    if _reversal_path_passes(metrics, reversal):
        primary_candidates.append("reversal_day")
        hits.append("reversal_day: opening leg and reversal leg passed")

    trend = _cfg(thresholds, "trend_day")
    trend_ofi_confirmed = (
        abs(metrics["net_return"]) >= float(trend["abs_ret_threshold"])
        and metrics["ofi_persistence"] >= float(trend["ofi_persistence_threshold"])
    )
    trend_path_fallback = _trend_path_passes(metrics, trend)
    if trend_ofi_confirmed or trend_path_fallback:
        primary_candidates.append("trend_day")
        if trend_ofi_confirmed and trend_path_fallback:
            hits.append("trend_day: ofi-confirmed and directional-path fallback both passed")
        elif trend_ofi_confirmed:
            hits.append("trend_day: abs_ret and ofi_persistence passed")
        else:
            hits.append("trend_day: directional-path fallback passed")

    balance = _cfg(thresholds, "balance_day")
    if _balance_path_passes(metrics, balance):
        primary_candidates.append("balance_day")
        hits.append("balance_day: low directional control passed")

    primary = "balance_day"
    for tag in primary_priority:
        if tag in primary_candidates:
            primary = tag
            break

    if primary not in primary_candidates:
        hits.append("balance_day: default fallback")

    return {
        "primary_day_type": primary,
        "context_modifiers": context_modifiers,
        "close_profile": _close_profile(metrics, thresholds),
        "rule_hits": hits,
        "primary_candidates": primary_candidates,
    }
