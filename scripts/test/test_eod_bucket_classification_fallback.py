from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    path = Path("scripts/diagnostics/eod_bucket_archive.py")
    spec = importlib.util.spec_from_file_location("eod_bucket_archive_fallback", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load eod_bucket_archive module")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _cfg() -> dict:
    return {
        "primary_priority": [
            "high_vol_open",
            "gap_trend_day",
            "vol_crush_day",
            "pinning_day",
            "whipsaw_day",
            "trend_day",
            "range_day",
        ],
        "thresholds": {
            "high_vol_open": {"window": "09:30-10:00", "open_rv_1m_threshold": 0.0015},
            "trend_day": {
                "abs_ret_threshold": 0.0070,
                "ofi_persistence_threshold": 0.55,
                "directional_efficiency_min": 0.60,
                "open_side_persistence_min": 0.65,
                "close_to_extreme_max": 0.20,
                "state_switch_rate_max": 0.35,
            },
            "range_day": {"realized_range_threshold": 0.0120, "net_return_cap": 0.0030},
            "gap_trend_day": {
                "overnight_gap_abs_min": 0.0060,
                "intraday_followthrough_abs_min": 0.0040,
                "require_same_direction": True,
            },
            "vol_crush_day": {
                "atm_iv_change_pct_max": -0.12,
                "net_return_cap": 0.0050,
                "realized_range_cap": 0.0150,
            },
            "pinning_day": {
                "close_to_key_level_max": 0.0015,
                "pin_band_ratio_min": 0.30,
                "pin_band_width": 0.0020,
                "realized_range_cap": 0.0150,
            },
            "whipsaw_day": {
                "state_switch_rate_min": 0.55,
                "realized_range_min": 0.0120,
                "net_return_cap": 0.0040,
            },
        },
    }


def _base_metrics() -> dict:
    return {
        "open_rv_1m": 0.0001,
        "net_return": 0.0,
        "ofi_persistence": 0.0,
        "realized_range": 0.001,
        "intraday_followthrough": 0.0,
        "overnight_gap": 0.0,
        "overnight_gap_available": False,
        "atm_iv_change_pct": 0.0,
        "atm_iv_available": False,
        "directional_efficiency": 0.0,
        "open_side_persistence": 0.0,
        "close_to_extreme": 1.0,
        "close_to_key_level": 1.0,
        "pin_band_ratio": 0.0,
        "key_level_coverage": 0.0,
        "state_switch_rate": 0.0,
    }


def test_trend_day_directional_fallback_matches_without_ofi_confirmation():
    mod = _load_module()
    metrics = _base_metrics()
    metrics.update(
        {
            "net_return": -0.015,
            "realized_range": 0.016,
            "directional_efficiency": 0.94,
            "open_side_persistence": 0.98,
            "close_to_extreme": 0.03,
            "state_switch_rate": 0.02,
            "ofi_persistence": 0.0,
        }
    )
    matched, primary, hits = mod._classify_metrics(metrics, _cfg()["thresholds"], _cfg()["primary_priority"])
    assert "trend_day" in matched
    assert primary == "trend_day"
    assert any("directional-path fallback" in hit for hit in hits)


def test_trend_day_fallback_does_not_match_whipsaw_like_day():
    mod = _load_module()
    metrics = _base_metrics()
    metrics.update(
        {
            "net_return": 0.008,
            "realized_range": 0.025,
            "directional_efficiency": 0.32,
            "open_side_persistence": 0.54,
            "close_to_extreme": 0.48,
            "state_switch_rate": 0.74,
        }
    )
    matched, _, _ = mod._classify_metrics(metrics, _cfg()["thresholds"], _cfg()["primary_priority"])
    assert "trend_day" not in matched


def test_gap_trend_excludes_trend_day_when_gap_rule_matches():
    mod = _load_module()
    metrics = _base_metrics()
    metrics.update(
        {
            "net_return": -0.009,
            "intraday_followthrough": -0.009,
            "overnight_gap_available": True,
            "overnight_gap": -0.008,
            "directional_efficiency": 0.70,
            "open_side_persistence": 0.80,
            "close_to_extreme": 0.12,
            "state_switch_rate": 0.08,
        }
    )
    matched, primary, _ = mod._classify_metrics(metrics, _cfg()["thresholds"], _cfg()["primary_priority"])
    assert "gap_trend_day" in matched
    assert "trend_day" not in matched
    assert primary == "gap_trend_day"
