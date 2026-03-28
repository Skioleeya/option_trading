#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True)
class SourceEntry:
    role: str
    path: Path
    required: bool


@dataclass(frozen=True)
class SourceSignature:
    role: str
    path: str
    required: bool
    exists: bool
    size_bytes: int
    last_write_ns: int


@dataclass(frozen=True)
class WaitResult:
    stable: bool
    elapsed_seconds: float
    snapshot: tuple[SourceSignature, ...]


def _default_sources(root: Path, date_str: str) -> tuple[SourceEntry, ...]:
    return (
        SourceEntry("research_raw", root / "research" / "raw" / f"raw_{date_str}.parquet", True),
        SourceEntry("research_feature", root / "research" / "feature" / f"feature_{date_str}.parquet", True),
        SourceEntry("research_label", root / "research" / "label" / f"label_{date_str}.parquet", True),
        SourceEntry("atm_series", root / "atm_decay" / f"atm_series_{date_str}.jsonl", False),
        SourceEntry("mtf_iv_series", root / "mtf_iv" / f"mtf_iv_series_{date_str}.jsonl", False),
        SourceEntry("wall_series", root / "wall_migration" / f"wall_series_{date_str}.jsonl", False),
    )


def _capture_snapshot(entries: Iterable[SourceEntry]) -> tuple[SourceSignature, ...]:
    captured: list[SourceSignature] = []
    for entry in entries:
        exists = entry.path.exists()
        size_bytes = -1
        last_write_ns = -1
        if exists:
            stat = entry.path.stat()
            size_bytes = int(stat.st_size)
            last_write_ns = int(stat.st_mtime_ns)
        captured.append(
            SourceSignature(
                role=entry.role,
                path=entry.path.as_posix(),
                required=entry.required,
                exists=exists,
                size_bytes=size_bytes,
                last_write_ns=last_write_ns,
            )
        )
    return tuple(captured)


def _required_sources_ready(snapshot: Iterable[SourceSignature]) -> bool:
    required = [sig for sig in snapshot if sig.required]
    return bool(required) and all(sig.exists for sig in required)


def _all_sources_present(snapshot: Iterable[SourceSignature]) -> bool:
    return all(sig.exists for sig in snapshot)


def _all_existing_sources_older_than(
    snapshot: Iterable[SourceSignature],
    *,
    stable_window_seconds: float,
    now_ns: int,
) -> bool:
    threshold_ns = int(max(0.0, stable_window_seconds) * 1_000_000_000)
    for sig in snapshot:
        if not sig.exists:
            continue
        if sig.last_write_ns < 0 or now_ns - sig.last_write_ns < threshold_ns:
            return False
    return True


def wait_for_settle(
    *,
    capture_fn: Callable[[], tuple[SourceSignature, ...]],
    stable_window_seconds: float,
    timeout_seconds: float,
    poll_seconds: float,
    monotonic_fn: Callable[[], float] = time.monotonic,
    time_ns_fn: Callable[[], int] = time.time_ns,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> WaitResult:
    start = monotonic_fn()
    stable_since: float | None = None
    previous: tuple[SourceSignature, ...] | None = None
    latest: tuple[SourceSignature, ...] = tuple()

    while True:
        now = monotonic_fn()
        latest = capture_fn()
        ready = _required_sources_ready(latest)
        changed = previous is not None and latest != previous

        if ready:
            if _all_sources_present(latest) and _all_existing_sources_older_than(
                latest,
                stable_window_seconds=stable_window_seconds,
                now_ns=time_ns_fn(),
            ):
                return WaitResult(True, now - start, latest)
            if stable_since is None or changed:
                stable_since = now
            elif now - stable_since >= stable_window_seconds:
                return WaitResult(True, now - start, latest)
        else:
            stable_since = None

        if now - start >= timeout_seconds:
            return WaitResult(False, now - start, latest)

        previous = latest
        sleep_fn(poll_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Wait until EOD archive source files stop changing.")
    parser.add_argument("--date", required=True, help="Trade date in YYYYMMDD.")
    parser.add_argument("--root", default="data", help="Data root (default: data).")
    parser.add_argument("--stable-window-seconds", type=float, default=300.0)
    parser.add_argument("--timeout-seconds", type=float, default=2400.0)
    parser.add_argument("--poll-seconds", type=float, default=15.0)
    return parser


def run_cli(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    entries = _default_sources(Path(args.root), str(args.date))
    result = wait_for_settle(
        capture_fn=lambda: _capture_snapshot(entries),
        stable_window_seconds=float(args.stable_window_seconds),
        timeout_seconds=float(args.timeout_seconds),
        poll_seconds=float(args.poll_seconds),
    )
    payload = {
        "date": str(args.date),
        "stable": result.stable,
        "elapsed_seconds": round(result.elapsed_seconds, 3),
        "snapshot": [asdict(sig) for sig in result.snapshot],
    }
    prefix = "[EODSettle]"
    print(f"{prefix} {json.dumps(payload, ensure_ascii=True)}")
    return 0 if result.stable else 2


if __name__ == "__main__":
    raise SystemExit(run_cli())
