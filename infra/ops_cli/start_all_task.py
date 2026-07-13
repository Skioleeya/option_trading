from __future__ import annotations

import argparse
import os
import socket
import subprocess
import time
from getpass import getuser
from pathlib import Path

from .common import ensure_dir, now_in_timezone, repo_root, shell_join
from . import start_all, start_backend


def _resolve_python(python_exe: str) -> str:
    if python_exe == "python":
        return str((repo_root() / ".venv" / "Scripts" / "python.exe").resolve())
    return python_exe


def _resolve_repo_root(candidate: str) -> Path:
    if candidate:
        return Path(candidate).resolve()
    return repo_root()


def _today_et_iso() -> str:
    return now_in_timezone("America/New_York").strftime("%Y-%m-%d")


def _is_trading_session(date_iso: str) -> bool:
    import exchange_calendars as xc

    return bool(xc.get_calendar("XNYS").is_session(date_iso))


def _task_command(repo: Path, args: argparse.Namespace) -> list[str]:
    return [
        _resolve_python(args.python_exe),
        str(repo / "manage.py"),
        "run-scheduled-start-all",
        "--python-exe",
        args.python_exe,
        "--repo-root",
        str(repo),
        "--run-label",
        "schtasks",
        "--start-attempts",
        str(args.start_attempts),
        "--retry-delay-sec",
        str(args.retry_delay_sec),
    ]


def _run_powershell(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )


def _stop_frontend(repo: Path, frontend_port: int) -> list[int]:
    ui_dir = repo / "l4_ui"
    start_all._kill_existing_vite(ui_dir)
    killed = start_all._kill_processes_on_port(frontend_port)
    return killed


def _stop_redis(redis_port: int) -> list[int]:
    try:
        with socket.create_connection(("127.0.0.1", redis_port), timeout=1.5) as sock:
            sock.sendall(b"*2\r\n$8\r\nSHUTDOWN\r\n$6\r\nNOSAVE\r\n")
    except OSError:
        pass

    if not start_all._is_listening(redis_port):
        return []

    killed: list[int] = []
    for pid in start_all._listening_pids(redis_port):
        proc = _run_powershell(f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue")
        if proc.returncode == 0:
            killed.append(pid)
    return killed


def _shutdown_stack(repo: Path, *, backend_port: int, frontend_port: int, redis_port: int) -> int:
    backend_ok, backend_remaining = start_backend._graceful_stop_existing_backend(10.0)
    frontend_killed = _stop_frontend(repo, frontend_port)
    redis_killed = _stop_redis(redis_port)

    print(
        "[StartAllTask][shutdown] backend_ok={} backend_remaining={} frontend_killed={} redis_killed={}".format(
            backend_ok,
            backend_remaining,
            frontend_killed,
            redis_killed,
        )
    )
    return 0 if backend_ok else 1


def run_scheduled_start_all(args: argparse.Namespace) -> int:
    repo = _resolve_repo_root(args.repo_root)
    python_exe = _resolve_python(args.python_exe)
    date_iso = args.date.strip() or _today_et_iso()
    attempts = max(1, int(args.start_attempts))
    retry_delay_sec = max(0.0, float(args.retry_delay_sec))

    cmd = [python_exe, str(repo / "manage.py"), "start-all"]
    last_exit = 1
    for attempt in range(1, attempts + 1):
        print(
            f"[StartAllTask][{args.run_label}] launch: "
            f"date={date_iso} attempt={attempt}/{attempts} cmd={shell_join(cmd)}"
        )
        proc = subprocess.run(cmd, cwd=repo, check=False)
        last_exit = int(proc.returncode)

        if not _is_trading_session(date_iso):
            print(
                f"[StartAllTask][{args.run_label}] non-trading-session detected after launch attempt: "
                f"date={date_iso}; start-all-exit={last_exit}; shutting stack down."
            )
            stop_code = _shutdown_stack(
                repo,
                backend_port=args.backend_port,
                frontend_port=args.frontend_port,
                redis_port=args.redis_port,
            )
            print(f"[StartAllTask][{args.run_label}] done: exit={stop_code}")
            return stop_code

        if last_exit == 0:
            print(f"[StartAllTask][{args.run_label}] trading-session confirmed: date={date_iso}; stack remains up.")
            print(f"[StartAllTask][{args.run_label}] done: exit=0")
            return 0

        if attempt < attempts:
            print(
                f"[StartAllTask][{args.run_label}] start-all failed: "
                f"exit={last_exit}; retrying in {retry_delay_sec:.1f}s."
            )
            time.sleep(retry_delay_sec)

    print(f"[StartAllTask][{args.run_label}] done: exit={last_exit}")
    return last_exit


def run_register_start_all_task(args: argparse.Namespace) -> int:
    if os.name != "nt":
        print(
            "[StartAllTask] Windows-only runtime contract violation: "
            "register-start-all-task must run on Windows host."
        )
        return 1

    repo = _resolve_repo_root(args.repo_root)
    task_name = args.task_name.strip() or "OptionV4-StartAll-PreOpen"
    out_dir = Path(args.output_dir).resolve()
    ensure_dir(out_dir)

    preview_cmd = out_dir / "run_start_all_preopen.cmd"
    command = _task_command(repo, args)
    preview_cmd.write_text(
        f"@echo off\ncd /d {shell_join([str(repo)])}\n{shell_join(command)}\n",
        encoding="utf-8",
    )

    user = args.user.strip() or getuser()
    schtasks_cmd = [
        "schtasks",
        "/Create",
        "/TN",
        task_name,
        "/TR",
        str(preview_cmd),
        "/SC",
        "WEEKLY",
        "/D",
        "MON,TUE,WED,THU,FRI",
        "/ST",
        args.start_time,
        "/RU",
        user,
        "/F",
    ]

    print("[StartAllTask] Preview command generated:")
    print(f"- {preview_cmd}")
    print(f"- TaskName: {task_name}")
    print(f"- User: {user}")
    print(f"- StartTime: {args.start_time}")
    print(f"- RetryPolicy: start-all attempts={args.start_attempts} retry_delay_sec={args.retry_delay_sec}")
    print("- TradingDayGuard: start-all runs first; non-XNYS days trigger immediate shutdown")
    print(f"- schtasks: {shell_join(schtasks_cmd)}")

    if not args.apply:
        print("\n[StartAllTask] Apply=false. Use --apply to install/update the scheduled task.")
        return 0

    proc = subprocess.run(schtasks_cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        print("[StartAllTask] Failed to create/update scheduled task.")
        if proc.stdout.strip():
            print(proc.stdout.strip())
        if proc.stderr.strip():
            print(proc.stderr.strip())
        return 1

    print(f"[StartAllTask] Installed/updated task: {task_name}")
    return 0


def build_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    runner = subparsers.add_parser(
        "run-scheduled-start-all",
        help="Run start-all, then shut the stack down immediately if the current ET date is not an XNYS trading session",
    )
    runner.add_argument("--python-exe", default="python")
    runner.add_argument("--repo-root", default="")
    runner.add_argument("--date", default="")
    runner.add_argument("--run-label", default="manual")
    runner.add_argument("--backend-port", type=int, default=8001)
    runner.add_argument("--frontend-port", type=int, default=5173)
    runner.add_argument("--redis-port", type=int, default=6380)
    runner.add_argument("--start-attempts", type=int, default=3)
    runner.add_argument("--retry-delay-sec", type=float, default=60.0)
    runner.set_defaults(func=run_scheduled_start_all)

    scheduler = subparsers.add_parser(
        "register-start-all-task",
        help="Generate or install Windows scheduled task for pre-open start-all",
    )
    scheduler.add_argument("--python-exe", default="python")
    scheduler.add_argument("--repo-root", default="")
    scheduler.add_argument("--task-name", default="OptionV4-StartAll-PreOpen")
    scheduler.add_argument("--user", default="")
    scheduler.add_argument("--start-time", default="09:25")
    scheduler.add_argument("--output-dir", default="tmp/schtasks")
    scheduler.add_argument("--start-attempts", type=int, default=3)
    scheduler.add_argument("--retry-delay-sec", type=float, default=60.0)
    scheduler.add_argument("--apply", action="store_true")
    scheduler.set_defaults(func=run_register_start_all_task)
