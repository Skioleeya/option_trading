"""Orchestration helpers for ATM decay tracker state transitions."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from shared.config import settings

from .anchor import (
    calculate_raw_pct,
    select_opening_anchor,
    select_roll_anchor,
    validate_anchor,
)
from .models import ET, MAX_ANCHOR_DISTANCE, is_valid_spot, spot_distance
from .stitching import advance_factor, default_stitch_factor, factor_to_legacy_offset, legacy_offset_to_factor

logger = logging.getLogger(__name__)


def _is_flat_zero_point(item: dict[str, Any] | None) -> bool:
    if not isinstance(item, dict):
        return False
    try:
        return (
            abs(float(item.get("call_pct", 0.0))) < 1e-9
            and abs(float(item.get("put_pct", 0.0))) < 1e-9
            and abs(float(item.get("straddle_pct", 0.0))) < 1e-9
        )
    except (TypeError, ValueError):
        return False


def _locked_at_matches_anchor(item: dict[str, Any] | None, anchor: dict[str, Any]) -> bool:
    if not isinstance(item, dict):
        return False
    try:
        anchor_locked_at = datetime.fromisoformat(str(anchor["timestamp"])).strftime("%H:%M:%S")
    except (KeyError, TypeError, ValueError):
        return False
    return str(item.get("locked_at") or "").strip() == anchor_locked_at


async def _is_bad_restore_anchor(tracker: Any, date_str: str, anchor: dict[str, Any], source: str) -> bool:
    latest = await tracker._storage.get_latest_history_point(date_str)  # noqa: SLF001 - runtime helper
    if not _locked_at_matches_anchor(latest, anchor) or not _is_flat_zero_point(latest):
        return False
    logger.warning(
        "[AtmDecayTracker] %s anchor discarded (latest history is flat zero opening point): date=%s strike=%.2f locked_at=%s",
        source,
        date_str,
        float(anchor["strike"]),
        latest.get("locked_at"),
    )
    return True


async def initialize_tracker(tracker: Any, spot: float = 0.0) -> None:
    now = datetime.now(ET)
    tracker._today = now.strftime("%Y%m%d")  # noqa: SLF001 - runtime helper
    tracker._pending_restore_anchor = None  # noqa: SLF001 - runtime helper
    tracker._pending_restore_source = None  # noqa: SLF001 - runtime helper

    if tracker.redis:
        try:
            anchor = await tracker._storage.load_anchor_from_redis(tracker._today)  # noqa: SLF001
            if anchor and validate_anchor(anchor):
                if await _is_bad_restore_anchor(tracker, tracker._today, anchor, "Redis"):
                    anchor = None
                else:
                    dist = spot_distance(anchor.get("strike"), spot)
                    if dist is None:
                        logger.warning(
                            "[AtmDecayTracker] Redis anchor skipped: spot unavailable for strict restore "
                            "(date=%s strike=%.2f spot=%s).",
                            tracker._today,
                            float(anchor["strike"]),
                            spot,
                        )
                        tracker._pending_restore_anchor = anchor  # noqa: SLF001
                        tracker._pending_restore_source = "redis"  # noqa: SLF001
                        logger.info(
                            "[AtmDecayTracker] Redis anchor deferred for later restore when spot is available "
                            "(date=%s strike=%.2f).",
                            tracker._today,
                            float(anchor["strike"]),
                        )
                        tracker.is_initialized = True
                        return
                    if dist > MAX_ANCHOR_DISTANCE:
                        logger.warning(
                            "[AtmDecayTracker] Redis anchor discarded (distance check): "
                            "date=%s strike=%.2f spot=%.2f diff=%.2f max=%.2f",
                            tracker._today,
                            float(anchor["strike"]),
                            float(spot),
                            dist,
                            MAX_ANCHOR_DISTANCE,
                        )
                    else:
                        tracker.anchor = anchor
                        load_stitch_state(tracker, anchor)
                        logger.info(
                            "[AtmDecayTracker] Restored anchor from Redis: strike=%s (spot=%s)",
                            anchor["strike"],
                            spot if spot else "N/A",
                        )
                        tracker.is_initialized = True
                        return
            elif anchor:
                logger.warning("[AtmDecayTracker] Redis anchor failed validation — discarding")
        except Exception as exc:
            logger.error("[AtmDecayTracker] Redis read failed: %s", exc)

    try:
        anchor = tracker._storage.load_anchor_from_cold(tracker._today)  # noqa: SLF001
        if anchor and validate_anchor(anchor):
            if await _is_bad_restore_anchor(tracker, tracker._today, anchor, "Cold JSON"):
                anchor = None
            else:
                dist = spot_distance(anchor.get("strike"), spot)
                if dist is None:
                    logger.warning(
                        "[AtmDecayTracker] Cold JSON anchor skipped: spot unavailable for strict restore "
                        "(date=%s strike=%.2f spot=%s).",
                        tracker._today,
                        float(anchor["strike"]),
                        spot,
                    )
                    tracker._pending_restore_anchor = anchor  # noqa: SLF001
                    tracker._pending_restore_source = "cold_json"  # noqa: SLF001
                    logger.info(
                        "[AtmDecayTracker] Cold JSON anchor deferred for later restore when spot is available "
                        "(date=%s strike=%.2f).",
                        tracker._today,
                        float(anchor["strike"]),
                    )
                    tracker.is_initialized = True
                    return
                if dist > MAX_ANCHOR_DISTANCE:
                    logger.warning(
                        "[AtmDecayTracker] Cold JSON anchor discarded (distance check): "
                        "date=%s strike=%.2f spot=%.2f diff=%.2f max=%.2f",
                        tracker._today,
                        float(anchor["strike"]),
                        float(spot),
                        dist,
                        MAX_ANCHOR_DISTANCE,
                    )
                else:
                    tracker.anchor = anchor
                    load_stitch_state(tracker, anchor)
                    logger.info(
                        "[AtmDecayTracker] Restored anchor from cold JSON: strike=%s (spot=%s)",
                        anchor["strike"],
                        spot if spot else "N/A",
                    )
                    if tracker.redis:
                        try:
                            await tracker._storage.save_anchor(  # noqa: SLF001
                                tracker._today,
                                anchor,
                                settings.opening_atm_redis_ttl_seconds,
                            )
                        except Exception as exc:
                            logger.error("[AtmDecayTracker] Redis sync for cold-restored anchor failed: %s", exc)
                        await tracker._storage.recover_series_from_cold_if_needed(  # noqa: SLF001
                            tracker._today,
                            settings.opening_atm_redis_ttl_seconds,
                        )
                    tracker.is_initialized = True
                    return
        elif anchor:
            logger.warning("[AtmDecayTracker] Cold JSON anchor failed validation — discarding")
    except Exception as exc:
        logger.error("[AtmDecayTracker] Cold JSON read failed: %s", exc)

    logger.info("[AtmDecayTracker] No valid anchor for today. Will capture on current session ticks.")
    tracker.is_initialized = True


def invalidate_tracker(tracker: Any) -> None:
    if tracker.anchor:
        logger.warning(
            "[AtmDecayTracker] Anchor INVALIDATED (was strike=%s). Will re-capture on next tick.",
            tracker.anchor.get("strike"),
        )
    tracker.anchor = None
    tracker._prev_pcts = None  # noqa: SLF001 - runtime helper
    tracker._warmup_ticks_remaining = 5  # noqa: SLF001 - runtime helper
    tracker._recent_spots.clear()  # noqa: SLF001 - runtime helper
    tracker._opening_tick_pending = False  # noqa: SLF001 - runtime helper
    tracker.accumulated_factor = default_stitch_factor()
    tracker.accumulated_offset = factor_to_legacy_offset(tracker.accumulated_factor)
    tracker._pending_restore_anchor = None  # noqa: SLF001 - runtime helper
    tracker._pending_restore_source = None  # noqa: SLF001 - runtime helper


def load_stitch_state(tracker: Any, anchor: dict[str, Any]) -> None:
    raw_factor = anchor.get("accumulated_factor")
    if isinstance(raw_factor, dict):
        merged: dict[str, float] = default_stitch_factor()
        for key in ("c", "p", "s"):
            val = raw_factor.get(key, 1.0)
            try:
                merged[key] = max(0.0, float(val))
            except (TypeError, ValueError):
                merged[key] = 1.0
        tracker.accumulated_factor = merged
    else:
        tracker.accumulated_factor = legacy_offset_to_factor(anchor.get("accumulated_offset"))
    tracker.accumulated_offset = factor_to_legacy_offset(tracker.accumulated_factor)


def reset_for_new_day(tracker: Any, today: str) -> None:
    if tracker.anchor:
        logger.info(
            "[AtmDecayTracker] New trade date detected (%s -> %s). Resetting in-memory anchor/stitch state.",
            tracker._today,  # noqa: SLF001 - runtime helper
            today,
        )
    tracker._today = today  # noqa: SLF001 - runtime helper
    tracker.anchor = None
    tracker._prev_pcts = None  # noqa: SLF001 - runtime helper
    tracker._warmup_ticks_remaining = 5  # noqa: SLF001 - runtime helper
    tracker._out_of_bounds_ticks = 0  # noqa: SLF001 - runtime helper
    tracker._strike_changed_flag = False  # noqa: SLF001 - runtime helper
    tracker._recent_spots.clear()  # noqa: SLF001 - runtime helper
    tracker._opening_tick_pending = False  # noqa: SLF001 - runtime helper
    tracker.accumulated_factor = default_stitch_factor()
    tracker.accumulated_offset = factor_to_legacy_offset(tracker.accumulated_factor)
    tracker._pending_restore_anchor = None  # noqa: SLF001 - runtime helper
    tracker._pending_restore_source = None  # noqa: SLF001 - runtime helper


async def try_restore_pending_anchor(tracker: Any, spot: Any) -> bool:
    pending = tracker._pending_restore_anchor  # noqa: SLF001 - runtime helper
    if pending is None or not is_valid_spot(spot):
        return False
    if await _is_bad_restore_anchor(
        tracker,
        tracker._today,  # noqa: SLF001 - runtime helper
        pending,
        f"Deferred {tracker._pending_restore_source or 'unknown'}",
    ):
        tracker._pending_restore_anchor = None  # noqa: SLF001 - runtime helper
        tracker._pending_restore_source = None  # noqa: SLF001 - runtime helper
        return False
    spot_f = float(spot)
    dist = spot_distance(pending.get("strike"), spot_f)
    if dist is None:
        return False
    if dist > MAX_ANCHOR_DISTANCE:
        logger.warning(
            "[AtmDecayTracker] Deferred anchor discarded (distance check): date=%s source=%s strike=%.2f spot=%.2f diff=%.2f max=%.2f",
            tracker._today,  # noqa: SLF001 - runtime helper
            tracker._pending_restore_source or "unknown",  # noqa: SLF001 - runtime helper
            float(pending["strike"]),
            spot_f,
            dist,
            MAX_ANCHOR_DISTANCE,
        )
        tracker._pending_restore_anchor = None  # noqa: SLF001 - runtime helper
        tracker._pending_restore_source = None  # noqa: SLF001 - runtime helper
        return False

    tracker.anchor = pending
    load_stitch_state(tracker, pending)
    logger.info(
        "[AtmDecayTracker] Deferred anchor restored: source=%s strike=%.2f spot=%.2f",
        tracker._pending_restore_source or "unknown",  # noqa: SLF001 - runtime helper
        float(pending["strike"]),
        spot_f,
    )

    if tracker.redis and tracker._pending_restore_source == "cold_json":  # noqa: SLF001 - runtime helper
        try:
            await tracker._storage.save_anchor(  # noqa: SLF001 - runtime helper
                tracker._today,  # noqa: SLF001 - runtime helper
                pending,
                settings.opening_atm_redis_ttl_seconds,
            )
        except Exception as exc:
            logger.error("[AtmDecayTracker] Failed syncing deferred cold anchor to Redis: %s", exc)
        try:
            await tracker._storage.recover_series_from_cold_if_needed(  # noqa: SLF001 - runtime helper
                tracker._today,  # noqa: SLF001 - runtime helper
                settings.opening_atm_redis_ttl_seconds,
            )
        except Exception as exc:
            logger.error("[AtmDecayTracker] Failed recovering deferred cold series into Redis: %s", exc)

    tracker._pending_restore_anchor = None  # noqa: SLF001 - runtime helper
    tracker._pending_restore_source = None  # noqa: SLF001 - runtime helper
    return True


async def persist_anchor(tracker: Any, anchor: dict[str, Any]) -> None:
    anchor["accumulated_factor"] = dict(getattr(tracker, "accumulated_factor", default_stitch_factor()))
    anchor["accumulated_offset"] = factor_to_legacy_offset(anchor["accumulated_factor"])
    tracker.anchor = anchor
    tracker._opening_tick_pending = True  # noqa: SLF001 - runtime helper
    tracker._today = datetime.fromisoformat(anchor["timestamp"]).strftime("%Y%m%d")  # noqa: SLF001
    await tracker._storage.save_anchor(tracker._today, anchor, settings.opening_atm_redis_ttl_seconds)  # noqa: SLF001
    logger.info(
        "[AtmDecayTracker] ANCHOR LOCKED — strike=%s call=%s put=%s C$%.2f P$%.2f",
        anchor["strike"],
        anchor["call_symbol"],
        anchor["put_symbol"],
        anchor["call_price"],
        anchor["put_price"],
    )


async def capture_anchor(tracker: Any, chain: list[dict[str, Any]], spot: float, now: datetime) -> None:
    anchor = select_opening_anchor(chain, spot, now, logger=logger)
    if anchor:
        await persist_anchor(tracker, anchor)


async def roll_anchor(tracker: Any, chain: list[dict[str, Any]], spot: float, now: datetime) -> None:
    if not tracker.anchor:
        return

    next_anchor, same_strike = select_roll_anchor(tracker.anchor, chain, spot, now)
    if same_strike:
        tracker._out_of_bounds_ticks = 0  # noqa: SLF001 - runtime helper
        return
    if not next_anchor:
        return

    raw_pcts = calculate_raw_pct(tracker.anchor, chain)
    if raw_pcts:
        tracker.accumulated_factor["c"] = advance_factor(tracker.accumulated_factor.get("c", 1.0), raw_pcts[0])
        tracker.accumulated_factor["p"] = advance_factor(tracker.accumulated_factor.get("p", 1.0), raw_pcts[1])
        tracker.accumulated_factor["s"] = advance_factor(tracker.accumulated_factor.get("s", 1.0), raw_pcts[2])
        tracker.accumulated_offset = factor_to_legacy_offset(tracker.accumulated_factor)

    logger.warning(
        "[AtmDecay] Rolling anchor %s -> %s (SCM CDD stitched, offsets: S=%+.3f)",
        tracker.anchor["strike"],
        next_anchor["strike"],
        tracker.accumulated_offset["s"],
    )
    await persist_anchor(tracker, next_anchor)
    tracker._strike_changed_flag = True  # noqa: SLF001 - runtime helper
    tracker._out_of_bounds_ticks = 0  # noqa: SLF001 - runtime helper
