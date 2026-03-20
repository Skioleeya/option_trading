"""P2 — ChainStateStore: In-Memory Option Chain State (唯一所有者).

Replaces the raw `self._chain: dict[str, dict]` in OptionChainBuilder with
a purpose-built store that enforces:

  1. Single-write path: all mutations go through `apply_*` methods.
  2. Sequence-number ordering: stale REST writes cannot overwrite fresh WS data.
  3. Thread-safe read: `get_snapshot()` returns a shallow copy — callers cannot
     accidentally mutate the internal state through the returned list.
  4. Flow-merge: `get_flow_merged_snapshot()` inlines DepthEngine toxicity/BBO
     fields before returning to the caller, keeping DepthEngine decoupled.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from l0_ingest.feeds.sanitization import CleanQuoteEvent, CleanDepthEvent, EventType

logger = logging.getLogger(__name__)
MAX_WS_FLOW_VOLUME = 1_000_000_000.0


class ChainStateStore:
    """Sole owner of the in-memory option chain.

    THREAD SAFETY: All methods are called from the asyncio event loop.
    Mutations are protected by a baseline sequence-number check.
    """

    def __init__(self) -> None:
        # Primary state: symbol → option entry dict
        self._chain: dict[str, dict[str, Any]] = {}

        # Per-symbol last-accepted sequence number (prevents stale overwrites)
        self._last_seq: dict[str, int] = {}

        # Spot price (updated by SPY quote handler)
        self._spot: float | None = None
        self._last_spot_update: datetime | None = None

        # OI EMA smoothing state (α=0.2, matches original PP-4 fix)
        self._oi_smooth: dict[str, float] = {}

        # Volume map: strike → total volume (from volume research scan)
        self._volume_map: dict[float, int] = {}

        # Monotonic snapshot version for downstream cache invalidation.
        self._version: int = 0

        # WS authority flags for controlled REST fallback on flow fields.
        self._ws_volume_seen: set[str] = set()
        self._ws_current_volume_seen: set[str] = set()
        self._ws_turnover_seen: set[str] = set()
        self._ws_volume_dropped: int = 0
        self._ws_current_volume_dropped: int = 0

    # ── Spot ──────────────────────────────────────────────────────────────────

    @property
    def spot(self) -> float | None:
        return self._spot

    @property
    def last_spot_update(self) -> "datetime | None":
        """Timestamp of the most recent spot price update (public access for FeedOrchestrator)."""
        return self._last_spot_update

    @property
    def version(self) -> int:
        """Monotonic state version used by downstream reactors."""
        return self._version

    def update_spot(self, price: float) -> None:
        """Update the SPY spot price."""
        import math
        if not math.isfinite(price) or price <= 0:
            return
        if self._spot == price:
            return
        self._spot = price
        self._last_spot_update = datetime.now(ZoneInfo("US/Eastern"))
        self._bump_version()

    # ── Quote / Depth Events ──────────────────────────────────────────────────

    def apply_event(self, event: CleanQuoteEvent) -> bool:
        """Write a sanitized quote event into the store.

        Field ownership (LongBridge API constraint):
          - WS events own: bid / ask / last_price / volume / current_volume / turnover
          - REST events own: implied_volatility / iv_timestamp  (sole IV source)

        Sequence-number guard: REST events with seq_no <= last known are dropped.
        """
        symbol = event.symbol
        last = self._last_seq.get(symbol, 0)

        is_rest = event.event_type == EventType.REST

        # REST events only win if they are strictly newer than any prior event.
        if is_rest and event.seq_no <= last:
            return False

        entry, created = self._ensure_entry(symbol, event)
        changed = False

        def _set(key: str, val: Any) -> None:
            nonlocal changed
            if val is not None and entry.get(key) != val:
                entry[key] = val
                changed = True

        self._apply_price_and_flow_fields(symbol, event, is_rest=is_rest, setter=_set)
        self._apply_iv_and_greeks(event, setter=_set)

        # P0-1 FIX (BUG-8 resolved): OI 写入统一走 apply_oi_smooth() 保持 EMA 连续性。
        # apply_event() 不再直写 open_interest，消除与 apply_oi_smooth() 的双写竞争。
        # 调用方必须在 apply_event() 后显式调用 apply_oi_smooth(symbol, event.open_interest)。

        entry["last_update"] = datetime.now(ZoneInfo("US/Eastern"))
        self._last_seq[symbol] = event.seq_no

        if created or changed:
            self._bump_version()

        return True

    def _ensure_entry(
        self,
        symbol: str,
        event: CleanQuoteEvent,
    ) -> tuple[dict[str, Any], bool]:
        if symbol not in self._chain:
            self._chain[symbol] = {
                "symbol": symbol,
                "strike": event.strike,
                "type": event.opt_type,
                "bid": 0.0,
                "ask": 0.0,
                "last_price": 0.0,
                "volume": 0,
                "open_interest": 0,
                "implied_volatility": 0.0,
                "iv_timestamp": 0.0,
                "delta": 0.0,
                "gamma": 0.0,
                "theta": 0.0,
                "vega": 0.0,
                "current_volume": 0.0,
                "turnover": 0.0,
            }
            return self._chain[symbol], True
        return self._chain[symbol], False

    def _apply_price_and_flow_fields(
        self,
        symbol: str,
        event: CleanQuoteEvent,
        *,
        is_rest: bool,
        setter: Any,
    ) -> None:
        if not is_rest:
            setter("bid", event.bid)
            setter("ask", event.ask)
            setter("last_price", event.last_price)
            if self._event_allows_flow_fields(event):
                self._apply_ws_flow_fields(symbol, event, setter)
            return

        self._apply_rest_flow_fallback(symbol, event, setter)

    @staticmethod
    def _event_allows_flow_fields(event: CleanQuoteEvent) -> bool:
        return event.event_type in (EventType.QUOTE, EventType.TRADE)

    @staticmethod
    def _is_positive_numeric(value: Any) -> bool:
        if value is None:
            return False
        try:
            return float(value) > 0.0
        except (TypeError, ValueError):
            return False

    @classmethod
    def _sanitize_ws_volume_candidate(cls, value: Any) -> float | None:
        if not cls._is_positive_numeric(value):
            return None
        parsed = float(value)
        if parsed > MAX_WS_FLOW_VOLUME:
            return None
        return parsed

    def _apply_ws_flow_fields(self, symbol: str, event: CleanQuoteEvent, setter: Any) -> None:
        raw_volume_positive = self._is_positive_numeric(event.volume)
        raw_current_positive = self._is_positive_numeric(event.current_volume)
        sanitized_volume = self._sanitize_ws_volume_candidate(event.volume)
        sanitized_current_volume = self._sanitize_ws_volume_candidate(event.current_volume)
        self._track_implausible_ws_volume(
            symbol=symbol,
            field_name="volume",
            raw_positive=raw_volume_positive,
            sanitized_value=sanitized_volume,
            raw_value=event.volume,
        )
        self._track_implausible_ws_volume(
            symbol=symbol,
            field_name="current_volume",
            raw_positive=raw_current_positive,
            sanitized_value=sanitized_current_volume,
            raw_value=event.current_volume,
        )

        ws_volume = self._resolve_ws_volume(sanitized_volume, sanitized_current_volume)
        volume_owned_by_ws = (
            event.event_type == EventType.TRADE
            or self._is_positive_numeric(event.turnover)
        )
        if volume_owned_by_ws and self._is_positive_numeric(ws_volume):
            setter("volume", ws_volume)
        if sanitized_current_volume is not None:
            setter("current_volume", sanitized_current_volume)
        setter("turnover", event.turnover)
        self._mark_ws_flow_owner_seen(
            symbol=symbol,
            volume_owned_by_ws=volume_owned_by_ws,
            ws_volume=ws_volume,
            current_volume=sanitized_current_volume,
            turnover=event.turnover,
        )

    def _track_implausible_ws_volume(
        self,
        *,
        symbol: str,
        field_name: str,
        raw_positive: bool,
        sanitized_value: float | None,
        raw_value: Any,
    ) -> None:
        if not raw_positive or sanitized_value is not None:
            return
        if field_name == "current_volume":
            self._ws_current_volume_dropped += 1
        else:
            self._ws_volume_dropped += 1
        logger.warning(
            "[ChainStateStore] dropped implausible WS %s: symbol=%s value=%s cap=%s",
            field_name,
            symbol,
            raw_value,
            int(MAX_WS_FLOW_VOLUME),
        )

    def _mark_ws_flow_owner_seen(
        self,
        *,
        symbol: str,
        volume_owned_by_ws: bool,
        ws_volume: float,
        current_volume: float | None,
        turnover: float | None,
    ) -> None:
        if volume_owned_by_ws and self._is_positive_numeric(ws_volume):
            self._ws_volume_seen.add(symbol)
        if self._is_positive_numeric(current_volume):
            self._ws_current_volume_seen.add(symbol)
        if self._is_positive_numeric(turnover):
            self._ws_turnover_seen.add(symbol)

    @classmethod
    def _resolve_ws_volume(cls, volume: Any, current_volume: Any) -> float:
        """Resolve WS volume from dual fields while guarding against single-field corruption."""
        vol_ok = cls._is_positive_numeric(volume)
        cur_ok = cls._is_positive_numeric(current_volume)
        if vol_ok and cur_ok:
            return min(float(volume), float(current_volume))
        if vol_ok:
            return float(volume)
        if cur_ok:
            return float(current_volume)
        return 0.0

    def _apply_rest_flow_fallback(self, symbol: str, event: CleanQuoteEvent, setter: Any) -> None:
        if symbol not in self._ws_volume_seen:
            setter("volume", event.volume)
        if symbol not in self._ws_current_volume_seen:
            setter("current_volume", event.current_volume)
        if symbol not in self._ws_turnover_seen:
            setter("turnover", event.turnover)

    @staticmethod
    def _apply_iv_and_greeks(event: CleanQuoteEvent, *, setter: Any) -> None:
        # IV 字段：REST 是唯一来源（长桥 WS 不提供 IV）
        setter("implied_volatility", event.implied_volatility)
        setter("iv_timestamp", event.iv_timestamp)
        setter("delta", event.delta)
        setter("gamma", event.gamma)
        setter("theta", event.theta)
        setter("vega", event.vega)

    def apply_depth(self, event: CleanDepthEvent) -> None:
        """Update top-of-book bid/ask from a depth event."""
        if event.symbol not in self._chain:
            return
        entry = self._chain[event.symbol]
        changed = False
        if event.bid is not None and event.bid > 0:
            if entry.get("bid") != event.bid:
                entry["bid"] = event.bid
                changed = True
        if event.ask is not None and event.ask > 0:
            if entry.get("ask") != event.ask:
                entry["ask"] = event.ask
                changed = True
        if changed:
            self._bump_version()

    # ── Greeks patch (from GreeksEngine) ─────────────────────────────────────

    def apply_greeks(self, symbol: str, greeks: dict[str, float]) -> None:
        """Write BSM-computed Greeks back into the store."""
        if symbol not in self._chain:
            return
        entry = self._chain[symbol]
        changed = False
        for key, value in greeks.items():
            if entry.get(key) != value:
                entry[key] = value
                changed = True
        if changed:
            self._bump_version()

    # ── OI EMA smoothing (PP-4) ───────────────────────────────────────────────

    def apply_oi_smooth(self, symbol: str, raw_oi: int) -> int:
        """Apply EMA(α=0.2) smoothing to OI and store result. Returns smoothed value."""
        prev = self._oi_smooth.get(symbol, float(raw_oi))
        smoothed = prev + 0.2 * (raw_oi - prev)
        self._oi_smooth[symbol] = smoothed
        oi_int = int(smoothed)
        if symbol in self._chain:
            if self._chain[symbol].get("open_interest") != oi_int:
                self._chain[symbol]["open_interest"] = oi_int
                self._bump_version()
        return oi_int

    # ── Volume map ────────────────────────────────────────────────────────────

    def update_volume_map(self, volume_map: dict[float, int]) -> None:
        """Replace the volume map (from volume research scan)."""
        if self._volume_map == volume_map:
            return
        self._volume_map = volume_map
        self._bump_version()

    @property
    def volume_map(self) -> dict[float, int]:
        return self._volume_map

    # ── Read interface ────────────────────────────────────────────────────────

    def get_snapshot(self, target_symbols: set[str] | None = None) -> list[dict[str, Any]]:
        """Return a read-only shallow copy of chain entries."""
        if target_symbols is not None:
            return [dict(v) for k, v in self._chain.items() if k in target_symbols]
        return [dict(v) for v in self._chain.values()]

    def get_flow_merged_snapshot(
        self,
        flow_snapshot: dict[str, dict[str, float]],
        target_symbols: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return snapshot with DepthEngine toxicity/BBO fields merged in."""
        snapshot = self.get_snapshot(target_symbols)
        for entry in snapshot:
            sym = entry["symbol"]
            flow = flow_snapshot.get(sym, {})
            entry["toxicity_score"] = flow.get("toxicity_score", 0.0)
            entry["bbo_imbalance"]  = flow.get("bbo_imbalance",  0.0)
            entry["vpin_score"]     = flow.get("vpin_score",      0.0)
        return snapshot

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def diagnostics(self) -> dict[str, Any]:
        return {
            "chain_size":          len(self._chain),
            "version":             self._version,
            "spot":                self._spot,
            "last_spot_update":    self._last_spot_update.isoformat() if self._last_spot_update else None,
            "volume_map_size":     len(self._volume_map),
            "oi_smooth_entries":   len(self._oi_smooth),
            "ws_volume_seen":      len(self._ws_volume_seen),
            "ws_current_volume_seen": len(self._ws_current_volume_seen),
            "ws_turnover_seen":    len(self._ws_turnover_seen),
            "ws_volume_dropped":   self._ws_volume_dropped,
            "ws_current_volume_dropped": self._ws_current_volume_dropped,
        }

    def _bump_version(self) -> None:
        self._version += 1
