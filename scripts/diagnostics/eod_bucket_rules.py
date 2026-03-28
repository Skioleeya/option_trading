from __future__ import annotations

from typing import Any


def _sign(v: float) -> int:
    if v > 0:
        return 1
    if v < 0:
        return -1
    return 0


def _trend_path_passes(metrics: dict[str, Any], trend: dict[str, Any]) -> bool:
    return (
        abs(metrics["net_return"]) >= float(trend["abs_ret_threshold"])
        and metrics["directional_efficiency"] >= float(trend["directional_efficiency_min"])
        and metrics["open_side_persistence"] >= float(trend["open_side_persistence_min"])
        and metrics["close_to_extreme"] <= float(trend["close_to_extreme_max"])
        and metrics["state_switch_rate"] <= float(trend["state_switch_rate_max"])
    )


def classify_metrics(
    metrics: dict[str, Any], thresholds: dict[str, Any], primary_priority: list[str]
) -> tuple[list[str], str, list[str]]:
    matched: list[str] = []
    hits: list[str] = []

    high = thresholds["high_vol_open"]
    if metrics["open_rv_1m"] >= float(high["open_rv_1m_threshold"]):
        matched.append("high_vol_open")
        hits.append("high_vol_open: open_rv_1m >= threshold")

    gap = thresholds["gap_trend_day"]
    gap_trend_matched = False
    if metrics["overnight_gap_available"]:
        cond = (
            abs(metrics["overnight_gap"]) >= float(gap["overnight_gap_abs_min"])
            and abs(metrics["intraday_followthrough"]) >= float(gap["intraday_followthrough_abs_min"])
        )
        if cond and bool(gap.get("require_same_direction", True)):
            cond = _sign(metrics["overnight_gap"]) != 0 and _sign(metrics["overnight_gap"]) == _sign(
                metrics["intraday_followthrough"]
            )
        if cond:
            gap_trend_matched = True
            matched.append("gap_trend_day")
            hits.append("gap_trend_day: overnight_gap and followthrough passed")

    trend = thresholds["trend_day"]
    trend_ofi_confirmed = (
        abs(metrics["net_return"]) >= float(trend["abs_ret_threshold"])
        and metrics["ofi_persistence"] >= float(trend["ofi_persistence_threshold"])
    )
    trend_path_fallback = _trend_path_passes(metrics, trend)
    if not gap_trend_matched and (trend_ofi_confirmed or trend_path_fallback):
        matched.append("trend_day")
        if trend_ofi_confirmed and trend_path_fallback:
            hits.append("trend_day: ofi-confirmed and directional-path fallback both passed")
        elif trend_ofi_confirmed:
            hits.append("trend_day: abs_ret and ofi_persistence passed")
        else:
            hits.append("trend_day: directional-path fallback passed")

    rg = thresholds["range_day"]
    if (
        metrics["realized_range"] >= float(rg["realized_range_threshold"])
        and abs(metrics["net_return"]) <= float(rg["net_return_cap"])
    ):
        matched.append("range_day")
        hits.append("range_day: realized_range high with capped net_return")

    crush = thresholds["vol_crush_day"]
    if (
        metrics["atm_iv_available"]
        and metrics["atm_iv_change_pct"] <= float(crush["atm_iv_change_pct_max"])
        and abs(metrics["net_return"]) <= float(crush["net_return_cap"])
        and metrics["realized_range"] <= float(crush["realized_range_cap"])
    ):
        matched.append("vol_crush_day")
        hits.append("vol_crush_day: iv crush with muted price action")

    pin = thresholds["pinning_day"]
    if (
        metrics["key_level_coverage"] > 0
        and metrics["close_to_key_level"] <= float(pin["close_to_key_level_max"])
        and metrics["pin_band_ratio"] >= float(pin["pin_band_ratio_min"])
        and metrics["realized_range"] <= float(pin["realized_range_cap"])
    ):
        matched.append("pinning_day")
        hits.append("pinning_day: spot clustered near key level")

    whipsaw = thresholds["whipsaw_day"]
    if (
        metrics["state_switch_rate"] >= float(whipsaw["state_switch_rate_min"])
        and metrics["realized_range"] >= float(whipsaw["realized_range_min"])
        and abs(metrics["net_return"]) <= float(whipsaw["net_return_cap"])
    ):
        matched.append("whipsaw_day")
        hits.append("whipsaw_day: high switching and high range with low drift")

    primary = "unclassified"
    for tag in primary_priority:
        if tag in matched:
            primary = tag
            break

    return matched, primary, hits
