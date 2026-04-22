from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path


def make_stage_root(*, out_root: Path, date_str: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    stage_root = out_root / ".staging" / f"{date_str}-{os.getpid()}-{stamp}"
    stage_root.mkdir(parents=True, exist_ok=False)
    return stage_root


def stage_daily_dir(*, stage_root: Path, date_str: str) -> Path:
    path = stage_root / "daily" / date_str
    path.mkdir(parents=True, exist_ok=False)
    return path


def stage_report_path(*, stage_root: Path, date_str: str) -> Path:
    path = stage_root / "reports" / f"{date_str}_quality.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def stage_regime_dir(*, stage_root: Path, date_str: str, primary_day_type: str) -> Path:
    path = stage_root / "by_regime" / primary_day_type / date_str
    path.mkdir(parents=True, exist_ok=False)
    return path


def write_stage_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def publish_stage_tree(*, staged: Path, final: Path) -> None:
    final.parent.mkdir(parents=True, exist_ok=True)
    if final.exists():
        raise FileExistsError(f"final publish target already exists: {final}")
    staged.rename(final)


def publish_stage_file(*, staged: Path, final: Path) -> None:
    final.parent.mkdir(parents=True, exist_ok=True)
    if final.exists():
        raise FileExistsError(f"final publish target already exists: {final}")
    staged.rename(final)


def cleanup_stage_root(stage_root: Path) -> None:
    shutil.rmtree(stage_root, ignore_errors=True)
