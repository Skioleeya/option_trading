"""ActiveOptions runtime service (shared neutral service layer).

Orchestrates the three FlowEngine_D/E/G engines and the DEGComposer to
produce the final Active Options UI payload with stable VOL-first ranking.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from shared.config import settings
from shared.models.flow_engine import FlowEngineInput, FlowEngineOutput
from shared.cache.oi_snapshot import save_oi_snapshot
from shared.system.persistent_oi_store import PersistentOIStore
from .deg_composer import DEGComposer
from .flow_engine_d import FlowEngineD
from .flow_engine_e import FlowEngineE
from .flow_engine_g import FlowEngineG

logger = logging.getLogger(__name__)

# Colour decisions (Asian style): positive flow = Red (bullish), negative = Green (bearish)
_DIRECTION_COLOR = {
    "BULLISH": "text-accent-red",
    "BEARISH": "text-accent-green",
    "NEUTRAL": "text-text-secondary",
}

_INTENSITY_GLOW = {
    "EXTREME": "shadow-[0_0_12px_rgba(255,77,79,0.6)] animate-pulse",
    "HIGH": "shadow-[0_0_8px_rgba(255,77,79,0.35)]",
    "MODERATE": "",
    "LOW": "",
}

_ACTIVE_OPTIONS_SWITCH_CONFIRM_TICKS = 3
_PLACEHOLDER_SIGNATURE_PREFIX = "__placeholder__#"


def _direction_from_flow_amount(flow_amount: float) -> str:
    if flow_amount > 0:
        return "BULLISH"
    if flow_amount < 0:
        return "BEARISH"
    return "NEUTRAL"


def _is_charm_surge() -> bool:
    """Return True if now is within the last 2 hours before market close (ET)."""
    now = datetime.now(ZoneInfo("US/Eastern"))
    return now.hour >= 14 and now.hour < 16


def _format_flow(val: float) -> str:
    abs_v = abs(val)
    sign = "" if val >= 0 else "-"
    prefix = "$"
    if abs_v >= 1_000_000:
        return f"{sign}{prefix}{abs_v / 1_000_000:.1f}M"
    if abs_v >= 1_000:
        return f"{sign}{prefix}{abs_v / 1_000:.0f}K"
    return f"{sign}{prefix}{int(abs_v)}"


def _format_volume(v: int) -> str:
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v / 1_000:.0f}K"
    return str(v)


class ActiveOptionsRuntimeService:
    """Build the Active Options UI state using the DEG-FLOW composite engine."""

    def __init__(self) -> None:
        self._engine_d = FlowEngineD()
        self._engine_e = FlowEngineE()
        self._engine_g = FlowEngineG()
        self._composer = DEGComposer()
        self._oi_store = PersistentOIStore()
        self._latest_payload: list[dict[str, Any]] = []
        self._latest_signature: tuple[tuple[str, str, float], ...] | None = None
        self._pending_signature: tuple[tuple[str, str, float], ...] | None = None
        self._pending_rows: list[dict[str, Any]] = []
        self._pending_hits = 0
        self._switch_confirm_ticks = _ACTIVE_OPTIONS_SWITCH_CONFIRM_TICKS

    def get_latest(self) -> list[dict[str, Any]]:
        """Return the latest cached generated rows without blocking."""
        return self._latest_payload

    async def update_background(
        self,
        chain: list[dict[str, Any]],
        spot: float,
        atm_iv: float,
        gex_regime: str = "NEUTRAL",
        ttm_seconds: float | None = None,
        redis: Any | None = None,
        limit: int = 5,
    ) -> None:
        """Run the full D+E+G pipeline and update the background cache."""
        target_limit = max(0, int(limit))
        if target_limit == 0:
            self._latest_payload = []
            self._latest_signature = None
            self._pending_signature = None
            self._pending_rows = []
            self._pending_hits = 0
            return

        min_vol = settings.flow_active_min_volume
        filtered = [o for o in chain if int(o.get("volume", 0) or 0) >= min_vol]

        if not filtered:
            logger.warning(
                "[ActiveOptionsRuntimeService] No options above min_volume threshold — "
                "emitting neutral placeholders to keep fixed row contract."
            )
            rows, signature = self._build_ranked_candidate([], target_limit)
            self._commit_or_hold_candidate(rows=rows, signature=signature)
            return

        if redis:
            await save_oi_snapshot(redis, filtered)

        inputs = [
            FlowEngineInput.from_chain_entry(opt, spot=spot, atm_iv=atm_iv)
            for opt in filtered
        ]
        inputs_by_symbol = {inp.symbol: inp for inp in inputs}

        today_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
        d_results = self._engine_d.compute(inputs)
        e_results = self._engine_e.compute(inputs)
        g_results = await self._engine_g.compute(
            inputs,
            redis=redis,
            oi_store=self._oi_store,
            date_str=today_str,
        )

        charm_surge = _is_charm_surge()
        outputs: list[FlowEngineOutput] = self._composer.compose(
            d_results,
            e_results,
            g_results,
            inputs_by_symbol=inputs_by_symbol,
            is_charm_surge=charm_surge,
            gex_regime=gex_regime,
            ttm_seconds=ttm_seconds,
        )

        rows, signature = self._build_ranked_candidate(outputs, target_limit)
        self._commit_or_hold_candidate(rows=rows, signature=signature)

    @staticmethod
    def _rank_outputs(outputs: list[FlowEngineOutput]) -> list[FlowEngineOutput]:
        return sorted(
            outputs,
            key=lambda o: (
                -int(o.volume),
                -float(o.turnover),
                -float(o.impact_index),
                str(o.symbol),
                float(o.strike),
                str(o.option_type),
            ),
        )

    @classmethod
    def _build_ranked_candidate(
        cls,
        outputs: list[FlowEngineOutput],
        limit: int,
    ) -> tuple[list[dict[str, Any]], tuple[tuple[str, str, float], ...]]:
        target = max(0, int(limit))
        ranked = cls._rank_outputs(outputs)[:target]
        rows = [cls._format_row(o, slot_index=idx + 1) for idx, o in enumerate(ranked)]
        padded_rows = cls._pad_rows(rows, target)

        signature_entries: list[tuple[str, str, float]] = [
            (str(o.symbol), str(o.option_type), round(float(o.strike), 4))
            for o in ranked
        ]
        while len(signature_entries) < target:
            signature_entries.append((f"{_PLACEHOLDER_SIGNATURE_PREFIX}{len(signature_entries) + 1}", "CALL", 0.0))
        return padded_rows, tuple(signature_entries)

    def _commit_or_hold_candidate(
        self,
        *,
        rows: list[dict[str, Any]],
        signature: tuple[tuple[str, str, float], ...],
    ) -> None:
        # Empty-data degradation must cut over immediately (no stale retention window).
        if self._is_placeholder_signature(signature):
            self._latest_payload = rows
            self._latest_signature = signature
            self._pending_signature = None
            self._pending_rows = []
            self._pending_hits = 0
            return

        # First publish has no prior state; commit immediately.
        if self._latest_signature is None:
            self._latest_payload = rows
            self._latest_signature = signature
            self._pending_signature = None
            self._pending_rows = []
            self._pending_hits = 0
            return

        # No ranking change — refresh numeric fields in-place and clear pending candidate.
        # This keeps VOL-top composition stable while still allowing live value updates.
        if signature == self._latest_signature:
            self._latest_payload = rows
            self._pending_signature = None
            self._pending_rows = []
            self._pending_hits = 0
            return

        # Candidate changed — require N consecutive identical signatures before switch.
        if signature != self._pending_signature:
            self._pending_signature = signature
            self._pending_rows = rows
            self._pending_hits = 1
            return

        self._pending_hits += 1
        if self._pending_hits < self._switch_confirm_ticks:
            return

        self._latest_payload = self._pending_rows
        self._latest_signature = self._pending_signature
        self._pending_signature = None
        self._pending_rows = []
        self._pending_hits = 0

    @staticmethod
    def _is_placeholder_signature(signature: tuple[tuple[str, str, float], ...]) -> bool:
        if not signature:
            return False
        return all(str(entry[0]).startswith(_PLACEHOLDER_SIGNATURE_PREFIX) for entry in signature)

    @staticmethod
    def _format_row(o: FlowEngineOutput, *, slot_index: int = 1) -> dict[str, Any]:
        # UI semantics are amount-first: displayed FLOW sign must match direction/color.
        flow_amount = o.flow_d + o.flow_e + o.flow_g
        flow_direction = _direction_from_flow_amount(flow_amount)
        flow_color = _DIRECTION_COLOR.get(flow_direction, "text-text-secondary")
        glow = _INTENSITY_GLOW.get(o.flow_intensity, "")

        return {
            "symbol": "SPY",
            "option_type": o.option_type,
            "strike": o.strike,
            "implied_volatility": o.implied_volatility,
            "volume": o.volume,
            "turnover": o.turnover,
            "flow": flow_amount,
            "flow_score": o.flow_deg,
            "impact_index": o.impact_index,
            "is_sweep": o.is_sweep,
            "flow_deg_formatted": _format_flow(flow_amount),
            "flow_volume_label": _format_volume(o.volume),
            "flow_color": flow_color,
            "flow_glow": glow if not o.is_sweep else "shadow-[0_0_15px_rgba(255,255,255,0.7)] animate-pulse",
            "flow_intensity": o.flow_intensity,
            "flow_direction": flow_direction,
            "flow_d_z": round(o.flow_d_z, 3),
            "flow_e_z": round(o.flow_e_z, 3),
            "flow_g_z": round(o.flow_g_z, 3),
            "is_placeholder": False,
            "slot_index": max(1, int(slot_index)),
        }

    @staticmethod
    def _placeholder_row(slot_index: int) -> dict[str, Any]:
        idx = max(1, int(slot_index))
        return {
            "symbol": "—",
            "option_type": "CALL",
            "strike": 0.0,
            "implied_volatility": 0.0,
            "volume": 0,
            "turnover": 0.0,
            "flow": 0.0,
            "flow_score": 0.0,
            "impact_index": 0.0,
            "is_sweep": False,
            "flow_deg_formatted": "—",
            "flow_volume_label": "—",
            "flow_color": "text-text-secondary",
            "flow_glow": "",
            "flow_intensity": "LOW",
            "flow_direction": "NEUTRAL",
            "flow_d_z": 0.0,
            "flow_e_z": 0.0,
            "flow_g_z": 0.0,
            "is_placeholder": True,
            "slot_index": idx,
        }

    @classmethod
    def _pad_rows(cls, rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        target = max(0, int(limit))
        trimmed = rows[:target]
        for idx, row in enumerate(trimmed):
            row["slot_index"] = idx + 1
            row["is_placeholder"] = bool(row.get("is_placeholder", False))
        while len(trimmed) < target:
            trimmed.append(cls._placeholder_row(len(trimmed) + 1))
        return trimmed


