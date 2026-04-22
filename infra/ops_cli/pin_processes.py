from __future__ import annotations

import argparse
import os
import subprocess


def _run_powershell(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
    )


def _parse_core_mask(raw: str) -> int:
    mask = 0
    for chunk in raw.split(","):
        token = chunk.strip()
        if not token:
            continue
        if "-" in token:
            left, right = token.split("-", 1)
            start = int(left)
            end = int(right)
            if end < start:
                raise ValueError(f"Invalid core range: {token}")
            for core in range(start, end + 1):
                mask |= 1 << core
        else:
            core = int(token)
            mask |= 1 << core
    if mask <= 0:
        raise ValueError("Core mask must not be empty")
    return mask


def _find_python_main_pids() -> list[int]:
    proc = _run_powershell(
        (
            "$rows = Get-CimInstance Win32_Process | "
            "Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*main.py*' }; "
            "$rows | ForEach-Object { $_.ProcessId }"
        )
    )
    if proc.returncode != 0:
        return []
    pids: list[int] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pids.append(int(line))
        except ValueError:
            continue
    return pids


def run_pin_processes(args: argparse.Namespace) -> int:
    if os.name != "nt":
        print("Windows-only runtime contract violation: pin-processes must run on Windows host.")
        return 1

    print("Searching for SPX Sentinel Python processes...")
    pids = _find_python_main_pids()
    if not pids:
        print("No active SPX Sentinel Python processes found.")
        return 0

    try:
        affinity_mask = _parse_core_mask(args.cores)
    except ValueError as exc:
        print(f"ERROR parsing --cores: {exc}")
        return 1

    for pid in pids:
        result = _run_powershell(
            f"$p=Get-Process -Id {pid} -ErrorAction Stop; $p.ProcessorAffinity = {affinity_mask}; Write-Output 'OK'"
        )
        if result.returncode == 0:
            print(f"Successfully pinned PID {pid} to mask {affinity_mask} (cores={args.cores})")
        else:
            msg = result.stderr.strip() or result.stdout.strip() or "unknown error"
            print(f"ERROR pinning PID {pid}: {msg}")

    print("Optimization Complete.")
    return 0


def build_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("pin-processes", help="Pin python main.py processes to CPU cores")
    parser.add_argument("--cores", default="0-3")
    parser.set_defaults(func=run_pin_processes)
