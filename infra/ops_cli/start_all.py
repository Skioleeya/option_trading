from __future__ import annotations

import argparse
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.request import Request, urlopen

from .common import ensure_dir, is_listening, read_tail_lines, repo_root, resolve_abs_path
from .frontend_launch import start_frontend
from .log_layout import LOG_ROOT_DEFAULT, SERVICE_BACKEND, SERVICE_REDIS, allocate_run_log_path
from .redis_preflight import describe_redis_preflight, preflight_redis_runtime
from .start_backend import run_start_backend

DEFAULT_REDIS_EXE = r"C:\Program Files\Memurai\memurai.exe"


def _step(message: str) -> None:
    print(f"[start-all] {message}")


def _wait_listening(port: int, timeout_sec: int) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if is_listening(port):
            return True
        time.sleep(0.5)
    return is_listening(port)


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


def _wait_backend_healthy(
    bind_host: str,
    port: int,
    timeout_sec: int,
    child: subprocess.Popen | None = None,
) -> bool:
    """Poll /health, but stop early once the child process is gone.

    A dead backend can never become healthy; waiting out the full timeout only hides the
    failure. `child` is the exact process handle returned by the launcher, so this needs no
    process-name guessing.
    """
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if _backend_healthy(bind_host, port):
            return True
        if child is not None and child.poll() is not None:
            return False
        time.sleep(1.0)
    return _backend_healthy(bind_host, port)


def _default_redis_exe(repo: Path) -> Path:
    return Path(DEFAULT_REDIS_EXE)


def _start_redis(repo: Path, args: argparse.Namespace) -> None:
    conf = repo / "infra/redis/redis.conf.local"
    if not conf.exists():
        raise FileNotFoundError(f"Redis config not found: {conf}")
    preflight = preflight_redis_runtime(repo, conf)
    _step(f"Redis preflight passed: {describe_redis_preflight(preflight)}")
    redis_exe = resolve_abs_path(repo, args.redis_exe)
    if not redis_exe.exists():
        raise FileNotFoundError(
            "Redis executable not found. "
            f"Expected: {redis_exe}. "
            "Place the Windows Redis binary at the repo-fixed path or pass --redis-exe <abs-path>."
        )

    port_was_listening = is_listening(args.redis_port)
    if port_was_listening:
        if _test_redis_ready(args.redis_port):
            _step(f"Redis already listening and ready at port {args.redis_port}, skip start.")
        else:
            raise RuntimeError(
                f"Port {args.redis_port} is occupied but not responding to PING. "
                "Stop the conflicting process and retry."
            )
    else:
        redis_cmd = [str(redis_exe), str(conf)]
        # Claimed here, not up front: a skipped Redis must not leave an empty run log behind.
        redis_log = allocate_run_log_path(repo, SERVICE_REDIS, log_root=args.log_root)
        ensure_dir(preflight.resolved_dir)
        ensure_dir(redis_log.parent)
        _step(f"Redis log -> {redis_log}")
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
            redis_log_tail = "\n".join(read_tail_lines(redis_log, 20))
            raise RuntimeError(
                f"Redis did not open port {args.redis_port} within {args.wait_timeout_sec}s.\n"
                f"Check if port is in use or see log tail:\n{redis_log_tail}"
            )
        _step(f"Redis is listening on port {args.redis_port}.")

    if not _wait_redis_ready(args.redis_port, args.redis_ready_timeout_sec):
        raise RuntimeError(
            "Redis did not become ready (PING) within "
            f"{args.redis_ready_timeout_sec}s. {describe_redis_preflight(preflight)}"
        )
    _step(f"Redis is ready (PING=PONG) on port {args.redis_port}.")


def _start_backend(repo: Path, args: argparse.Namespace) -> None:
    _step("Starting backend in strict mode ...")
    backend_log = allocate_run_log_path(repo, SERVICE_BACKEND, log_root=args.log_root)
    _step(f"Backend log -> {backend_log}")
    backend_args = argparse.Namespace(
        bind_host=args.bind_host,
        port=args.backend_port,
        degraded=False,
        hotfix_active_options=False,
        hotfix_min_volume=10,
        log_file=str(backend_log),
        foreground=False,
        dry_run=False,
        shutdown_timeout_sec=args.backend_shutdown_timeout_sec,
    )
    started: list[subprocess.Popen] = []
    exit_code = run_start_backend(backend_args, on_process_started=started.append)
    if exit_code != 0:
        raise RuntimeError(f"Backend start failed with exit code {exit_code}")

    child = started[0] if started else None
    _step(f"Backend readiness gate: /health timeout={args.backend_ready_timeout_sec}s")
    if _wait_backend_healthy(args.bind_host, args.backend_port, args.backend_ready_timeout_sec, child):
        _step(f"Backend is healthy (/health=200) on port {args.backend_port}.")
        return

    if backend_log.exists():
        _step("Backend log tail:")
        print("\n".join(read_tail_lines(backend_log, 40)))
    if child is not None and child.poll() is not None:
        raise RuntimeError(
            "Backend strict mode exited before becoming ready "
            f"(exit_code={child.returncode}); see {backend_log}."
        )
    raise RuntimeError(f"Backend strict mode failed (/health not ready within {args.backend_ready_timeout_sec}s).")


def _verify_stack(bind_host: str, redis_port: int, backend_port: int, frontend_port: int) -> None:
    # Backend readiness means /health == 200, not merely an open port: the
    # runtime can be listening while research persistence has hard-stopped it
    # and every endpoint is degraded.
    backend_ready = is_listening(backend_port) and _backend_healthy(bind_host, backend_port)
    rows = [
        ("Redis", redis_port, is_listening(redis_port)),
        ("Backend", backend_port, backend_ready),
        ("Frontend", frontend_port, is_listening(frontend_port)),
    ]

    print("\n[start-all] Verification summary:")
    print(f"{'Service':<10} {'Port':<8} {'Ready':<10}")
    for service, port, ready in rows:
        print(f"{service:<10} {port:<8} {str(ready):<10}")

    failed = [service for service, _, ready in rows if not ready]
    if failed:
        raise RuntimeError(
            f"Verification failed: not ready -> {', '.join(failed)}. "
            "Backend readiness requires GET /health == 200, not just an open port."
        )


def run_start_all(args: argparse.Namespace) -> int:
    if os.name != "nt":
        raise RuntimeError("Windows-only runtime contract violation: start-all must run on Windows host.")

    repo = repo_root()
    os.chdir(repo)

    if args.verify_only:
        _step("VerifyOnly=true; skip startup and run verification only.")
        _verify_stack(args.bind_host, args.redis_port, args.backend_port, args.frontend_port)
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
    start_frontend(repo, args, _step)
    _verify_stack(args.bind_host, args.redis_port, args.backend_port, args.frontend_port)

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
    parser.add_argument(
        "--log-root",
        default=LOG_ROOT_DEFAULT,
        help=(
            "Log root; each start claims logs/<YYYY-MM-DD>/<service>/run-<NNN>.log "
            "underneath it."
        ),
    )
    parser.add_argument(
        "--redis-exe",
        default=DEFAULT_REDIS_EXE,
        help="Redis executable path; defaults to the repo-fixed Windows binary.",
    )
    parser.add_argument("--no-degraded-retry", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.set_defaults(func=run_start_all)
