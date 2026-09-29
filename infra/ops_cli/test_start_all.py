from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import pytest

from infra.ops_cli import redis_preflight
from infra.ops_cli import start_all


class _DeadChild:
    """A launcher handle whose process has already exited."""

    returncode = 3

    def poll(self) -> int:
        return self.returncode


class _LiveChild:
    returncode = None

    def poll(self) -> None:
        return None


def _backend_args() -> argparse.Namespace:
    return argparse.Namespace(
        bind_host="0.0.0.0",
        backend_port=8001,
        backend_ready_timeout_sec=30,
        backend_shutdown_timeout_sec=10.0,
        log_root="logs",
    )


def test_redis_preflight_rejects_unc_path(monkeypatch, tmp_path: Path) -> None:
    if os.name != "nt":
        pytest.skip("Windows contract test")
    conf = tmp_path / "redis.conf.local"
    conf.write_text("dir \\\\server\\redis\nappendonly yes\n", encoding="utf-8")
    monkeypatch.setattr(redis_preflight, "_filesystem_type", lambda path: "NTFS")
    monkeypatch.setattr(redis_preflight, "_is_fixed_drive", lambda path: True)

    with pytest.raises(RuntimeError, match="must not be UNC/network path"):
        redis_preflight.preflight_redis_runtime(tmp_path, conf)


def test_redis_preflight_rejects_non_ntfs(monkeypatch, tmp_path: Path) -> None:
    if os.name != "nt":
        pytest.skip("Windows contract test")
    conf = tmp_path / "redis.conf.local"
    conf.write_text("dir ./var/redis\nappendonly yes\n", encoding="utf-8")
    monkeypatch.setattr(redis_preflight, "_filesystem_type", lambda path: "ReFS")
    monkeypatch.setattr(redis_preflight, "_is_fixed_drive", lambda path: True)

    with pytest.raises(RuntimeError, match="must resolve to NTFS fixed drive"):
        redis_preflight.preflight_redis_runtime(tmp_path, conf)


def test_redis_preflight_rejects_large_aof(monkeypatch, tmp_path: Path) -> None:
    if os.name != "nt":
        pytest.skip("Windows contract test")
    conf = tmp_path / "redis.conf.local"
    conf.write_text("dir ./var/redis\nappendonly yes\n", encoding="utf-8")
    redis_dir = tmp_path / "var/redis/appendonlydir"
    redis_dir.mkdir(parents=True)
    (redis_dir / "appendonly.aof.manifest").write_text(
        "file appendonly.aof.1.base.rdb seq 1 type b\n"
        "file appendonly.aof.1.incr.aof seq 1 type i\n",
        encoding="utf-8",
    )
    (redis_dir / "appendonly.aof.1.base.rdb").write_bytes(b"b" * 8)
    (redis_dir / "appendonly.aof.1.incr.aof").write_bytes(b"i" * 5)
    monkeypatch.setattr(redis_preflight, "_filesystem_type", lambda path: "NTFS")
    monkeypatch.setattr(redis_preflight, "_is_fixed_drive", lambda path: True)

    with pytest.raises(RuntimeError, match="AOF total exceeds strict startup cap"):
        redis_preflight.preflight_redis_runtime(tmp_path, conf, aof_total_cap_bytes=12)


def test_redis_preflight_accepts_ntfs_fixed_drive(monkeypatch, tmp_path: Path) -> None:
    if os.name != "nt":
        pytest.skip("Windows contract test")
    conf = tmp_path / "redis.conf.local"
    conf.write_text("dir ./var/redis\nappendonly yes\n", encoding="utf-8")
    monkeypatch.setattr(redis_preflight, "_filesystem_type", lambda path: "NTFS")
    monkeypatch.setattr(redis_preflight, "_is_fixed_drive", lambda path: True)

    result = redis_preflight.preflight_redis_runtime(tmp_path, conf)

    assert result.data_dir == tmp_path / "var/redis"
    assert result.resolved_dir == tmp_path / "var/redis"
    assert result.fs_type == "NTFS"
    assert result.aof_total_bytes == 0


def test_default_redis_exe_points_to_program_files_memurai() -> None:
    assert start_all._default_redis_exe(Path("E:/US.market/Option_v4")) == Path(
        r"C:\Program Files\Memurai\memurai.exe"
    )


def test_verify_stack_rejects_listening_but_unhealthy_backend(monkeypatch) -> None:
    """An open port is not readiness: /health must be 200."""
    monkeypatch.setattr(start_all, "is_listening", lambda port: True)
    monkeypatch.setattr(start_all, "_backend_healthy", lambda bind_host, port: False)

    with pytest.raises(RuntimeError, match="Backend"):
        start_all._verify_stack("0.0.0.0", 6380, 8001, 5173)


def test_verify_stack_accepts_healthy_stack(monkeypatch) -> None:
    monkeypatch.setattr(start_all, "is_listening", lambda port: True)
    monkeypatch.setattr(start_all, "_backend_healthy", lambda bind_host, port: True)

    start_all._verify_stack("0.0.0.0", 6380, 8001, 5173)


def test_wait_backend_healthy_stops_early_when_child_exited(monkeypatch) -> None:
    """A dead backend can never become healthy: do not blind-wait the full timeout."""
    monkeypatch.setattr(start_all, "_backend_healthy", lambda bind_host, port: False)

    started = time.monotonic()
    ready = start_all._wait_backend_healthy("0.0.0.0", 8001, 30, _DeadChild())
    elapsed = time.monotonic() - started

    assert ready is False
    assert elapsed < 5.0, f"waited {elapsed:.1f}s instead of aborting on the dead child"


def test_wait_backend_healthy_still_waits_for_a_live_child(monkeypatch) -> None:
    """Early abort must key off process death, not merely an unhealthy /health."""
    monkeypatch.setattr(start_all, "_backend_healthy", lambda bind_host, port: False)

    started = time.monotonic()
    ready = start_all._wait_backend_healthy("0.0.0.0", 8001, 3, _LiveChild())
    elapsed = time.monotonic() - started

    assert ready is False
    assert elapsed >= 3.0


def test_start_backend_reports_early_exit_instead_of_blind_wait(monkeypatch, tmp_path: Path) -> None:
    def fake_run_start_backend(args, *, on_process_started=None):
        if on_process_started is not None:
            on_process_started(_DeadChild())
        return 0

    monkeypatch.setattr(start_all, "run_start_backend", fake_run_start_backend)
    monkeypatch.setattr(start_all, "_backend_healthy", lambda bind_host, port: False)

    with pytest.raises(RuntimeError, match="exited before becoming ready"):
        start_all._start_backend(tmp_path, _backend_args())
