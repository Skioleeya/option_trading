from __future__ import annotations

import datetime as dt
import fnmatch
import os
import re
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
