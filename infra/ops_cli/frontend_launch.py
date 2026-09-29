"""Frontend (Vite strict preview) launcher for the start-all flow."""

from __future__ import annotations

import argparse
import ipaddress
import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from urllib.request import Request, urlopen

from .common import (
    ensure_dir,
    is_listening,
    kill_processes_on_port,
    read_tail_lines,
    run_powershell,
)
from .log_layout import SERVICE_FRONTEND, allocate_run_log_path


def kill_existing_vite(ui_dir: Path) -> None:
    marker = str(ui_dir).replace("\\", "\\\\")
    script = (
        "$rows = Get-CimInstance Win32_Process | Where-Object { "
        "$_.CommandLine -like '*vite*' -and $_.CommandLine -like '*"
        + marker
        + "*' }; "
        "$rows | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    run_powershell(script)


def resolve_backend_origin(bind_host: str, backend_port: int) -> str:
    host = "127.0.0.1" if bind_host in {"0.0.0.0", "::"} else bind_host
    raw = host.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    try:
        addr = ipaddress.ip_address(raw)
        host = f"[{raw}]" if addr.version == 6 else raw
    except ValueError:
        host = raw
    return f"http://{host}:{backend_port}"


def _frontend_ready(port: int) -> bool:
    req = Request(f"http://127.0.0.1:{port}", method="GET")
    try:
        with urlopen(req, timeout=2) as resp:  # nosec - local readiness probe
            return 200 <= resp.status < 500
    except Exception:
        return False


def _wait_frontend_ready(port: int, timeout_sec: int) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if is_listening(port) and _frontend_ready(port):
            return True
        time.sleep(0.5)
    return is_listening(port) and _frontend_ready(port)


def _validate_frontend_env(env: dict[str, str]) -> None:
    legacy_api = env.get("VITE_L4_API_BASE", "").strip()
    legacy_ws = env.get("VITE_L4_WS_URL", "").strip()
    if legacy_api or legacy_ws:
        raise RuntimeError(
            "Legacy frontend env vars are forbidden in strict mode: "
            "unset VITE_L4_API_BASE and VITE_L4_WS_URL, use VITE_BACKEND_ORIGIN only."
        )


def start_frontend(repo: Path, args: argparse.Namespace, step: Callable[[str], None]) -> None:
    ui_dir = repo / "l4_ui"
    if not ui_dir.exists():
        raise FileNotFoundError(f"Frontend directory not found: {ui_dir}")

    if is_listening(args.frontend_port):
        step(f"Frontend port {args.frontend_port} is busy, forcing restart to apply strict env.")
        kill_existing_vite(ui_dir)
        if is_listening(args.frontend_port):
            killed = kill_processes_on_port(args.frontend_port)
            if killed:
                step(f"Stopped existing frontend listener(s) on port {args.frontend_port}: pids={killed}")
        time.sleep(0.8)
        if is_listening(args.frontend_port):
            raise RuntimeError(
                f"Frontend port {args.frontend_port} remains occupied after Vite cleanup; "
                "stop the conflicting process and retry."
            )

    frontend_log = allocate_run_log_path(repo, SERVICE_FRONTEND, log_root=args.log_root)
    ensure_dir(frontend_log.parent)
    step(f"Frontend log -> {frontend_log}")

    kill_existing_vite(ui_dir)

    env = os.environ.copy()
    _validate_frontend_env(env)
    backend_origin = resolve_backend_origin(args.bind_host, args.backend_port)
    env["VITE_BACKEND_ORIGIN"] = backend_origin

    cmd = [
        "node",
        "./scripts/preview-strict.mjs",
        "--host",
        "0.0.0.0",
        "--port",
        str(args.frontend_port),
        "--strictPort",
    ]
    step(f"Starting frontend via node scripts/preview-strict.mjs (VITE_BACKEND_ORIGIN={backend_origin}) ...")
    with frontend_log.open("a", encoding="utf-8") as fp:
        proc = subprocess.Popen(
            cmd,
            cwd=ui_dir,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=fp,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    step(f"Frontend launcher pid={proc.pid}")

    if not _wait_frontend_ready(args.frontend_port, args.frontend_ready_timeout_sec):
        if frontend_log.exists():
            step("Frontend log tail:")
            print("\n".join(read_tail_lines(frontend_log, 40)))
        raise RuntimeError(
            f"Frontend did not become HTTP-ready on port {args.frontend_port} within {args.frontend_ready_timeout_sec}s."
        )
    step(f"Frontend is HTTP-ready on port {args.frontend_port}.")
