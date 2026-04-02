from __future__ import annotations

import math
from typing import Any, Iterable

from ._native_sync_support import (
    apply_repair_rows_native,
    clamp_subscription_cap_native,
    is_rate_limit_error_native,
    parse_implied_volatility_native,
    parse_open_interest_native,
    pick_price_repair_candidates_native,
    safe_batch_size_native,
    split_sync_chunks_native,
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
    return clamp_subscription_cap_native(raw_cap)


def safe_batch_size(max_symbol_weight: Any) -> int:
    return safe_batch_size_native(max_symbol_weight)


def iter_batches(symbols: list[str], batch_size: int) -> Iterable[list[str]]:
    size = max(MIN_BATCH_SIZE, int(batch_size))
    for i in range(0, len(symbols), size):
        yield symbols[i : i + size]


def split_sync_chunks(symbols: list[str]) -> list[list[str]]:
    return split_sync_chunks_native(symbols)


def parse_implied_volatility(item: Any) -> float | None:
    value = parse_implied_volatility_native(item)
    return value if value is None or math.isfinite(value) else None


def parse_open_interest(item: Any) -> int | None:
    return parse_open_interest_native(item)


def is_rate_limit_error(exc: Exception) -> bool:
    return is_rate_limit_error_native(exc)


def pick_price_repair_candidates(
    *,
    batch: list[str],
    repair_symbols: set[str],
    needs_price_repair: callable,
    last_repair_at: dict[str, float],
    now_mono: float,
) -> list[str]:
    eligible_symbols = {
        symbol
        for symbol in batch
        if symbol in repair_symbols and needs_price_repair(symbol)
    }
    return pick_price_repair_candidates_native(
        batch=batch,
        eligible_symbols=eligible_symbols,
        last_repair_at=last_repair_at,
        now_mono=now_mono,
    )


def apply_repair_rows(
    rows: list[Any],
    *,
    now_mono: float,
) -> dict[str, Any]:
    return apply_repair_rows_native(rows, now_mono)
