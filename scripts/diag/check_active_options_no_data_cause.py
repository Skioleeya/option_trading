"""Diagnose why ActiveOptions shows only placeholder rows.

This script is independent from frontend runtime and can be run anytime:

    python scripts/diag/check_active_options_no_data_cause.py
    python scripts/diag/check_active_options_no_data_cause.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

EMPTY_FILTER_PATTERN = re.compile(
    r"No options above min_volume threshold",
    re.IGNORECASE,
)
SPOT_FALLBACK_FAIL_PATTERN = re.compile(
    r"Spot REST fallback failed",
    re.IGNORECASE,
)
TOKEN_FAIL_PATTERN = re.compile(
    r"/socket/token",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RuntimeSnapshot:
    chain_size: int | None
    ws_volume_seen: int | None
    ws_current_volume_seen: int | None
    spot: float | None
    quote_hub_active: bool | None


@dataclass(frozen=True)
class PayloadSnapshot:
    has_history_row: bool
    active_options_rows: int
    placeholder_rows: int


@dataclass(frozen=True)
class ActiveOptionsDiagSnapshot:
    rows_total: int | None
    rows_placeholder: int | None
    rows_real: int | None
    rows_real_non_synthetic: int | None
    rows_synthetic_fallback: int | None
    last_fallback_mode: str | None


@dataclass(frozen=True)
class Evidence:
    min_volume_threshold: int
    log_lines_scanned: int
    empty_filter_hits: int
    spot_fallback_fail_hits: int
    token_fail_hits: int
    runtime: RuntimeSnapshot
    payload: PayloadSnapshot
    active_options_diag: ActiveOptionsDiagSnapshot


@dataclass(frozen=True)
class Diagnosis:
    verdict: str
    primary_reason: str
    confidence: str
    actions: list[str]
    evidence: Evidence
    sources: list[str]
    errors: list[str]


def _read_tail_lines(path: Path, tail_lines: int) -> list[str]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if tail_lines <= 0 or tail_lines >= len(content):
        return content
    return content[-tail_lines:]


def _count_hits(pattern: re.Pattern[str], lines: list[str]) -> int:
    return sum(1 for line in lines if pattern.search(line))


def _http_get_json(url: str, timeout: float) -> dict[str, Any]:
    with urlopen(url, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        body = resp.read().decode(charset, errors="replace")
    return json.loads(body)


def _to_int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_nested(mapping: dict[str, Any], *keys: str) -> Any:
    cursor: Any = mapping
    for key in keys:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return cursor


def _extract_runtime_snapshot(debug_json: dict[str, Any]) -> RuntimeSnapshot:
    stores = debug_json.get("stores", {})
    store = stores.get("store", {}) if isinstance(stores, dict) else {}

    chain_size = _to_int_or_none(
        store.get("chain_size") if isinstance(store, dict) else stores.get("chain_size")
    )
    ws_volume_seen = _to_int_or_none(
        store.get("ws_volume_seen") if isinstance(store, dict) else stores.get("ws_volume_seen")
    )
    ws_current_volume_seen = _to_int_or_none(
        store.get("ws_current_volume_seen")
        if isinstance(store, dict)
        else stores.get("ws_current_volume_seen")
    )
    spot = _to_float_or_none(stores.get("spot"))
    quote_hub_active = _get_nested(debug_json, "quote_hub", "active")
    if not isinstance(quote_hub_active, bool):
        quote_hub_active = None

    return RuntimeSnapshot(
        chain_size=chain_size,
        ws_volume_seen=ws_volume_seen,
        ws_current_volume_seen=ws_current_volume_seen,
        spot=spot,
        quote_hub_active=quote_hub_active,
    )


def _extract_active_options_diag(debug_json: dict[str, Any]) -> ActiveOptionsDiagSnapshot:
    diag = debug_json.get("active_options", {})
    if not isinstance(diag, dict):
        diag = {}

    last_fallback_mode = diag.get("last_fallback_mode")
    if last_fallback_mode is not None:
        last_fallback_mode = str(last_fallback_mode).strip() or None

    return ActiveOptionsDiagSnapshot(
        rows_total=_to_int_or_none(diag.get("rows_total")),
        rows_placeholder=_to_int_or_none(diag.get("rows_placeholder")),
        rows_real=_to_int_or_none(diag.get("rows_real")),
        rows_real_non_synthetic=_to_int_or_none(diag.get("rows_real_non_synthetic")),
        rows_synthetic_fallback=_to_int_or_none(diag.get("rows_synthetic_fallback")),
        last_fallback_mode=last_fallback_mode,
    )


def _extract_payload_snapshot(history_json: dict[str, Any]) -> PayloadSnapshot:
    history = history_json.get("history", [])
    if not isinstance(history, list) or not history:
        return PayloadSnapshot(has_history_row=False, active_options_rows=0, placeholder_rows=0)

    row = history[0] if isinstance(history[0], dict) else {}
    active_options = _get_nested(row, "agent_g", "data", "ui_state", "active_options")
    if not isinstance(active_options, list):
        active_options = []

    placeholder_rows = 0
    for item in active_options:
        if isinstance(item, dict) and bool(item.get("is_placeholder")):
            placeholder_rows += 1

    return PayloadSnapshot(
        has_history_row=True,
        active_options_rows=len(active_options),
        placeholder_rows=placeholder_rows,
    )


def _resolve_min_volume_threshold() -> int:
    try:
        from shared.config import settings

        return int(getattr(settings, "flow_active_min_volume", 100) or 100)
    except Exception:
        return 100


def _classify(
    *,
    evidence: Evidence,
) -> tuple[str, str, str, list[str]]:
    diag = evidence.active_options_diag
    if (
        (evidence.runtime.chain_size or 0) > 0
        and (diag.rows_total or 0) > 0
        and (diag.rows_real_non_synthetic or 0) == 0
        and (diag.rows_synthetic_fallback or 0) > 0
    ):
        return (
            "ACTIVE_OPTIONS_SYNTHETIC_ONLY",
            "链路已恢复但 ActiveOptions 仅输出合成 fallback 行（无 row_quality=REAL）。",
            "HIGH",
            [
                "优先排查 L0 flow 字段有效性（volume/current_volume/turnover）是否被 depth/零值污染。",
                "确认 active_options.last_fallback_mode 持续值，并验证非合成真实行是否出现。",
            ],
        )

    all_placeholders = (
        evidence.payload.active_options_rows > 0
        and evidence.payload.placeholder_rows == evidence.payload.active_options_rows
    )
    no_data_signal = evidence.empty_filter_hits > 0 or all_placeholders

    if not no_data_signal:
        return (
            "NO_ACTIVE_ISSUE_DETECTED",
            "未检测到 ActiveOptions 全量占位降级信号。",
            "MEDIUM",
            [],
        )

    if evidence.runtime.chain_size == 0:
        return (
            "ACTIVE_OPTIONS_DEGRADED",
            "L0 链路当前链表为空（chain_size=0），导致 ActiveOptions 无候选可排榜。",
            "HIGH",
            [
                "先检查订阅与行情连通性，确认链路先产生有效 chain 数据。",
                "确认后端日志中是否持续出现网关连接失败。",
            ],
        )

    has_ws_volume_stats = (
        evidence.runtime.ws_volume_seen is not None
        and evidence.runtime.ws_current_volume_seen is not None
    )
    if has_ws_volume_stats and evidence.runtime.ws_volume_seen == 0 and evidence.runtime.ws_current_volume_seen == 0:
        return (
            "ACTIVE_OPTIONS_DEGRADED",
            "链路有合约但成交量字段未进入（ws_volume_seen/ws_current_volume_seen=0），被 min_volume 全部过滤。",
            "HIGH",
            [
                "检查 L0 WS 流是否持续接收 volume/current_volume。",
                "检查订阅池是否覆盖了当前近月高成交合约。",
            ],
        )

    if evidence.spot_fallback_fail_hits > 0 or evidence.token_fail_hits > 0:
        return (
            "ACTIVE_OPTIONS_DEGRADED",
            "行情连接存在失败迹象（socket/token 或 Spot fallback error），可交易数据密度不足触发占位降级。",
            "HIGH",
            [
                "先恢复行情网关连通性，再观察 ActiveOptions 是否自动恢复。",
                "恢复后若仍为空，再评估是否临时下调 min_volume 阈值。",
            ],
        )

    return (
        "ACTIVE_OPTIONS_DEGRADED",
        "ActiveOptions 候选在 min_volume 过滤后为空，当前阈值可能高于可用成交量。",
        "MEDIUM",
        [
            "临时将 FLOW_ACTIVE_MIN_VOLUME 下调到 10 或 1 进行 A/B 验证。",
            "观察日志中 “No options above min_volume threshold” 是否消失。",
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose why ActiveOptions panel has no real rows.",
    )
    parser.add_argument(
        "--api-base",
        default="http://127.0.0.1:8001",
        help="Backend API base URL.",
    )
    parser.add_argument(
        "--log-file",
        default="logs/backend_runtime.current.log",
        help="Backend runtime log path.",
    )
    parser.add_argument(
        "--tail-lines",
        type=int,
        default=4000,
        help="How many recent log lines to scan.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3.0,
        help="HTTP timeout seconds.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    errors: list[str] = []
    sources: list[str] = []

    log_path = (REPO_ROOT / args.log_file).resolve()
    lines = _read_tail_lines(log_path, max(0, int(args.tail_lines)))
    if lines:
        sources.append(str(log_path))
    else:
        errors.append(f"log file missing/empty: {log_path}")

    empty_filter_hits = _count_hits(EMPTY_FILTER_PATTERN, lines)
    spot_fallback_fail_hits = _count_hits(SPOT_FALLBACK_FAIL_PATTERN, lines)
    token_fail_hits = _count_hits(TOKEN_FAIL_PATTERN, lines)

    runtime = RuntimeSnapshot(
        chain_size=None,
        ws_volume_seen=None,
        ws_current_volume_seen=None,
        spot=None,
        quote_hub_active=None,
    )
    active_options_diag = ActiveOptionsDiagSnapshot(
        rows_total=None,
        rows_placeholder=None,
        rows_real=None,
        rows_real_non_synthetic=None,
        rows_synthetic_fallback=None,
        last_fallback_mode=None,
    )
    payload = PayloadSnapshot(
        has_history_row=False,
        active_options_rows=0,
        placeholder_rows=0,
    )

    debug_url = f"{args.api_base.rstrip('/')}/debug/persistence_status"
    history_qs = urlencode({"view": "full", "count": 1})
    history_url = f"{args.api_base.rstrip('/')}/history?{history_qs}"

    try:
        debug_json = _http_get_json(debug_url, timeout=float(args.timeout))
        runtime = _extract_runtime_snapshot(debug_json)
        active_options_diag = _extract_active_options_diag(debug_json)
        sources.append(debug_url)
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        errors.append(f"debug endpoint unavailable: {exc}")

    try:
        history_json = _http_get_json(history_url, timeout=float(args.timeout))
        payload = _extract_payload_snapshot(history_json)
        sources.append(history_url)
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        errors.append(f"history endpoint unavailable: {exc}")

    evidence = Evidence(
        min_volume_threshold=_resolve_min_volume_threshold(),
        log_lines_scanned=len(lines),
        empty_filter_hits=empty_filter_hits,
        spot_fallback_fail_hits=spot_fallback_fail_hits,
        token_fail_hits=token_fail_hits,
        runtime=runtime,
        payload=payload,
        active_options_diag=active_options_diag,
    )
    verdict, primary_reason, confidence, actions = _classify(evidence=evidence)
    diagnosis = Diagnosis(
        verdict=verdict,
        primary_reason=primary_reason,
        confidence=confidence,
        actions=actions,
        evidence=evidence,
        sources=sources,
        errors=errors,
    )

    if args.json:
        print(json.dumps(asdict(diagnosis), ensure_ascii=True, indent=2))
        return 0

    print("=== ActiveOptions No-Data Diagnosis ===")
    print(f"Verdict               : {diagnosis.verdict}")
    print(f"Confidence            : {diagnosis.confidence}")
    print(f"Primary Reason        : {diagnosis.primary_reason}")
    print(f"Min Volume Threshold  : {diagnosis.evidence.min_volume_threshold}")
    print(f"Log Lines Scanned     : {diagnosis.evidence.log_lines_scanned}")
    print(f"Empty Filter Hits     : {diagnosis.evidence.empty_filter_hits}")
    print(f"Spot Fallback Fail    : {diagnosis.evidence.spot_fallback_fail_hits}")
    print(f"Token Fail Hits       : {diagnosis.evidence.token_fail_hits}")
    print(f"Chain Size            : {diagnosis.evidence.runtime.chain_size}")
    print(f"WS Volume Seen        : {diagnosis.evidence.runtime.ws_volume_seen}")
    print(f"WS Current Volume Seen: {diagnosis.evidence.runtime.ws_current_volume_seen}")
    print(f"Spot                  : {diagnosis.evidence.runtime.spot}")
    print(f"Quote Hub Active      : {diagnosis.evidence.runtime.quote_hub_active}")
    print(f"History Row Exists    : {diagnosis.evidence.payload.has_history_row}")
    print(f"Active Rows           : {diagnosis.evidence.payload.active_options_rows}")
    print(f"Placeholder Rows      : {diagnosis.evidence.payload.placeholder_rows}")
    print(f"Diag Rows Total       : {diagnosis.evidence.active_options_diag.rows_total}")
    print(f"Diag Real Rows        : {diagnosis.evidence.active_options_diag.rows_real}")
    print(f"Diag Real NonSynthetic: {diagnosis.evidence.active_options_diag.rows_real_non_synthetic}")
    print(f"Diag Synthetic Rows   : {diagnosis.evidence.active_options_diag.rows_synthetic_fallback}")
    print(f"Diag LastFallbackMode : {diagnosis.evidence.active_options_diag.last_fallback_mode}")
    if diagnosis.actions:
        print("Recommended Actions   :")
        for idx, action in enumerate(diagnosis.actions, start=1):
            print(f"  {idx}. {action}")
    if diagnosis.sources:
        print("Sources               :")
        for source in diagnosis.sources:
            print(f"  - {source}")
    if diagnosis.errors:
        print("Errors                :")
        for err in diagnosis.errors:
            print(f"  - {err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
