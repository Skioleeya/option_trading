from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from infra.ops_cli import redis_preflight
from infra.ops_cli import start_all


class _FakeProcess:
    pid = 4242


def _args() -> argparse.Namespace:
    return argparse.Namespace(
        frontend_port=5173,
        frontend_log="logs/frontend_runtime.current.log",
        frontend_ready_timeout_sec=1,
        backend_port=8001,
        bind_host="0.0.0.0",
    )


def test_start_frontend_detaches_stdin_and_sets_backend_origin(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path
    ui_dir = repo / "l4_ui"
    ui_dir.mkdir()

    calls: list[dict[str, Any]] = []

    def fake_popen(*args: Any, **kwargs: Any) -> _FakeProcess:
        calls.append({"args": args, "kwargs": kwargs})
        return _FakeProcess()

    states = iter([False, True])
    monkeypatch.setattr(start_all, "_is_listening", lambda port: next(states))
    monkeypatch.setattr(start_all, "_kill_existing_vite", lambda _ui_dir: None)
    monkeypatch.setattr(start_all, "_validate_frontend_env", lambda env: None)
    monkeypatch.setattr(start_all.subprocess, "Popen", fake_popen)

    start_all._start_frontend(repo, _args())

    assert len(calls) == 1
    popen_kwargs = calls[0]["kwargs"]
    assert popen_kwargs["cwd"] == ui_dir
    assert popen_kwargs["stdin"] is subprocess.DEVNULL
    assert popen_kwargs["start_new_session"] is True
    assert popen_kwargs["env"]["VITE_BACKEND_ORIGIN"] == "http://127.0.0.1:8001"


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
