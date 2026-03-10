"""ActiveOptions runtime service (shared neutral service layer).

Orchestrates the three FlowEngine_D/E/G engines and the DEGComposer to
produce the final Active Options UI payload ordered by flow intensity.
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
            return

        min_vol = settings.flow_active_min_volume
        filtered = [o for o in chain if int(o.get("volume", 0) or 0) >= min_vol]

        if not filtered:
            logger.warning(
                "[ActiveOptionsRuntimeService] No options above min_volume threshold — "
                "emitting neutral placeholders to keep fixed row contract."
            )
            self._latest_payload = self._pad_rows([], target_limit)
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

        top = sorted(outputs, key=lambda o: o.impact_index, reverse=True)[:target_limit]
        rows = [self._format_row(o, slot_index=idx + 1) for idx, o in enumerate(top)]
        self._latest_payload = self._pad_rows(rows, target_limit)

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
