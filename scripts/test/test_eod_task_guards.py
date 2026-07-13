from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import uuid
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


WAIT_MOD = _load_module("scripts/diagnostics/wait_for_eod_sources_settle.py", "wait_for_eod_sources_settle")
SYNC_MOD = _load_module("scripts/diagnostics/check_eod_manifest_sync.py", "check_eod_manifest_sync")


def test_windows_eod_wrapper_uses_repo_virtualenv_python():
    script = Path("scripts/ops/run_eod_bucket.ps1").read_text(encoding="utf-8")

    assert ".venv\\Scripts\\python.exe" in script
    assert "Get-Command python" not in script
    assert '"--python-exe", $pythonExe' in script
    assert '"--python-exe", "python"' not in script


def _sig(role: str, exists: bool, size_bytes: int = -1, last_write_ns: int = -1, required: bool = True):
    return WAIT_MOD.SourceSignature(
        role=role,
        path=f"/tmp/{role}",
        required=required,
        exists=exists,
        size_bytes=size_bytes,
        last_write_ns=last_write_ns,
    )


def test_wait_for_settle_respects_stable_window_after_last_change():
    snapshots = iter(
        [
            (_sig("research_canonical", False), _sig("mtf_iv_series", False, required=False)),
            (_sig("research_canonical", True, 10, 100), _sig("mtf_iv_series", False, required=False)),
            (_sig("research_canonical", True, 10, 100), _sig("mtf_iv_series", False, required=False)),
            (_sig("research_canonical", True, 20, 200), _sig("mtf_iv_series", False, required=False)),
            (_sig("research_canonical", True, 20, 200), _sig("mtf_iv_series", False, required=False)),
            (_sig("research_canonical", True, 20, 200), _sig("mtf_iv_series", False, required=False)),
            (_sig("research_canonical", True, 20, 200), _sig("mtf_iv_series", False, required=False)),
        ]
    )
    times = iter([0.0, 0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0])

    result = WAIT_MOD.wait_for_settle(
        capture_fn=lambda: next(snapshots),
        stable_window_seconds=15.0,
        timeout_seconds=60.0,
        poll_seconds=5.0,
        monotonic_fn=lambda: next(times),
        time_ns_fn=lambda: 0,
        sleep_fn=lambda _: None,
    )

    assert result.stable is True
    assert result.elapsed_seconds == 30.0
    assert result.snapshot[0].size_bytes == 20


def test_wait_parser_defaults_cover_late_post_close_writes():
    args = WAIT_MOD.build_parser().parse_args(["--date", "20260327"])

    assert args.stable_window_seconds == 300.0
    assert args.timeout_seconds == 2400.0
    assert args.poll_seconds == 15.0


def test_wait_for_settle_ignores_optional_source_churn():
    snapshots = iter(
        [
            (_sig("research_canonical", True, 20, 100), _sig("mtf_iv_series", False, required=False)),
            (_sig("research_canonical", True, 20, 100), _sig("mtf_iv_series", True, 1, 101, required=False)),
            (_sig("research_canonical", True, 20, 100), _sig("mtf_iv_series", True, 2, 102, required=False)),
            (_sig("research_canonical", True, 20, 100), _sig("mtf_iv_series", True, 3, 103, required=False)),
            (_sig("research_canonical", True, 20, 100), _sig("mtf_iv_series", True, 4, 104, required=False)),
        ]
    )
    times = iter([0.0, 0.0, 5.0, 10.0, 15.0, 20.0])

    result = WAIT_MOD.wait_for_settle(
        capture_fn=lambda: next(snapshots),
        stable_window_seconds=15.0,
        timeout_seconds=60.0,
        poll_seconds=5.0,
        monotonic_fn=lambda: next(times),
        time_ns_fn=lambda: 0,
        sleep_fn=lambda _: None,
    )

    assert result.stable is True
    assert result.elapsed_seconds == 15.0


def test_wait_for_settle_returns_immediately_for_historical_stable_snapshot():
    snapshot = (_sig("research_canonical", True, 10, 1_000_000_000),)

    result = WAIT_MOD.wait_for_settle(
        capture_fn=lambda: snapshot,
        stable_window_seconds=300.0,
        timeout_seconds=600.0,
        poll_seconds=15.0,
        monotonic_fn=iter([0.0, 0.0]).__next__,
        time_ns_fn=lambda: 1_000_000_000 + 400_000_000_000,
        sleep_fn=lambda _: None,
    )

    assert result.stable is True
    assert result.elapsed_seconds == 0.0


def test_check_manifest_sync_reports_row_hash_and_size_mismatch():
    base_dir = Path("tmp/pytest_cache/test_eod_task_guards")
    base_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = base_dir / f"case_{uuid.uuid4().hex[:8]}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    parquet_path = tmp_path / "raw_20260327.parquet"
    pq.write_table(pa.table({"spot": [1.0, 2.0], "data_timestamp": ["a", "b"]}), parquet_path)

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "source_files": [
                    {
                        "role": "research_raw",
                        "path": str(parquet_path),
                        "size_bytes": 1,
                        "sha256": "bad",
                    }
                ],
                "metrics": {"rows": {"research_raw": 99}},
            }
        ),
        encoding="utf-8",
    )

    result = SYNC_MOD.check_manifest_sync(manifest_path)

    reasons = {item["reason"] for item in result["mismatches"]}
    assert result["ok"] is False
    assert {"size_mismatch", "hash_mismatch", "row_mismatch"} <= reasons


def test_runner_continues_archive_when_settle_guard_times_out():
    base_dir = Path("tmp/pytest_cache/test_eod_task_guards")
    base_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = base_dir / f"runner_case_{uuid.uuid4().hex[:8]}"
    tmp_path.mkdir(parents=True, exist_ok=True)

    date_str = "20260326"
    data_root = tmp_path / "data"
    out_root = tmp_path / "cold"

    for folder, filename in (
        ("atm_decay", f"atm_series_{date_str}.jsonl"),
        ("mtf_iv", f"mtf_iv_series_{date_str}.jsonl"),
        ("wall_migration", f"wall_series_{date_str}.jsonl"),
    ):
        path = data_root / folder / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"ok": true}\n', encoding="utf-8")

    cmd = [
        sys.executable,
        "manage.py",
        "run-eod-bucket",
        "--date",
        date_str,
        "--data-root",
        str(data_root),
        "--out-root",
        str(out_root),
        "--settle-stable-window-seconds",
        "1",
        "--settle-timeout-seconds",
        "0.2",
        "--settle-poll-seconds",
        "0.1",
        "--max-attempts",
        "1",
        "--run-label",
        "pytest",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    assert result.returncode == 2
    output = f"{result.stdout}\n{result.stderr}"
    assert "settle_guard=timeout" in output
    assert "archive=start" in output

    manifest_path = out_root / "daily" / date_str / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["primary_day_type"] == "INCOMPLETE_SOURCE"
    assert manifest["quality"]["classification_blocked"] is True
