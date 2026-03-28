from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def _load_archive_module():
    path = Path("scripts/diagnostics/eod_bucket_archive.py")
    spec = importlib.util.spec_from_file_location("eod_bucket_archive_rth", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load eod_bucket_archive module")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_metrics_module():
    path = Path("scripts/diagnostics/eod_bucket_metrics.py")
    spec = importlib.util.spec_from_file_location("eod_bucket_metrics_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load eod_bucket_metrics module")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_parquet(path: Path, cols: dict[str, list]):
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(cols), path)


def _case_dir() -> Path:
    p = Path("tmp/pytest_cache/eod_bucket_rth_cases") / uuid.uuid4().hex[:10]
    p.mkdir(parents=True, exist_ok=True)
    return p


def test_read_raw_metrics_uses_rth_and_trims_spot_outlier():
    mod = _load_metrics_module()
    root = _case_dir()
    path = root / "raw.parquet"
    ts = [
        "2026-03-26T04:00:00-04:00",
        "2026-03-26T09:30:00-04:00",
        "2026-03-26T10:00:00-04:00",
        "2026-03-26T11:00:00-04:00",
        "2026-03-26T12:00:00-04:00",
        "2026-03-26T13:00:00-04:00",
        "2026-03-26T14:00:00-04:00",
        "2026-03-26T15:00:00-04:00",
        "2026-03-26T15:00:01-04:00",
        "2026-03-26T15:00:02-04:00",
        "2026-03-26T15:30:00-04:00",
        "2026-03-26T16:00:00-04:00",
        "2026-03-26T16:05:00-04:00",
    ]
    spots = [700.0, 100.0, 99.8, 99.4, 99.1, 98.9, 98.7, 50.0, 98.6, 98.5, 98.4, 98.3, 97.0]
    _write_parquet(
        path,
        {
            "data_timestamp": ts,
            "spot": spots,
            "atm_iv": [0.20] * len(ts),
            "bbo_imbalance_raw": [0.0] * len(ts),
            "net_gex": [1.0] * len(ts),
        },
    )
    metrics = mod.read_raw_metrics(
        path,
        {"high_vol_open": {"window": "09:30-10:00"}, "pinning_day": {"pin_band_width": 0.0020}, "raw_sanitizer": {"spot_trim_quantile": 0.1}},
        None,
    )
    assert metrics["start_timestamp"].startswith("2026-03-26T14:00:00")
    assert metrics["end_timestamp"].startswith("2026-03-26T20:00:00")
    assert metrics["spot_outlier_rows_dropped"] >= 1
    assert metrics["realized_range"] < 0.03


def test_rth_sanitizer_allows_trend_day_classification_despite_dirty_tick():
    archive = _load_archive_module()
    metrics = {
        "open_rv_1m": 0.0001,
        "net_return": -0.0177,
        "ofi_persistence": 0.0,
        "realized_range": 0.0181,
        "intraday_followthrough": -0.0177,
        "overnight_gap": 0.0,
        "overnight_gap_available": False,
        "atm_iv_change_pct": 1.29,
        "atm_iv_available": True,
        "directional_efficiency": 0.97,
        "open_side_persistence": 1.0,
        "close_to_extreme": 0.02,
        "close_to_key_level": 0.003,
        "pin_band_ratio": 0.0,
        "key_level_coverage": 1.0,
        "state_switch_rate": 0.001,
    }
    thresholds = {
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
        "gap_trend_day": {"overnight_gap_abs_min": 0.0060, "intraday_followthrough_abs_min": 0.0040, "require_same_direction": True},
        "vol_crush_day": {"atm_iv_change_pct_max": -0.12, "net_return_cap": 0.0050, "realized_range_cap": 0.0150},
        "pinning_day": {"close_to_key_level_max": 0.0015, "pin_band_ratio_min": 0.30, "pin_band_width": 0.0020, "realized_range_cap": 0.0150},
        "whipsaw_day": {"state_switch_rate_min": 0.55, "realized_range_min": 0.0120, "net_return_cap": 0.0040},
    }
    priority = ["high_vol_open", "gap_trend_day", "vol_crush_day", "pinning_day", "whipsaw_day", "trend_day", "range_day"]
    matched, primary, hits = archive._classify_metrics(metrics, thresholds, priority)
    assert "trend_day" in matched
    assert primary == "trend_day"
    assert any("directional-path fallback" in hit for hit in hits)
