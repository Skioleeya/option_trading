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
        raise RuntimeError(f"failed to load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _case_dir() -> Path:
    path = Path("tmp/pytest_cache/eod_archive_guards") / uuid.uuid4().hex[:10]
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_parquet(path: Path, cols: dict[str, list]):
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(cols), path)


def test_wait_for_settle_returns_stable_when_snapshot_stops_changing():
    mod = _load_module("wait_for_eod_sources_settle", "scripts/diagnostics/wait_for_eod_sources_settle.py")
    snapshots = [
        (
            mod.SourceSignature("research_raw", "a", True, True, 10, 1),
            mod.SourceSignature("research_feature", "b", True, True, 10, 1),
            mod.SourceSignature("research_label", "c", True, True, 10, 1),
        ),
        (
            mod.SourceSignature("research_raw", "a", True, True, 12, 2),
            mod.SourceSignature("research_feature", "b", True, True, 10, 1),
            mod.SourceSignature("research_label", "c", True, True, 10, 1),
        ),
        (
            mod.SourceSignature("research_raw", "a", True, True, 12, 2),
            mod.SourceSignature("research_feature", "b", True, True, 10, 1),
            mod.SourceSignature("research_label", "c", True, True, 10, 1),
        ),
        (
            mod.SourceSignature("research_raw", "a", True, True, 12, 2),
            mod.SourceSignature("research_feature", "b", True, True, 10, 1),
            mod.SourceSignature("research_label", "c", True, True, 10, 1),
        ),
    ]
    clock = {"now": 0.0, "capture_count": 0}

    def capture():
        idx = min(clock["capture_count"], len(snapshots) - 1)
        clock["capture_count"] += 1
        return snapshots[idx]

    def monotonic():
        return clock["now"]

    def sleep(seconds: float):
        clock["now"] += seconds

    result = mod.wait_for_settle(
        capture_fn=capture,
        stable_window_seconds=0.5,
        timeout_seconds=5.0,
        poll_seconds=0.5,
        monotonic_fn=monotonic,
        time_ns_fn=lambda: int(clock["now"] * 1_000_000_000),
        sleep_fn=sleep,
    )
    assert result.stable is True
    assert result.snapshot == snapshots[-1]


def test_check_manifest_sync_detects_stale_size_and_hash():
    mod = _load_module("check_eod_manifest_sync", "scripts/diagnostics/check_eod_manifest_sync.py")
    root = _case_dir()
    source = root / "data" / "research" / "raw" / "raw_20260326.parquet"
    _write_parquet(
        source,
        {
            "data_timestamp": ["2026-03-26T16:00:00-04:00", "2026-03-26T16:01:00-04:00"],
            "spot": [100.0, 101.0],
        },
    )
    manifest = root / "cold" / "daily" / "20260326" / "manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "source_files": [
                    {
                        "role": "research_raw",
                        "path": source.as_posix(),
                        "size_bytes": 1,
                        "sha256": "deadbeef",
                    }
                ],
                "metrics": {"rows": {"research_raw": 1}},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = mod.check_manifest_sync(manifest)
    reasons = {item["reason"] for item in result["mismatches"]}
    assert result["ok"] is False
    assert {"size_mismatch", "hash_mismatch", "row_mismatch"} <= reasons
