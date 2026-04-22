"""Replay a sparse ActiveOptions chain to exercise partial fallback.

Usage:
    python scripts/diag/replay_active_options_partial_fallback.py
    python scripts/diag/replay_active_options_partial_fallback.py --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.services.active_options_runtime import ActiveOptionsRuntimeService


def _chain_row(
    symbol: str,
    volume: int,
    turnover: float,
    strike: float,
    option_type: str = "C",
) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "option_type": option_type,
        "strike": strike,
        "volume": volume,
        "current_volume": volume,
        "turnover": turnover,
        "implied_volatility": 0.2,
        "historical_volatility": 0.18,
        "open_interest": 1000,
        "gamma": 0.01,
        "vanna": 0.02,
        "last_price": 2.5,
    }


def _build_sparse_chain() -> list[dict[str, Any]]:
    return [
        _chain_row("SPY_REAL_1", 220, 220_000.0, 560.0, "C"),
        _chain_row("SPY_REAL_2", 180, 180_000.0, 561.0, "P"),
        _chain_row("SPY_FB_1", 40, 500_000.0, 562.0, "C"),
        _chain_row("SPY_FB_2", 30, 450_000.0, 563.0, "P"),
        _chain_row("SPY_FB_3", 20, 400_000.0, 564.0, "C"),
    ]


async def _run_replay(limit: int) -> dict[str, Any]:
    service = ActiveOptionsRuntimeService()
    await service.update_background(
        chain=_build_sparse_chain(),
        spot=560.0,
        atm_iv=0.2,
        redis=None,
        limit=limit,
    )
    rows = service.get_latest()
    diag = service.get_diagnostics()
    return {
        "diagnostics": {
            "rows_total": diag.get("rows_total"),
            "rows_real": diag.get("rows_real"),
            "rows_real_non_synthetic": diag.get("rows_real_non_synthetic"),
            "rows_synthetic_fallback": diag.get("rows_synthetic_fallback"),
            "filtered_candidates_count": diag.get("filtered_candidates_count"),
            "supplemented_rows": diag.get("supplemented_rows"),
            "partial_fallback_count": diag.get("partial_fallback_count"),
            "last_partial_fallback_mode": diag.get("last_partial_fallback_mode"),
            "last_fallback_mode": diag.get("last_fallback_mode"),
        },
        "rows": [
            {
                "slot_index": row.get("slot_index"),
                "symbol": row.get("symbol"),
                "contract_symbol": row.get("contract_symbol"),
                "option_type": row.get("option_type"),
                "strike": row.get("strike"),
                "row_quality": row.get("row_quality"),
                "fallback_reason": row.get("fallback_reason"),
                "is_placeholder": row.get("is_placeholder"),
                "is_synthetic_fallback": row.get("is_synthetic_fallback"),
            }
            for row in rows
        ],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay a sparse ActiveOptions chain to prove partial fallback behavior."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Target ActiveOptions row limit. Default: 5.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON only.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = asyncio.run(_run_replay(max(1, int(args.limit))))

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
        return 0

    diag = result["diagnostics"]
    print("=== ActiveOptions Partial Fallback Replay ===")
    print(f"rows_total              : {diag['rows_total']}")
    print(f"rows_real               : {diag['rows_real']}")
    print(f"rows_real_non_synthetic : {diag['rows_real_non_synthetic']}")
    print(f"rows_synthetic_fallback : {diag['rows_synthetic_fallback']}")
    print(f"filtered_candidates     : {diag['filtered_candidates_count']}")
    print(f"supplemented_rows       : {diag['supplemented_rows']}")
    print(f"partial_fallback_count  : {diag['partial_fallback_count']}")
    print(f"last_partial_mode       : {diag['last_partial_fallback_mode']}")
    print(f"last_fallback_mode      : {diag['last_fallback_mode']}")
    print("rows:")
    for row in result["rows"]:
        print(
            "  "
            f"slot={row['slot_index']} "
            f"contract={row['contract_symbol'] or row['symbol']} "
            f"type={row['option_type']} "
            f"strike={row['strike']} "
            f"quality={row['row_quality']} "
            f"fallback={row['fallback_reason']} "
            f"placeholder={row['is_placeholder']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
