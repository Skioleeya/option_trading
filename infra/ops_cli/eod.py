from __future__ import annotations

import argparse
import os
import subprocess
import sys
from getpass import getuser
from pathlib import Path

from .common import ensure_dir, repo_root, shell_join


def _resolve_python(python_exe: str) -> str:
    return sys.executable if python_exe == "python" else python_exe


def _resolve_repo_root(candidate: str) -> Path:
    if candidate:
        path = Path(candidate)
        return path.resolve()
    return repo_root()


def _today_et_yyyymmdd(python_exe: str) -> str:
    code = "from datetime import datetime;from zoneinfo import ZoneInfo;print(datetime.now(ZoneInfo('America/New_York')).strftime('%Y%m%d'))"
    proc = subprocess.run([python_exe, "-c", code], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError("Failed to determine ET trade date for EOD bucket run.")
    value = proc.stdout.strip()
    if not value:
        raise RuntimeError("Failed to determine ET trade date for EOD bucket run.")
    return value


def run_eod_bucket(args: argparse.Namespace) -> int:
    python_exe = _resolve_python(args.python_exe)
    repo = _resolve_repo_root(args.repo_root)

    wait_script = repo / "scripts/diagnostics/wait_for_eod_sources_settle.py"
    verify_script = repo / "scripts/diagnostics/check_eod_manifest_sync.py"
    archive_script = repo / "scripts/diagnostics/eod_bucket_archive.py"
    if not wait_script.exists():
        raise FileNotFoundError(f"Settle guard script not found: {wait_script}")
    if not verify_script.exists():
        raise FileNotFoundError(f"Manifest sync script not found: {verify_script}")
    if not archive_script.exists():
        raise FileNotFoundError(f"Archive script not found: {archive_script}")

    os.chdir(repo)
    date_value = args.date.strip() if args.date else _today_et_yyyymmdd(python_exe)

    final_exit = 1
    for attempt in range(1, args.max_attempts + 1):
        print(f"[EODBucketRunner][{args.run_label}] attempt={attempt} date={date_value} settle_guard=start")
        settle_cmd = [
            python_exe,
            str(wait_script),
            "--date",
            date_value,
            "--root",
            args.data_root,
            "--stable-window-seconds",
            str(args.settle_stable_window_seconds),
            "--timeout-seconds",
            str(args.settle_timeout_seconds),
            "--poll-seconds",
            str(args.settle_poll_seconds),
        ]
        settle_exit = subprocess.run(settle_cmd, check=False).returncode
        if settle_exit == 0:
            print(f"[EODBucketRunner][{args.run_label}] attempt={attempt} settle_guard=passed")
        elif settle_exit == 2:
            print(
                f"[EODBucketRunner][{args.run_label}] attempt={attempt} "
                "settle_guard=timeout exit=2; continuing archive for INCOMPLETE_SOURCE evidence."
            )
        else:
            print(f"[EODBucketRunner][{args.run_label}] attempt={attempt} settle_guard=error exit={settle_exit}")
            return settle_exit

        print(f"[EODBucketRunner][{args.run_label}] attempt={attempt} archive=start")
        archive_cmd = [
            python_exe,
            str(archive_script),
            "--date",
            date_value,
            "--config",
            args.config_path,
            "--root",
            args.data_root,
            "--out-root",
            args.out_root,
            "--strict-quality",
        ]
        archive_exit = subprocess.run(archive_cmd, check=False).returncode
        print(f"[EODBucketRunner][{args.run_label}] attempt={attempt} archive=done exit={archive_exit}")

        print(f"[EODBucketRunner][{args.run_label}] attempt={attempt} sync_check=start")
        sync_cmd = [python_exe, str(verify_script), "--date", date_value, "--out-root", args.out_root]
        sync_exit = subprocess.run(sync_cmd, check=False).returncode
        print(f"[EODBucketRunner][{args.run_label}] attempt={attempt} sync_check=done exit={sync_exit}")

        if sync_exit == 0 and archive_exit in (0, 2):
            return archive_exit

        final_exit = archive_exit if archive_exit != 0 else sync_exit
        print(
            f"[EODBucketRunner][{args.run_label}] attempt={attempt} "
            f"incomplete (archive_exit={archive_exit} sync_exit={sync_exit}); retrying if attempts remain."
        )

    return final_exit


def _build_task_command(repo: Path, args: argparse.Namespace) -> list[str]:
    exec_cmd = [
        _resolve_python(args.python_exe),
        str(repo / "manage.py"),
        "run-eod-bucket",
        "--python-exe",
        args.python_exe,
        "--repo-root",
        str(repo),
        "--config-path",
        args.config_path,
        "--data-root",
        args.data_root,
        "--out-root",
        args.out_root,
        "--run-label",
        "schtasks",
        "--settle-stable-window-seconds",
        str(args.settle_stable_window_seconds),
        "--settle-timeout-seconds",
        str(args.settle_timeout_seconds),
        "--settle-poll-seconds",
        str(args.settle_poll_seconds),
        "--max-attempts",
        str(args.max_attempts),
    ]
    return exec_cmd


def run_register_eod_bucket_task(args: argparse.Namespace) -> int:
    if os.name != "nt":
        print("[EODBucketTask] Windows-only runtime contract violation: register-eod-bucket-task must run on Windows host.")
        return 1

    repo = _resolve_repo_root(args.repo_root)
    task_name = args.task_name.strip() or "OptionV4-EOD-Bucket"

    out_dir = Path(args.output_dir).resolve()
    ensure_dir(out_dir)
    preview_cmd = out_dir / "run_eod_bucket.cmd"
    command = _build_task_command(repo, args)
    preview_cmd.write_text(f"@echo off\n{shell_join(command)}\n", encoding="utf-8")

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

    print("[EODBucketTask] Preview command generated:")
    print(f"- {preview_cmd}")
    print(f"- TaskName: {task_name}")
    print(f"- User: {user}")
    print(f"- StartTime: {args.start_time}")
    print(f"- schtasks: {shell_join(schtasks_cmd)}")

    if not args.apply:
        print("\n[EODBucketTask] Apply=false. Use --apply to install/update the scheduled task.")
        return 0

    proc = subprocess.run(schtasks_cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        print("[EODBucketTask] Failed to create/update scheduled task.")
        if proc.stdout.strip():
            print(proc.stdout.strip())
        if proc.stderr.strip():
            print(proc.stderr.strip())
        return 1

    print(f"[EODBucketTask] Installed/updated task: {task_name}")
    return 0


def build_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    runner = subparsers.add_parser("run-eod-bucket", help="Run EOD archive runner")
    runner.add_argument("--python-exe", default="python")
    runner.add_argument("--repo-root", default="")
    runner.add_argument("--date", default="")
    runner.add_argument("--config-path", default="scripts/diagnostics/config/eod_bucket_thresholds.json")
    runner.add_argument("--data-root", default="data")
    runner.add_argument("--out-root", default="data/cold")
    runner.add_argument("--run-label", default="manual")
    runner.add_argument("--settle-stable-window-seconds", type=float, default=30)
    runner.add_argument("--settle-timeout-seconds", type=float, default=900)
    runner.add_argument("--settle-poll-seconds", type=float, default=5)
    runner.add_argument("--max-attempts", type=int, default=2)
    runner.set_defaults(func=run_eod_bucket)

    scheduler = subparsers.add_parser("register-eod-bucket-task", help="Generate or install Windows scheduled task")
    scheduler.add_argument("--python-exe", default="python")
    scheduler.add_argument("--repo-root", default="")
    scheduler.add_argument("--config-path", default="scripts/diagnostics/config/eod_bucket_thresholds.json")
    scheduler.add_argument("--data-root", default="data")
    scheduler.add_argument("--out-root", default="data/cold")
    scheduler.add_argument("--task-name", default="OptionV4-EOD-Bucket")
    scheduler.add_argument("--user", default="")
    scheduler.add_argument("--start-time", default="16:30")
    scheduler.add_argument("--output-dir", default="tmp/schtasks")
    scheduler.add_argument("--settle-stable-window-seconds", type=float, default=30)
    scheduler.add_argument("--settle-timeout-seconds", type=float, default=900)
    scheduler.add_argument("--settle-poll-seconds", type=float, default=5)
    scheduler.add_argument("--max-attempts", type=int, default=2)
    scheduler.add_argument("--apply", action="store_true")
    scheduler.set_defaults(func=run_register_eod_bucket_task)
