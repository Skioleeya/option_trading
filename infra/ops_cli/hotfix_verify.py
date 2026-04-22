from __future__ import annotations

import argparse
import json
from urllib.request import Request, urlopen


def _json_get(url: str, timeout_sec: int) -> dict:
    req = Request(url, method="GET")
    with urlopen(req, timeout=timeout_sec) as resp:  # nosec - local endpoint check
        payload = resp.read().decode("utf-8")
    return json.loads(payload)


def _resolve_chain_size(debug_json: dict) -> int:
    stores = debug_json.get("stores")
    if not isinstance(stores, dict):
        return 0
    if isinstance(stores.get("store"), dict):
        return int(stores["store"].get("chain_size", 0) or 0)
    return int(stores.get("chain_size", 0) or 0)


def _int_field(obj: dict | None, field: str) -> int:
    if not isinstance(obj, dict):
        return 0
    return int(obj.get(field, 0) or 0)


def run_verify_active_options_hotfix(args: argparse.Namespace) -> int:
    base = args.api_base.rstrip("/")
    health_url = f"{base}/health"
    debug_url = f"{base}/debug/persistence_status"

    print(f"[verify-hotfix] health_url={health_url}")
    try:
        health = _json_get(health_url, args.timeout_sec)
    except Exception as exc:
        print(f"[verify-hotfix] health request failed: {exc}")
        return 1

    if not isinstance(health, dict) or health.get("status") != "ok":
        print("[verify-hotfix] health status is not ok")
        return 1
    print("[verify-hotfix] health_status=200")

    debug_json = _json_get(debug_url, args.timeout_sec)
    chain_size = _resolve_chain_size(debug_json)
    active = debug_json.get("active_options")
    if not isinstance(active, dict):
        print("[verify-hotfix] missing active_options diagnostics in /debug/persistence_status response.")
        return 1

    total_rows = _int_field(active, "rows_total")
    placeholder_rows = _int_field(active, "rows_placeholder")
    real_rows = _int_field(active, "rows_real")
    live_rows = _int_field(active, "live_rows")
    degraded_rows = _int_field(active, "degraded_rows")
    missing_gamma_rows = _int_field(active, "missing_gamma_rows")
    missing_turnover_rows = _int_field(active, "missing_turnover_rows")

    print(f"[verify-hotfix] chain_size={chain_size} active_options_total={total_rows} placeholder={placeholder_rows} real={real_rows}")
    print(
        "[verify-hotfix] "
        f"live_rows={live_rows} degraded_rows={degraded_rows} missing_gamma_rows={missing_gamma_rows} "
        f"missing_turnover_rows={missing_turnover_rows}"
    )

    if chain_size > 0 and live_rows < 1:
        print("[verify-hotfix] chain has data but live_rows=0; degraded output is forbidden.")
        return 1
    if chain_size > 0 and real_rows < 1:
        print("[verify-hotfix] chain has data but active_options has no real rows according to diagnostics.")
        return 1
    if chain_size > 0 and total_rows < 1:
        print("[verify-hotfix] chain has data but active_options diagnostics report zero rows.")
        return 1
    if chain_size > 0 and degraded_rows > 0:
        print("[verify-hotfix] chain has data but degraded_rows > 0; fallback/degraded rows are forbidden.")
        return 1
    if chain_size > 0 and real_rows > 0 and missing_turnover_rows >= real_rows:
        print("[verify-hotfix] all real rows are missing turnover; turnover hotfix regression suspected.")
        return 1

    print("[verify-hotfix] PASS")
    return 0


def build_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("verify-active-options-hotfix", help="Verify active options hotfix diagnostics")
    parser.add_argument("--api-base", default="http://127.0.0.1:8001")
    parser.add_argument("--timeout-sec", type=int, default=5)
    parser.set_defaults(func=run_verify_active_options_hotfix)
