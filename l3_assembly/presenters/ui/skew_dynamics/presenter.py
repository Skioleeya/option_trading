"""Skew Dynamics submodule — Presenter.
"""

from typing import Any
from l3_assembly.presenters.ui.skew_dynamics.mappings import SKEW_STATES

class SkewDynamicsPresenter:
    
    @classmethod
    def build(cls, skew_val: float, state: str) -> dict[str, Any]:
        """Build the Skew Dynamics UI state block."""
        # --- Internal Standardisation: Strip Enum prefixes ---
        state = str(state or "NEUTRAL")
        if "." in state: state = state.split(".")[-1]

        mapping = SKEW_STATES.get(state, SKEW_STATES["NEUTRAL"])
        value = "N/A" if mapping["label"] == "UNAVAILABLE" else f"{skew_val:.2f}"
        
        return {
            "value": value,
            "state_label": mapping["label"],
            "color_class": mapping["color_class"],
            "border_class": mapping["border_class"],
            "bg_class": mapping["bg_class"],
            "shadow_class": mapping["shadow_class"],
            "badge": mapping["badge"]
        }
