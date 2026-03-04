"""Tactical Triad submodule — Presenter.

Converts Agent B and Agent G output into the Tactical Triad UI components:
VRP (Variance Risk Premium), CHARM (Delta Decay), S-VOL (Spot-Vol Correlation).
"""

from typing import Any
from datetime import datetime
from zoneinfo import ZoneInfo
from app.ui.tactical_triad import mappings


class TacticalTriadPresenter:

    @classmethod
    def build(
        cls,
        vrp: float | None,
        vrp_state: str | None,
        net_charm: float | None,
        svol_corr: float | None,
        svol_state: str | None,
        fused_signal_direction: str | None = None
    ) -> dict[str, Any]:
        """Build the Tactical Triad UI state block for the frontend.
        """
        # --- Internal Standardisation: Strip Enum prefixes ---
        vrp_state = str(vrp_state or "FAIR")
        if "." in vrp_state: vrp_state = vrp_state.split(".")[-1]
        
        svol_state = str(svol_state or "NORMAL")
        if "." in svol_state: svol_state = svol_state.split(".")[-1]

        # Determine if we are in the pre-close amplification window (after 14:00 ET)
        now_et = datetime.now(ZoneInfo("America/New_York"))
        is_pre_close = now_et.hour >= 14

        # Map the 3 tactical components
        vrp_ui = mappings.get_vrp_style(vrp, vrp_state)
        charm_ui = mappings.get_charm_style(net_charm, is_pre_close)
        svol_ui = mappings.get_svol_style(svol_corr, svol_state)
        
        # Determine the subtitle inferences (e.g. MEDIUM BREAKOUT)
        # We will use simple heuristics matching the original design logic
        vrp_sub = "NEUTRAL"
        if vrp_state == "BARGAIN": vrp_sub = "BREAKOUT"
        elif vrp_state == "TRAP": vrp_sub = "WASH OUT"
        
        charm_sub = "STABLE"
        if charm_ui["state_label"] == "RISING": charm_sub = "REVERSAL"
        elif charm_ui["state_label"] == "DECAYING": charm_sub = "ACCELERATING"
        
        svol_sub = "NEUTRAL"
        if svol_state == "DANGER_ZONE": svol_sub = "TOXIC DRAG"
        elif svol_state == "GRIND_STABLE": svol_sub = "MOMENTUM"
        elif svol_state == "VANNA_FLIP": svol_sub = "FLIP RISK"

        return {
            "vrp": {
                **vrp_ui,
                "sub_intensity": "HIGH" if abs(vrp or 0) > 5 else "MEDIUM" if abs(vrp or 0) > 2 else "LOW",
                "sub_label": vrp_sub
            },
            "charm": {
                **charm_ui,
                "sub_intensity": "HIGH" if (net_charm or 0) > 50 else "LOW",
                "sub_label": charm_sub
            },
            "svol": {
                **svol_ui,
                "sub_intensity": "HIGH" if svol_state == "DANGER_ZONE" else "LOW",
                "sub_label": svol_sub
            }
        }
