"""Audit the intraday Longbridge/LongPort core flow health.

Usage:
  python scripts/diag/audit_intraday_core_flow.py
  python scripts/diag/audit_intraday_core_flow.py --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import websockets


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass(frozen=True)
class PersistenceSample:
    sample: int
    timestamp: str | None
    l1_version: int
    l1_computed_at: str | None
    atm_iv_source: str | None
    runner_age_s: float | None
    active_input_age_s: float | None
    active_input_version: int
    transport_status: str | None
    last_batch_id: int
    gateway_connected: bool
    gateway_rust_started: bool
    active_rows_real: int
    active_rows_degraded: int
    iv_probe_suppressed_reason: str | None


@dataclass(frozen=True)
class WsSample:
    msg_type: str
    timestamp: str | None
    heartbeat_timestamp: str | None
    version: int | None
    data_timestamp: str | None
    change_keys: list[str]
    atm_present: bool


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    summary: str
    evidence: list[str]


def _http_get_json(url: str, timeout: float) -> dict[str, Any]:
    with urlopen(url, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        body = resp.read().decode(charset, errors="replace")
    return json.loads(body)


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sample_persistence_status(api_base: str, samples: int, delay_s: float, timeout: float) -> list[PersistenceSample]:
    out: list[PersistenceSample] = []
    url = f"{api_base.rstrip('/')}/debug/persistence_status"
    for idx in range(samples):
        data = _http_get_json(url, timeout=timeout)
        l1 = data.get("l1_runtime", {}) if isinstance(data, dict) else {}
        active_input = data.get("active_options_input", {}) if isinstance(data, dict) else {}
        stores = data.get("stores", {}) if isinstance(data, dict) else {}
        transport = stores.get("transport", {}) if isinstance(stores, dict) else {}
        gateway = stores.get("gateway", {}) if isinstance(stores, dict) else {}
        active_options = data.get("active_options", {}) if isinstance(data, dict) else {}
        probe = ((data.get("agent_runner", {}) or {}).get("stats", {}) or {}).get("snapshot_version_iv_probe", {})
        out.append(
            PersistenceSample(
                sample=idx + 1,
                timestamp=data.get("timestamp"),
                l1_version=_to_int(l1.get("version")),
                l1_computed_at=l1.get("computed_at"),
                atm_iv_source=((l1.get("atm_iv_context") or {}).get("iv_source")),
                runner_age_s=_to_float((data.get("agent_runner", {}) or {}).get("last_update_age_seconds")),
                active_input_age_s=_to_float(active_input.get("age_seconds")),
                active_input_version=_to_int(active_input.get("source_version")),
                transport_status=transport.get("status"),
                last_batch_id=_to_int(transport.get("last_batch_id")),
                gateway_connected=bool(gateway.get("connected")),
                gateway_rust_started=bool(gateway.get("rust_started")),
                active_rows_real=_to_int(active_options.get("rows_real")),
                active_rows_degraded=_to_int(active_options.get("degraded_rows")),
                iv_probe_suppressed_reason=(probe.get("suppressed_reason") if isinstance(probe, dict) else None),
            )
        )
        if idx + 1 < samples:
            time.sleep(delay_s)
    return out


async def _sample_ws(ws_url: str, message_count: int, timeout: float) -> list[WsSample]:
    samples: list[WsSample] = []
    async with websockets.connect(ws_url, open_timeout=timeout, ping_timeout=timeout) as ws:
        while len(samples) < message_count:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            msg = json.loads(raw)
            if msg.get("type") == "keepalive":
                continue
            changes = msg.get("changes") if isinstance(msg.get("changes"), dict) else {}
            samples.append(
                WsSample(
                    msg_type=str(msg.get("type") or ""),
                    timestamp=msg.get("timestamp"),
                    heartbeat_timestamp=msg.get("heartbeat_timestamp"),
                    version=_to_int(msg.get("version") if msg.get("version") is not None else changes.get("version")) or None,
                    data_timestamp=(msg.get("data_timestamp") or changes.get("data_timestamp")),
                    change_keys=sorted(list(changes.keys())),
                    atm_present=(
                        ("atm" in msg and msg.get("atm") is not None)
                        or ("atm" in changes and changes.get("atm") is not None)
                    ),
                )
            )
    return samples


def _sample_atm_history(api_base: str, timeout: float) -> dict[str, Any]:
    url = (
        f"{api_base.rstrip('/')}/api/atm-decay/history"
        "?fields=timestamp,straddle_pct,call_pct,put_pct,strike_changed&schema=v2"
    )
    data = _http_get_json(url, timeout=timeout)
    rows = data.get("rows") if isinstance(data, dict) else []
    if not isinstance(rows, list):
        rows = []
    return {
        "schema": data.get("schema"),
        "count": _to_int(data.get("count")),
        "first_row": rows[0] if rows else None,
        "last_row": rows[-1] if rows else None,
    }


def _run_log_analysis(log_lines: int) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "diag" / "pull_backend_log_analysis.py"),
        "--lines",
        str(log_lines),
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=REPO_ROOT)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "log analysis failed")
    return json.loads(proc.stdout)


def _is_strictly_advancing(values: list[int]) -> bool:
    if len(values) < 2:
        return True
    return all(curr > prev for prev, curr in zip(values, values[1:]))


def _check_l0(samples: list[PersistenceSample], log_analysis: dict[str, Any]) -> CheckResult:
    versions = [s.last_batch_id for s in samples]
    ok = all(s.gateway_connected and s.gateway_rust_started and s.transport_status == "OK" for s in samples)
    ok = ok and _is_strictly_advancing(versions)
    analysis = log_analysis.get("analysis", {})
    ok = ok and analysis.get("health") == "OK"
    status = "PASS" if ok else "FAIL"
    return CheckResult(
        name="L0 ingest/runtime",
        status=status,
        summary="Arrow transport and Longbridge runtime are connected and advancing."
        if ok
        else "Runtime connectivity or batch advancement is degraded.",
        evidence=[
            f"gateway_connected={samples[-1].gateway_connected} rust_started={samples[-1].gateway_rust_started}",
            f"transport_status={samples[-1].transport_status} last_batch_id_series={versions}",
            f"log_health={analysis.get('health')} rate_limit_hits={analysis.get('rate_limit_301607_hits')}",
        ],
    )


def _check_l1(samples: list[PersistenceSample]) -> CheckResult:
    ages = [s.runner_age_s for s in samples if s.runner_age_s is not None]
    versions = [s.l1_version for s in samples]
    fresh = bool(ages) and max(ages) < 2.0 and _is_strictly_advancing(versions)
    status = "PASS" if fresh else "FAIL"
    summary = "L1 compute cadence is fresh and versions are advancing." if fresh else "L1 freshness exceeded threshold or stopped advancing."
    evidence = [
        f"l1_version_series={versions}",
        f"runner_age_series={ages}",
        f"atm_iv_source={samples[-1].atm_iv_source}",
    ]
    if samples[-1].iv_probe_suppressed_reason:
        evidence.append(f"iv_probe_suppressed_reason={samples[-1].iv_probe_suppressed_reason}")
    return CheckResult(name="L1 compute freshness", status=status, summary=summary, evidence=evidence)


def _check_l3(ws_samples: list[WsSample]) -> CheckResult:
    data_ts_present = all(s.data_timestamp for s in ws_samples[1:]) if len(ws_samples) > 1 else bool(ws_samples)
    atm_present = any(s.atm_present for s in ws_samples)
    heartbeat_only = any(s.msg_type == "dashboard_delta" and s.change_keys == ["heartbeat_timestamp"] for s in ws_samples)
    ok = data_ts_present and atm_present and not heartbeat_only
    status = "PASS" if ok else "WARN"
    summary = "L3 websocket payloads carry live business deltas, not only heartbeats." if ok else "L3 websocket sampling observed degraded or incomplete deltas."
    evidence = [
        f"message_types={[s.msg_type for s in ws_samples]}",
        f"versions={[s.version for s in ws_samples if s.version is not None]}",
        f"delta_change_keys={[s.change_keys for s in ws_samples if s.msg_type == 'dashboard_delta']}",
    ]
    return CheckResult(name="L3 payload continuity", status=status, summary=summary, evidence=evidence)


def _check_atm(ws_samples: list[WsSample], history: dict[str, Any]) -> CheckResult:
    atm_present = any(s.atm_present for s in ws_samples)
    count = _to_int(history.get("count"))
    last_row = history.get("last_row")
    ok = atm_present and count > 0 and last_row is not None
    status = "PASS" if ok else "FAIL"
    summary = "Root ATM payload and ATM history are advancing intraday." if ok else "ATM payload or history did not provide live evidence."
    evidence = [
        f"ws_atm_present={atm_present}",
        f"history_count={count}",
        f"history_last_row={last_row}",
    ]
    return CheckResult(name="ATM live continuity", status=status, summary=summary, evidence=evidence)


def _check_active_options(samples: list[PersistenceSample]) -> CheckResult:
    ages = [s.active_input_age_s for s in samples if s.active_input_age_s is not None]
    versions = [s.active_input_version for s in samples]
    latest = samples[-1]
    ok = bool(ages) and max(ages) < 2.0 and _is_strictly_advancing(versions) and latest.active_rows_real > 0
    status = "PASS" if ok else "FAIL"
    summary = "ActiveOptions input and live rows remain fresh." if ok else "ActiveOptions input or live rows degraded."
    evidence = [
        f"active_input_age_series={ages}",
        f"active_input_version_series={versions}",
        f"rows_real={latest.active_rows_real} rows_degraded={latest.active_rows_degraded}",
    ]
    return CheckResult(name="ActiveOptions live continuity", status=status, summary=summary, evidence=evidence)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the intraday Longbridge/LongPort core flow.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8001")
    parser.add_argument("--ws-url", default="ws://127.0.0.1:8001/ws/dashboard")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--sample-delay", type=float, default=5.0)
    parser.add_argument("--ws-messages", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--log-lines", type=int, default=350)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    persistence_samples = _sample_persistence_status(args.api_base, args.samples, args.sample_delay, args.timeout)
    ws_samples = asyncio.run(_sample_ws(args.ws_url, args.ws_messages, args.timeout))
    history = _sample_atm_history(args.api_base, args.timeout)
    log_analysis = _run_log_analysis(args.log_lines)

    checks = [
        _check_l0(persistence_samples, log_analysis),
        _check_l1(persistence_samples),
        _check_l3(ws_samples),
        _check_atm(ws_samples, history),
        _check_active_options(persistence_samples),
    ]
    overall = "PASS" if all(c.status == "PASS" for c in checks) else "WARN"
    result = {
        "overall": overall,
        "checks": [asdict(c) for c in checks],
        "persistence_samples": [asdict(s) for s in persistence_samples],
        "ws_samples": [asdict(s) for s in ws_samples],
        "atm_history": history,
        "log_analysis": log_analysis.get("analysis", {}),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print("=== Intraday Core Flow Audit ===")
        print(f"Overall: {overall}")
        for check in checks:
            print(f"[{check.status}] {check.name}: {check.summary}")
            for line in check.evidence:
                print(f"  - {line}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
