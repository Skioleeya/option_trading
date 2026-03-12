from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


def _load_module():
    path = Path("scripts/diagnostics/eod_bucket_archive.py")
    spec = importlib.util.spec_from_file_location("eod_bucket_archive", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load eod_bucket_archive module")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_parquet(path: Path, cols: dict[str, list]):
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(cols)
    pq.write_table(table, path)


def _case_dir() -> Path:
    p = Path("tmp/pytest_cache/eod_bucket_cases") / uuid.uuid4().hex[:10]
    p.mkdir(parents=True, exist_ok=True)
    return p


def _default_cfg() -> dict:
    return {
        "classification_mode": "primary_only",
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
            "trend_day": {"abs_ret_threshold": 0.0070, "ofi_persistence_threshold": 0.55},
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
            "quality_gate": {
                "min_rows_raw": 50,
                "min_rows_feature": 50,
                "min_rows_label": 50,
                "max_null_pct": 0.05,
            },
        },
    }


def _write_cfg(path: Path, cfg: dict):
    path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def _make_day_files(
    root: Path,
    date_str: str,
    rows: int,
    *,
    include_feature_label: bool = True,
    include_walls: bool = True,
    with_prev_day: bool = False,
):
    if with_prev_day:
        prev_day = "20260310"
        prev_ts = ["2026-03-10T15:59:00-04:00", "2026-03-10T16:00:00-04:00"]
        _write_parquet(
            root / "research/raw" / f"raw_{prev_day}.parquet",
            {
                "data_timestamp": prev_ts,
                "spot": [100.0, 100.0],
                "atm_iv": [0.20, 0.20],
                "net_gex": [300.0, 300.0],
                "bbo_imbalance_raw": [0.0, 0.0],
            },
        )

    start = datetime.fromisoformat("2026-03-11T09:30:00-04:00")
    ts = [(start + timedelta(seconds=i * 60)).isoformat() for i in range(rows)]

    spot = []
    price = 100.0
    for i in range(rows):
        if i < 30:
            price += 0.01
        elif i < 70:
            price += 0.05
        else:
            price -= 0.05
        spot.append(price)

    cols = {
        "data_timestamp": ts,
        "spot": spot,
        "atm_iv": [0.20 for _ in range(rows)],
        "net_gex": [300.0 + i for i in range(rows)],
        "bbo_imbalance_raw": [0.1 for _ in range(rows)],
    }
    if include_walls:
        cols["call_wall"] = [101.0 for _ in range(rows)]
        cols["put_wall"] = [99.0 for _ in range(rows)]
        cols["flip_level"] = [100.0 for _ in range(rows)]

    _write_parquet(root / "research/raw" / f"raw_{date_str}.parquet", cols)

    if include_feature_label:
        _write_parquet(
            root / "research/feature" / f"feature_{date_str}.parquet",
            {"data_timestamp": ts, "spot": spot},
        )
        _write_parquet(
            root / "research/label" / f"label_{date_str}.parquet",
            {"data_timestamp": ts, "fwd_ret_1m": [0.0 for _ in range(rows)]},
        )

    for folder, name in [
        ("atm_decay", f"atm_series_{date_str}.jsonl"),
        ("mtf_iv", f"mtf_iv_series_{date_str}.jsonl"),
        ("wall_migration", f"wall_series_{date_str}.jsonl"),
    ]:
        p = root / folder / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"ok": true}\n', encoding="utf-8")


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
        "close_to_key_level": 1.0,
        "pin_band_ratio": 0.0,
        "key_level_coverage": 0.0,
        "state_switch_rate": 0.0,
    }


@pytest.mark.parametrize(
    ("expected", "patch"),
    [
        ("high_vol_open", {"open_rv_1m": 0.01}),
        ("trend_day", {"net_return": 0.02, "ofi_persistence": 0.9}),
        ("range_day", {"realized_range": 0.03, "net_return": 0.001}),
        (
            "gap_trend_day",
            {
                "overnight_gap_available": True,
                "overnight_gap": 0.01,
                "intraday_followthrough": 0.01,
                "net_return": 0.01,
                "ofi_persistence": 0.1,
            },
        ),
        (
            "vol_crush_day",
            {"atm_iv_available": True, "atm_iv_change_pct": -0.2, "net_return": 0.001, "realized_range": 0.01},
        ),
        (
            "pinning_day",
            {"close_to_key_level": 0.001, "pin_band_ratio": 0.6, "key_level_coverage": 0.9, "realized_range": 0.01},
        ),
        ("whipsaw_day", {"state_switch_rate": 0.8, "realized_range": 0.03, "net_return": 0.001}),
    ],
)
def test_each_class_can_be_selected_as_primary(expected: str, patch: dict):
    mod = _load_module()
    cfg = _default_cfg()
    metrics = _base_metrics()
    metrics.update(patch)
    matched, primary, _ = mod._classify_metrics(metrics, cfg["thresholds"], cfg["primary_priority"])
    assert expected in matched
    assert primary == expected


def test_priority_conflict_prefers_high_vol_open():
    mod = _load_module()
    cfg = _default_cfg()
    metrics = _base_metrics()
    metrics.update(
        {
            "open_rv_1m": 0.02,
            "net_return": 0.02,
            "ofi_persistence": 0.9,
            "state_switch_rate": 0.8,
            "realized_range": 0.03,
        }
    )
    matched, primary, _ = mod._classify_metrics(metrics, cfg["thresholds"], cfg["primary_priority"])
    assert "high_vol_open" in matched
    assert "trend_day" in matched
    assert primary == "high_vol_open"


def test_missing_previous_day_disables_gap_trend(tmp_path_factory=None):
    mod = _load_module()
    root = _case_dir()
    data_root = root / "data"
    out_root = root / "cold"
    date_str = "20260311"
    _make_day_files(data_root, date_str, rows=120, include_feature_label=True, include_walls=True, with_prev_day=False)

    cfg = _default_cfg()
    cfg["thresholds"]["trend_day"]["abs_ret_threshold"] = 1.0
    cfg["thresholds"]["range_day"]["realized_range_threshold"] = 1.0
    cfg["thresholds"]["high_vol_open"]["open_rv_1m_threshold"] = 1.0
    cfg["thresholds"]["vol_crush_day"]["atm_iv_change_pct_max"] = -1.0
    cfg["thresholds"]["pinning_day"]["pin_band_ratio_min"] = 1.1
    cfg["thresholds"]["whipsaw_day"]["state_switch_rate_min"] = 1.0
    cfg_path = root / "cfg.json"
    _write_cfg(cfg_path, cfg)

    rc = mod.run_cli(
        [
            "--date",
            date_str,
            "--config",
            str(cfg_path),
            "--root",
            str(data_root),
            "--out-root",
            str(out_root),
            "--strict-quality",
        ]
    )
    assert rc == 0
    daily = json.loads((out_root / "daily" / date_str / "manifest.json").read_text(encoding="utf-8"))
    assert "gap_trend_day" not in daily["matched_tags"]


def test_missing_wall_fields_does_not_match_pinning():
    mod = _load_module()
    root = _case_dir()
    data_root = root / "data"
    out_root = root / "cold"
    date_str = "20260311"
    _make_day_files(data_root, date_str, rows=120, include_feature_label=True, include_walls=False, with_prev_day=True)

    cfg = _default_cfg()
    cfg["thresholds"]["trend_day"]["abs_ret_threshold"] = 1.0
    cfg["thresholds"]["range_day"]["realized_range_threshold"] = 1.0
    cfg["thresholds"]["high_vol_open"]["open_rv_1m_threshold"] = 1.0
    cfg["thresholds"]["vol_crush_day"]["atm_iv_change_pct_max"] = -1.0
    cfg["thresholds"]["whipsaw_day"]["state_switch_rate_min"] = 1.0
    cfg_path = root / "cfg2.json"
    _write_cfg(cfg_path, cfg)

    rc = mod.run_cli(
        [
            "--date",
            date_str,
            "--config",
            str(cfg_path),
            "--root",
            str(data_root),
            "--out-root",
            str(out_root),
            "--strict-quality",
        ]
    )
    assert rc == 0
    daily = json.loads((out_root / "daily" / date_str / "manifest.json").read_text(encoding="utf-8"))
    assert "pinning_day" not in daily["matched_tags"]


def test_strict_quality_still_returns_2():
    mod = _load_module()
    root = _case_dir()
    data_root = root / "data"
    out_root = root / "cold"
    date_str = "20260311"
    _make_day_files(data_root, date_str, rows=10, include_feature_label=False, include_walls=True, with_prev_day=False)

    cfg = _default_cfg()
    cfg["thresholds"]["quality_gate"]["min_rows_raw"] = 100
    cfg["thresholds"]["quality_gate"]["min_rows_feature"] = 100
    cfg["thresholds"]["quality_gate"]["min_rows_label"] = 100
    cfg_path = root / "cfg_lowq.json"
    _write_cfg(cfg_path, cfg)

    rc = mod.run_cli(
        [
            "--date",
            date_str,
            "--config",
            str(cfg_path),
            "--root",
            str(data_root),
            "--out-root",
            str(out_root),
            "--strict-quality",
        ]
    )
    assert rc == 2


def test_primary_manifest_is_idempotent_and_by_regime_aligned():
    mod = _load_module()
    root = _case_dir()
    data_root = root / "data"
    out_root = root / "cold"
    date_str = "20260311"
    _make_day_files(data_root, date_str, rows=160, include_feature_label=True, include_walls=True, with_prev_day=True)

    cfg = _default_cfg()
    cfg_path = root / "cfg_main.json"
    _write_cfg(cfg_path, cfg)

    argv = [
        "--date",
        date_str,
        "--config",
        str(cfg_path),
        "--root",
        str(data_root),
        "--out-root",
        str(out_root),
        "--strict-quality",
    ]
    assert mod.run_cli(argv) == 0
    first = json.loads((out_root / "daily" / date_str / "manifest.json").read_text(encoding="utf-8"))
    assert mod.run_cli(argv) == 0
    second = json.loads((out_root / "daily" / date_str / "manifest.json").read_text(encoding="utf-8"))

    assert first["primary_tag"] == second["primary_tag"]
    assert first["source_files"] == second["source_files"]
    reg = out_root / "by_regime" / first["primary_tag"] / date_str / "manifest.json"
    assert reg.exists()
    reg_payload = json.loads(reg.read_text(encoding="utf-8"))
    assert reg_payload["source_files"] == first["source_files"]


def test_non_trading_weekend_date_returns_1():
    mod = _load_module()
    rc = mod.run_cli(["--date", "20260314"])
    assert rc == 1


def test_non_trading_holiday_date_returns_1():
    mod = _load_module()
    rc = mod.run_cli(["--date", "20260703"])
    assert rc == 1


def test_missing_prev_session_file_does_not_fallback_to_older_day():
    mod = _load_module()
    root = _case_dir()
    data_root = root / "data"
    out_root = root / "cold"
    date_str = "20260311"
    _make_day_files(data_root, date_str, rows=120, include_feature_label=True, include_walls=True, with_prev_day=False)

    # Intentionally provide an older file but keep the immediate previous session file absent.
    _write_parquet(
        data_root / "research/raw" / "raw_20260309.parquet",
        {
            "data_timestamp": ["2026-03-09T15:59:00-04:00", "2026-03-09T16:00:00-04:00"],
            "spot": [99.0, 100.0],
            "atm_iv": [0.20, 0.20],
            "net_gex": [300.0, 300.0],
            "bbo_imbalance_raw": [0.0, 0.0],
        },
    )

    cfg = _default_cfg()
    cfg_path = root / "cfg_prev_missing.json"
    _write_cfg(cfg_path, cfg)

    rc = mod.run_cli(
        [
            "--date",
            date_str,
            "--config",
            str(cfg_path),
            "--root",
            str(data_root),
            "--out-root",
            str(out_root),
            "--strict-quality",
        ]
    )
    assert rc == 0
    daily = json.loads((out_root / "daily" / date_str / "manifest.json").read_text(encoding="utf-8"))
    raw_day = daily["metrics"]["raw_day"]
    assert raw_day["prev_trade_day"] == "20260310"
    assert raw_day["overnight_gap_available"] is False
