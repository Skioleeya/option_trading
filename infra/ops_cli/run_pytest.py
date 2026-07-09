from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from .common import ensure_dir, is_root_user, print_fail, repo_root


def _test_directory_write_access(path: Path) -> bool:
    probe = path / f".pytest-acl-probe-{os.getpid()}"
    try:
        probe.write_text("probe", encoding="utf-8")
        probe.unlink()
        return True
    except Exception:
        return False


def _assert_cache_dir_writable(path: Path) -> None:
    ensure_dir(path)
    if _test_directory_write_access(path):
        return
    raise PermissionError(f"Pytest cache directory '{path}' is not writable; run manage.py repair-pytest-cache-perms and retry.")


def run_pytest(args: argparse.Namespace) -> int:
    if is_root_user():
        print_fail("Refusing to run pytest as root. Use a normal user shell to avoid mixed-permission cache artifacts.")
        return 1

    repo = repo_root()
    cache_dir = repo / "tmp/pytest_cache"
    temp_dir = repo / "tmp/pytest_tmp"
    try:
        _assert_cache_dir_writable(cache_dir)
        _assert_cache_dir_writable(temp_dir)
    except Exception as exc:
        print_fail(str(exc))
        return 1

    env = os.environ.copy()
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    env.setdefault("HOME", str(Path.home()))
    env["TMP"] = str(temp_dir)
    env["TEMP"] = str(temp_dir)

    cmd = [sys.executable, "-m", "pytest", "-p", "pytest_asyncio.plugin", "-o", f"cache_dir={cache_dir}"]
    cmd.extend(args.pytest_args)

    print(f"[pytest-wrapper] cache_dir={cache_dir}")
    print("[pytest-wrapper] context=non-root")
    proc = subprocess.run(cmd, cwd=repo, env=env, check=False)
    return proc.returncode


def run_repair_pytest_cache_perms(args: argparse.Namespace) -> int:
    repo = repo_root()
    cache_dir = Path(args.cache_dir)
    if not cache_dir.is_absolute():
        cache_dir = repo / cache_dir
    ensure_dir(cache_dir)

    print(f"[pytest-cache-perms] target={cache_dir}")
    uid = os.getuid() if hasattr(os, "getuid") else -1
    gid = os.getgid() if hasattr(os, "getgid") else -1
    print(f"[pytest-cache-perms] uid={uid} gid={gid}")

    try:
        if hasattr(os, "chown") and uid >= 0 and gid >= 0:
            for root, dirs, files in os.walk(cache_dir):
                os.chown(root, uid, gid)
                os.chmod(root, 0o700)
                for name in dirs:
                    path = Path(root) / name
                    os.chown(path, uid, gid)
                    os.chmod(path, 0o700)
                for name in files:
                    path = Path(root) / name
                    os.chown(path, uid, gid)
                    os.chmod(path, 0o600)
        else:
            os.chmod(cache_dir, 0o700)
    except PermissionError as exc:
        print_fail(f"Unable to repair permissions for '{cache_dir}': {exc}")
        return 1

    if not _test_directory_write_access(cache_dir):
        print_fail(f"Permission repair did not restore write access for '{cache_dir}'.")
        return 1

    print("[pytest-cache-perms] write_probe=passed")
    return 0


def build_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    pytest_parser = subparsers.add_parser("run-pytest", help="Run pytest via repository wrapper")
    pytest_parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    pytest_parser.set_defaults(func=run_pytest)

    repair_parser = subparsers.add_parser("repair-pytest-cache-perms", help="Repair pytest cache permissions")
    repair_parser.add_argument("--cache-dir", default="tmp/pytest_cache")
    repair_parser.set_defaults(func=run_repair_pytest_cache_perms)
