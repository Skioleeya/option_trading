"""Pull latest backend logs and emit a structured health analysis.

Usage examples:
  python scripts/diag/pull_backend_log_analysis.py
  python scripts/diag/pull_backend_log_analysis.py --lines 400 --print-tail
  python scripts/diag/pull_backend_log_analysis.py --source console --json
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import sys
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

try:
    import psutil
except Exception as exc:  # pragma: no cover
    print(f"[ERROR] psutil is required: {exc}", file=sys.stderr)
    raise SystemExit(3)


DEFAULT_LINES = 400
DEFAULT_LOG_DIR = Path("logs")
DEFAULT_BACKEND_PORT = 8001
DEFAULT_FILE_RECENCY_GRACE_SECONDS = 120
DEFAULT_WARN_LAG_SECONDS = 120.0
DEFAULT_WARN_SABR_NO_DATA_HITS = 3
DEFAULT_CONSOLE_SCAN_ROWS_MULTIPLIER = 8
DEFAULT_CONSOLE_MIN_SCAN_ROWS = 1200
DEFAULT_REPORT_PATH = Path("tmp/session_validation_diag/backend_runtime_log_analysis.json")
DEFAULT_TAIL_PATH = Path("tmp/session_validation_diag/backend_runtime_log_tail.log")

PATTERN_RATE_LIMIT_301607 = re.compile(r"301607|Too many option securities request", re.IGNORECASE)
PATTERN_GLOBAL_COOLDOWN = re.compile(r"Global Cooldown", re.IGNORECASE)
PATTERN_WARMUP_START = re.compile(r"Warm-up batch .*STARTING", re.IGNORECASE)
PATTERN_WARMUP_SUCCESS = re.compile(r"Batch SUCCESS", re.IGNORECASE)
PATTERN_WARMUP_FAIL = re.compile(r"Warm-up batch failed", re.IGNORECASE)
PATTERN_NO_OPTIONS_WARN = re.compile(r"No options above min_volume threshold", re.IGNORECASE)
PATTERN_SABR_NO_DATA = re.compile(r"Insufficient market data for SABR", re.IGNORECASE)
PATTERN_IV_DRIFT = re.compile(r"snapshot_version_iv_drift_ongoing", re.IGNORECASE)
PATTERN_LAG_SECONDS = re.compile(r"lag_seconds=(\d+(?:\.\d+)?)")

LOG_SUFFIXES = (".log", ".txt", ".out", ".err")


@dataclass(frozen=True)
class BackendProcessInfo:
    pid: int
    parent_pid: int | None
    started_at: str
    cmdline: list[str]
    parent_cmdline: list[str]


@dataclass(frozen=True)
class SourceInfo:
    source_type: str
    source_ref: str


@dataclass(frozen=True)
class Analysis:
    health: str
    warnings: list[str]
    line_count: int
    rate_limit_301607_hits: int
    global_cooldown_hits: int
    warmup_start_hits: int
    warmup_success_hits: int
    warmup_fail_hits: int
    no_options_warn_hits: int
    sabr_no_data_hits: int
    iv_drift_hits: int
    max_lag_seconds: float | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pull latest backend logs and analyze health markers.")
    parser.add_argument("--pid", type=int, default=0, help="Explicit backend PID. Auto-discover if omitted.")
    parser.add_argument(
        "--source",
        choices=("auto", "file", "console"),
        default="auto",
        help="Log source strategy. auto=file first then console fallback.",
    )
    parser.add_argument(
        "--log-dir",
        default=str(DEFAULT_LOG_DIR),
        help="Directory used when source=file or source=auto.",
    )
    parser.add_argument(
        "--log-file",
        default="",
        help="Explicit log file path override when source=file.",
    )
    parser.add_argument("--lines", type=int, default=DEFAULT_LINES, help="How many latest lines to pull.")
    parser.add_argument("--port", type=int, default=DEFAULT_BACKEND_PORT, help="Backend port hint for process lookup.")
    parser.add_argument("--json", action="store_true", help="Output JSON report to stdout.")
    parser.add_argument("--print-tail", action="store_true", help="Print pulled tail lines to stdout.")
    parser.add_argument(
        "--report-out",
        default=str(DEFAULT_REPORT_PATH),
        help="Write analysis JSON to this path. Use empty string to disable.",
    )
    parser.add_argument(
        "--tail-out",
        default=str(DEFAULT_TAIL_PATH),
        help="Write pulled tail lines to this path. Use empty string to disable.",
    )
    return parser.parse_args()


def _safe_cmdline(proc: psutil.Process | None) -> list[str]:
    if proc is None:
        return []
    try:
        return proc.cmdline()
    except Exception:
        return []


def _is_backend_process(proc: psutil.Process, port: int) -> bool:
    cmdline = " ".join(_safe_cmdline(proc)).lower()
    if "uvicorn" not in cmdline:
        return False
    if "main:app" in cmdline:
        return True
    return f"--port {port}" in cmdline


def _find_backend_process(explicit_pid: int, port: int) -> psutil.Process:
    if explicit_pid > 0:
        return psutil.Process(explicit_pid)

    candidates: list[psutil.Process] = []
    for proc in psutil.process_iter(["pid", "name", "create_time"]):
        try:
            if _is_backend_process(proc, port):
                candidates.append(proc)
        except Exception:
            continue
    if not candidates:
        raise RuntimeError("No uvicorn backend process found.")
    candidates.sort(key=lambda p: p.create_time(), reverse=True)
    return candidates[0]


def _to_backend_info(proc: psutil.Process) -> BackendProcessInfo:
    parent = None
    try:
        parent = proc.parent()
    except Exception:
        parent = None
    started_at = datetime.fromtimestamp(proc.create_time()).isoformat(sep=" ", timespec="seconds")
    return BackendProcessInfo(
        pid=proc.pid,
        parent_pid=(parent.pid if parent else None),
        started_at=started_at,
        cmdline=_safe_cmdline(proc),
        parent_cmdline=_safe_cmdline(parent),
    )


def _tail_file_lines(path: Path, lines: int) -> list[str]:
    dq: deque[str] = deque(maxlen=max(1, lines))
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            dq.append(line.rstrip("\n"))
    return list(dq)


def _is_log_like(path: Path) -> bool:
    lower = path.name.lower()
    return lower.endswith(LOG_SUFFIXES)


def _find_fresh_log_file(log_dir: Path, backend_started_at: datetime, explicit_log_file: str) -> Path | None:
    if explicit_log_file:
        path = Path(explicit_log_file)
        return path if path.exists() else None

    if not log_dir.exists():
        return None

    grace = timedelta(seconds=DEFAULT_FILE_RECENCY_GRACE_SECONDS)
    threshold = backend_started_at - grace
    candidates = [p for p in log_dir.iterdir() if p.is_file() and _is_log_like(p)]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for candidate in candidates:
        modified_at = datetime.fromtimestamp(candidate.stat().st_mtime)
        if modified_at >= threshold:
            return candidate
    return None


def _read_console_lines(console_pid: int, lines: int) -> list[str]:
    if os.name != "nt":
        raise RuntimeError("Console attach is only supported on Windows.")

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    generic_read = 0x80000000
    generic_write = 0x40000000
    file_share_read = 0x00000001
    file_share_write = 0x00000002
    open_existing = 3

    class COORD(ctypes.Structure):
        _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

    class SMALL_RECT(ctypes.Structure):
        _fields_ = [
            ("Left", ctypes.c_short),
            ("Top", ctypes.c_short),
            ("Right", ctypes.c_short),
            ("Bottom", ctypes.c_short),
        ]

    class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [
            ("dwSize", COORD),
            ("dwCursorPosition", COORD),
            ("wAttributes", ctypes.c_ushort),
            ("srWindow", SMALL_RECT),
            ("dwMaximumWindowSize", COORD),
        ]

    kernel32.FreeConsole()
    if not kernel32.AttachConsole(int(console_pid)):
        err = ctypes.get_last_error()
        raise RuntimeError(f"AttachConsole failed for pid={console_pid}, err={err}")

    handle = kernel32.CreateFileW(
        "CONOUT$",
        generic_read | generic_write,
        file_share_read | file_share_write,
        None,
        open_existing,
        0,
        None,
    )
    if int(handle) == -1:
        err = ctypes.get_last_error()
        raise RuntimeError(f"CreateFileW(CONOUT$) failed, err={err}")

    csbi = CONSOLE_SCREEN_BUFFER_INFO()
    if not kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(csbi)):
        err = ctypes.get_last_error()
        raise RuntimeError(f"GetConsoleScreenBufferInfo failed, err={err}")

    width = int(csbi.dwSize.X)
    cursor_y = int(csbi.dwCursorPosition.Y)
    scan_rows = max(DEFAULT_CONSOLE_MIN_SCAN_ROWS, lines * DEFAULT_CONSOLE_SCAN_ROWS_MULTIPLIER)
    start_y = max(0, cursor_y - scan_rows)

    read_count = ctypes.c_uint32(0)
    non_empty_rows: list[str] = []
    for y in range(start_y, cursor_y + 1):
        buf = ctypes.create_unicode_buffer(width)
        coord = COORD(0, y)
        ok = kernel32.ReadConsoleOutputCharacterW(
            handle,
            buf,
            width,
            coord,
            ctypes.byref(read_count),
        )
        if not ok:
            continue
        line = buf.value.rstrip()
        if line:
            non_empty_rows.append(line)
    return non_empty_rows[-max(1, lines) :]


def _count(pattern: re.Pattern[str], lines: Iterable[str]) -> int:
    return sum(1 for line in lines if pattern.search(line))


def _extract_max_lag_seconds(lines: Iterable[str]) -> float | None:
    max_lag: float | None = None
    for line in lines:
        match = PATTERN_LAG_SECONDS.search(line)
        if not match:
            continue
        current = float(match.group(1))
        if max_lag is None or current > max_lag:
            max_lag = current
    return max_lag


def _analyze(lines: list[str]) -> Analysis:
    warmup_start_hits = _count(PATTERN_WARMUP_START, lines)
    warmup_success_hits = _count(PATTERN_WARMUP_SUCCESS, lines)
    warmup_fail_hits = _count(PATTERN_WARMUP_FAIL, lines)
    rate_limit_hits = _count(PATTERN_RATE_LIMIT_301607, lines)
    cooldown_hits = _count(PATTERN_GLOBAL_COOLDOWN, lines)
    no_options_hits = _count(PATTERN_NO_OPTIONS_WARN, lines)
    sabr_no_data_hits = _count(PATTERN_SABR_NO_DATA, lines)
    iv_drift_hits = _count(PATTERN_IV_DRIFT, lines)
    max_lag = _extract_max_lag_seconds(lines)

    warnings: list[str] = []
    if rate_limit_hits > 0:
        warnings.append("Rate-limit hit detected (301607 / too many option requests).")
    if cooldown_hits > 0:
        warnings.append("Global cooldown was triggered.")
    if warmup_fail_hits > 0:
        warnings.append("Warm-up batch failure detected.")
    if warmup_start_hits > (warmup_success_hits + warmup_fail_hits):
        warnings.append("Warm-up batches started but not fully closed in current tail window.")
    if max_lag is not None and max_lag >= DEFAULT_WARN_LAG_SECONDS:
        warnings.append(f"IV drift lag is high: max_lag_seconds={max_lag:.3f}.")
    if sabr_no_data_hits >= DEFAULT_WARN_SABR_NO_DATA_HITS:
        warnings.append("SABR insufficient-market-data appears repeatedly.")

    health = "WARN" if warnings else "OK"
    return Analysis(
        health=health,
        warnings=warnings,
        line_count=len(lines),
        rate_limit_301607_hits=rate_limit_hits,
        global_cooldown_hits=cooldown_hits,
        warmup_start_hits=warmup_start_hits,
        warmup_success_hits=warmup_success_hits,
        warmup_fail_hits=warmup_fail_hits,
        no_options_warn_hits=no_options_hits,
        sabr_no_data_hits=sabr_no_data_hits,
        iv_drift_hits=iv_drift_hits,
        max_lag_seconds=max_lag,
    )


def _write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines) + ("\n" if lines else "")
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def main() -> int:
    args = parse_args()
    line_limit = max(1, int(args.lines))

    try:
        proc = _find_backend_process(explicit_pid=int(args.pid), port=int(args.port))
    except Exception as exc:
        print(f"[ERROR] Failed to locate backend process: {exc}", file=sys.stderr)
        return 2

    backend_info = _to_backend_info(proc)
    backend_started_at = datetime.fromtimestamp(proc.create_time())

    source_type = ""
    source_ref = ""
    pulled_lines: list[str] = []
    log_dir = Path(args.log_dir)

    if args.source in ("auto", "file"):
        file_path = _find_fresh_log_file(log_dir, backend_started_at, args.log_file)
        if file_path is not None:
            source_type = "file"
            source_ref = str(file_path)
            pulled_lines = _tail_file_lines(file_path, line_limit)

    if args.source in ("auto", "console") and not pulled_lines:
        parent_pid = backend_info.parent_pid
        if parent_pid is None:
            print("[ERROR] Backend process has no parent PID for console attach.", file=sys.stderr)
            return 2
        try:
            source_type = "console"
            source_ref = f"pid={parent_pid}"
            pulled_lines = _read_console_lines(parent_pid, line_limit)
        except Exception as exc:
            print(f"[ERROR] Failed to read console output: {exc}", file=sys.stderr)
            return 2

    if not pulled_lines:
        print("[ERROR] No lines pulled from selected source.", file=sys.stderr)
        return 2

    analysis = _analyze(pulled_lines)
    source_info = SourceInfo(source_type=source_type, source_ref=source_ref)

    report = {
        "generated_at": datetime.now().isoformat(sep=" ", timespec="seconds"),
        "requested_lines": line_limit,
        "backend": asdict(backend_info),
        "source": asdict(source_info),
        "analysis": asdict(analysis),
        "tail_preview": pulled_lines[-20:],
    }

    report_out = str(args.report_out).strip()
    if report_out:
        _write_json(Path(report_out), report)
    tail_out = str(args.tail_out).strip()
    if tail_out:
        _write_text(Path(tail_out), pulled_lines)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print("=== Backend Log Pull + Analysis ===")
        print(f"Backend PID            : {backend_info.pid}")
        print(f"Backend Start          : {backend_info.started_at}")
        print(f"Source                 : {source_info.source_type} ({source_info.source_ref})")
        print(f"Requested Lines        : {line_limit}")
        print(f"Pulled Lines           : {analysis.line_count}")
        print(f"Health                 : {analysis.health}")
        print(f"RateLimit(301607)      : {analysis.rate_limit_301607_hits}")
        print(f"GlobalCooldown         : {analysis.global_cooldown_hits}")
        print(f"Warmup Start/OK/Fail   : {analysis.warmup_start_hits}/{analysis.warmup_success_hits}/{analysis.warmup_fail_hits}")
        print(f"NoOptionsWarn          : {analysis.no_options_warn_hits}")
        print(f"SABR NoData            : {analysis.sabr_no_data_hits}")
        print(f"IV Drift Hits          : {analysis.iv_drift_hits}")
        print(f"Max Lag Seconds        : {analysis.max_lag_seconds}")
        if analysis.warnings:
            print("Warnings:")
            for warning in analysis.warnings:
                print(f"  - {warning}")
        if report_out:
            print(f"Report Out             : {report_out}")
        if tail_out:
            print(f"Tail Out               : {tail_out}")

    if args.print_tail:
        print("---TAIL_START---")
        for line in pulled_lines:
            print(line)
        print("---TAIL_END---")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
