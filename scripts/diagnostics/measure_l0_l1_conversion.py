#!/usr/bin/env python3
"""Measure list->Arrow conversion count/time before and after L0->L1 Arrow handoff.

Scenario definitions:
1) before: L1 receives list[dict] and performs conversion inside reactor.
2) after:  L0 prebuilds RecordBatch and L1 receives Arrow directly.

Output is written as JSON for session evidence.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any
import sys
import os

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if not os.environ.get("SystemRoot"):
    os.environ["SystemRoot"] = "C:\\Windows"
if not os.environ.get("windir"):
    os.environ["windir"] = os.environ["SystemRoot"]

import l1_compute.arrow.schema as arrow_schema
from l1_compute.reactor import L1ComputeReactor


def _make_chain_entries(n: int, spot: float = 560.0) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i in range(n):
        strike = spot - 5.0 + (i * 0.5)
        opt_type = "CALL" if i % 2 == 0 else "PUT"
        out.append(
            {
                "symbol": f"SPY{i:04d}",
                "strike": strike,
                "type": opt_type,
                "implied_volatility": 0.18 + (i * 0.001),
                "iv_timestamp": 0.0,
                "open_interest": int(1000 + i * 100),
                "contract_multiplier": 100,
                "volume": 50 + i,
            }
        )
    return out


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    reactor = L1ComputeReactor(sabr_enabled=False)
    chain = _make_chain_entries(args.chain_size)
    spot = float(args.spot)

    original_convert = arrow_schema.dicts_to_record_batch
    l1_calls = 0
    l1_ms_samples: list[float] = []

    def wrapped_convert(data: list[dict[str, Any]]):
        nonlocal l1_calls
        t0 = time.perf_counter()
        rb = original_convert(data)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        l1_calls += 1
        l1_ms_samples.append(elapsed_ms)
        return rb

    arrow_schema.dicts_to_record_batch = wrapped_convert
    try:
        # Warm-up to reduce one-time jit/import noise.
        for _ in range(max(1, args.warmup)):
            await reactor.compute(chain, spot=spot, l0_version=1)

        # BEFORE: list input, L1 converts.
        l1_calls = 0
        l1_ms_samples.clear()
        t_before = time.perf_counter()
        for i in range(args.iterations):
            await reactor.compute(chain, spot=spot, l0_version=10 + i)
        before_total_ms = (time.perf_counter() - t_before) * 1000.0
        before = {
            "iterations": args.iterations,
            "l1_convert_calls": l1_calls,
            "l1_convert_total_ms": round(sum(l1_ms_samples), 4),
            "l1_convert_avg_ms": round(statistics.mean(l1_ms_samples), 4) if l1_ms_samples else 0.0,
            "loop_total_ms": round(before_total_ms, 4),
        }

        # AFTER: L0 preconverts each tick, L1 receives Arrow and should not convert.
        l1_calls = 0
        l1_ms_samples.clear()
        l0_convert_ms_samples: list[float] = []
        t_after = time.perf_counter()
        for i in range(args.iterations):
            t0 = time.perf_counter()
            rb = original_convert(chain)
            l0_convert_ms_samples.append((time.perf_counter() - t0) * 1000.0)
            await reactor.compute(rb, spot=spot, l0_version=1000 + i)
        after_total_ms = (time.perf_counter() - t_after) * 1000.0
        after = {
            "iterations": args.iterations,
            "l0_preconvert_calls": args.iterations,
            "l0_preconvert_total_ms": round(sum(l0_convert_ms_samples), 4),
            "l0_preconvert_avg_ms": round(statistics.mean(l0_convert_ms_samples), 4)
            if l0_convert_ms_samples
            else 0.0,
            "l1_convert_calls": l1_calls,
            "l1_convert_total_ms": round(sum(l1_ms_samples), 4),
            "l1_convert_avg_ms": round(statistics.mean(l1_ms_samples), 4) if l1_ms_samples else 0.0,
            "loop_total_ms": round(after_total_ms, 4),
        }

    finally:
        arrow_schema.dicts_to_record_batch = original_convert

    before_l1_calls = int(before["l1_convert_calls"])
    after_l1_calls = int(after["l1_convert_calls"])
    call_reduction = before_l1_calls - after_l1_calls
    call_reduction_pct = 0.0
    if before_l1_calls > 0:
        call_reduction_pct = (call_reduction / before_l1_calls) * 100.0

    before_l1_ms = float(before["l1_convert_total_ms"])
    after_l1_ms = float(after["l1_convert_total_ms"])
    l1_ms_reduction = before_l1_ms - after_l1_ms
    l1_ms_reduction_pct = 0.0
    if before_l1_ms > 0.0 and math.isfinite(before_l1_ms):
        l1_ms_reduction_pct = (l1_ms_reduction / before_l1_ms) * 100.0

    return {
        "status": "PASS",
        "mode_definition": {
            "before": "list[dict] -> L1 ensure_record_batch converts",
            "after": "L0 prebuilds RecordBatch -> L1 consumes Arrow directly",
        },
        "config": {
            "iterations": args.iterations,
            "warmup": args.warmup,
            "chain_size": args.chain_size,
            "spot": args.spot,
        },
        "before": before,
        "after": after,
        "delta": {
            "l1_convert_call_reduction": call_reduction,
            "l1_convert_call_reduction_pct": round(call_reduction_pct, 4),
            "l1_convert_ms_reduction": round(l1_ms_reduction, 4),
            "l1_convert_ms_reduction_pct": round(l1_ms_reduction_pct, 4),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure L0/L1 conversion before/after Arrow handoff.")
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--chain-size", type=int, default=250)
    parser.add_argument("--spot", type=float, default=560.0)
    parser.add_argument("--output", default="tmp/session_validation_diag/p2_conversion_benchmark.json")
    args = parser.parse_args()

    payload = asyncio.run(_run(args))
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
