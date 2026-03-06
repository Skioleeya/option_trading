"""ATM Decay tracker orchestrator."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from longport.openapi import QuoteContext
from redis.asyncio import Redis

from shared.config import settings

from .anchor import (
    calculate_raw_pct,
    is_spot_stable_for_lock,
    record_spot_sample,
    select_opening_anchor,
    select_roll_anchor,
    validate_anchor,
)
from .models import ET, MAX_ANCHOR_DISTANCE, SPOT_STABILITY_MAX_RANGE, SPOT_STABILITY_MIN_SAMPLES, spot_distance
from .storage import AtmDecayStorage
from .stitching import (
    advance_factor,
    default_stitch_factor,
    factor_to_legacy_offset,
    legacy_offset_to_factor,
    stitch_with_factor,
)

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
        # Keep for compatibility with existing diagnostics/scripts.
        self._cold_dir = self._storage.cold_dir

        self._prev_pcts: tuple[float, float, float] | None = None
        self._warmup_ticks_remaining: int = 5
        self.accumulated_offset = {"c": 0.0, "p": 0.0, "s": 0.0}
        self.accumulated_factor = default_stitch_factor()
        self._out_of_bounds_ticks: int = 0
        self._strike_changed_flag: bool = False
        self._recent_spots: list[float] = []
        self.is_initialized = False

    @property
    def redis(self) -> Redis | None:
        return self._storage.redis

    @redis.setter
    def redis(self, client: Redis | None) -> None:
        self._storage.redis = client

    async def initialize(self, spot: float = 0.0) -> None:
        """Restore today's anchor from Redis -> cold JSON -> empty."""
        now = datetime.now(ET)
        self._today = now.strftime("%Y%m%d")

        # 1) Redis
        if self.redis:
            try:
                anchor = await self._storage.load_anchor_from_redis(self._today)
                if anchor:
                    if validate_anchor(anchor):
                        dist = spot_distance(anchor.get("strike"), spot)
                        if dist is None:
                            logger.warning(
                                "[AtmDecayTracker] Redis anchor skipped: spot unavailable for strict restore "
                                "(date=%s strike=%.2f spot=%s).",
                                self._today,
                                float(anchor["strike"]),
                                spot,
                            )
                        elif dist > MAX_ANCHOR_DISTANCE:
                            logger.warning(
                                "[AtmDecayTracker] Redis anchor discarded (distance check): "
                                "date=%s strike=%.2f spot=%.2f diff=%.2f max=%.2f",
                                self._today,
                                float(anchor["strike"]),
                                float(spot),
                                dist,
                                MAX_ANCHOR_DISTANCE,
                            )
                        else:
                            self.anchor = anchor
                            self._load_stitch_state(anchor)
                            logger.info(
                                f"[AtmDecayTracker] Restored anchor from Redis: "
                                f"strike={anchor['strike']} (spot={spot if spot else 'N/A'})"
                            )
                            self.is_initialized = True
                            return
                    else:
                        logger.warning("[AtmDecayTracker] Redis anchor failed validation — discarding")
            except Exception as exc:
                logger.error(f"[AtmDecayTracker] Redis read failed: {exc}")

        # 2) Cold JSON
        try:
            anchor = self._storage.load_anchor_from_cold(self._today)
            if anchor:
                if validate_anchor(anchor):
                    dist = spot_distance(anchor.get("strike"), spot)
                    if dist is None:
                        logger.warning(
                            "[AtmDecayTracker] Cold JSON anchor skipped: spot unavailable for strict restore "
                            "(date=%s strike=%.2f spot=%s).",
                            self._today,
                            float(anchor["strike"]),
                            spot,
                        )
                    elif dist > MAX_ANCHOR_DISTANCE:
                        logger.warning(
                            "[AtmDecayTracker] Cold JSON anchor discarded (distance check): "
                            "date=%s strike=%.2f spot=%.2f diff=%.2f max=%.2f",
                            self._today,
                            float(anchor["strike"]),
                            float(spot),
                            dist,
                            MAX_ANCHOR_DISTANCE,
                        )
                    else:
                        self.anchor = anchor
                        self._load_stitch_state(anchor)
                        logger.info(
                            f"[AtmDecayTracker] Restored anchor from cold JSON: "
                            f"strike={anchor['strike']} (spot={spot if spot else 'N/A'})"
                        )
                        if self.redis:
                            try:
                                await self._storage.save_anchor(
                                    self._today,
                                    anchor,
                                    settings.opening_atm_redis_ttl_seconds,
                                )
                            except Exception:
                                pass
                            await self._storage.recover_series_from_cold_if_needed(
                                self._today,
                                settings.opening_atm_redis_ttl_seconds,
                            )
                        self.is_initialized = True
                        return
                else:
                    logger.warning("[AtmDecayTracker] Cold JSON anchor failed validation — discarding")
        except Exception as exc:
            logger.error(f"[AtmDecayTracker] Cold JSON read failed: {exc}")

        logger.info("[AtmDecayTracker] No valid anchor for today. Will capture at market open.")
        self.is_initialized = True

    def invalidate_anchor(self) -> None:
        if self.anchor:
            logger.warning(
                f"[AtmDecayTracker] Anchor INVALIDATED (was strike={self.anchor.get('strike')}). "
                "Will re-capture on next tick."
            )
        self.anchor = None
        self._prev_pcts = None
        self._warmup_ticks_remaining = 5
        self._recent_spots.clear()
        self.accumulated_factor = default_stitch_factor()
        self.accumulated_offset = factor_to_legacy_offset(self.accumulated_factor)

    def _load_stitch_state(self, anchor: dict[str, Any]) -> None:
        raw_factor = anchor.get("accumulated_factor")
        if isinstance(raw_factor, dict):
            merged: dict[str, float] = default_stitch_factor()
            for key in ("c", "p", "s"):
                val = raw_factor.get(key, 1.0)
                try:
                    merged[key] = max(0.0, float(val))
                except (TypeError, ValueError):
                    merged[key] = 1.0
            self.accumulated_factor = merged
        else:
            self.accumulated_factor = legacy_offset_to_factor(anchor.get("accumulated_offset"))
        self.accumulated_offset = factor_to_legacy_offset(self.accumulated_factor)

    def _reset_for_new_day(self, today: str) -> None:
        if self.anchor:
            logger.info(
                "[AtmDecayTracker] New trade date detected (%s -> %s). "
                "Resetting in-memory anchor/stitch state.",
                self._today,
                today,
            )
        self._today = today
        self.anchor = None
        self._prev_pcts = None
        self._warmup_ticks_remaining = 5
        self._out_of_bounds_ticks = 0
        self._strike_changed_flag = False
        self._recent_spots.clear()
        self.accumulated_factor = default_stitch_factor()
        self.accumulated_offset = factor_to_legacy_offset(self.accumulated_factor)

    async def _persist(self, anchor: dict[str, Any]) -> None:
        anchor["accumulated_factor"] = dict(getattr(self, "accumulated_factor", default_stitch_factor()))
        anchor["accumulated_offset"] = factor_to_legacy_offset(anchor["accumulated_factor"])
        self.anchor = anchor
        self._today = datetime.fromisoformat(anchor["timestamp"]).strftime("%Y%m%d")
        await self._storage.save_anchor(self._today, anchor, settings.opening_atm_redis_ttl_seconds)
        logger.info(
            f"[AtmDecayTracker] ANCHOR LOCKED — strike={anchor['strike']} "
            f"call={anchor['call_symbol']} put={anchor['put_symbol']} "
            f"C${anchor['call_price']:.2f} P${anchor['put_price']:.2f}"
        )

    async def update(self, chain: list[dict[str, Any]], spot: float) -> dict[str, Any] | None:
        if not self.is_initialized:
            return None

        logger.debug(f"[AtmDecayTracker] Update tick. Redis presence: {self.redis is not None}")
        now = datetime.now(ET)
        today = now.strftime("%Y%m%d")
        if today != self._today:
            self._reset_for_new_day(today)

        if now.hour < 9 or (now.hour == 9 and now.minute < 30):
            return None
        if now.hour > 16 or (now.hour == 16 and (now.minute > 0 or now.second > 0)):
            return None

        record_spot_sample(self._recent_spots, spot)

        if not self.anchor:
            if self._warmup_ticks_remaining > 0:
                self._warmup_ticks_remaining -= 1
                logger.debug(
                    f"[AtmDecay] Warm-up delay: {self._warmup_ticks_remaining} ticks remaining before anchor capture"
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
                    await self._capture_anchor(chain, spot, now)

        if not self.anchor:
            return None

        alpha = 0.0035
        tau_ticks = 45
        current_strike = self.anchor["strike"]
        if spot > 0 and abs(spot - current_strike) / spot > alpha:
            self._out_of_bounds_ticks += 1
            if self._out_of_bounds_ticks >= tau_ticks:
                await self._roll_anchor(chain, spot, now)
        else:
            self._out_of_bounds_ticks = 0

        return self._calculate_decay(chain)

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
        logger.info(f"[AtmDecayTracker] Flushing series for {self._today}")
        await self._storage.flush_series(self._today)
        self._prev_pcts = None

    async def pre_fill_history(self) -> None:
        logger.info("[AtmDecayTracker] pre_fill_history skipped (API limitation).")

    async def _capture_anchor(self, chain: list[dict[str, Any]], spot: float, now: datetime) -> None:
        anchor = select_opening_anchor(chain, spot, now, logger=logger)
        if anchor:
            await self._persist(anchor)

    async def _roll_anchor(self, chain: list[dict[str, Any]], spot: float, now: datetime) -> None:
        if not self.anchor:
            return

        next_anchor, same_strike = select_roll_anchor(self.anchor, chain, spot, now)
        if same_strike:
            self._out_of_bounds_ticks = 0
            return
        if not next_anchor:
            return

        raw_pcts = self._calculate_raw_pct(chain)
        if raw_pcts:
            self.accumulated_factor["c"] = advance_factor(self.accumulated_factor.get("c", 1.0), raw_pcts[0])
            self.accumulated_factor["p"] = advance_factor(self.accumulated_factor.get("p", 1.0), raw_pcts[1])
            self.accumulated_factor["s"] = advance_factor(self.accumulated_factor.get("s", 1.0), raw_pcts[2])
            self.accumulated_offset = factor_to_legacy_offset(self.accumulated_factor)

        logger.warning(
            f"[AtmDecay] Rolling anchor {self.anchor['strike']} -> {next_anchor['strike']} "
            f"(SCM CDD stitched, offsets: S={self.accumulated_offset['s']:+.3f})"
        )
        await self._persist(next_anchor)
        self._strike_changed_flag = True
        self._out_of_bounds_ticks = 0

    def _calculate_raw_pct(self, chain: list[dict[str, Any]]) -> tuple[float, float, float] | None:
        return calculate_raw_pct(self.anchor, chain)

    def _calculate_decay(self, chain: list[dict[str, Any]]) -> dict[str, Any] | None:
        raw_pcts = self._calculate_raw_pct(chain)
        if not raw_pcts:
            return None

        c_raw, p_raw, s_raw = raw_pcts
        factors = self.accumulated_factor
        c_pct = stitch_with_factor(c_raw, factors.get("c", 1.0))
        p_pct = stitch_with_factor(p_raw, factors.get("p", 1.0))
        s_pct = stitch_with_factor(s_raw, factors.get("s", 1.0))

        ts = datetime.now(ET)
        item = {
            "strike": self.anchor["strike"],
            "base_strike": self.anchor.get("base_strike", self.anchor["strike"]),
            "locked_at": datetime.fromisoformat(self.anchor["timestamp"]).strftime("%H:%M:%S"),
            "call_pct": c_pct,
            "put_pct": p_pct,
            "straddle_pct": s_pct,
            "timestamp": ts.isoformat(),
            "strike_changed": self._strike_changed_flag,
        }

        if self._strike_changed_flag:
            self._strike_changed_flag = False

        should_store = True
        if self._prev_pcts is not None:
            pc, pp, ps = self._prev_pcts
            if abs(c_pct - pc) < 1e-6 and abs(p_pct - pp) < 1e-6 and abs(s_pct - ps) < 1e-6:
                should_store = False

        if should_store:
            self._prev_pcts = (c_pct, p_pct, s_pct)
            asyncio.ensure_future(self._append_series(item, ts.strftime("%Y%m%d")))
            logger.info(
                f"[AtmDecay] {int(self.anchor['strike'])} | "
                f"C:{c_pct:+.4f}  P:{p_pct:+.4f}  S:{s_pct:+.4f} (stored)"
            )

        return item

    async def _append_series(self, data: dict[str, Any], date_str: str) -> None:
        await self._storage.append_series(date_str, data)
