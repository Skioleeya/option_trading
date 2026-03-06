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

    # ── Spot ──────────────────────────────────────────────────────────────────

    @property
    def spot(self) -> float | None:
        return self._spot

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

        # Build or update the entry
        created = False
        if symbol not in self._chain:
            self._chain[symbol] = {
                "symbol":         symbol,
                "strike":         event.strike,
                "type":           event.opt_type,
                "bid":            0.0,
                "ask":            0.0,
                "last_price":     0.0,
                "volume":         0,
                "open_interest":  0,
                "implied_volatility": 0.0,
                "iv_timestamp":   0.0,
                "delta":          0.0,
                "gamma":          0.0,
                "theta":          0.0,
                "vega":           0.0,
                "current_volume": 0.0,
                "turnover":       0.0,
            }
            created = True

        entry = self._chain[symbol]
        changed = False

        def _set(key: str, val: Any) -> None:
            nonlocal changed
            if val is not None and entry.get(key) != val:
                entry[key] = val
                changed = True

        # BUG-1 FIX: 价格字段仅 WS 推送写入；REST 不得覆盖实盘成交价
        if not is_rest:
            _set("bid",            event.bid)
            _set("ask",            event.ask)
            _set("last_price",     event.last_price)
            _set("volume",         event.volume)
            _set("current_volume", event.current_volume)
            _set("turnover",       event.turnover)

        # IV 字段：REST 是唯一来源（长桥 WS 不提供 IV）
        _set("implied_volatility", event.implied_volatility)
        _set("iv_timestamp",       event.iv_timestamp)

        _set("delta",              event.delta)
        _set("gamma",              event.gamma)
        _set("theta",              event.theta)
        _set("vega",               event.vega)

        # BUG-8 NOTE (P2): OI 统一通过 apply_oi_smooth() 写入以保持 EMA 连续性。
        # 调用方负责在 apply_event() 后显式调用 apply_oi_smooth(symbol, event.open_interest)。
        # 此处保留直写作为热启动路径（seq_no=0），后续 P2 轮修复。
        if event.open_interest is not None:
            _set("open_interest", event.open_interest)

        entry["last_update"] = datetime.now(ZoneInfo("US/Eastern"))
        self._last_seq[symbol] = event.seq_no

        if created or changed:
            self._bump_version()

        return True

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
        }

    def _bump_version(self) -> None:
        self._version += 1
