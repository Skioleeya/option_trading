"""Minimal SPY.US Rust dataflow MVP (live connectivity smoke).

Official Rust SDK reference:
https://github.com/longbridge/openapi/tree/master/rust

What this script validates:
1) REST quote path via Rust runtime gateway.
2) Streaming path via Rust gateway + Arrow IPC batch reader.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

from longport.openapi import SubType

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.services.l0_runtime.source import build_runtime_bundle
from shared.services.l0_runtime.source.runtime import ArrowIpcReader


def _pick_spot(rows: list[Any]) -> float | None:
    for row in rows:
        candidates: list[Any] = []
        if isinstance(row, dict):
            candidates.extend([row.get("last_done"), row.get("last_price"), row.get("price")])
        else:
            candidates.extend(
                [
                    getattr(row, "last_done", None),
                    getattr(row, "last_price", None),
                    getattr(row, "price", None),
                ]
            )
        for value in candidates:
            if value is None:
                continue
            try:
                return float(value)
            except Exception:
                pass
    return None


async def _read_one_batch(reader: ArrowIpcReader, timeout_sec: float) -> tuple[int, set[str]]:
    batch = await asyncio.wait_for(reader.read_next_batch(), timeout=timeout_sec)
    rows = batch.to_pylist()
    symbols: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get("symbol")
        if isinstance(value, str) and value:
            symbols.add(value)
    return len(rows), symbols


async def run_mvp(symbol: str, timeout_sec: float) -> dict[str, Any]:
    bundle = build_runtime_bundle()
    runtime = bundle.quote_runtime
    reader = ArrowIpcReader()
    t0 = time.time()
    result: dict[str, Any] = {
        "symbol": symbol,
        "ok": False,
        "rest_quote_rows": 0,
        "rest_spot": None,
        "stream_rows": 0,
        "stream_symbols": [],
        "transport": {},
        "diagnostics": {},
        "error": None,
        "elapsed_sec": 0.0,
    }

    try:
        await runtime.connect()
        rest_rows = await runtime.quote([symbol])
        result["rest_quote_rows"] = len(rest_rows)
        result["rest_spot"] = _pick_spot(rest_rows)

        quote_subtype = getattr(SubType, "Quote", None) or getattr(SubType, "QUOTE", None)
        if quote_subtype is None:
            raise RuntimeError("unable to resolve quote subtype from longport.openapi.SubType")
        await runtime.subscribe([symbol], [quote_subtype])
        transport = runtime.transport_contract()
        result["transport"] = dict(transport or {})
        if transport.get("transport") != "arrow_ipc_named_event":
            raise RuntimeError(f"unexpected transport: {transport}")

        shm_path = str(transport.get("shm_path") or "").strip()
        signal_name = str(transport.get("signal_name") or "").strip()
        if not shm_path or not signal_name:
            raise RuntimeError(f"incomplete transport contract: {transport}")

        reader.connect(shm_path, signal_name)
        row_count, symbols = await _read_one_batch(reader, timeout_sec=timeout_sec)
        result["stream_rows"] = row_count
        result["stream_symbols"] = sorted(symbols)
        result["diagnostics"] = runtime.diagnostics()
        result["ok"] = bool(result["rest_quote_rows"] > 0 and result["stream_rows"] > 0)
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        try:
            result["diagnostics"] = runtime.diagnostics()
        except Exception:
            pass
    finally:
        result["elapsed_sec"] = round(time.time() - t0, 3)
        reader.close()
        await runtime.disconnect()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="SPY.US Rust live dataflow MVP")
    parser.add_argument("--symbol", default="SPY.US", help="Quote symbol (default: SPY.US)")
    parser.add_argument(
        "--timeout-sec",
        type=float,
        default=25.0,
        help="Arrow batch wait timeout in seconds (default: 25)",
    )
    args = parser.parse_args()

    result = asyncio.run(run_mvp(symbol=args.symbol, timeout_sec=max(1.0, args.timeout_sec)))
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("ok"):
        print("[MVP] PASS: Rust REST + stream dataflow connected for", args.symbol)
        return 0
    print("[MVP] FAIL:", result.get("error"))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
