"""OI Snapshot Cache — Redis-backed Open Interest history.

Provides per-strike OI snapshots so the DEG-FLOW FlowEngine_G can
compute ΔOI (Open Interest momentum) without requiring tick-level data.

Key schema:
    oi:spy:{YYYYMMDD}:{symbol}  →  int (OI value)
    TTL = 86400s (one trading day)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_OI_KEY_PREFIX = "oi:spy"
_OI_TTL_SECONDS = 86_400  # 24 hours — one trading session


def _make_key(symbol: str, date_str: str) -> str:
    """Build the Redis key for the OI snapshot."""
    return f"{_OI_KEY_PREFIX}:{date_str}:{symbol}"


async def save_oi_snapshot(
    redis,
    chain: list[dict],
    *,
    date_str: str | None = None,
) -> int:
    """Persist current OI values for all strikes in the chain.

    Args:
        redis:     Redis async client (or None — silently skips).
        chain:     Option chain entries, each must have 'symbol' and 'open_interest'.
        date_str:  Override date key (YYYYMMDD).  Defaults to today ET.

    Returns:
        Number of keys written (0 if Redis unavailable).
    """
    if not redis:
        return 0

    if date_str is None:
        date_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")

    written = 0
    try:
        pipe = redis.pipeline()
        for opt in chain:
            symbol = opt.get("symbol")
            oi = opt.get("open_interest")
            if not symbol or oi is None:
                continue
            key = _make_key(symbol, date_str)
            pipe.set(key, int(oi), ex=_OI_TTL_SECONDS)
            written += 1
        await pipe.execute()
        logger.debug(f"[OICache] Saved {written} OI snapshots for {date_str}")
    except Exception as exc:
        logger.warning(f"[OICache] save_oi_snapshot failed: {exc}")
        return 0

    return written


async def get_oi_delta(
    redis,
    symbol: str,
    current_oi: int,
    *,
    date_str: str | None = None,
) -> int:
    """Return ΔOI = current_oi − prev_oi for a given symbol.

    Falls back to 0 (no signal) if Redis is unavailable or key is missing.

    Args:
        redis:       Redis async client (or None).
        symbol:      Option contract symbol.
        current_oi:  Latest OI value from the chain snapshot.
        date_str:    Date key override (YYYYMMDD).

    Returns:
        int — ΔOI.  Positive = new positions opened, Negative = closed.
    """
    if not redis:
        return 0

    if date_str is None:
        date_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")

    try:
        key = _make_key(symbol, date_str)
        raw = await redis.get(key)
        if raw is None:
            return 0  # Cache miss — degraded gracefully
        prev_oi = int(raw)
        return current_oi - prev_oi
    except Exception as exc:
        logger.warning(f"[OICache] get_oi_delta failed for {symbol}: {exc}")
        return 0


async def get_oi_cache_stats(
    redis,
    *,
    date_str: str | None = None,
) -> dict:
    """Diagnostic helper for the audit harness (Phase 20)."""
    if not redis:
        return {"available": False, "key_count": 0}

    if date_str is None:
        date_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")

    try:
        pattern = f"{_OI_KEY_PREFIX}:{date_str}:*"
        keys = await redis.keys(pattern)
        return {
            "available": True,
            "key_count": len(keys),
            "date": date_str,
        }
    except Exception as exc:
        logger.warning(f"[OICache] stats failed: {exc}")
        return {"available": False, "error": str(exc)}
