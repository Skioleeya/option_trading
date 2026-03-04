"""ActiveOptions BFF Presenter v2.0 — DEG-FLOW Composite Engine.

Orchestrates the three FlowEngine_D/E/G engines and the DEGComposer to
produce the final Active Options UI payload ordered by flow intensity.

Sorting priority: |flow_deg| DESC  (strongest signal at top)
Min volume gate:  settings.flow_active_min_volume
Max rows:         5 (Top by DEG composite)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.config import settings
from app.models.flow_engine import FlowEngineInput, FlowEngineOutput
from app.services.cache.oi_snapshot import get_oi_cache_stats, save_oi_snapshot
from app.services.flow import DEGComposer, FlowEngineD, FlowEngineE, FlowEngineG
from app.services.system.persistent_oi_store import PersistentOIStore

logger = logging.getLogger(__name__)

# Colour decisions (Asian style):  positive flow = Red (bullish), negative = Green (bearish)
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


class ActiveOptionsPresenter:
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
        redis: Any | None = None,
        limit: int = 5,
    ) -> None:
        """Run the full D+E+G pipeline and update the background cache.

        Args:
            chain:      Raw option chain (from OptionChainBuilder).
            spot:       SPY spot price.
            atm_iv:     ATM implied volatility (from GreeksExtractor).
            gex_regime: Current GEX regime string for adaptive weighting.
            redis:      Async Redis client (None → G engine degrades gracefully).
            limit:      Number of rows to return (default 5).
        """
        # 1. Filter by minimum volume
        min_vol = settings.flow_active_min_volume
        filtered = [o for o in chain if int(o.get("volume", 0) or 0) >= min_vol]

        if not filtered:
            logger.warning(
                "[ActiveOptionsPresenter] No options above min_volume threshold — "
                "retaining last valid payload (market closed or cold-start)."
            )
            return  # Preserve _latest_payload — do NOT blank out after market close

        # 2. Persist OI snapshot (for next cycle's ΔOI)
        if redis:
            await save_oi_snapshot(redis, filtered)

        # 3. Build typed input contracts
        inputs = [
            FlowEngineInput.from_chain_entry(opt, spot=spot, atm_iv=atm_iv)
            for opt in filtered
        ]
        inputs_by_symbol = {inp.symbol: inp for inp in inputs}

        # 4. Run the three engines
        today_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
        d_results = self._engine_d.compute(inputs)
        e_results = self._engine_e.compute(inputs)
        g_results = await self._engine_g.compute(
            inputs, 
            redis=redis, 
            oi_store=self._oi_store,
            date_str=today_str
        )

        # 5. Compose DEG-FLOW score
        charm_surge = _is_charm_surge()
        outputs: list[FlowEngineOutput] = self._composer.compose(
            d_results, e_results, g_results,
            inputs_by_symbol=inputs_by_symbol,
            is_charm_surge=charm_surge,
            gex_regime=gex_regime,
        )

        # 6. Sort by |flow_deg| descending and slice to limit
        top = sorted(outputs, key=lambda o: abs(o.flow_deg), reverse=True)[:limit]

        # 7. Format for frontend and store
        self._latest_payload = [self._format_row(o) for o in top]

    @staticmethod
    def _format_row(o: FlowEngineOutput) -> dict[str, Any]:
        flow_color = _DIRECTION_COLOR.get(o.flow_direction, "text-text-secondary")
        glow = _INTENSITY_GLOW.get(o.flow_intensity, "")

        return {
            # Standard ActiveOption fields (TypeScript interface compatible)
            "symbol": "SPY",
            "option_type": o.option_type,
            "strike": o.strike,
            "implied_volatility": o.implied_volatility,
            "volume": o.volume,
            "turnover": o.turnover,
            "flow": o.flow_deg,                        # Composite Z-Score for colour logic

            # DEG-specific extended fields
            "flow_deg_formatted": _format_flow(o.flow_d + o.flow_e + o.flow_g),  # heuristic $ label
            "flow_volume_label": _format_volume(o.volume),
            "flow_color": flow_color,
            "flow_glow": glow,
            "flow_intensity": o.flow_intensity,
            "flow_direction": o.flow_direction,

            # Component breakdown (useful for debug overlay)
            "flow_d_z": round(o.flow_d_z, 3),
            "flow_e_z": round(o.flow_e_z, 3),
            "flow_g_z": round(o.flow_g_z, 3),
        }
