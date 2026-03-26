"""Capture a same-version ActiveOptions raw-chain vs displayed-top5 artifact.

Usage:
    python scripts/diag/capture_same_version_active_options.py
    python scripts/diag/capture_same_version_active_options.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass(frozen=True)
class CaptureResult:
    artifact_path: str
    aligned: bool
    sparse_window: bool
    input_source_version: int
    payload_source_version: int
    filtered_candidates_count: int
    displayed_real_rows: int
    chain_size: int
    attempts: int


def _http_get_json(url: str, timeout: float) -> dict[str, Any]:
    with urlopen(url, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        body = resp.read().decode(charset, errors="replace")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object payload from {url}")
    return payload


def _score_capture(payload: dict[str, Any]) -> tuple[int, int, int]:
    alignment = payload.get("version_alignment", {}) if isinstance(payload, dict) else {}
    sparse = payload.get("sparse_window", {}) if isinstance(payload, dict) else {}
    input_capture = payload.get("active_options_input", {}) if isinstance(payload, dict) else {}
    aligned = 1 if bool(alignment.get("aligned", False)) else 0
    sparse_flag = 1 if bool(sparse.get("is_sparse_window", False)) else 0
    chain_size = int(input_capture.get("chain_size", 0) or 0)
    return aligned, sparse_flag, chain_size


def _capture_best(
    *,
    api_base: str,
    attempts: int,
    delay_s: float,
    timeout: float,
) -> tuple[dict[str, Any], int]:
    url = f"{api_base.rstrip('/')}/debug/active_options_capture"
    best_payload: dict[str, Any] | None = None
    best_score = (-1, -1, -1)
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            payload = _http_get_json(url, timeout=timeout)
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            time.sleep(delay_s)
            continue

        score = _score_capture(payload)
        if score > best_score:
            best_payload = payload
            best_score = score
        if score[0] == 1 and score[1] == 1:
            return payload, attempt
        if score[0] == 1:
            return payload, attempt
        time.sleep(delay_s)

    if best_payload is not None:
        return best_payload, attempts
    if last_error is not None:
        raise RuntimeError(f"capture endpoint unavailable: {last_error}") from last_error
    raise RuntimeError("capture endpoint returned no usable payload")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture a same-version ActiveOptions raw input vs displayed Top5 artifact.",
    )
    parser.add_argument(
        "--api-base",
        default="http://127.0.0.1:8001",
        help="Backend API base URL.",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=20,
        help="Maximum polling attempts for a version-aligned capture.",
    )
    parser.add_argument(
        "--delay-s",
        type=float,
        default=0.5,
        help="Delay between polling attempts in seconds.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3.0,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--output",
        default="tmp/active_options_same_version_capture.json",
        help="Artifact output path.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print result metadata as JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload, attempts_used = _capture_best(
        api_base=args.api_base,
        attempts=max(1, int(args.attempts)),
        delay_s=max(0.0, float(args.delay_s)),
        timeout=max(0.1, float(args.timeout)),
    )

    output_path = (REPO_ROOT / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    alignment = payload.get("version_alignment", {})
    sparse = payload.get("sparse_window", {})
    input_capture = payload.get("active_options_input", {})
    displayed_payload = payload.get("displayed_payload", {})
    result = CaptureResult(
        artifact_path=str(output_path),
        aligned=bool(alignment.get("aligned", False)),
        sparse_window=bool(sparse.get("is_sparse_window", False)),
        input_source_version=int(alignment.get("input_source_version", 0) or 0),
        payload_source_version=int(alignment.get("payload_source_version", 0) or 0),
        filtered_candidates_count=int(sparse.get("filtered_candidates_count", 0) or 0),
        displayed_real_rows=int(sparse.get("displayed_real_rows", 0) or 0),
        chain_size=int(input_capture.get("chain_size", 0) or 0),
        attempts=attempts_used,
    )

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=True, indent=2))
        return 0

    print("=== ActiveOptions Same-Version Capture ===")
    print(f"Artifact Path             : {result.artifact_path}")
    print(f"Aligned                   : {result.aligned}")
    print(f"Sparse Window             : {result.sparse_window}")
    print(f"Input Source Version      : {result.input_source_version}")
    print(f"Payload Source Version    : {result.payload_source_version}")
    print(f"Filtered Candidates Count : {result.filtered_candidates_count}")
    print(f"Displayed Real Rows       : {result.displayed_real_rows}")
    print(f"Input Chain Size          : {result.chain_size}")
    print(f"Attempts Used             : {result.attempts}")
    print(
        f"Displayed Total Rows      : "
        f"{int(displayed_payload.get('rows_total', 0) or 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
