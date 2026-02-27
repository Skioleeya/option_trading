"""MicroStats submodule — Presenter.

Assembles the UI state dictionary for frontend MicroStats rendering.
No business logic. No if/else color judgments. Only dict lookups.
"""

from typing import Any
from app.ui import theme
from app.ui.micro_stats import mappings, thresholds


class MicroStatsPresenter:

    @classmethod
    def build(
        cls,
        gex_regime: str,
        wall_dyn: dict[str, Any],
        vanna: str,
        momentum: str,
    ) -> dict[str, Any]:
        """Build the MicroStats UI state block for the frontend.

        Args:
            gex_regime: Raw regime string from VannaFlowResult.
            wall_dyn: WallMigration micro_structure_state dict.
            vanna: Raw vanna state string from VannaFlowResult.
            momentum: Agent A signal (BULLISH / BEARISH / NEUTRAL).
        """
        # --- Derive wall domination key from raw states ---
        call_st = wall_dyn.get("call_wall_state", "") if wall_dyn else ""
        put_st  = wall_dyn.get("put_wall_state",  "") if wall_dyn else ""

        if call_st in thresholds.WALL_SIEGE_STATES or put_st in thresholds.WALL_SIEGE_STATES:
            wall_key = "REINFORCED_WALL"
        elif call_st in thresholds.WALL_RETREAT_STATES:
            wall_key = "RETREATING_RESISTANCE"
        else:
            wall_key = "STABLE"

        return {
            "net_gex":  mappings.GEX_REGIME_MAP.get(gex_regime,       mappings.GEX_REGIME_MAP["NEUTRAL"]),
            "wall_dyn": mappings.WALL_DYNAMICS_MAP.get(wall_key,       mappings.WALL_DYNAMICS_MAP["STABLE"]),
            "vanna":    mappings.VANNA_STATE_MAP.get(vanna,            mappings.VANNA_STATE_MAP["NEUTRAL"]),
            "momentum": {
                "label": momentum if momentum not in ("NEUTRAL", "") else "\u2014",
                "badge": theme.BADGE_NEUTRAL,
            },
        }
