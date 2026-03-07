"""Skew Dynamics submodule — Configuration and Thresholds.
"""

# Regimes mapping
SKEW_STATES = {
    "SPECULATIVE": {
        "label": "SPECULATIVE",
        "color_class": "text-accent-red", # Asian: Red = Speculative/Bullish
        "border_class": "border-accent-red/40",
        "bg_class": "bg-accent-red/5",
        "shadow_class": "shadow-[0_0_8px_rgba(255,77,79,0.15)]",
        "badge": "badge-red"
    },
    "DEFENSIVE": {
        "label": "DEFENSIVE",
        "color_class": "text-accent-green", # Asian: Green = Defensive/Bearish
        "border_class": "border-accent-green/40",
        "bg_class": "bg-accent-green/5",
        "shadow_class": "shadow-[0_0_8px_rgba(0,230,118,0.15)]",
        "badge": "badge-green"
    },
    "NEUTRAL": {
        "label": "NEUTRAL",
        "color_class": "text-text-primary",
        "border_class": "border-bg-border",
        "bg_class": "bg-bg-card",
        "shadow_class": "shadow-none",
        "badge": "badge-neutral"
    }
}
