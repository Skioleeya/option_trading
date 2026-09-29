from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

import pytest

from infra.ops_cli import frontend_launch


class _FakeProcess:
    pid = 4242


def _args() -> argparse.Namespace:
    return argparse.Namespace(
        frontend_port=5173,
        frontend_ready_timeout_sec=1,
        log_root="logs",
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

    monkeypatch.setattr(frontend_launch, "is_listening", lambda port: False)
    monkeypatch.setattr(frontend_launch, "_wait_frontend_ready", lambda port, timeout_sec: True)
    monkeypatch.setattr(frontend_launch, "kill_existing_vite", lambda _ui_dir: None)
    monkeypatch.setattr(frontend_launch, "_validate_frontend_env", lambda env: None)
    monkeypatch.setattr(frontend_launch.subprocess, "Popen", fake_popen)

    frontend_launch.start_frontend(repo, _args(), lambda _message: None)

    assert len(calls) == 1
    popen_kwargs = calls[0]["kwargs"]
    assert popen_kwargs["cwd"] == ui_dir
    assert popen_kwargs["stdin"] is subprocess.DEVNULL
    assert popen_kwargs["start_new_session"] is True
    assert popen_kwargs["env"]["VITE_BACKEND_ORIGIN"] == "http://127.0.0.1:8001"


def test_start_frontend_reports_through_the_injected_step(monkeypatch, tmp_path: Path) -> None:
    ui_dir = tmp_path / "l4_ui"
    ui_dir.mkdir()
    lines: list[str] = []

    monkeypatch.setattr(frontend_launch, "is_listening", lambda port: False)
    monkeypatch.setattr(frontend_launch, "_wait_frontend_ready", lambda port, timeout_sec: True)
    monkeypatch.setattr(frontend_launch, "kill_existing_vite", lambda _ui_dir: None)
    monkeypatch.setattr(frontend_launch, "_validate_frontend_env", lambda env: None)
    monkeypatch.setattr(frontend_launch.subprocess, "Popen", lambda *a, **k: _FakeProcess())

    frontend_launch.start_frontend(tmp_path, _args(), lines.append)

    assert any("HTTP-ready" in line for line in lines)


@pytest.mark.parametrize(
    ("bind_host", "expected"),
    [
        ("0.0.0.0", "http://127.0.0.1:8001"),
        ("127.0.0.1", "http://127.0.0.1:8001"),
        ("::", "http://127.0.0.1:8001"),
        ("::1", "http://[::1]:8001"),
        ("localhost", "http://localhost:8001"),
    ],
)
def test_resolve_backend_origin_normalizes_hosts(bind_host: str, expected: str) -> None:
    assert frontend_launch.resolve_backend_origin(bind_host, 8001) == expected


def test_validate_frontend_env_rejects_legacy_vars() -> None:
    with pytest.raises(RuntimeError, match="Legacy frontend env vars"):
        frontend_launch._validate_frontend_env({"VITE_L4_API_BASE": "http://x"})

    frontend_launch._validate_frontend_env({"VITE_BACKEND_ORIGIN": "http://127.0.0.1:8001"})
