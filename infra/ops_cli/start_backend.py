from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from .common import ensure_dir, repo_root


def _run_powershell(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )


def _backend_pids() -> list[int]:
    proc = _run_powershell(
        (
            "$ErrorActionPreference='Stop'; "
            "$rows = Get-CimInstance Win32_Process | "
            "Where-Object { "
            "$_.Name -like 'python*' -and "
            "$_.CommandLine -like '*uvicorn*' -and "
            "$_.CommandLine -like '*main:app*' "
            "}; "
            "$rows | ForEach-Object { $_.ProcessId }"
        )
    )
    if proc.returncode != 0:
        return []
    out = proc.stdout or ""
    pids: list[int] = []
    for raw in out.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            pids.append(int(raw))
        except ValueError:
            continue
    return pids


def _graceful_stop_existing_backend(timeout_sec: float) -> tuple[bool, list[int]]:
    current = _backend_pids()
    if not current:
        return True, []
    for pid in current:
        _run_powershell(f"Stop-Process -Id {pid} -ErrorAction SilentlyContinue")
    deadline = time.time() + max(0.1, timeout_sec)
    while time.time() < deadline:
        remaining = _backend_pids()
        if not remaining:
            return True, []
        time.sleep(0.2)
    remaining = _backend_pids()
    for pid in remaining:
        _run_powershell(f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue")
    return False, _backend_pids()


def _resolve_log_path(repo: Path, log_file: str) -> Path:
    path = Path(log_file)
    return path if path.is_absolute() else repo / path


def _resolve_python_executable(repo: Path) -> Path:
    venv_python = repo / ".venv/Scripts/python.exe"
    if venv_python.exists():
        return venv_python
    return Path(sys.executable)


def _preflight_check_python(python_exec: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [str(python_exec), "-c", "import uvicorn"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, ""
    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()
    msg = stderr or stdout or "uvicorn import failed"
    return False, msg


def _build_env(hotfix_active_options: bool, hotfix_min_volume: int) -> tuple[dict[str, str], str, int]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    boot_mode = "strict"
    hotfix_volume = max(1, int(hotfix_min_volume))
    if hotfix_active_options:
        env["FLOW_ACTIVE_MIN_VOLUME"] = str(hotfix_volume)
        boot_mode = "strict+active-options-hotfix"
    return env, boot_mode, hotfix_volume


def run_start_backend(args: argparse.Namespace) -> int:
    if os.name != "nt":
        print("[backend-start] Windows-only runtime contract violation: start-backend must run on Windows host.")
        return 1

    repo = repo_root()
    os.chdir(repo)

    if args.degraded:
        print("[backend-start] Degraded startup mode is forbidden. Use strict startup only.")
        return 1

    stopped, remaining = _graceful_stop_existing_backend(args.shutdown_timeout_sec)
    if not stopped:
        print(
            "[backend-start] Existing backend did not exit cleanly within "
            f"{args.shutdown_timeout_sec:.1f}s. Remaining pids={remaining}"
        )
        print("[backend-start] Strict mode refuses to launch a replacement over a live backend.")
        return 1

    log_path = _resolve_log_path(repo, args.log_file)
    ensure_dir(log_path.parent)
    python_exec = _resolve_python_executable(repo)
    ok, uvicorn_err = _preflight_check_python(python_exec)
    if not ok:
        print(
            "[backend-start] Missing runtime dependency in selected python: "
            f"{python_exec} cannot import uvicorn ({uvicorn_err})."
        )
        print("[backend-start] Use repo virtualenv: .venv\\Scripts\\python.exe manage.py start-backend")
        return 1

    env, boot_mode, hotfix_volume = _build_env(args.hotfix_active_options, args.hotfix_min_volume)
    uvicorn_cmd = [str(python_exec), "-m", "uvicorn", "main:app", "--host", args.bind_host, "--port", str(args.port)]
    printable_cmd = " ".join(shlex.quote(token) for token in uvicorn_cmd)

    if args.dry_run:
        print("[backend-start] DryRun=true")
        print(f"[backend-start] mode={boot_mode}")
        print(f"[backend-start] python={python_exec}")
        print(f"[backend-start] hotfix_active_options={args.hotfix_active_options}")
        if args.hotfix_active_options:
            print(f"[backend-start] flow_active_min_volume={hotfix_volume}")
        print(f"[backend-start] foreground={args.foreground}")
        print(f"[backend-start] log={log_path}")
        print(f"[backend-start] cmd={printable_cmd}")
        return 0

    with log_path.open("a", encoding="utf-8") as fp:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fp.write(f"[{stamp}] [BOOT] mode={boot_mode} host={args.bind_host} port={args.port}\n")

    if args.foreground:
        print(f"[backend-start] foreground=true mode={boot_mode} log={log_path}")
        print(f"[backend-start] hotfix_active_options={args.hotfix_active_options}")
        if args.hotfix_active_options:
            print(f"[backend-start] flow_active_min_volume={hotfix_volume}")
        print(f"[backend-start] running={printable_cmd}")

        with log_path.open("a", encoding="utf-8") as fp:
            proc = subprocess.Popen(
                uvicorn_cmd,
                cwd=repo,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                print(line, end="")
                fp.write(line)
            return proc.wait()

    with log_path.open("a", encoding="utf-8") as fp:
        proc = subprocess.Popen(
            uvicorn_cmd,
            cwd=repo,
            env=env,
            stdout=fp,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    print(f"[backend-start] started pid={proc.pid} mode={boot_mode} log={log_path}")
    return 0

def build_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("start-backend", help="Start backend service in strict mode")
    parser.add_argument("--bind-host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--degraded", action="store_true")
    parser.add_argument("--hotfix-active-options", action="store_true")
    parser.add_argument("--hotfix-min-volume", type=int, default=10)
    parser.add_argument("--log-file", default="logs/backend_runtime.current.log")
    parser.add_argument("--foreground", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--shutdown-timeout-sec", type=float, default=10.0)
    parser.set_defaults(func=run_start_backend)
