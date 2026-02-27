"""Skew Dynamics submodule — Presenter.
"""

from typing import Any
from app.ui.skew_dynamics.mappings import SKEW_STATES

class SkewDynamicsPresenter:
    
    @classmethod
    def build(cls, skew_val: float, state: str) -> dict[str, Any]:
        """Build the Skew Dynamics UI state block."""
        mapping = SKEW_STATES.get(state, SKEW_STATES["NEUTRAL"])
        
        return {
            "value": f"{skew_val:.2f}",
            "state_label": mapping["label"],
            "color_class": mapping["color_class"],
            "border_class": mapping["border_class"],
            "bg_class": mapping["bg_class"],
            "shadow_class": mapping["shadow_class"],
            "badge": mapping["badge"]
        }
