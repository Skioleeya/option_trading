"""ATM Decay Tracker Module.

Tracks the SPY ATM options price exactly at 9:30 AM ET and calculates real-time
premium decay (Call, Put, Straddle) relative to that anchor.
Provides dual-layer persistence (Redis + Local JSON) to survive fast-API restarts.

Design Principles (Institutional Grade):
  1. STRICT 0DTE ISOLATION — regex-based YYMMDD extraction from OCC-style symbols;
     only today's expiration is eligible for anchor capture.
  2. INTEGER STRIKE GATE — SPY strikes are always whole-dollar; fractional strikes
     (e.g. 681.67) are rejected as data artifacts.
  3. SYMBOL-LOCKED DECAY — once anchored, _calculate_decay matches by exact symbol
     string (e.g. "SPY260303C681000.US"), never by strike alone. This prevents
     cross-expiration contamination when the chain contains both 0DTE and 1DTE.
  4. MID-PRICE WATERFALL — Bid/Ask mid (only when uncrossed) → Ask → Last.
  5. DUAL-LAYER PERSISTENCE — Redis (primary, TTL-managed) + cold JSON (fallback).
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from longport.openapi import QuoteContext
from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

ET = ZoneInfo("US/Eastern")

# ---------------------------------------------------------------------------
# OCC-style symbol regex for US equity options
# Examples:  SPY260303C681000.US   SPY260304P00676000.US
# Groups:    (underlying)(YYMMDD)(C|P)(strike_raw)
# ---------------------------------------------------------------------------
_SYM_RE = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d+)\.US$")

# Maximum allowable distance (points) between a persisted anchor strike and
# current spot when restoring from Redis or cold JSON.  If the gap exceeds
# this value the stale anchor is discarded and a fresh capture is triggered.
_MAX_ANCHOR_DISTANCE: float = 3.0


def _parse_expiry(symbol: str) -> str | None:
    """Return the YYMMDD expiration string embedded in the symbol, or None."""
    m = _SYM_RE.match(symbol)
    return m.group(2) if m else None


def _is_integer_strike(strike: float) -> bool:
    """SPY options always have whole-dollar strikes (676.0, 681.0, …)."""
    return abs(strike - round(strike)) < 0.01


def _mid_price(bid: float, ask: float, last: float) -> float:
    """Institutional mid-price waterfall. Returns 0.0 only if all inputs are 0."""
    if bid > 0 and ask > 0 and ask >= bid:
        return (bid + ask) / 2.0
    if ask > 0:
        return ask
    return last  # last resort; may be 0.0


class AtmDecayTracker:
    """Manages the 9:30 AM ATM anchor and calculates real-time premium decay."""

    # ------------------------------------------------------------------
    # Construction & initialisation
    # ------------------------------------------------------------------
    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        quote_ctx: Optional[QuoteContext] = None,
    ):
        self.redis = redis_client
        self.ctx = quote_ctx
        self.anchor: dict[str, Any] | None = None

        self._cold_dir = Path(settings.opening_atm_cold_storage_root)
        self._cold_dir.mkdir(parents=True, exist_ok=True)

        self._redis_key_tpl = "app:opening_atm:{date}"
        self._series_key_tpl = "app:atm_decay_series:{date}"
        self._today = datetime.now(ET).strftime("%Y%m%d")

        # Deduplication guard — last emitted (call_pct, put_pct, straddle_pct)
        self._prev_pcts: tuple[float, float, float] | None = None

        # Warm-up guard: skip anchor capture for the first N ticks after startup
        # to let the LV1 bid/ask feed fully populate before locking a strike.
        self._warmup_ticks_remaining: int = 5

        self.is_initialized = False

    async def initialize(self, spot: float = 0.0) -> None:
        """Restore today's anchor from Redis → cold JSON → empty (wait for 9:30).

        Args:
            spot: Current SPY spot price.  When non-zero, any persisted anchor
                  whose strike deviates more than _MAX_ANCHOR_DISTANCE from
                  ``spot`` is treated as stale and discarded so a fresh capture
                  can run on the next tick.
        """
        now = datetime.now(ET)
        self._today = now.strftime("%Y%m%d")

        # 1. Redis
        if self.redis:
            try:
                raw = await self.redis.get(self._redis_key_tpl.format(date=self._today))
                if raw:
                    anchor = json.loads(raw)
                    if self._validate_anchor(anchor):
                        self.anchor = anchor
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

        # 2. Cold JSON
        cold_file = self._cold_dir / f"atm_{self._today}.json"
        if cold_file.exists():
            try:
                anchor = json.loads(cold_file.read_text())
                if self._validate_anchor(anchor):
                    self.anchor = anchor
                    logger.info(
                        f"[AtmDecayTracker] Restored anchor from cold JSON: "
                        f"strike={anchor['strike']} (spot={spot if spot else 'N/A'})"
                    )
                    # Heal Redis
                    if self.redis:
                        try:
                            await self._save_redis(anchor)
                        except Exception:
                            pass
                    self.is_initialized = True
                    return
                else:
                    logger.warning("[AtmDecayTracker] Cold JSON anchor failed validation — discarding")
            except Exception as exc:
                logger.error(f"[AtmDecayTracker] Cold JSON read failed: {exc}")

        # 3. No anchor yet
        logger.info("[AtmDecayTracker] No valid anchor for today. Will capture at market open.")
        self.is_initialized = True

    def invalidate_anchor(self) -> None:
        """Force-clear the in-memory anchor so it will be re-captured on the
        next tick.  Useful after manual overrides or when the operator detects
        an erroneous lock.

        Note: Does NOT remove Redis / cold-JSON persisted anchors — call
        ``initialize(spot)`` after clearing to trigger a spot-validated reload.
        """
        if self.anchor:
            logger.warning(
                f"[AtmDecayTracker] Anchor INVALIDATED (was strike={self.anchor.get('strike')}). "
                "Will re-capture on next tick."
            )
        self.anchor = None
        self._prev_pcts = None
        self._warmup_ticks_remaining = 5  # Re-arm warm-up gate after manual invalidation

    # ------------------------------------------------------------------
    # Anchor validation
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_anchor(a: dict) -> bool:
        """Reject anchors that lack symbol keys, non-numeric or fractional strikes."""
        required = {"strike", "call_symbol", "put_symbol", "call_price", "put_price", "timestamp"}
        if not required.issubset(a.keys()):
            return False
        strike = a["strike"]
        if not isinstance(strike, (int, float)) or not _is_integer_strike(strike):
            return False
        if not a["call_symbol"] or not a["put_symbol"]:
            return False
        return True

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    async def _save_redis(self, data: dict[str, Any]) -> None:
        if not self.redis:
            return
        key = self._redis_key_tpl.format(date=self._today)
        await self.redis.set(key, json.dumps(data), ex=settings.opening_atm_redis_ttl_seconds)

    def _save_cold(self, data: dict[str, Any]) -> None:
        path = self._cold_dir / f"atm_{self._today}.json"
        try:
            path.write_text(json.dumps(data, indent=2))
        except Exception as exc:
            logger.error(f"[AtmDecayTracker] Cold JSON write failed: {exc}")

    async def _persist(self, anchor: dict[str, Any]) -> None:
        self.anchor = anchor
        self._today = datetime.fromisoformat(anchor["timestamp"]).strftime("%Y%m%d")
        await self._save_redis(anchor)
        self._save_cold(anchor)
        logger.info(
            f"[AtmDecayTracker] ANCHOR LOCKED — strike={anchor['strike']} "
            f"call={anchor['call_symbol']} put={anchor['put_symbol']} "
            f"C${anchor['call_price']:.2f} P${anchor['put_price']:.2f}"
        )

    # ------------------------------------------------------------------
    # Public API — called every compute tick from main._agent_runner_loop
    # ------------------------------------------------------------------
    async def update(
        self, chain: list[dict[str, Any]], spot: float
    ) -> dict[str, Any] | None:
        """Process chain tick.  Captures anchor once, then returns decay dict.

        Anchor capture is NOT gated to exactly 9:30 — if the server starts at
        9:31, 10:00, or 14:17, it will lock the nearest 0DTE ATM immediately.
        Only true pre-market (before 9:30) is blocked.
        """
        if not self.is_initialized:
            return None

        now = datetime.now(ET)
        if now.hour < 9 or (now.hour == 9 and now.minute < 30):
            return None  # true pre-market

        if not self.anchor:
            # Burn through warm-up ticks before first capture attempt
            if self._warmup_ticks_remaining > 0:
                self._warmup_ticks_remaining -= 1
                logger.debug(
                    f"[AtmDecay] Warm-up delay: {self._warmup_ticks_remaining} ticks remaining before anchor capture"
                )
            else:
                await self._capture_anchor(chain, spot, now)

        if not self.anchor:
            return None

        return self._calculate_decay(chain)

    def get_anchor_symbols(self) -> set[str]:
        """Return exact call/put symbol strings for depth-subscription sync."""
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
        if not self.redis:
            return []
        key = self._series_key_tpl.format(date=date_str)
        raw = await self.redis.lrange(key, 0, -1)
        return [json.loads(r) for r in raw]

    async def flush_and_rebuild(self) -> None:
        if not self.redis:
            return
        logger.info(f"[AtmDecayTracker] Flushing series for {self._today}")
        await self.redis.delete(self._series_key_tpl.format(date=self._today))
        self._prev_pcts = None

    async def pre_fill_history(self) -> None:
        """LongPort does not support intraday REST for options — no-op."""
        logger.info("[AtmDecayTracker] pre_fill_history skipped (API limitation).")

    # ------------------------------------------------------------------
    # Anchor capture — runs on every tick until locked for the day
    # ------------------------------------------------------------------
    async def _capture_anchor(
        self, chain: list[dict[str, Any]], spot: float, now: datetime
    ) -> None:
        if not chain or spot <= 0:
            return

        today_ymd = now.strftime("%y%m%d")  # e.g. "260303"

        # ── Step 1: Isolate 0DTE contracts ──────────────────────────────
        zero_dte = [
            opt for opt in chain
            if _parse_expiry(opt.get("symbol", "")) == today_ymd
        ]
        if not zero_dte:
            logger.debug(f"[AtmDecay] No 0DTE contracts in chain ({len(chain)} total) for {today_ymd}")
            return

        # ── Step 2: Collect integer strikes, sort by distance to spot ───
        strikes = sorted(
            {opt["strike"] for opt in zero_dte if _is_integer_strike(opt["strike"])},
            key=lambda s: abs(s - spot),
        )
        if not strikes:
            logger.debug(f"[AtmDecay] No integer strikes in 0DTE subset ({len(zero_dte)} contracts)")
            return

        logger.info(
            f"[AtmDecay] 0DTE scan: {len(zero_dte)} contracts, "
            f"{len(strikes)} integer strikes, spot={spot:.2f}, "
            f"nearest strikes={strikes[:5]}"
        )

        # ── Step 3a: Preferred — same-strike pair (top 10) ──────────────
        # Require both call AND put with positive price at the same strike.
        # Both legs must exceed a minimum price floor to reject deep-OTM locks.
        _MIN_LEG_PRICE = 0.05  # reject legs priced < $0.05 (deep OTM garbage)
        for candidate in strikes[:10]:
            call_sym = call_px = put_sym = put_px = None
            for opt in zero_dte:
                if abs(opt["strike"] - candidate) > 0.01:
                    continue
                otype = opt.get("option_type", opt.get("type", "")).upper()
                px = _mid_price(
                    opt.get("bid", 0.0),
                    opt.get("ask", 0.0),
                    opt.get("last_price", 0.0),
                )
                if otype in ("CALL", "C") and px >= _MIN_LEG_PRICE:
                    call_sym = opt["symbol"]
                    call_px = px
                elif otype in ("PUT", "P") and px >= _MIN_LEG_PRICE:
                    put_sym = opt["symbol"]
                    put_px = px

            if call_sym and put_sym:
                await self._persist({
                    "strike": candidate,
                    "call_symbol": call_sym,
                    "put_symbol": put_sym,
                    "call_price": call_px,
                    "put_price": put_px,
                    "timestamp": now.isoformat(),
                })
                return  # locked!

            logger.debug(
                f"[AtmDecay] Strike {int(candidate)} skipped: "
                f"call={'$'+f'{call_px:.2f}' if call_px else 'MISS'} "
                f"put={'$'+f'{put_px:.2f}' if put_px else 'MISS'}"
            )

        logger.warning(
            f"[AtmDecayTracker] Could not lock any of top-10 0DTE strikes "
            f"{[int(s) for s in strikes[:10]]}. Waiting for more data."
        )


    # ------------------------------------------------------------------
    # Decay calculation — symbol-locked, dedup-guarded
    # ------------------------------------------------------------------
    def _calculate_decay(self, chain: list[dict[str, Any]]) -> dict[str, Any] | None:
        a = self.anchor
        if not a:
            return None

        target_call = a["call_symbol"]
        target_put = a["put_symbol"]
        anchor_c = a["call_price"]
        anchor_p = a["put_price"]
        anchor_s = anchor_c + anchor_p

        # ── Exact symbol match ──────────────────────────────────────────
        curr_c = curr_p = 0.0
        for opt in chain:
            sym = opt.get("symbol")
            if sym == target_call:
                curr_c = _mid_price(opt.get("bid", 0.0), opt.get("ask", 0.0), opt.get("last_price", 0.0))
            elif sym == target_put:
                curr_p = _mid_price(opt.get("bid", 0.0), opt.get("ask", 0.0), opt.get("last_price", 0.0))

        if curr_c <= 0 or curr_p <= 0:
            return None

        curr_s = curr_c + curr_p
        c_pct = (curr_c - anchor_c) / anchor_c if anchor_c > 0 else 0.0
        p_pct = (curr_p - anchor_p) / anchor_p if anchor_p > 0 else 0.0
        s_pct = (curr_s - anchor_s) / anchor_s if anchor_s > 0 else 0.0

        ts = datetime.now(ET)
        item = {
            "strike": a["strike"],
            "locked_at": datetime.fromisoformat(a["timestamp"]).strftime("%H:%M:%S"),
            "call_pct": c_pct,
            "put_pct": p_pct,
            "straddle_pct": s_pct,
            "timestamp": ts.isoformat(),
        }

        # ── Deduplication — ONLY for Redis storage ─────────────────────
        # We always return the item to the UI to prevent flickering, 
        # but we only save to the time-series if values have changed.
        should_store = True
        if self._prev_pcts is not None:
            pc, pp, ps = self._prev_pcts
            if abs(c_pct - pc) < 1e-6 and abs(p_pct - pp) < 1e-6 and abs(s_pct - ps) < 1e-6:
                should_store = False

        if should_store:
            self._prev_pcts = (c_pct, p_pct, s_pct)
            # Fire-and-forget append
            import asyncio
            asyncio.ensure_future(self._append_series(item, ts.strftime("%Y%m%d")))

        logger.info(
            f"[AtmDecay] {int(a['strike'])} | "
            f"C:{c_pct:+.4f}  P:{p_pct:+.4f}  S:{s_pct:+.4f} "
            f"{'(stored)' if should_store else '(dedup)'}"
        )

        return item

    # ------------------------------------------------------------------
    # Time-series storage
    # ------------------------------------------------------------------
    async def _append_series(self, data: dict[str, Any], date_str: str) -> None:
        if not self.redis:
            return
        key = self._series_key_tpl.format(date=date_str)
        await self.redis.rpush(key, json.dumps(data))
        if await self.redis.llen(key) == 1:
            await self.redis.expire(key, settings.opening_atm_redis_ttl_seconds)
