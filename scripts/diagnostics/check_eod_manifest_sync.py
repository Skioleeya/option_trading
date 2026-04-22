#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_path(out_root: Path, date_str: str) -> Path:
    return out_root / "daily" / date_str / "manifest.json"


def _rows_for_parquet(path: Path) -> int:
    return int(pq.read_table(path).num_rows)


def check_manifest_sync(manifest_path: Path) -> dict[str, Any]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    mismatches: list[dict[str, Any]] = []
    row_metrics = dict(payload.get("metrics", {}).get("rows", {}))
    for source in payload.get("source_files", []):
        rel_path = str(source["path"])
        path = Path(rel_path)
        if not path.exists():
            mismatches.append({"role": source["role"], "reason": "missing", "path": rel_path})
            continue
        actual_size = int(path.stat().st_size)
        actual_hash = _sha256(path)
        if int(source["size_bytes"]) != actual_size:
            mismatches.append(
                {
                    "role": source["role"],
                    "reason": "size_mismatch",
                    "path": rel_path,
                    "manifest_size": int(source["size_bytes"]),
                    "actual_size": actual_size,
                }
            )
        if str(source["sha256"]) != actual_hash:
            mismatches.append(
                {
                    "role": source["role"],
                    "reason": "hash_mismatch",
                    "path": rel_path,
                    "manifest_sha256": str(source["sha256"]),
                    "actual_sha256": actual_hash,
                }
            )
        if path.suffix == ".parquet" and source["role"] in row_metrics:
            actual_rows = _rows_for_parquet(path)
            expected_rows = int(row_metrics[source["role"]])
            if expected_rows != actual_rows:
                mismatches.append(
                    {
                        "role": source["role"],
                        "reason": "row_mismatch",
                        "path": rel_path,
                        "manifest_rows": expected_rows,
                        "actual_rows": actual_rows,
                    }
                )
    return {
        "manifest_path": manifest_path.as_posix(),
        "ok": not mismatches,
        "mismatches": mismatches,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify EOD manifest metadata matches current source files.")
    parser.add_argument("--date", required=True, help="Trade date in YYYYMMDD.")
    parser.add_argument("--out-root", default="data/cold", help="Cold storage root (default: data/cold).")
    return parser


def run_cli(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = check_manifest_sync(_manifest_path(Path(args.out_root), str(args.date)))
    print(f"[EODSync] {json.dumps(result, ensure_ascii=True)}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(run_cli())
