"""ATM Decay tracker orchestrator."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from longport.openapi import QuoteContext
from redis.asyncio import Redis

from shared.config import settings

from .anchor import is_spot_stable_for_lock, record_spot_sample, summarize_opening_chain_inputs
from .decay_output import (
    build_decay_item,
    handle_raw_pct_unavailable,
    is_flat_decay,
    record_flat_post_lock_if_needed,
    should_store_decay,
    store_decay_item,
)
from .models import (
    CAPTURE_STALL_LOG_EVERY_FAILURES,
    ET,
    SPOT_STABILITY_MAX_RANGE,
    SPOT_STABILITY_MIN_SAMPLES,
    is_valid_spot,
)
from .runtime import (
    capture_anchor,
    initialize_tracker,
    invalidate_tracker,
    load_stitch_state,
    reset_for_new_day,
    roll_anchor,
    try_restore_pending_anchor,
)
from .raw_pct import RawPctResult, calculate_raw_pct_result
from .storage import AtmDecayStorage
from .stitching import default_stitch_factor, factor_to_legacy_offset, stitch_with_factor

logger = logging.getLogger(__name__)


class AtmDecayTracker:
    """Manages opening ATM anchor and computes stitched ATM decay."""

    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        quote_ctx: Optional[QuoteContext] = None,
    ):
        self.ctx = quote_ctx
        self.anchor: dict[str, Any] | None = None
        self._redis_key_tpl = "app:opening_atm:{date}"
        self._series_key_tpl = "app:atm_decay_series:{date}"
        self._today = datetime.now(ET).strftime("%Y%m%d")
        self._storage = AtmDecayStorage(
            redis_client=redis_client,
            cold_dir=settings.opening_atm_cold_storage_root,
            redis_key_tpl=self._redis_key_tpl,
            series_key_tpl=self._series_key_tpl,
        )
        self._cold_dir = self._storage.cold_dir
        self._prev_pcts: tuple[float, float, float] | None = None
        self._warmup_ticks_remaining: int = 5
        self.accumulated_offset = {"c": 0.0, "p": 0.0, "s": 0.0}
        self.accumulated_factor = default_stitch_factor()
        self._out_of_bounds_ticks: int = 0
        self._strike_changed_flag: bool = False
        self._recent_spots: list[float] = []
        self._pending_restore_anchor: dict[str, Any] | None = None
        self._pending_restore_source: str | None = None
        self._opening_tick_pending: bool = False
        self._capture_failure_streak: int = 0
        self._raw_pct_failure_streak: int = 0
        self.is_initialized = False

    @property
    def redis(self) -> Redis | None:
        return self._storage.redis

    @redis.setter
    def redis(self, client: Redis | None) -> None:
        self._storage.redis = client

    async def initialize(self, spot: float = 0.0) -> None:
        """Restore today's anchor from Redis -> cold JSON -> empty."""
        await initialize_tracker(self, spot)

    def invalidate_anchor(self) -> None:
        invalidate_tracker(self)

    def _reset_for_new_day(self, today: str) -> None:
        reset_for_new_day(self, today)

    def _load_stitch_state(self, anchor: dict[str, Any]) -> None:
        load_stitch_state(self, anchor)

    async def _try_restore_pending_anchor(self, spot: Any) -> bool:
        return await try_restore_pending_anchor(self, spot)

    async def _capture_anchor(self, chain: list[dict[str, Any]], spot: float, now: datetime) -> None:
        await capture_anchor(self, chain, spot, now)

    async def _roll_anchor(self, chain: list[dict[str, Any]], spot: float, now: datetime) -> None:
        await roll_anchor(self, chain, spot, now)

    def _calculate_raw_pct(
        self,
        chain: list[dict[str, Any]],
        *,
        source_freshness: dict[str, Any] | None = None,
    ) -> RawPctResult:
        return calculate_raw_pct_result(
            self.anchor,
            chain,
            source_timestamp=_source_timestamp(source_freshness),
            require_freshness=source_freshness is not None,
        )

    def get_anchor_symbols(self) -> set[str]:
        if not self.anchor:
            return set()
        syms: set[str] = set()
        cs = self.anchor.get("call_symbol")
        ps = self.anchor.get("put_symbol")
        if cs:
            syms.add(cs)
        if ps:
            syms.add(ps)
        return syms

    async def get_history(self, date_str: str) -> list[dict[str, Any]]:
        return await self._storage.get_history(date_str)

    async def flush_and_rebuild(self) -> None:
        logger.info("[AtmDecayTracker] Flushing series for %s", self._today)
        await self._storage.flush_series(self._today)
        self._prev_pcts = None

    async def pre_fill_history(self) -> None:
        logger.info("[AtmDecayTracker] pre_fill_history skipped (API limitation).")

    def _note_capture_failure(self, chain: list[dict[str, Any]], spot: float, now: datetime, context: str) -> None:
        self._capture_failure_streak += 1
        if self._capture_failure_streak % CAPTURE_STALL_LOG_EVERY_FAILURES != 0:
            return
        summary = summarize_opening_chain_inputs(chain, now)
        logger.warning(
            "[AtmDecayTracker] capture stall: failures=%d context=%s spot=%.2f chain=%d zero_dte=%d integer_strikes=%d",
            self._capture_failure_streak,
            context,
            spot,
            summary["total_contracts"],
            summary["zero_dte_contracts"],
            summary["integer_strikes"],
        )

    async def update(
        self,
        chain: list[dict[str, Any]],
        spot: Any,
        *,
        source_freshness: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if not self.is_initialized:
            logger.debug("[AtmDecayTracker] update skipped: not initialized")
            return None

        now = datetime.now(ET)
        today = now.strftime("%Y%m%d")
        
        logger.debug("[AtmDecayTracker] update tick: spot=%s chain_size=%s anchor=%s", spot, len(chain), "YES" if self.anchor else "NO")

        if today != self._today:
            self._reset_for_new_day(today)

        if now.hour < 9 or (now.hour == 9 and now.minute < 30):
            return None
        if now.hour > 16 or (now.hour == 16 and (now.minute > 0 or now.second > 0)):
            return None

        spot_f = float(spot) if is_valid_spot(spot) else 0.0
        record_spot_sample(self._recent_spots, spot_f)

        if not self.anchor and self._pending_restore_anchor is not None:
            await self._try_restore_pending_anchor(spot_f)

        if not self.anchor:
            if self._warmup_ticks_remaining > 0:
                self._warmup_ticks_remaining -= 1
                logger.debug(
                    "[AtmDecay] Warm-up delay: %s ticks remaining before anchor capture",
                    self._warmup_ticks_remaining,
                )
            else:
                ready, span = is_spot_stable_for_lock(self._recent_spots)
                if not ready:
                    logger.debug(
                        "[AtmDecay] Spot lock gate pending: samples=%d/%d span=%s max=%.2f",
                        len(self._recent_spots),
                        SPOT_STABILITY_MIN_SAMPLES,
                        f"{span:.3f}" if span is not None else "N/A",
                        SPOT_STABILITY_MAX_RANGE,
                    )
                else:
                    await self._capture_anchor(chain, spot_f, now)
                    if not self.anchor:
                        self._note_capture_failure(chain, spot_f, now, "update")

        if not self.anchor:
            return None

        alpha = 0.0035
        tau_ticks = 45
        current_strike = self.anchor["strike"]
        if spot_f > 0 and abs(spot_f - current_strike) / spot_f > alpha:
            self._out_of_bounds_ticks += 1
            if self._out_of_bounds_ticks >= tau_ticks:
                await self._roll_anchor(chain, spot_f, now)
        else:
            self._out_of_bounds_ticks = 0

        return self._calculate_decay(chain, source_freshness=source_freshness)

    async def bootstrap_intraday_anchor(self, chain: list[dict[str, Any]], spot: Any) -> dict[str, Any] | None:
        if not self.is_initialized or self.anchor:
            return None

        now = datetime.now(ET)
        if now.hour < 9 or (now.hour == 9 and now.minute < 30):
            return None
        if now.hour > 16 or (now.hour == 16 and (now.minute > 0 or now.second > 0)):
            return None

        spot_f = float(spot) if is_valid_spot(spot) else 0.0
        if not is_valid_spot(spot_f):
            return None

        had_pending_restore = self._pending_restore_anchor is not None
        if had_pending_restore:
            await self._try_restore_pending_anchor(spot_f)
            if self.anchor:
                logger.info(
                    "[AtmDecayTracker] Intraday startup bootstrap satisfied by deferred restore: strike=%s spot=%.2f",
                    self.anchor["strike"],
                    spot_f,
                )
                return self._calculate_decay(chain)
            if self._pending_restore_anchor is None:
                logger.info(
                    "[AtmDecayTracker] Deferred startup anchor was discarded; continuing with fresh intraday capture "
                    "using spot=%.2f",
                    spot_f,
                )

        await self._capture_anchor(chain, spot_f, now)
        if not self.anchor:
            self._note_capture_failure(chain, spot_f, now, "startup_bootstrap")
            return None

        logger.info(
            "[AtmDecayTracker] Intraday startup bootstrap locked anchor immediately: strike=%s spot=%.2f",
            self.anchor["strike"],
            spot_f,
        )
        return self._calculate_decay(chain)

    def compute_current_decay(self, chain: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not self.anchor:
            return None
        return self._calculate_decay(chain)

    def _calculate_decay(
        self,
        chain: list[dict[str, Any]],
        *,
        source_freshness: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        raw_result = self._calculate_raw_pct(chain, source_freshness=source_freshness)
        if not raw_result.raw_pcts:
            handle_raw_pct_unavailable(self, chain, raw_result, logger)
            return None

        c_raw, p_raw, s_raw = raw_result.raw_pcts
        self._raw_pct_failure_streak = 0
        factors = self.accumulated_factor
        c_pct = stitch_with_factor(c_raw, factors.get("c", 1.0))
        p_pct = stitch_with_factor(p_raw, factors.get("p", 1.0))
        s_pct = stitch_with_factor(s_raw, factors.get("s", 1.0))

        ts = datetime.now(ET)
        pcts = (c_pct, p_pct, s_pct)
        item = build_decay_item(
            anchor=self.anchor,
            call_pct=c_pct,
            put_pct=p_pct,
            straddle_pct=s_pct,
            ts=ts,
            strike_changed=self._strike_changed_flag,
            source_timestamp=_source_timestamp(source_freshness),
            source_gap_ms=_source_gap_ms(source_freshness),
            stale_recovery=bool((source_freshness or {}).get("stale_recovery")),
            leg_freshness=raw_result.leg_freshness,
        )

        if self._opening_tick_pending and is_flat_decay(*pcts):
            logger.info(
                "[AtmDecay] opening tick suppressed for strike=%s while waiting for post-lock movement",
                int(self.anchor["strike"]),
            )
            return None

        if should_store_decay(self._prev_pcts, pcts):
            record_flat_post_lock_if_needed(self, chain, ts=ts, pcts=pcts, logger=logger)
            store_decay_item(self, item, ts=ts, pcts=pcts, logger=logger)

        return item


def _source_timestamp(source_freshness: dict[str, Any] | None) -> str | None:
    raw = (source_freshness or {}).get("source_timestamp")
    return raw if isinstance(raw, str) and raw else None


def _source_gap_ms(source_freshness: dict[str, Any] | None) -> float | None:
    raw = (source_freshness or {}).get("source_gap_ms")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None
