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
            "whipsaw_day",
            "reversal_day",
            "trend_day",
            "balance_day",
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
            "reversal_day": {
                "midday_pivot_time": "12:00",
                "opening_leg_abs_min": 0.0035,
                "reversal_leg_abs_min": 0.0040,
                "net_return_abs_min": 0.0025,
                "state_switch_rate_max": 0.45,
            },
            "balance_day": {"net_return_cap": 0.0050, "directional_efficiency_max": 0.55},
            "gap_open": {"overnight_gap_abs_min": 0.0060},
            "vol_crush": {
                "atm_iv_change_pct_max": -0.12,
                "net_return_cap": 0.0050,
                "realized_range_cap": 0.0150,
            },
            "pinning": {
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
            "close_profile": {"strong_close_max": 0.10, "mid_close_max": 0.35},
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
        "midday_return": 0.0,
        "afternoon_return": 0.0,
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
    result = mod._classify_metrics(metrics, _cfg()["thresholds"], _cfg()["primary_priority"])
    assert result["primary_day_type"] == "trend_day"
    assert any("directional-path fallback" in hit for hit in result["rule_hits"])


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
    result = mod._classify_metrics(metrics, _cfg()["thresholds"], _cfg()["primary_priority"])
    assert "trend_day" not in result["primary_candidates"]


def test_gap_open_is_context_modifier_while_trend_remains_primary():
    mod = _load_module()
    metrics = _base_metrics()
    metrics.update(
        {
            "net_return": -0.009,
            "overnight_gap_available": True,
            "overnight_gap": -0.008,
            "directional_efficiency": 0.70,
            "open_side_persistence": 0.80,
            "close_to_extreme": 0.12,
            "state_switch_rate": 0.08,
            "midday_return": -0.006,
            "afternoon_return": -0.003,
        }
    )
    result = mod._classify_metrics(metrics, _cfg()["thresholds"], _cfg()["primary_priority"])
    assert result["primary_day_type"] == "trend_day"
    assert "gap_open" in result["context_modifiers"]
    assert "legacy_primary_tag" not in result


def test_reversal_day_is_not_upgraded_to_reversal_trend():
    mod = _load_module()
    metrics = _base_metrics()
    metrics.update(
        {
            "net_return": -0.0035,
            "realized_range": 0.017,
            "directional_efficiency": 0.20,
            "open_side_persistence": 0.41,
            "close_to_extreme": 0.26,
            "state_switch_rate": 0.10,
            "midday_return": 0.005,
            "afternoon_return": -0.008,
        }
    )
    result = mod._classify_metrics(metrics, _cfg()["thresholds"], _cfg()["primary_priority"])
    assert result["primary_day_type"] == "reversal_day"
    assert result["close_profile"] == "mid_close"
