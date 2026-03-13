"""Diagnose whether ActiveOptions freeze is caused by stale-retain empty-data path.

Usage:
    python scripts/diag/check_active_options_freeze_rootcause.py
    python scripts/diag/check_active_options_freeze_rootcause.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_LOG_PATHS = (
    Path("logs/backend_runtime.err.log"),
    Path("logs/backend.verify.err.log"),
    Path("logs/backend.verify.escalated.err.log"),
)
DEFAULT_RUNTIME_SERVICE = Path("shared/services/active_options/runtime_service.py")

RETAIN_PATTERN = re.compile(
    r"No options above min_volume threshold.*retaining last valid payload",
    re.IGNORECASE,
)
EMIT_PLACEHOLDER_PATTERN = re.compile(
    r"No options above min_volume threshold.*emitting neutral placeholders",
    re.IGNORECASE,
)
CONNECTION_OPEN_PATTERN = re.compile(r"\bconnection open\b", re.IGNORECASE)
L0_FETCH_PATTERN = re.compile(r"\[Debug\]\s*L0 Fetch:", re.IGNORECASE)
SPOT_FALLBACK_FAIL_PATTERN = re.compile(r"Spot REST fallback failed", re.IGNORECASE)


@dataclass(frozen=True)
class Evidence:
    total_log_lines: int
    retain_hits: int
    emit_placeholder_hits: int
    connection_open_hits: int
    l0_fetch_hits: int
    spot_fallback_fail_hits: int
    runtime_service_mode: str


@dataclass(frozen=True)
class Diagnosis:
    verdict: str
    likely_root_cause: bool
    confidence: str
    summary: str
    evidence: Evidence
    scanned_logs: list[str]
    missing_logs: list[str]


def _count_hits(pattern: re.Pattern[str], text: str) -> int:
    return len(pattern.findall(text))


def _detect_runtime_service_mode(runtime_service_text: str) -> str:
    lower = runtime_service_text.lower()
    has_retain = "retaining last valid payload" in lower
    has_emit = "emitting neutral placeholders" in lower
    if has_retain and not has_emit:
        return "retain_last_valid"
    if has_emit and not has_retain:
        return "emit_placeholders"
    if has_retain and has_emit:
        return "mixed"
    return "unknown"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def build_diagnosis(
    log_texts: Iterable[str],
    runtime_service_text: str,
    *,
    retain_threshold: int = 3,
    l0_fetch_threshold: int = 3,
) -> Diagnosis:
    joined = "\n".join(log_texts)
    lines = joined.count("\n") + (1 if joined else 0)

    retain_hits = _count_hits(RETAIN_PATTERN, joined)
    emit_hits = _count_hits(EMIT_PLACEHOLDER_PATTERN, joined)
    conn_hits = _count_hits(CONNECTION_OPEN_PATTERN, joined)
    l0_hits = _count_hits(L0_FETCH_PATTERN, joined)
    spot_fail_hits = _count_hits(SPOT_FALLBACK_FAIL_PATTERN, joined)
    mode = _detect_runtime_service_mode(runtime_service_text)

    if retain_hits >= retain_threshold and conn_hits > 0 and l0_hits >= l0_fetch_threshold:
        verdict = "YES"
        likely = True
        confidence = "HIGH"
        summary = (
            "Likely root cause confirmed: backend repeatedly retained last valid "
            "ActiveOptions while pipeline/connection remained active."
        )
    elif emit_hits >= retain_threshold and retain_hits == 0 and mode == "emit_placeholders":
        verdict = "NO"
        likely = False
        confidence = "HIGH"
        summary = (
            "Root cause unlikely in current build: empty-data branch emits placeholders "
            "instead of retaining stale rows."
        )
    elif retain_hits > 0:
        verdict = "INCONCLUSIVE"
        likely = False
        confidence = "MEDIUM"
        summary = (
            "Retain pattern appears, but runtime activity evidence is insufficient for "
            "high-confidence confirmation."
        )
    else:
        verdict = "INCONCLUSIVE"
        likely = False
        confidence = "LOW"
        summary = "Insufficient evidence in scanned logs."

    evidence = Evidence(
        total_log_lines=lines,
        retain_hits=retain_hits,
        emit_placeholder_hits=emit_hits,
        connection_open_hits=conn_hits,
        l0_fetch_hits=l0_hits,
        spot_fallback_fail_hits=spot_fail_hits,
        runtime_service_mode=mode,
    )
    return Diagnosis(
        verdict=verdict,
        likely_root_cause=likely,
        confidence=confidence,
        summary=summary,
        evidence=evidence,
        scanned_logs=[],
        missing_logs=[],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose whether ActiveOptions freeze is caused by the stale-retain "
            "empty-data path (min_volume filter result is empty)."
        )
    )
    parser.add_argument(
        "--logs",
        nargs="*",
        default=[str(p) for p in DEFAULT_LOG_PATHS],
        help="Log files to scan.",
    )
    parser.add_argument(
        "--runtime-service",
        default=str(DEFAULT_RUNTIME_SERVICE),
        help="Path to shared ActiveOptions runtime service source file.",
    )
    parser.add_argument(
        "--retain-threshold",
        type=int,
        default=3,
        help="Minimum retain-pattern hits to treat as strong evidence.",
    )
    parser.add_argument(
        "--l0-fetch-threshold",
        type=int,
        default=3,
        help="Minimum L0 fetch log hits to treat pipeline as active.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print diagnosis as JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    scanned_logs: list[str] = []
    missing_logs: list[str] = []
    log_texts: list[str] = []
    for raw_path in args.logs:
        path = Path(raw_path)
        if not path.exists():
            missing_logs.append(str(path))
            continue
        scanned_logs.append(str(path))
        try:
            log_texts.append(_read_text(path))
        except OSError as exc:
            print(f"[ERROR] Failed to read log file {path}: {exc}", file=sys.stderr)
            return 2

    runtime_path = Path(args.runtime_service)
    runtime_text = ""
    if runtime_path.exists():
        try:
            runtime_text = _read_text(runtime_path)
        except OSError as exc:
            print(f"[ERROR] Failed to read runtime service file {runtime_path}: {exc}", file=sys.stderr)
            return 2
    else:
        print(f"[WARN] Runtime service file not found: {runtime_path}", file=sys.stderr)

    diagnosis = build_diagnosis(
        log_texts,
        runtime_text,
        retain_threshold=max(1, int(args.retain_threshold)),
        l0_fetch_threshold=max(1, int(args.l0_fetch_threshold)),
    )
    diagnosis = Diagnosis(
        verdict=diagnosis.verdict,
        likely_root_cause=diagnosis.likely_root_cause,
        confidence=diagnosis.confidence,
        summary=diagnosis.summary,
        evidence=diagnosis.evidence,
        scanned_logs=scanned_logs,
        missing_logs=missing_logs,
    )

    if args.json:
        print(json.dumps(asdict(diagnosis), indent=2, ensure_ascii=True))
    else:
        print("=== ActiveOptions Freeze Root Cause Check ===")
        print(f"Verdict             : {diagnosis.verdict}")
        print(f"Likely Root Cause   : {diagnosis.likely_root_cause}")
        print(f"Confidence          : {diagnosis.confidence}")
        print(f"Summary             : {diagnosis.summary}")
        print(f"Runtime Service Mode: {diagnosis.evidence.runtime_service_mode}")
        print(f"Retain Hits         : {diagnosis.evidence.retain_hits}")
        print(f"Emit Placeholder Hits: {diagnosis.evidence.emit_placeholder_hits}")
        print(f"Connection Open Hits: {diagnosis.evidence.connection_open_hits}")
        print(f"L0 Fetch Hits       : {diagnosis.evidence.l0_fetch_hits}")
        print(f"Spot Fallback Fail  : {diagnosis.evidence.spot_fallback_fail_hits}")
        if diagnosis.scanned_logs:
            print(f"Scanned Logs        : {', '.join(diagnosis.scanned_logs)}")
        if diagnosis.missing_logs:
            print(f"Missing Logs        : {', '.join(diagnosis.missing_logs)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
