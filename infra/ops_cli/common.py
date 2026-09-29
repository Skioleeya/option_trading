from __future__ import annotations

import datetime as dt
import fnmatch
import os
import re
import socket
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def normalize_repo_path(path: str) -> str:
    value = path.replace("\\", "/").strip()
    if value.startswith("./"):
        value = value[2:]
    return value


def read_text_utf8(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


TAIL_READ_MAX_BYTES = 256 * 1024


def read_tail_lines(path: Path, max_lines: int, *, max_bytes: int = TAIL_READ_MAX_BYTES) -> list[str]:
    """Return the trailing lines of ``path``, reading at most ``max_bytes`` from the end.

    Runtime logs grow unbounded (the backend log reached 3.36 GB / 27.9M lines),
    so ``read_text().splitlines()[-N:]`` on a failure path costs minutes and
    gigabytes of RSS. This reads only the trailing byte window.

    Contract: at most ``max_lines`` complete lines are returned, and fewer are
    returned when ``max_bytes`` covers less than that many lines. Bounded work is
    the priority here — a diagnostic tail must never be able to stall startup.
    """
    if max_lines <= 0:
        raise ValueError("max_lines must be positive")
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    if not path.exists():
        return []
    with path.open("rb") as fp:
        fp.seek(0, os.SEEK_END)
        size = fp.tell()
        start = max(0, size - max_bytes)
        fp.seek(start)
        chunk = fp.read()
    lines = chunk.decode("utf-8", errors="ignore").splitlines()
    if start > 0 and lines:
        # The first entry is a partial fragment of the byte window.
        lines = lines[1:]
    return lines[-max_lines:]


def is_test_like_path(path: str) -> bool:
    norm = normalize_repo_path(path)
    if not norm:
        return False
    if "/tests/" in norm or "/test/" in norm or "/__tests__/" in norm:
        return True

    leaf = Path(norm).name.lower()
    if not leaf:
        return False
    if leaf == "conftest.py":
        return True
    if re.match(r"^test_.*\.(py|ts|tsx|js|jsx)$", leaf):
        return True
    if re.match(r"^.*_test\.(py|ts|tsx|js|jsx)$", leaf):
        return True
    if re.match(r"^.*\.(spec|test)\.(ts|tsx|js|jsx)$", leaf):
        return True
    return False


def path_glob_match(path: str, glob: str) -> bool:
    return fnmatch.fnmatch(normalize_repo_path(path), normalize_repo_path(glob))


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def run_powershell(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )


def is_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.6)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def resolve_abs_path(repo: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo / path


def listening_pids(port: int) -> list[int]:
    """PIDs of processes listening on ``port`` (TCP), parsed from ``netstat``."""
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


def kill_processes_on_port(port: int) -> list[int]:
    """Force-stop every listener on ``port``; returns only the PIDs that actually died."""
    killed: list[int] = []
    for pid in listening_pids(port):
        proc = run_powershell(f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue")
        if proc.returncode == 0 and pid not in listening_pids(port):
            killed.append(pid)
    return killed


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def now_in_timezone(timezone_name: str) -> dt.datetime:
    try:
        from zoneinfo import ZoneInfo

        return dt.datetime.now(ZoneInfo(timezone_name))
    except Exception as exc:  # pragma: no cover - environment specific
        raise ValueError(f"Invalid timezone: {timezone_name}") from exc


def shell_join(argv: list[str]) -> str:
    escaped: list[str] = []
    for token in argv:
        if re.search(r"\s", token):
            escaped.append(f'"{token}"')
        else:
            escaped.append(token)
    return " ".join(escaped)


def print_fail(message: str) -> None:
    print(f"[FAIL] {message}")


def print_ok(message: str) -> None:
    print(f"[OK]   {message}")


def print_warn(message: str) -> None:
    print(f"[WARN] {message}", file=sys.stderr)


def is_root_user() -> bool:
    geteuid = getattr(os, "geteuid", None)
    if callable(geteuid):
        return geteuid() == 0
    return False
