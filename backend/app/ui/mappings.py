"""UI Mappings Engine.

Maps raw business states (from Agents) directly to frontend UI definitions 
(Labels and CSS Tokens defined in theme.py).
"""

from app.ui import theme

# ---------------------------------------------------------------------------
# MicroStats State Mappings
# ---------------------------------------------------------------------------

GEX_REGIME_MAP = {
    "SUPER_PIN": {"label": "SUPER PIN", "badge": theme.BADGE_AMBER},
    "DAMPING": {"label": "DAMPING", "badge": theme.BADGE_GREEN},
    "ACCELERATION": {"label": "VOLATILE", "badge": theme.BADGE_HOLLOW_PURPLE},
    "NEUTRAL": {"label": "NEUTRAL", "badge": theme.BADGE_NEUTRAL},
}

WALL_DYNAMICS_MAP = {
    "REINFORCED_WALL": {"label": "SIEGE", "badge": theme.BADGE_HOLLOW_AMBER},
    "REINFORCED_SUPPORT": {"label": "SIEGE", "badge": theme.BADGE_HOLLOW_AMBER},
    "RETREATING_RESISTANCE": {"label": "RETREAT", "badge": theme.BADGE_HOLLOW_AMBER},
    # Default fallback
    "STABLE": {"label": "STABLE", "badge": theme.BADGE_NEUTRAL},
}

VANNA_STATE_MAP = {
    "CMPRS": {"label": "CMPRS", "badge": theme.BADGE_HOLLOW_CYAN},
    "GRIND_STABLE": {"label": "CMPRS", "badge": theme.BADGE_HOLLOW_CYAN},
    "DANGER": {"label": "DANGER", "badge": theme.BADGE_RED},
    "DANGER_ZONE": {"label": "DANGER", "badge": theme.BADGE_RED},
    "FLIP": {"label": "FLIP", "badge": theme.BADGE_PURPLE},
    "VANNA_FLIP": {"label": "FLIP", "badge": theme.BADGE_PURPLE},
    # Default fallback
    "NEUTRAL": {"label": "NEUTRAL", "badge": theme.BADGE_NEUTRAL},
}
