"""Presenter for the MicroStats frontend component."""

from typing import Any
from app.ui import theme

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
        """Calculates frontend color and styling bindings.
        
        Args:
            gex_regime: E.g., 'SUPER_PIN', 'DAMPING', 'ACCELERATION'.
            wall_dyn: Wall migration dictionary.
            vanna: Vanna micro structure state.
            momentum: Agent A signal ('BULLISH', 'BEARISH').
        """
        ui = {
            "net_gex": {"label": "NEUTRAL", "badge": theme.BADGE_NEUTRAL},
            "wall_dyn": {"label": "STABLE", "badge": theme.BADGE_NEUTRAL},
            "vanna": {"label": "NEUTRAL", "badge": theme.BADGE_NEUTRAL},
            "momentum": {"label": momentum if momentum != "NEUTRAL" else "—", "badge": theme.BADGE_NEUTRAL}
        }

        # 1. NET GEX
        if gex_regime == "SUPER_PIN":
            ui["net_gex"] = {"label": "SUPER PIN", "badge": theme.BADGE_AMBER}
        elif gex_regime == "DAMPING":
            ui["net_gex"] = {"label": "DAMPING", "badge": theme.BADGE_GREEN}
        elif gex_regime == "ACCELERATION":
            ui["net_gex"] = {"label": "VOLATILE", "badge": theme.BADGE_HOLLOW_PURPLE}

        # 2. WALL DYN
        if wall_dyn:
            call_st = wall_dyn.get("call_wall_state", "")
            put_st = wall_dyn.get("put_wall_state", "")
            
            if call_st == "REINFORCED_WALL" or put_st == "REINFORCED_SUPPORT":
                ui["wall_dyn"] = {"label": "SIEGE", "badge": theme.BADGE_HOLLOW_AMBER}
            elif call_st == "RETREATING_RESISTANCE":
                ui["wall_dyn"] = {"label": "RETREAT", "badge": theme.BADGE_HOLLOW_AMBER}

        # 3. VANNA
        if vanna in ["CMPRS", "GRIND_STABLE"]:
            ui["vanna"] = {"label": "CMPRS", "badge": theme.BADGE_HOLLOW_CYAN}
        elif vanna in ["DANGER", "DANGER_ZONE"]:
            ui["vanna"] = {"label": "DANGER", "badge": theme.BADGE_RED}
        elif vanna in ["FLIP", "VANNA_FLIP"]:
            ui["vanna"] = {"label": "FLIP", "badge": theme.BADGE_PURPLE}

        return ui
