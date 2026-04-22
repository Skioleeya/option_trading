"""Synchronization service namespace for L0 V2."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable

from shared.services.l0_runtime.native_loader import load_l0_rust

_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "_native_generated"
_L0_RUST = load_l0_rust(
    candidates=[
        _PACKAGE_DIR / "wave7" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave6" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave5" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave4" / "l0_rust.pyd",
        _PACKAGE_DIR / "l0_rust.pyd",
    ],
    module_suffix="l0_rust_wave7_sync_support",
)

MAX_WARM_UP_SUBSCRIPTION_CAP = 500
MIN_BATCH_SIZE = 1
MAX_BATCH_SIZE = 50
WARMUP_COOLDOWN_SECONDS = 60
WARMUP_COOLDOWN_SLEEP_SECONDS = 10.0
SYNC_COOLDOWN_SLEEP_SECONDS = 5.0
SYNC_CHUNK_COUNT = 2
PRICE_REPAIR_BATCH_LIMIT = 4
PRICE_REPAIR_COOLDOWN_SECONDS = 15.0


def clamp_subscription_cap(raw_cap: Any) -> int:
    return int(_L0_RUST.l0_sync_clamp_subscription_cap(raw_cap))


def safe_batch_size(max_symbol_weight: Any) -> int:
    return int(_L0_RUST.l0_sync_safe_batch_size(max_symbol_weight))


def iter_batches(symbols: list[str], batch_size: int) -> Iterable[list[str]]:
    size = max(MIN_BATCH_SIZE, int(batch_size))
    for i in range(0, len(symbols), size):
        yield symbols[i : i + size]


def split_sync_chunks(symbols: list[str]) -> list[list[str]]:
    return [list(chunk) for chunk in _L0_RUST.l0_sync_split_sync_chunks(list(symbols))]


def parse_implied_volatility(item: Any) -> float | None:
    value = _L0_RUST.l0_sync_parse_implied_volatility(item)
    value = None if value is None else float(value)
    return value if value is None or math.isfinite(value) else None


def parse_open_interest(item: Any) -> int | None:
    value = _L0_RUST.l0_sync_parse_open_interest(item)
    return None if value is None else int(value)


def is_rate_limit_error(exc: Exception) -> bool:
    return bool(_L0_RUST.l0_sync_is_rate_limit_error(str(exc)))


def pick_price_repair_candidates(
    *,
    batch: list[str],
    repair_symbols: set[str],
    needs_price_repair: Any,
    last_repair_at: dict[str, float],
    now_mono: float,
) -> list[str]:
    eligible_symbols = {symbol for symbol in batch if symbol in repair_symbols and needs_price_repair(symbol)}
    return list(
        _L0_RUST.l0_sync_pick_price_repair_candidates(
            list(batch),
            sorted(eligible_symbols),
            dict(last_repair_at),
            float(now_mono),
        )
    )


def apply_repair_rows(rows: list[Any], *, now_mono: float) -> dict[str, Any]:
    data = dict(_L0_RUST.l0_sync_apply_repair_rows(list(rows), float(now_mono)))
    data["updates"] = [dict(item) for item in data.get("updates", [])]
    data["last_repair_at"] = dict(data.get("last_repair_at", {}))
    return data


from .core import IVBaselineSync

__all__ = [
    "IVBaselineSync",
    "MAX_WARM_UP_SUBSCRIPTION_CAP",
    "MIN_BATCH_SIZE",
    "MAX_BATCH_SIZE",
    "WARMUP_COOLDOWN_SECONDS",
    "WARMUP_COOLDOWN_SLEEP_SECONDS",
    "SYNC_COOLDOWN_SLEEP_SECONDS",
    "SYNC_CHUNK_COUNT",
    "PRICE_REPAIR_BATCH_LIMIT",
    "PRICE_REPAIR_COOLDOWN_SECONDS",
    "apply_repair_rows",
    "clamp_subscription_cap",
    "is_rate_limit_error",
    "iter_batches",
    "parse_implied_volatility",
    "parse_open_interest",
    "pick_price_repair_candidates",
    "safe_batch_size",
    "split_sync_chunks",
]
