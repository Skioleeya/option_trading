"""Presenter for the MicroStats frontend component."""

from typing import Any
from app.ui import theme
from app.ui import mappings

class MicroStatsPresenter:
    """Format business data into MicroStats UI state."""

    @classmethod
    def build(
        cls,
        gex_regime: str,
        wall_dyn: dict[str, Any],
        vanna: str,
        momentum: str,
    ) -> dict[str, Any]:
        """Calculates frontend color and styling bindings via mappings.
        
        Args:
            gex_regime: The environment regime (SUPER_PIN, DAMPING, etc.)
            wall_dyn: Dict containing Wall Migration states
            vanna: Vanna flow string descriptor
            momentum: Agent A's signal
        """
        # Determine dominant Wall state (call or put state)
        wall_st = "STABLE"
        if wall_dyn:
            if wall_dyn.get("call_wall_state") == "REINFORCED_WALL" or wall_dyn.get("put_wall_state") == "REINFORCED_SUPPORT":
                wall_st = "REINFORCED_WALL"
            elif wall_dyn.get("call_wall_state") == "RETREATING_RESISTANCE":
                wall_st = "RETREATING_RESISTANCE"
            
        return {
            "net_gex": mappings.GEX_REGIME_MAP.get(
                gex_regime, 
                mappings.GEX_REGIME_MAP["NEUTRAL"]
            ),
            "wall_dyn": mappings.WALL_DYNAMICS_MAP.get(
                wall_st, 
                mappings.WALL_DYNAMICS_MAP["STABLE"]
            ),
            "vanna": mappings.VANNA_STATE_MAP.get(
                vanna, 
                mappings.VANNA_STATE_MAP["NEUTRAL"]
            ),
            "momentum": {
                "label": momentum if momentum != "NEUTRAL" else "—", 
                "badge": theme.BADGE_NEUTRAL
            }
        }
