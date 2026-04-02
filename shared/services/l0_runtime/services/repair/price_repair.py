from __future__ import annotations

import logging
from typing import Any, Callable

from shared.services.l0_runtime.services.sync.support import (
    PRICE_REPAIR_BATCH_LIMIT,
    apply_repair_rows,
    pick_price_repair_candidates,
)
from shared.services.l0_runtime.source.runtime.quote_runtime import L0QuoteRuntime
from shared.services.l0_runtime.source.runtime.rate_limiter import APIRateLimiter

logger = logging.getLogger(__name__)


async def repair_symbol_prices(
    *,
    batch: list[str],
    repair_symbols: set[str],
    needs_price_repair: Callable[[str], bool],
    last_repair_at: dict[str, float],
    now_mono: float,
    runtime: L0QuoteRuntime,
    limiter: APIRateLimiter,
    on_update: Callable[[str, Any], None],
    log_prefix: str,
) -> int:
    candidates = pick_price_repair_candidates(
        batch=batch,
        repair_symbols=repair_symbols,
        needs_price_repair=needs_price_repair,
        last_repair_at=last_repair_at,
        now_mono=now_mono,
    )
    if not candidates:
        return 0

    async with limiter.acquire(weight=len(candidates)):
        rows = await runtime.option_quote(candidates)

    applied = apply_repair_rows(list(rows or []), now_mono=now_mono)
    for item in applied.get("updates", []):
        symbol = str(item.get("symbol", "") or "")
        update = item.get("item")
        if not symbol or update is None:
            continue
        last_repair_at[symbol] = now_mono
        on_update(symbol, update)
    updated = int(applied.get("updated", 0) or 0)

    logger.info(
        "%s option_quote price repair attempted: symbols=%d limit=%d",
        log_prefix,
        len(candidates),
        PRICE_REPAIR_BATCH_LIMIT,
    )
    return updated

