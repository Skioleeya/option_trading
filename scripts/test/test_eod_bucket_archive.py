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


def _load_sync_module():
    path = Path("scripts/diagnostics/check_eod_manifest_sync.py")
    spec = importlib.util.spec_from_file_location("check_eod_manifest_sync", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load check_eod_manifest_sync module")
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
        "classification_mode": "primary_plus_context_v1",
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


@pytest.mark.parametrize(
    ("expected", "patch"),
    [
        ("trend_day", {"net_return": 0.02, "ofi_persistence": 0.9, "midday_return": 0.01, "afternoon_return": 0.01}),
        ("balance_day", {"realized_range": 0.03, "net_return": 0.001, "directional_efficiency": 0.03}),
        ("whipsaw_day", {"state_switch_rate": 0.8, "realized_range": 0.03, "net_return": 0.001}),
        (
            "reversal_day",
            {
                "net_return": -0.004,
                "realized_range": 0.02,
                "midday_return": 0.008,
                "afternoon_return": -0.012,
                "state_switch_rate": 0.15,
                "close_to_extreme": 0.25,
            },
        ),
    ],
)
def test_each_class_can_be_selected_as_primary(expected: str, patch: dict):
    mod = _load_module()
    cfg = _default_cfg()
    metrics = _base_metrics()
    metrics.update(patch)
    result = mod._classify_metrics(metrics, cfg["thresholds"], cfg["primary_priority"])
    assert expected in result["primary_candidates"]
    assert result["primary_day_type"] == expected


def test_gap_open_is_modifier_without_legacy_alias():
    mod = _load_module()
    cfg = _default_cfg()
    metrics = _base_metrics()
    metrics.update(
        {
            "overnight_gap_available": True,
            "overnight_gap": 0.01,
            "net_return": 0.02,
            "ofi_persistence": 0.9,
            "midday_return": 0.01,
            "afternoon_return": 0.01,
        }
    )
    result = mod._classify_metrics(metrics, cfg["thresholds"], cfg["primary_priority"])
    assert result["primary_day_type"] == "trend_day"
    assert "gap_open" in result["context_modifiers"]
    assert "legacy_primary_tag" not in result


def test_high_vol_open_is_modifier_not_primary():
    mod = _load_module()
    cfg = _default_cfg()
    metrics = _base_metrics()
    metrics.update({"open_rv_1m": 0.02, "net_return": 0.001, "directional_efficiency": 0.03})
    result = mod._classify_metrics(metrics, cfg["thresholds"], cfg["primary_priority"])
    assert "high_vol_open" in result["context_modifiers"]
    assert result["primary_day_type"] == "balance_day"


def test_missing_previous_day_disables_gap_trend(tmp_path_factory=None):
    mod = _load_module()
    root = _case_dir()
    data_root = root / "data"
    out_root = root / "cold"
    date_str = "20260311"
    _make_day_files(data_root, date_str, rows=120, include_feature_label=True, include_walls=True, with_prev_day=False)

    cfg = _default_cfg()
    cfg["thresholds"]["trend_day"]["abs_ret_threshold"] = 1.0
    cfg["thresholds"]["balance_day"]["net_return_cap"] = 0.0001
    cfg["thresholds"]["high_vol_open"]["open_rv_1m_threshold"] = 1.0
    cfg["thresholds"]["vol_crush"]["atm_iv_change_pct_max"] = -1.0
    cfg["thresholds"]["pinning"]["pin_band_ratio_min"] = 1.1
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
    assert "gap_open" not in daily["context_modifiers"]
    assert "matched_tags" not in daily


def test_missing_wall_fields_does_not_match_pinning():
    mod = _load_module()
    root = _case_dir()
    data_root = root / "data"
    out_root = root / "cold"
    date_str = "20260311"
    _make_day_files(data_root, date_str, rows=120, include_feature_label=True, include_walls=False, with_prev_day=True)

    cfg = _default_cfg()
    cfg["thresholds"]["trend_day"]["abs_ret_threshold"] = 1.0
    cfg["thresholds"]["balance_day"]["net_return_cap"] = 0.0001
    cfg["thresholds"]["high_vol_open"]["open_rv_1m_threshold"] = 1.0
    cfg["thresholds"]["vol_crush"]["atm_iv_change_pct_max"] = -1.0
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
    assert "pinning" not in daily["context_modifiers"]
    assert "matched_tags" not in daily


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


def test_low_quality_blocks_primary_classification():
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
    cfg_path = root / "cfg_blocked.json"
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
        ]
    )
    assert rc == 0
    daily = json.loads((out_root / "daily" / date_str / "manifest.json").read_text(encoding="utf-8"))
    assert daily["primary_day_type"] == "INCOMPLETE_SOURCE"
    assert daily["context_modifiers"] == []
    assert daily["quality"]["classification_blocked"] is True


def test_published_day_fast_fails_on_rerun_and_by_regime_stays_aligned():
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
    assert mod.run_cli(argv) == 1

    reg = out_root / "by_regime" / first["primary_day_type"] / date_str / "manifest.json"
    assert reg.exists()
    reg_payload = json.loads(reg.read_text(encoding="utf-8"))
    assert reg_payload["source_files"] == first["source_files"]
    assert reg_payload["primary_day_type"] == first["primary_day_type"]
    assert "context_modifiers" in first
    assert "close_profile" in first
    assert "primary_tag" not in first
    assert "legacy_primary_tag" not in first


def test_existing_by_regime_target_fails_before_any_publish() -> None:
    mod = _load_module()
    root = _case_dir()
    data_root = root / "data"
    out_root = root / "cold"
    date_str = "20260311"
    _make_day_files(data_root, date_str, rows=160, include_feature_label=True, include_walls=True, with_prev_day=True)

    cfg = _default_cfg()
    cfg_path = root / "cfg_regime_conflict.json"
    _write_cfg(cfg_path, cfg)
    for regime in [*cfg["primary_priority"], "INCOMPLETE_SOURCE"]:
        conflict_dir = out_root / "by_regime" / regime / date_str
        conflict_dir.mkdir(parents=True, exist_ok=True)
        (conflict_dir / "manifest.json").write_text("{}", encoding="utf-8")

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

    assert rc == 1
    assert not (out_root / "daily" / date_str / "manifest.json").exists()
    assert not (out_root / "reports" / f"{date_str}_quality.json").exists()


def test_existing_report_target_fails_before_any_publish() -> None:
    mod = _load_module()
    root = _case_dir()
    data_root = root / "data"
    out_root = root / "cold"
    date_str = "20260311"
    _make_day_files(data_root, date_str, rows=160, include_feature_label=True, include_walls=True, with_prev_day=True)

    cfg = _default_cfg()
    cfg_path = root / "cfg_report_conflict.json"
    _write_cfg(cfg_path, cfg)
    final_report = out_root / "reports" / f"{date_str}_quality.json"
    final_report.parent.mkdir(parents=True, exist_ok=True)
    final_report.write_text("{}", encoding="utf-8")

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

    assert rc == 1
    assert not (out_root / "daily" / date_str / "manifest.json").exists()
    assert not any((out_root / "by_regime").glob(f"*/{date_str}/manifest.json"))


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


def test_manifest_uses_frozen_snapshot_paths_and_remains_sync_after_source_mutation():
    archive_mod = _load_module()
    sync_mod = _load_sync_module()
    root = _case_dir()
    data_root = root / "data"
    out_root = root / "cold"
    date_str = "20260311"
    _make_day_files(data_root, date_str, rows=120, include_feature_label=True, include_walls=True, with_prev_day=True)

    cfg = _default_cfg()
    cfg_path = root / "cfg_snapshot.json"
    _write_cfg(cfg_path, cfg)

    rc = archive_mod.run_cli(
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

    manifest_path = out_root / "daily" / date_str / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_paths = [Path(item["path"]) for item in manifest["source_files"]]
    frozen_root = out_root / "daily" / date_str / "sources"
    assert source_paths
    assert all(path.exists() for path in source_paths)
    assert all(path.is_relative_to(frozen_root) for path in source_paths)

    # Mutate upstream live source after archive snapshot is written.
    (data_root / "mtf_iv" / f"mtf_iv_series_{date_str}.jsonl").write_text(
        '{"ok": true}\n{"post_archive": true}\n',
        encoding="utf-8",
    )

    result = sync_mod.check_manifest_sync(manifest_path)
    assert result["ok"] is True
    assert result["mismatches"] == []


def test_corrupt_required_raw_fails_without_visible_publish() -> None:
    mod = _load_module()
    root = _case_dir()
    data_root = root / "data"
    out_root = root / "cold"
    date_str = "20260311"
    _make_day_files(data_root, date_str, rows=120, include_feature_label=True, include_walls=True, with_prev_day=True)
    (data_root / "research/raw" / f"raw_{date_str}.parquet").write_bytes(b"PAR1")

    cfg = _default_cfg()
    cfg_path = root / "cfg_corrupt.json"
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
    assert rc == 1
    assert not (out_root / "daily" / date_str / "manifest.json").exists()
    assert not any((out_root / "by_regime").glob(f"*/{date_str}/manifest.json"))
    assert not (out_root / "reports" / f"{date_str}_quality.json").exists()
