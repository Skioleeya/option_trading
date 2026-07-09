from __future__ import annotations

import argparse
import ipaddress
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.request import Request, urlopen

from .common import ensure_dir, repo_root
from .redis_preflight import describe_redis_preflight, preflight_redis_runtime
from .start_backend import run_start_backend

DEFAULT_REDIS_EXE = r"C:\Program Files\Memurai\memurai.exe"


def _step(message: str) -> None:
    print(f"[start-all] {message}")


def _run_powershell(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )


def _is_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.6)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _wait_listening(port: int, timeout_sec: int) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if _is_listening(port):
            return True
        time.sleep(0.5)
    return _is_listening(port)


def _test_redis_ready(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0) as sock:
            sock.sendall(b"*1\r\n$4\r\nPING\r\n")
            reply = sock.recv(128)
        return reply.startswith(b"+PONG")
    except OSError:
        return False


def _wait_redis_ready(port: int, timeout_sec: int) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if _test_redis_ready(port):
            return True
        time.sleep(1.0)
    return _test_redis_ready(port)


def _backend_healthy(bind_host: str, port: int) -> bool:
    host = "127.0.0.1" if bind_host == "0.0.0.0" else bind_host
    url = f"http://{host}:{port}/health"
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=2) as resp:  # nosec - local health probe
            return resp.status == 200
    except Exception:
        return False


def _wait_backend_healthy(bind_host: str, port: int, timeout_sec: int) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if _backend_healthy(bind_host, port):
            return True
        time.sleep(1.0)
    return _backend_healthy(bind_host, port)


def _resolve_abs_path(repo: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo / path


def _default_redis_exe(repo: Path) -> Path:
    return Path(DEFAULT_REDIS_EXE)


def _start_redis(repo: Path, args: argparse.Namespace) -> None:
    conf = repo / "infra/redis/redis.conf.local"
    if not conf.exists():
        raise FileNotFoundError(f"Redis config not found: {conf}")
    preflight = preflight_redis_runtime(repo, conf)
    _step(f"Redis preflight passed: {describe_redis_preflight(preflight)}")
    redis_exe = _resolve_abs_path(repo, args.redis_exe)
    if not redis_exe.exists():
        raise FileNotFoundError(
            "Redis executable not found. "
            f"Expected: {redis_exe}. "
            "Place the Windows Redis binary at the repo-fixed path or pass --redis-exe <abs-path>."
        )

    if _is_listening(args.redis_port):
        _step(f"Redis already listening at port {args.redis_port}, skip start.")
    else:
        redis_cmd = [str(redis_exe), str(conf)]
        redis_log = _resolve_abs_path(repo, args.redis_log)
        ensure_dir(preflight.resolved_dir)
        ensure_dir(redis_log.parent)
        _step(f"Starting Redis via {redis_exe} ...")
        with redis_log.open("a", encoding="utf-8") as fp:
            proc = subprocess.Popen(
                redis_cmd,
                cwd=repo,
                stdout=fp,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        _step(f"Redis launcher pid={proc.pid}")

        if not _wait_listening(args.redis_port, args.wait_timeout_sec):
            raise RuntimeError(f"Redis did not open port {args.redis_port} within {args.wait_timeout_sec}s.")
        _step(f"Redis is listening on port {args.redis_port}.")

    if not _wait_redis_ready(args.redis_port, args.redis_ready_timeout_sec):
        raise RuntimeError(
            "Redis did not become ready (PING) within "
            f"{args.redis_ready_timeout_sec}s. {describe_redis_preflight(preflight)}"
        )
    _step(f"Redis is ready (PING=PONG) on port {args.redis_port}.")


def _start_backend(repo: Path, args: argparse.Namespace) -> None:
    _step("Starting backend in strict mode ...")
    backend_args = argparse.Namespace(
        bind_host=args.bind_host,
        port=args.backend_port,
        degraded=False,
        hotfix_active_options=False,
        hotfix_min_volume=10,
        log_file=args.backend_log,
        foreground=False,
        dry_run=False,
        shutdown_timeout_sec=args.backend_shutdown_timeout_sec,
    )
    exit_code = run_start_backend(backend_args)
    if exit_code != 0:
        raise RuntimeError(f"Backend start failed with exit code {exit_code}")

    _step(f"Backend readiness gate: /health timeout={args.backend_ready_timeout_sec}s")
    if _wait_backend_healthy(args.bind_host, args.backend_port, args.backend_ready_timeout_sec):
        _step(f"Backend is healthy (/health=200) on port {args.backend_port}.")
        return

    log_path = _resolve_abs_path(repo, args.backend_log)
    if log_path.exists():
        _step("Backend log tail:")
        print("\n".join(log_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-40:]))
    raise RuntimeError(f"Backend strict mode failed (/health not ready within {args.backend_ready_timeout_sec}s).")


def _kill_existing_vite(ui_dir: Path) -> None:
    marker = str(ui_dir).replace("\\", "\\\\")
    script = (
        "$rows = Get-CimInstance Win32_Process | Where-Object { "
        "$_.CommandLine -like '*vite*' -and $_.CommandLine -like '*"
        + marker
        + "*' }; "
        "$rows | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    _run_powershell(script)


def _listening_pids(port: int) -> list[int]:
    proc = subprocess.run(
        ["cmd.exe", "/c", f"netstat -ano -p tcp | findstr LISTENING | findstr :{port}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return []
    pids: list[int] = []
    for raw in (proc.stdout or "").splitlines():
        parts = raw.split()
        if len(parts) < 5:
            continue
        local_addr = parts[1]
        if not local_addr.endswith(f":{port}"):
            continue
        try:
            pid = int(parts[-1])
        except ValueError:
            continue
        if pid not in pids:
            pids.append(pid)
    return pids


def _kill_processes_on_port(port: int) -> list[int]:
    killed: list[int] = []
    for pid in _listening_pids(port):
        proc = _run_powershell(f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue")
        if proc.returncode == 0 and pid not in _listening_pids(port):
            killed.append(pid)
    return killed


def _resolve_backend_origin(bind_host: str, backend_port: int) -> str:
    host = "127.0.0.1" if bind_host in {"0.0.0.0", "::"} else bind_host
    raw = host.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    try:
        addr = ipaddress.ip_address(raw)
        if addr.version == 6:
            host = f"[{raw}]"
        else:
            host = raw
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
        if _is_listening(port) and _frontend_ready(port):
            return True
        time.sleep(0.5)
    return _is_listening(port) and _frontend_ready(port)


def _validate_frontend_env(env: dict[str, str]) -> None:
    legacy_api = env.get("VITE_L4_API_BASE", "").strip()
    legacy_ws = env.get("VITE_L4_WS_URL", "").strip()
    if legacy_api or legacy_ws:
        raise RuntimeError(
            "Legacy frontend env vars are forbidden in strict mode: "
            "unset VITE_L4_API_BASE and VITE_L4_WS_URL, use VITE_BACKEND_ORIGIN only."
        )


def _start_frontend(repo: Path, args: argparse.Namespace) -> None:
    ui_dir = repo / "l4_ui"
    if not ui_dir.exists():
        raise FileNotFoundError(f"Frontend directory not found: {ui_dir}")

    if _is_listening(args.frontend_port):
        _step(f"Frontend port {args.frontend_port} is busy, forcing restart to apply strict env.")
        _kill_existing_vite(ui_dir)
        if _is_listening(args.frontend_port):
            killed = _kill_processes_on_port(args.frontend_port)
            if killed:
                _step(f"Stopped existing frontend listener(s) on port {args.frontend_port}: pids={killed}")
        time.sleep(0.8)
        if _is_listening(args.frontend_port):
            raise RuntimeError(
                f"Frontend port {args.frontend_port} remains occupied after Vite cleanup; "
                "stop the conflicting process and retry."
            )

    frontend_log_path = _resolve_abs_path(repo, args.frontend_log)
    ensure_dir(frontend_log_path.parent)

    _kill_existing_vite(ui_dir)

    env = os.environ.copy()
    _validate_frontend_env(env)
    backend_origin = _resolve_backend_origin(args.bind_host, args.backend_port)
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
    _step(f"Starting frontend via node scripts/preview-strict.mjs (VITE_BACKEND_ORIGIN={backend_origin}) ...")
    with frontend_log_path.open("a", encoding="utf-8") as fp:
        proc = subprocess.Popen(
            cmd,
            cwd=ui_dir,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=fp,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    _step(f"Frontend launcher pid={proc.pid}")

    if not _wait_frontend_ready(args.frontend_port, args.frontend_ready_timeout_sec):
        if frontend_log_path.exists():
            _step("Frontend log tail:")
            print("\n".join(frontend_log_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-40:]))
        raise RuntimeError(
            f"Frontend did not become HTTP-ready on port {args.frontend_port} within {args.frontend_ready_timeout_sec}s."
        )
    _step(f"Frontend is HTTP-ready on port {args.frontend_port}.")


def _verify_stack(redis_port: int, backend_port: int, frontend_port: int) -> None:
    rows = [
        ("Redis", redis_port, _is_listening(redis_port)),
        ("Backend", backend_port, _is_listening(backend_port)),
        ("Frontend", frontend_port, _is_listening(frontend_port)),
    ]

    print("\n[start-all] Verification summary:")
    print(f"{'Service':<10} {'Port':<8} {'Listening':<10}")
    for service, port, listening in rows:
        print(f"{service:<10} {port:<8} {str(listening):<10}")

    failed = [service for service, _, listening in rows if not listening]
    if failed:
        raise RuntimeError(f"Verification failed: not listening -> {', '.join(failed)}")


def run_start_all(args: argparse.Namespace) -> int:
    if os.name != "nt":
        raise RuntimeError("Windows-only runtime contract violation: start-all must run on Windows host.")

    repo = repo_root()
    os.chdir(repo)

    if args.verify_only:
        _step("VerifyOnly=true; skip startup and run verification only.")
        _verify_stack(args.redis_port, args.backend_port, args.frontend_port)
        return 0

    if args.no_degraded_retry:
        _step("NoDegradedRetry is deprecated; startup already enforces strict-only behavior.")

    _step(f"RepoRoot={repo}")
    _step("Startup order: Redis -> Backend(strict-only) -> Frontend")
    _step(
        "Readiness timeouts: "
        f"redis={args.redis_ready_timeout_sec}s backend={args.backend_ready_timeout_sec}s frontend={args.frontend_ready_timeout_sec}s"
    )

    _start_redis(repo, args)
    _start_backend(repo, args)
    _start_frontend(repo, args)
    _verify_stack(args.redis_port, args.backend_port, args.frontend_port)

    print()
    _step("All services are up.")
    _step(f"Frontend: http://localhost:{args.frontend_port}")
    _step(f"Backend:  http://localhost:{args.backend_port}")
    return 0


def build_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("start-all", help="Start Redis, backend, frontend")
    parser.add_argument("--bind-host", default="0.0.0.0")
    parser.add_argument("--redis-port", type=int, default=6380)
    parser.add_argument("--backend-port", type=int, default=8001)
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument("--wait-timeout-sec", type=int, default=25)
    parser.add_argument("--redis-ready-timeout-sec", type=int, default=120)
    parser.add_argument("--backend-ready-timeout-sec", type=int, default=180)
    parser.add_argument("--frontend-ready-timeout-sec", type=int, default=60)
    parser.add_argument("--backend-shutdown-timeout-sec", type=float, default=10.0)
    parser.add_argument("--backend-log", default="logs/backend_runtime.current.log")
    parser.add_argument("--frontend-log", default="logs/frontend_runtime.current.log")
    parser.add_argument("--redis-log", default="logs/redis_runtime.current.log")
    parser.add_argument(
        "--redis-exe",
        default=DEFAULT_REDIS_EXE,
        help="Redis executable path; defaults to the repo-fixed Windows binary.",
    )
    parser.add_argument("--no-degraded-retry", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.set_defaults(func=run_start_all)
