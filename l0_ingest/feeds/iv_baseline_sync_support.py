from __future__ import annotations

import math
from typing import Any, Iterable

MAX_WARM_UP_SUBSCRIPTION_CAP = 500
MIN_BATCH_SIZE = 1
MAX_BATCH_SIZE = 50
WARMUP_COOLDOWN_SECONDS = 60
WARMUP_COOLDOWN_SLEEP_SECONDS = 10.0
SYNC_COOLDOWN_SLEEP_SECONDS = 5.0
SYNC_CHUNK_COUNT = 2


def clamp_subscription_cap(raw_cap: Any) -> int:
    try:
        cap = int(raw_cap)
    except (TypeError, ValueError):
        cap = MAX_WARM_UP_SUBSCRIPTION_CAP
    cap = max(MIN_BATCH_SIZE, cap)
    return min(cap, MAX_WARM_UP_SUBSCRIPTION_CAP)


def safe_batch_size(max_symbol_weight: Any) -> int:
    try:
        weight = int(max_symbol_weight)
    except (TypeError, ValueError):
        weight = MAX_BATCH_SIZE
    return max(MIN_BATCH_SIZE, min(MAX_BATCH_SIZE, weight))


def iter_batches(symbols: list[str], batch_size: int) -> Iterable[list[str]]:
    size = max(MIN_BATCH_SIZE, int(batch_size))
    for i in range(0, len(symbols), size):
        yield symbols[i : i + size]


def split_sync_chunks(symbols: list[str]) -> list[list[str]]:
    if not symbols:
        return []
    half = len(symbols) // SYNC_CHUNK_COUNT
    return [symbols[:half], symbols[half:]]


def parse_implied_volatility(item: Any) -> float | None:
    iv_normalized = getattr(item, "implied_volatility_decimal", None)
    if iv_normalized is not None:
        try:
            f_iv = float(iv_normalized)
        except (TypeError, ValueError):
            return None
        if math.isfinite(f_iv):
            return f_iv
        return None

    iv_raw = getattr(item, "implied_volatility", None)
    if not iv_raw:
        return None
    try:
        f_iv = float(iv_raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f_iv):
        return None
    return f_iv / 100.0 if f_iv > 1.0 else f_iv


def parse_open_interest(item: Any) -> int | None:
    oi_raw = getattr(item, "open_interest", None)
    if not oi_raw:
        return None
    try:
        return int(oi_raw)
    except (TypeError, ValueError):
        return None


def is_rate_limit_error(exc: Exception) -> bool:
    return "301607" in str(exc)
