"""Runtime state holders for L0 V2."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from shared.services.l0_runtime.native_loader import load_l0_rust
from shared.services.l0_runtime.normalize.pipeline import (
    CleanDepthEvent,
    CleanQuoteEvent,
    EventType,
    SanitizationPipeline,
)

logger = logging.getLogger(__name__)
MAX_WS_FLOW_VOLUME = 1_000_000_000.0

_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "_native_generated"
_L0_RUST = load_l0_rust(
    candidates=[
        _PACKAGE_DIR / "wave5" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave4" / "l0_rust.pyd",
        _PACKAGE_DIR / "l0_rust.pyd",
    ],
    module_suffix="l0_rust_wave5_state",
)


def _default_entry(*, symbol: str, strike: float, opt_type: str) -> dict[str, Any]:
    return dict(_L0_RUST.l0_state_default_entry(symbol, float(strike), str(opt_type)))


def _apply_quote_patch(
    *,
    entry: dict[str, Any],
    event: Any,
    is_rest: bool,
    ws_price_seen: bool,
    ws_volume_seen: bool,
    ws_current_volume_seen: bool,
    ws_turnover_seen: bool,
    max_ws_flow_volume: float,
) -> dict[str, Any]:
    return dict(
        _L0_RUST.l0_state_apply_quote(
            entry,
            event,
            bool(is_rest),
            bool(ws_price_seen),
            bool(ws_volume_seen),
            bool(ws_current_volume_seen),
            bool(ws_turnover_seen),
            float(max_ws_flow_volume),
        )
    )


def _apply_depth_patch(*, entry: dict[str, Any], event: Any) -> dict[str, Any]:
    return dict(_L0_RUST.l0_state_apply_depth(entry, event))


class ChainStateStore:
    """Sole owner of the in-memory option chain."""

    def __init__(self) -> None:
        self._chain: dict[str, dict[str, Any]] = {}
        self._last_seq: dict[str, int] = {}
        self._spot: float | None = None
        self._last_spot_update: datetime | None = None
        self._oi_smooth: dict[str, float] = {}
        self._volume_map: dict[float, int] = {}
        self._version: int = 0
        self._ws_price_seen: set[str] = set()
        self._ws_volume_seen: set[str] = set()
        self._ws_current_volume_seen: set[str] = set()
        self._ws_turnover_seen: set[str] = set()
        self._ws_volume_dropped: int = 0
        self._ws_current_volume_dropped: int = 0

    @property
    def spot(self) -> float | None:
        return self._spot

    @property
    def last_spot_update(self) -> "datetime | None":
        """Timestamp of the most recent spot price update (public access for FeedOrchestrator)."""
        return self._last_spot_update

    @property
    def version(self) -> int:
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

    def apply_event(self, event: CleanQuoteEvent) -> bool:
        """Write a sanitized quote event into the store."""
        symbol = event.symbol
        last = self._last_seq.get(symbol, 0)
        is_rest = event.event_type == EventType.REST
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
            self._chain[symbol] = _default_entry(symbol=symbol, strike=event.strike, opt_type=event.opt_type)
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
        current = dict(self._chain[symbol])
        patch = _apply_quote_patch(
            entry=current,
            event=event,
            is_rest=is_rest,
            ws_price_seen=symbol in self._ws_price_seen,
            ws_volume_seen=symbol in self._ws_volume_seen,
            ws_current_volume_seen=symbol in self._ws_current_volume_seen,
            ws_turnover_seen=symbol in self._ws_turnover_seen,
            max_ws_flow_volume=MAX_WS_FLOW_VOLUME,
        )
        next_entry = patch["entry"]
        for key, value in next_entry.items():
            setter(key, value)
        if patch.get("ws_price_seen"):
            self._ws_price_seen.add(symbol)
        if patch.get("ws_volume_seen"):
            self._ws_volume_seen.add(symbol)
        if patch.get("ws_current_volume_seen"):
            self._ws_current_volume_seen.add(symbol)
        if patch.get("ws_turnover_seen"):
            self._ws_turnover_seen.add(symbol)
        if patch.get("ws_volume_dropped_inc"):
            self._track_implausible_ws_volume(
                symbol=symbol,
                field_name="volume",
                raw_positive=True,
                sanitized_value=None,
                raw_value=patch.get("ws_volume_drop_value"),
            )
        if patch.get("ws_current_volume_dropped_inc"):
            self._track_implausible_ws_volume(
                symbol=symbol,
                field_name="current_volume",
                raw_positive=True,
                sanitized_value=None,
                raw_value=patch.get("ws_current_volume_drop_value"),
            )

    @staticmethod
    def _is_positive_numeric(value: Any) -> bool:
        if value is None:
            return False
        try:
            return float(value) > 0.0
        except (TypeError, ValueError):
            return False

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

    @staticmethod
    def _apply_iv_and_greeks(event: CleanQuoteEvent, *, setter: Any) -> None:
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
        patch = _apply_depth_patch(entry=dict(self._chain[event.symbol]), event=event)
        changed = bool(patch.get("changed"))
        if changed:
            self._chain[event.symbol] = dict(patch["entry"])
            self._bump_version()

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

    def update_volume_map(self, volume_map: dict[float, int]) -> None:
        """Replace the volume map (from volume research scan)."""
        if self._volume_map == volume_map:
            return
        self._volume_map = volume_map
        self._bump_version()

    @property
    def volume_map(self) -> dict[float, int]:
        return self._volume_map

    def get_snapshot(self, target_symbols: set[str] | None = None) -> list[dict[str, Any]]:
        """Return a read-only shallow copy of chain entries."""
        if target_symbols is not None:
            return [dict(v) for k, v in self._chain.items() if k in target_symbols]
        return [dict(v) for v in self._chain.values()]

    def needs_price_repair(self, symbol: str) -> bool:
        entry = self._chain.get(symbol)
        if entry is None:
            return True
        return not any(
            self._is_positive_numeric(entry.get(field))
            for field in ("bid", "ask", "last_price")
        )

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
            entry["bbo_imbalance"] = flow.get("bbo_imbalance", 0.0)
            entry["vpin_score"] = flow.get("vpin_score", 0.0)
        return snapshot

    def diagnostics(self) -> dict[str, Any]:
        return {
            "chain_size": len(self._chain),
            "version": self._version,
            "spot": self._spot,
            "last_spot_update": self._last_spot_update.isoformat() if self._last_spot_update else None,
            "volume_map_size": len(self._volume_map),
            "oi_smooth_entries": len(self._oi_smooth),
            "ws_price_seen": len(self._ws_price_seen),
            "ws_volume_seen": len(self._ws_volume_seen),
            "ws_current_volume_seen": len(self._ws_current_volume_seen),
            "ws_turnover_seen": len(self._ws_turnover_seen),
            "ws_volume_dropped": self._ws_volume_dropped,
            "ws_current_volume_dropped": self._ws_current_volume_dropped,
        }

    def _bump_version(self) -> None:
        self._version += 1


@dataclass
class LiveState:
    store: ChainStateStore = field(default_factory=ChainStateStore)
    sanitizer: SanitizationPipeline = field(default_factory=SanitizationPipeline)

    def snapshot_rows(self, target_symbols: set[str] | None = None) -> list[dict[str, Any]]:
        return self.store.get_snapshot(target_symbols)


__all__ = ["ChainStateStore", "LiveState"]
