"""MicroStats submodule — UI mappings.

Maps Agent business state strings → frontend label + CSS badge token.
All theme tokens are imported from the global theme.py (single source of CSS truth).
"""

from app.ui import theme

# --- NET GEX ---
GEX_REGIME_MAP = {
    "SUPER_PIN":    {"label": "SUPER PIN", "badge": theme.BADGE_AMBER},
    "DAMPING":      {"label": "DAMPING",   "badge": theme.BADGE_GREEN},
    "ACCELERATION": {"label": "VOLATILE",  "badge": theme.BADGE_HOLLOW_PURPLE},
    "NEUTRAL":      {"label": "NEUTRAL",   "badge": theme.BADGE_NEUTRAL},
}

# --- WALL DYN ---
WALL_DYNAMICS_MAP = {
    "REINFORCED_WALL":       {"label": "SIEGE",   "badge": theme.BADGE_HOLLOW_AMBER},
    "REINFORCED_SUPPORT":    {"label": "SIEGE",   "badge": theme.BADGE_HOLLOW_AMBER},
    "RETREATING_RESISTANCE": {"label": "RETREAT", "badge": theme.BADGE_HOLLOW_AMBER},
    "STABLE":                {"label": "STABLE",  "badge": theme.BADGE_NEUTRAL},
}

# --- VANNA ---
VANNA_STATE_MAP = {
    "CMPRS":       {"label": "CMPRS",  "badge": theme.BADGE_HOLLOW_CYAN},
    "GRIND_STABLE":{"label": "CMPRS",  "badge": theme.BADGE_HOLLOW_CYAN},
    "DANGER":      {"label": "DANGER", "badge": theme.BADGE_RED},
    "DANGER_ZONE": {"label": "DANGER", "badge": theme.BADGE_RED},
    "FLIP":        {"label": "FLIP",   "badge": theme.BADGE_PURPLE},
    "VANNA_FLIP":  {"label": "FLIP",   "badge": theme.BADGE_PURPLE},
    "NORMAL":      {"label": "NORMAL", "badge": theme.BADGE_NEUTRAL},
    "NEUTRAL":     {"label": "NEUTRAL","badge": theme.BADGE_NEUTRAL},
}
