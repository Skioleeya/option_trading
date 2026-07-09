from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, Path(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_parquet(path: Path, cols: dict[str, list]):
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(cols), path)


def _case_dir() -> Path:
    path = Path("tmp/pytest_cache/eod_bucket_guard_cases") / uuid.uuid4().hex[:10]
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_day(root: Path, date_str: str):
    ts = ["2026-03-26T16:00:00-04:00", "2026-03-26T16:01:00-04:00"]
    _write_parquet(
        root / "research/raw" / f"raw_{date_str}.parquet",
        {"data_timestamp": ts, "spot": [1.0, 2.0], "atm_iv": [0.2, 0.3], "net_gex": [1.0, 2.0]},
    )
    _write_parquet(
        root / "research/feature" / f"feature_{date_str}.parquet",
        {"data_timestamp": ts, "spot": [1.0, 2.0]},
    )
    _write_parquet(
        root / "research/label" / f"label_{date_str}.parquet",
        {"data_timestamp": ts, "fwd_ret_1m": [0.0, 0.0]},
    )
    for folder, filename in (
        ("atm_decay", f"atm_series_{date_str}.jsonl"),
        ("mtf_iv", f"mtf_iv_series_{date_str}.jsonl"),
        ("wall_migration", f"wall_series_{date_str}.jsonl"),
    ):
        path = root / folder / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"ok": true}\n', encoding="utf-8")


def _write_manifest(out_root: Path, root: Path, date_str: str):
    manifest_path = out_root / "daily" / date_str / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_files": [],
        "metrics": {"rows": {}},
    }
    for role, rel_path in (
        ("research_raw", f"research/raw/raw_{date_str}.parquet"),
        ("research_feature", f"research/feature/feature_{date_str}.parquet"),
        ("research_label", f"research/label/label_{date_str}.parquet"),
        ("atm_series", f"atm_decay/atm_series_{date_str}.jsonl"),
        ("mtf_iv_series", f"mtf_iv/mtf_iv_series_{date_str}.jsonl"),
        ("wall_series", f"wall_migration/wall_series_{date_str}.jsonl"),
    ):
        path = root / rel_path
        entry = {"role": role, "path": path.as_posix(), "size_bytes": path.stat().st_size}
        if path.suffix == ".parquet":
            entry["sha256"] = _load_module("sync_mod_hash", "scripts/diagnostics/check_eod_manifest_sync.py")._sha256(path)
            payload["metrics"]["rows"][role] = pq.read_table(path).num_rows
        else:
            entry["sha256"] = _load_module("sync_mod_hash", "scripts/diagnostics/check_eod_manifest_sync.py")._sha256(path)
        payload["source_files"].append(entry)
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


def test_manifest_sync_detects_stale_metadata():
    mod = _load_module("sync_mod", "scripts/diagnostics/check_eod_manifest_sync.py")
    case_root = _case_dir()
    root = case_root / "data"
    out_root = case_root / "cold"
    date_str = "20260326"
    _write_day(root, date_str)
    manifest_path = _write_manifest(out_root, root, date_str)

    target = root / "mtf_iv" / f"mtf_iv_series_{date_str}.jsonl"
    target.write_text('{"ok": true}\n{"more": true}\n', encoding="utf-8")

    result = mod.check_manifest_sync(manifest_path)
    assert result["ok"] is False
    assert any(item["role"] == "mtf_iv_series" for item in result["mismatches"])


def test_manifest_sync_passes_for_matching_manifest():
    mod = _load_module("sync_mod_ok", "scripts/diagnostics/check_eod_manifest_sync.py")
    case_root = _case_dir()
    root = case_root / "data"
    out_root = case_root / "cold"
    date_str = "20260326"
    _write_day(root, date_str)
    manifest_path = _write_manifest(out_root, root, date_str)

    result = mod.check_manifest_sync(manifest_path)
    assert result["ok"] is True
    assert result["mismatches"] == []


def test_wait_for_settle_stabilizes_after_snapshot_changes():
    mod = _load_module("settle_mod", "scripts/diagnostics/wait_for_eod_sources_settle.py")
    sig = mod.SourceSignature
    snapshots = [
        (sig("research_canonical", "canonical", True, True, 10, 100),),
        (sig("research_canonical", "canonical", True, True, 10, 100),),
        (sig("research_canonical", "canonical", True, True, 11, 101),),
        (sig("research_canonical", "canonical", True, True, 11, 101),),
        (sig("research_canonical", "canonical", True, True, 11, 101),),
    ]
    idx = {"value": 0}
    clock = {"value": 0.0}

    def capture():
        current = snapshots[min(idx["value"], len(snapshots) - 1)]
        return current

    def monotonic():
        return clock["value"]

    def sleep_fn(seconds: float):
        clock["value"] += seconds
        idx["value"] += 1

    result = mod.wait_for_settle(
        capture_fn=capture,
        stable_window_seconds=0.2,
        timeout_seconds=1.0,
        poll_seconds=0.1,
        monotonic_fn=monotonic,
        time_ns_fn=lambda: int(clock["value"] * 1_000_000_000),
        sleep_fn=sleep_fn,
    )
    assert result.stable is True
    assert result.snapshot[0].size_bytes == 11


def test_wait_for_settle_times_out_when_required_sources_missing():
    mod = _load_module("settle_mod_timeout", "scripts/diagnostics/wait_for_eod_sources_settle.py")
    sig = mod.SourceSignature
    snapshot = (sig("research_canonical", "canonical", True, False, -1, -1),)
    clock = {"value": 0.0}

    def capture():
        return snapshot

    def monotonic():
        return clock["value"]

    def sleep_fn(seconds: float):
        clock["value"] += seconds

    result = mod.wait_for_settle(
        capture_fn=capture,
        stable_window_seconds=0.2,
        timeout_seconds=0.5,
        poll_seconds=0.1,
        monotonic_fn=monotonic,
        sleep_fn=sleep_fn,
    )
    assert result.stable is False
