"""Tests for the durable parquet write wrapper.

The wrapper exists because the native writer's ``ReplaceFileW`` swap failed
13/60 times on this host (probe evidence in ``durable_parquet_write`` docstring).
These tests pin the wrapper's own contract deterministically: staging goes to a
missing sibling path, the swap retries transient ``OSError``, the retry budget
is honoured, installation is idempotent (never self-wrapping), and staging is
cleaned up on failure.

Scratch directories follow the repo convention of ``tmp/<suite>/<uuid>``
(``tmp_path`` is unusable in this sandbox).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

import pytest

from shared.config import settings
from shared.services.l0_runtime import durable_parquet_write as dpw


class _FakeNativeModule:
    """Stand-in for the native ``l0_rust`` module."""

    def __init__(self, fail_times: int = 0) -> None:
        self.fail_times = fail_times
        self.writes: list[tuple[str, Any, Any]] = []

    def service_research_write_parquet_rows(self, path: str, rows: Any, schema: Any) -> None:
        if self.fail_times > 0:
            self.fail_times -= 1
            Path(path).write_bytes(b"partial")  # leaves a staging file behind
            raise OSError("native write failed")
        Path(path).write_bytes(b"parquet")
        self.writes.append((path, rows, schema))


@pytest.fixture()
def work_dir() -> Iterator[Path]:
    path = Path("tmp") / "durable_parquet_write_tests" / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    yield path


@pytest.fixture(autouse=True)
def _isolate_install_registry() -> Iterator[None]:
    """Keep the module-id registry from leaking between tests."""
    snapshot = set(dpw._INSTALLED_MODULE_IDS)
    yield
    dpw._INSTALLED_MODULE_IDS.clear()
    dpw._INSTALLED_MODULE_IDS.update(snapshot)


@pytest.fixture(autouse=True)
def _no_swap_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "parquet_swap_retry_delay_ms", 0)


def _staging_leftovers(root: Path) -> list[str]:
    return sorted(p.name for p in root.iterdir() if ".staging-" in p.name)


def test_staging_path_is_a_missing_sibling(work_dir: Path) -> None:
    target = work_dir / "day_20260924.parquet"
    target.write_bytes(b"existing")

    staging = dpw._staging_path(target)

    assert staging.parent == target.parent
    assert staging.name != target.name
    assert not staging.exists()


def test_swap_retries_transient_oserror(work_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    staging = work_dir / "staging.bin"
    target = work_dir / "target.bin"
    staging.write_bytes(b"new")
    target.write_bytes(b"old")

    real_replace = os.replace
    attempts = {"count": 0}

    def _flaky(src: Any, dst: Any) -> None:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise OSError(1175, "Unable to remove the file to be replaced")
        real_replace(src, dst)

    monkeypatch.setattr(dpw.os, "replace", _flaky)

    dpw._swap_with_retry(staging, target)

    assert attempts["count"] == 3
    assert target.read_bytes() == b"new"


def test_swap_raises_after_budget_exhausted(
    work_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "parquet_swap_max_attempts", 2)
    staging = work_dir / "staging.bin"
    target = work_dir / "target.bin"
    staging.write_bytes(b"new")

    attempts = {"count": 0}

    def _always_fails(src: Any, dst: Any) -> None:
        attempts["count"] += 1
        raise OSError(1175, "still stuck")

    monkeypatch.setattr(dpw.os, "replace", _always_fails)

    with pytest.raises(OSError, match="still stuck"):
        dpw._swap_with_retry(staging, target)

    assert attempts["count"] == 2


def test_install_is_idempotent_and_never_self_wraps(work_dir: Path) -> None:
    module = _FakeNativeModule()
    target = work_dir / "day.parquet"

    dpw.install_durable_parquet_write(module)
    wrapped_once = module.service_research_write_parquet_rows
    dpw.install_durable_parquet_write(module)

    assert module.service_research_write_parquet_rows is wrapped_once

    module.service_research_write_parquet_rows(str(target), [{"a": 1}], None)

    assert len(module.writes) == 1
    staged = Path(module.writes[0][0])
    assert staged.name != target.name
    assert target.read_bytes() == b"parquet"
    assert not staged.exists()


def test_staging_is_cleaned_up_when_native_write_fails(work_dir: Path) -> None:
    module = _FakeNativeModule(fail_times=1)
    dpw.install_durable_parquet_write(module)
    target = work_dir / "day.parquet"

    with pytest.raises(OSError, match="native write failed"):
        module.service_research_write_parquet_rows(str(target), [], None)

    assert _staging_leftovers(work_dir) == []
    assert not target.exists()
