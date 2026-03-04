"""Tactical Triad submodule — Mappings.

Translations of raw Greek values (VRP, S-VOL, Charm) into frontend Badge/Style properties.
Retrieved from Phase 18 offense logic audit.
"""

from typing import Any
from shared.config import settings

# =============================================================================
# VRP (Variance Risk Premium)
# =============================================================================
VRP_LABELS = {
    "BARGAIN": "BULL",
    "CHEAP": "BUY",
    "FAIR": "FAIR",
    "EXPENSIVE": "SELL",
    "TRAP": "BEAR"
}

def get_vrp_style(vrp: float | None, premium_state: str | None) -> dict[str, Any]:
    """Map VRP value and state to glowing style."""
    if vrp is None:
        return {
            "value": "—",
            "state_label": "VRP",
            "color_class": "text-text-secondary",
            "border_class": "border-bg-border",
            "bg_class": "bg-[#1e1e1e]",
            "shadow_class": "shadow-none",
            "animation": ""
        }

    # Format Value
    val_str = f"+{vrp:.1f}%" if vrp > 0 else f"{vrp:.1f}%"
    
    # State label mapping
    label = VRP_LABELS.get(premium_state, "VRP") if premium_state else "VRP"

    # Color resolution using config thresholds
    # Example logic: trap_threshold (7.0), expensive (3.5), cheap (-1.5)
    
    if vrp < (settings.vrp_cheap_threshold * 3): # Deep bargain (Bullish)
        return {
            "value": val_str,
            "state_label": label,
            "color_class": "text-accent-red", # Asian: Red = Bullish
            "border_class": "border-accent-red/40",
            "bg_class": "bg-accent-red/5",
            "shadow_class": "shadow-[0_0_8px_rgba(255,77,79,0.15)]",
            "animation": "animate-pulse"
        }
    elif vrp < settings.vrp_cheap_threshold: # Cheap (Bullish)
        return {
            "value": val_str,
            "state_label": label,
            "color_class": "text-accent-red/80",
            "border_class": "border-accent-red/20",
            "bg_class": "bg-accent-red/5",
            "shadow_class": "shadow-none",
            "animation": ""
        }
    elif vrp > settings.vrp_trap_threshold: # Trap/Extreme Expensive (Bearish)
        return {
            "value": val_str,
            "state_label": label,
            "color_class": "text-accent-green", # Asian: Green = Bearish
            "border_class": "border-accent-green/40",
            "bg_class": "bg-accent-green/5",
            "shadow_class": "shadow-[0_0_8px_rgba(0,230,118,0.15)]",
            "animation": "animate-pulse"
        }
    elif vrp > settings.vrp_expensive_threshold: # Expensive (Bearish)
        return {
            "value": val_str,
            "state_label": label,
            "color_class": "text-accent-green/80",
            "border_class": "border-accent-green/20",
            "bg_class": "bg-accent-green/5",
            "shadow_class": "shadow-none",
            "animation": ""
        }
    else:
        return {
            "value": val_str,
            "state_label": label,
            "color_class": "text-text-primary",
            "border_class": "border-bg-border",
            "bg_class": "bg-[#1e1e1e]",
            "shadow_class": "shadow-none",
            "animation": ""
        }

# =============================================================================
# CHARM (Delta Decay)
# =============================================================================
def get_charm_style(net_charm: float | None, is_pre_close: bool = False) -> dict[str, Any]:
    if net_charm is None:
        return {
            "value": "—",
            "state_label": "STABLE",
            "color_class": "text-text-secondary",
            "border_class": "border-bg-border",
            "bg_class": "bg-[#1e1e1e]",
            "shadow_class": "shadow-none",
            "multiplier": None
        }

    val_str = f"+{net_charm:.1f}" if net_charm > 0 else f"{net_charm:.1f}"
    effective_charm = net_charm * 8.0 if is_pre_close else net_charm
    
    if effective_charm > settings.charm_terminal_threshold:
        return {
            "value": val_str,
            "state_label": "RISING",
            "color_class": "text-accent-red", # Asian: Red = Rising/Bullish
            "border_class": "border-accent-red/40",
            "bg_class": "bg-accent-red/5",
            "shadow_class": "shadow-[0_0_8px_rgba(255,77,79,0.15)]",
            "multiplier": "8x" if is_pre_close else None
        }
    elif effective_charm < -settings.charm_terminal_threshold:
        return {
            "value": val_str,
            "state_label": "DECAYING",
            "color_class": "text-accent-green", # Asian: Green = Decaying/Bearish
            "border_class": "border-accent-green/40",
            "bg_class": "bg-accent-green/5",
            "shadow_class": "shadow-[0_0_8px_rgba(0,230,118,0.15)]",
            "multiplier": "8x" if is_pre_close else None
        }
    else:
        return {
            "value": val_str,
            "state_label": "STABLE",
            "color_class": "text-text-primary",
            "border_class": "border-bg-border",
            "bg_class": "bg-[#1e1e1e]",
            "shadow_class": "shadow-none",
            "multiplier": "8x" if is_pre_close else None
        }

# =============================================================================
# S-VOL (Spot-Vol Correlation)
# =============================================================================
SVOL_LABELS = {
    "DANGER_ZONE": "TOXIC",
    "GRIND_STABLE": "GRIND",
    "VANNA_FLIP": "FLIP",
    "NORMAL": "STBL",
}

def get_svol_style(correlation: float | None, state: str | None) -> dict[str, Any]:
    if correlation is None or state is None:
        return {
            "value": "—",
            "state_label": "S-VOL",
            "color_class": "text-text-secondary",
            "border_class": "border-bg-border",
            "bg_class": "bg-[#1e1e1e]",
            "shadow_class": "shadow-none",
            "animation": ""
        }

    val_str = f"{correlation:.2f}"
    label = SVOL_LABELS.get(state, "STBL")

    if state == "DANGER_ZONE":
        return {
            "value": val_str,
            "state_label": label,
            "color_class": "text-accent-red",  # Asian: Rapid price action upward -> Danger Zone -> Red
            "border_class": "border-accent-red/40",
            "bg_class": "bg-accent-red/5",
            "shadow_class": "shadow-[0_0_8px_rgba(255,77,79,0.15)]",
            "animation": "animate-pulse"
        }
    elif state == "GRIND_STABLE":
        return {
            "value": val_str,
            "state_label": label,
            "color_class": "text-[#22d3ee]",    # Asian: Slow grind -> Cyan/Blue
            "border_class": "border-[#22d3ee]/40",
            "bg_class": "bg-[#22d3ee]/5",
            "shadow_class": "shadow-[0_0_8px_rgba(34,211,238,0.15)]",
            "animation": ""
        }
    elif state == "VANNA_FLIP":
        return {
            "value": val_str,
            "state_label": label,
            "color_class": "text-accent-amber",
            "border_class": "border-accent-amber/40",
            "bg_class": "bg-accent-amber/5",
            "shadow_class": "shadow-[0_0_8px_rgba(255,193,7,0.15)]",
            "animation": ""
        }
    else:
        return {
            "value": val_str,
            "state_label": label,
            "color_class": "text-text-primary",
            "border_class": "border-bg-border",
            "bg_class": "bg-[#1e1e1e]",
            "shadow_class": "shadow-none",
            "animation": ""
        }
