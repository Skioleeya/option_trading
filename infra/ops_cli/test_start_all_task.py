from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from infra.ops_cli import start_all_task


def test_run_scheduled_start_all_shuts_down_non_trading_day_after_launch(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    calls: list[dict[str, Any]] = []

    class _Proc:
        returncode = 0

    def fake_run(cmd: list[str], cwd: Path, check: bool) -> _Proc:
        calls.append({"cmd": cmd, "cwd": cwd, "check": check})
        return _Proc()

    monkeypatch.setattr(start_all_task, "_is_trading_session", lambda date_iso: False)
    monkeypatch.setattr(start_all_task, "_resolve_python", lambda python_exe: r"E:\US.market\Option_v4\.venv\Scripts\python.exe")
    monkeypatch.setattr(start_all_task.subprocess, "run", fake_run)
    monkeypatch.setattr(start_all_task, "_shutdown_stack", lambda repo, **kwargs: 0)

    args = argparse.Namespace(
        python_exe="python",
        repo_root=str(tmp_path),
        date="2026-07-04",
        run_label="test",
        backend_port=8001,
        frontend_port=5173,
        redis_port=6380,
        start_attempts=3,
        retry_delay_sec=0.0,
    )

    exit_code = start_all_task.run_scheduled_start_all(args)

    assert exit_code == 0
    assert len(calls) == 1
    assert "non-trading-session detected after launch" in capsys.readouterr().out


def test_run_scheduled_start_all_launches_manage_start_all_and_keeps_trading_day(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    calls: list[dict[str, Any]] = []

    class _Proc:
        returncode = 0

    def fake_run(cmd: list[str], cwd: Path, check: bool) -> _Proc:
        calls.append({"cmd": cmd, "cwd": cwd, "check": check})
        return _Proc()

    monkeypatch.setattr(start_all_task, "_is_trading_session", lambda date_iso: True)
    monkeypatch.setattr(start_all_task, "_resolve_python", lambda python_exe: r"E:\US.market\Option_v4\.venv\Scripts\python.exe")
    monkeypatch.setattr(start_all_task.subprocess, "run", fake_run)

    args = argparse.Namespace(
        python_exe="python",
        repo_root=str(tmp_path),
        date="2026-07-09",
        run_label="test",
        backend_port=8001,
        frontend_port=5173,
        redis_port=6380,
        start_attempts=3,
        retry_delay_sec=0.0,
    )

    exit_code = start_all_task.run_scheduled_start_all(args)

    assert exit_code == 0
    assert len(calls) == 1
    assert calls[0]["cmd"][1:] == [str(tmp_path / "manage.py"), "start-all"]
    assert calls[0]["cwd"] == tmp_path
    stdout = capsys.readouterr().out
    assert "launch:" in stdout
    assert "attempt=1/3" in stdout
    assert "trading-session confirmed" in stdout


def test_run_scheduled_start_all_retries_trading_day_failure_then_success(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    calls: list[dict[str, Any]] = []
    returncodes = [1, 0]

    class _Proc:
        def __init__(self, returncode: int) -> None:
            self.returncode = returncode

    def fake_run(cmd: list[str], cwd: Path, check: bool) -> _Proc:
        calls.append({"cmd": cmd, "cwd": cwd, "check": check})
        return _Proc(returncodes.pop(0))

    monkeypatch.setattr(start_all_task, "_is_trading_session", lambda date_iso: True)
    monkeypatch.setattr(
        start_all_task,
        "_resolve_python",
        lambda python_exe: r"E:\US.market\Option_v4\.venv\Scripts\python.exe",
    )
    monkeypatch.setattr(start_all_task.subprocess, "run", fake_run)
    monkeypatch.setattr(start_all_task.time, "sleep", lambda _seconds: None)

    args = argparse.Namespace(
        python_exe="python",
        repo_root=str(tmp_path),
        date="2026-07-10",
        run_label="test",
        backend_port=8001,
        frontend_port=5173,
        redis_port=6380,
        start_attempts=3,
        retry_delay_sec=0.0,
    )

    exit_code = start_all_task.run_scheduled_start_all(args)

    assert exit_code == 0
    assert len(calls) == 2
    stdout = capsys.readouterr().out
    assert "attempt=1/3" in stdout
    assert "retrying in 0.0s" in stdout
    assert "attempt=2/3" in stdout
    assert "trading-session confirmed" in stdout


def test_register_start_all_task_generates_weekday_preopen_command(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(start_all_task, "_resolve_python", lambda python_exe: r"E:\US.market\Option_v4\.venv\Scripts\python.exe")
    monkeypatch.setattr(start_all_task, "getuser", lambda: "Lenovo")

    args = argparse.Namespace(
        python_exe="python",
        repo_root=str(tmp_path),
        task_name="OptionV4-StartAll-PreOpen",
        user="",
        start_time="09:25",
        output_dir=str(tmp_path / "out"),
        start_attempts=3,
        retry_delay_sec=60.0,
        apply=False,
    )

    exit_code = start_all_task.run_register_start_all_task(args)

    preview = tmp_path / "out" / "run_start_all_preopen.cmd"
    text = preview.read_text(encoding="utf-8")
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert "run-scheduled-start-all" in text
    assert "--repo-root" in text
    assert "--start-attempts 3" in text
    assert "--retry-delay-sec 60.0" in text
    assert "09:25" in stdout
    assert "RetryPolicy" in stdout
    assert "MON,TUE,WED,THU,FRI" in stdout
