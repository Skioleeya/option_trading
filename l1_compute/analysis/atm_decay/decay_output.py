"""ATM decay output orchestration helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from .anchor import build_anchor_leg_diagnostics
from .models import ET, MAX_CONSECUTIVE_RAW_PCT_FAILURES
from .raw_pct import RawPctResult

DECAY_ZERO_EPSILON = 1e-9
DECAY_DUPLICATE_EPSILON = 1e-6


def handle_raw_pct_unavailable(
    tracker: Any,
    chain: list[dict[str, Any]],
    raw_result: RawPctResult,
    logger: Any,
) -> None:
    """Record diagnostics and invalidate dead anchors on price failures."""
    _append_raw_pct_diagnostic(tracker, chain, raw_result, logger)
    if raw_result.failure_kind == "freshness":
        logger.warning("[AtmDecayFreshness] leg freshness rejected sample: %s", raw_result.leg_freshness)
        return
    tracker._raw_pct_failure_streak += 1  # noqa: SLF001 - tracker helper
    if tracker.anchor and tracker._raw_pct_failure_streak >= MAX_CONSECUTIVE_RAW_PCT_FAILURES:  # noqa: SLF001
        _invalidate_after_price_failures(tracker, logger)


def build_decay_item(
    *,
    anchor: dict[str, Any],
    call_pct: float,
    put_pct: float,
    straddle_pct: float,
    ts: datetime,
    strike_changed: bool,
    source_timestamp: str | None,
    source_gap_ms: float | None,
    stale_recovery: bool,
    leg_freshness: dict[str, Any],
) -> dict[str, Any]:
    return {
        "strike": anchor["strike"],
        "base_strike": anchor.get("base_strike", anchor["strike"]),
        "locked_at": datetime.fromisoformat(anchor["timestamp"]).strftime("%H:%M:%S"),
        "call_pct": call_pct,
        "put_pct": put_pct,
        "straddle_pct": straddle_pct,
        "timestamp": ts.isoformat(),
        "strike_changed": strike_changed,
        "source_timestamp": source_timestamp,
        "source_gap_ms": source_gap_ms,
        "stale_recovery": stale_recovery,
        "leg_freshness": leg_freshness,
    }


def is_flat_decay(call_pct: float, put_pct: float, straddle_pct: float) -> bool:
    return (
        abs(call_pct) < DECAY_ZERO_EPSILON
        and abs(put_pct) < DECAY_ZERO_EPSILON
        and abs(straddle_pct) < DECAY_ZERO_EPSILON
    )


def should_store_decay(prev: tuple[float, float, float] | None, current: tuple[float, float, float]) -> bool:
    if prev is None:
        return True
    return any(abs(current[idx] - prev[idx]) >= DECAY_DUPLICATE_EPSILON for idx in range(len(current)))


def record_flat_post_lock_if_needed(
    tracker: Any,
    chain: list[dict[str, Any]],
    *,
    ts: datetime,
    pcts: tuple[float, float, float],
    logger: Any,
) -> None:
    if tracker._opening_tick_pending or not is_flat_decay(*pcts):  # noqa: SLF001
        return
    diagnostic = build_anchor_leg_diagnostics(tracker.anchor, chain)
    if diagnostic is None:
        return
    diagnostic["reason"] = "flat_post_lock_row"
    diagnostic["tracker_today"] = tracker._today  # noqa: SLF001
    diagnostic["timestamp"] = ts.isoformat()
    diagnostic["call_pct"], diagnostic["put_pct"], diagnostic["straddle_pct"] = pcts
    diagnostic["previous_pcts"] = list(tracker._prev_pcts) if tracker._prev_pcts is not None else None  # noqa: SLF001
    logger.warning("[AtmDecay] post-lock flat row stored; anchor-leg diagnostics=%s", diagnostic)
    asyncio.ensure_future(tracker._storage.append_anchor_diagnostic(tracker._today, diagnostic))  # noqa: SLF001


def store_decay_item(
    tracker: Any,
    item: dict[str, Any],
    *,
    ts: datetime,
    pcts: tuple[float, float, float],
    logger: Any,
) -> None:
    tracker._opening_tick_pending = False  # noqa: SLF001
    tracker._prev_pcts = pcts  # noqa: SLF001
    if tracker._strike_changed_flag:  # noqa: SLF001
        tracker._strike_changed_flag = False  # noqa: SLF001
    asyncio.ensure_future(tracker._storage.append_series(ts.strftime("%Y%m%d"), item))  # noqa: SLF001
    logger.info("[AtmDecay] %s | C:%+.4f  P:%+.4f  S:%+.4f (stored)", int(tracker.anchor["strike"]), *pcts)


def _append_raw_pct_diagnostic(
    tracker: Any,
    chain: list[dict[str, Any]],
    raw_result: RawPctResult,
    logger: Any,
) -> None:
    diagnostic = build_anchor_leg_diagnostics(tracker.anchor, chain)
    if diagnostic is None:
        return
    diagnostic["reason"] = "raw_pct_unavailable"
    diagnostic["tracker_today"] = tracker._today  # noqa: SLF001
    diagnostic["timestamp"] = datetime.now(ET).isoformat()
    diagnostic["leg_freshness"] = raw_result.leg_freshness
    logger.warning("[AtmDecay] decay compute skipped; anchor-leg diagnostics=%s", diagnostic)
    asyncio.ensure_future(tracker._storage.append_anchor_diagnostic(tracker._today, diagnostic))  # noqa: SLF001


def _invalidate_after_price_failures(tracker: Any, logger: Any) -> None:
    strike = tracker.anchor.get("strike")
    failures = tracker._raw_pct_failure_streak  # noqa: SLF001
    logger.warning(
        "[AtmDecayTracker] Consecutive raw-pct failures hit threshold=%s for strike=%s; invalidating anchor.",
        MAX_CONSECUTIVE_RAW_PCT_FAILURES,
        strike,
    )
    tracker.invalidate_anchor()
    asyncio.ensure_future(tracker._storage.delete_anchor(tracker._today))  # noqa: SLF001
    logger.info("[AtmDecayTracker] Persisted anchor cleared after %s consecutive raw-pct failures.", failures)
