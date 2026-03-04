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

    # ── Spot ──────────────────────────────────────────────────────────────────

    @property
    def spot(self) -> float | None:
        return self._spot

    def update_spot(self, price: float) -> None:
        """Update the SPY spot price."""
        import math
        if not math.isfinite(price) or price <= 0:
            return
        self._spot = price
        self._last_spot_update = datetime.now(ZoneInfo("US/Eastern"))

    # ── Quote / Depth Events ──────────────────────────────────────────────────

    def apply_event(self, event: CleanQuoteEvent) -> bool:
        """Write a sanitized quote event into the store.

        Sequence-number guard: if a previous event with a HIGHER seq_no has
        already been applied for this symbol, the incoming event is dropped.
        This prevents slow REST batches from overwriting fresh WS pushes.
        """
        symbol = event.symbol
        last = self._last_seq.get(symbol, 0)

        # Allow WS events (always fresh) to skip the seq check for REST events.
        # REST events only win if they are strictly newer than any prior event.
        if event.event_type == EventType.REST and event.seq_no <= last:
            return False

        # Build or update the entry
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

        entry = self._chain[symbol]
        changed = False

        def _set(key: str, val: Any) -> None:
            nonlocal changed
            if val is not None and entry.get(key) != val:
                entry[key] = val
                changed = True

        _set("bid",                event.bid)
        _set("ask",                event.ask)
        _set("last_price",         event.last_price)
        _set("volume",             event.volume)
        _set("current_volume",     event.current_volume)
        _set("turnover",           event.turnover)
        _set("implied_volatility", event.implied_volatility)
        _set("iv_timestamp",       event.iv_timestamp)
        _set("delta",              event.delta)
        _set("gamma",              event.gamma)
        _set("theta",              event.theta)
        _set("vega",               event.vega)

        if event.open_interest is not None:
             # Apply smoothing or direct update? 
             # For Depth Profile logic, we typically want smoothed but 
             # hot-start seeding should be prioritized.
             _set("open_interest", event.open_interest)

        entry["last_update"] = datetime.now(ZoneInfo("US/Eastern"))
        self._last_seq[symbol] = event.seq_no

        return True

    def apply_depth(self, event: CleanDepthEvent) -> None:
        """Update top-of-book bid/ask from a depth event."""
        if event.symbol not in self._chain:
            return
        entry = self._chain[event.symbol]
        if event.bid is not None and event.bid > 0:
            entry["bid"] = event.bid
        if event.ask is not None and event.ask > 0:
            entry["ask"] = event.ask

    # ── Greeks patch (from GreeksEngine) ─────────────────────────────────────

    def apply_greeks(self, symbol: str, greeks: dict[str, float]) -> None:
        """Write BSM-computed Greeks back into the store."""
        if symbol not in self._chain:
            return
        self._chain[symbol].update(greeks)

    # ── OI EMA smoothing (PP-4) ───────────────────────────────────────────────

    def apply_oi_smooth(self, symbol: str, raw_oi: int) -> int:
        """Apply EMA(α=0.2) smoothing to OI and store result. Returns smoothed value."""
        prev = self._oi_smooth.get(symbol, float(raw_oi))
        smoothed = prev + 0.2 * (raw_oi - prev)
        self._oi_smooth[symbol] = smoothed
        oi_int = int(smoothed)
        if symbol in self._chain:
            self._chain[symbol]["open_interest"] = oi_int
        return oi_int

    # ── Volume map ────────────────────────────────────────────────────────────

    def update_volume_map(self, volume_map: dict[float, int]) -> None:
        """Replace the volume map (from volume research scan)."""
        self._volume_map = volume_map

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
            "spot":                self._spot,
            "last_spot_update":    self._last_spot_update.isoformat() if self._last_spot_update else None,
            "volume_map_size":     len(self._volume_map),
            "oi_smooth_entries":   len(self._oi_smooth),
        }
