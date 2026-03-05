"""MTF Flow submodule — Presenter v2.0 (VSRSD Academic Upgrade).

Signal source: MTFIVEngine (rolling ATM IV Z-Score per timeframe).

Color convention (亚洲龙风格：红涨绿跌):
    BREAKOUT / DRIFT_UP → BULLISH → Red
    STRESS   / DRIFT_DN → BEARISH → Green
    NOISE / UNAVAILABLE → NEUTRAL → Gray

Intensity tiers (by Z-Score magnitude):
    strength > 0.8  → Strong (EXTREME)   — pulse animation
    strength 0.4–0.8 → Moderate
    strength < 0.4  → Weak — muted opacity
"""

from __future__ import annotations

from typing import Any

# ── Color palette (亚洲风格) ───────────────────────────────────────────────────
_DIRECTION_DOT = {
    "BULLISH": {
        "dot_color": "bg-accent-red",
        "text_color": "text-accent-red",
        "shadow": "shadow-[0_0_8px_rgba(255,77,79,0.5)]",
        "border": "border-accent-red/30",
    },
    "BEARISH": {
        "dot_color": "bg-accent-green",
        "text_color": "text-accent-green",
        "shadow": "shadow-[0_0_8px_rgba(0,214,143,0.5)]",
        "border": "border-accent-green/30",
    },
    "NEUTRAL": {
        "dot_color": "bg-zinc-600",
        "text_color": "text-text-secondary",
        "shadow": "shadow-none",
        "border": "border-bg-border",
    },
}

_STRENGTH_ANIMATION = {
    "EXTREME":  "animate-pulse",
    "MODERATE": "",
    "WEAK":     "opacity-50",
}


def _strength_tier(s: float) -> str:
    if s >= 0.8:
        return "EXTREME"
    if s >= 0.4:
        return "MODERATE"
    return "WEAK"


def _format_tf_state(tf_data: dict[str, Any]) -> dict[str, Any]:
    """Convert a single-TF VSRSD result into a UI state block."""
    direction = tf_data.get("direction", "NEUTRAL")
    regime    = tf_data.get("regime", "NOISE")
    z         = tf_data.get("z", 0.0)
    strength  = tf_data.get("strength", 0.0)
    tier      = _strength_tier(strength)

    palette   = _DIRECTION_DOT.get(direction, _DIRECTION_DOT["NEUTRAL"])
    animation = _STRENGTH_ANIMATION[tier]

    # Regime label for tooltip / debug
    regime_short = {
        "BREAKOUT":     "BRK↑",
        "STRESS":       "STR↓",
        "DRIFT_UP":     "DFT↑",
        "DRIFT_DN":     "DFT↓",
        "NOISE":        "NOISE",
        "UNAVAILABLE":  "WARM",
    }.get(regime, regime)

    return {
        "direction":   direction,
        "regime":      regime,
        "regime_label": regime_short,
        "z":           round(z, 2),
        "strength":    round(strength, 2),
        "tier":        tier,
        "dot_color":   palette["dot_color"],
        "text_color":  palette["text_color"],
        "shadow":      f"{palette['shadow']} {animation}".strip(),
        "border":      palette["border"],
        "animate":     animation,
    }


class MTFFlowPresenter:
    """Transform MTFIVEngine output → frontend-ready UI payload."""

    @classmethod
    def build(cls, mtf_consensus: dict[str, Any]) -> dict[str, Any]:
        """Build the MTF Flow UI state.

        Accepts both legacy format (timeframe keys = state strings) and
        the new VSRSD format (timeframe keys = {regime, z, strength, direction}).
        """
        timeframes = mtf_consensus.get("timeframes", {})

        def _resolve(tf_key: str) -> dict[str, Any]:
            raw = timeframes.get(tf_key, {})
            # Legacy: if value is a plain string (old IV velocity state)
            if isinstance(raw, str):
                direction = _legacy_direction(raw)
                return _format_tf_state({"direction": direction, "z": 0.0,
                                          "strength": 0.3, "regime": raw})
            return _format_tf_state(raw)

        m1  = _resolve("1m")
        m5  = _resolve("5m")
        m15 = _resolve("15m")

        consensus = mtf_consensus.get("consensus", "NEUTRAL")
        strength  = mtf_consensus.get("strength", 0.0)
        alignment = mtf_consensus.get("alignment", 0.0)

        # Overall alignment is used in the header badge
        align_label = "ALIGNED" if alignment >= 0.67 else ("SPLIT" if alignment >= 0.34 else "DIVERGE")
        
        if align_label == "ALIGNED":
            if consensus == "BULLISH":
                align_color = "text-accent-red"
            elif consensus == "BEARISH":
                align_color = "text-accent-green"
            else:
                align_color = "text-text-secondary"
        elif align_label == "SPLIT":
            align_color = "text-accent-amber"
        else:
            align_color = "text-text-secondary"

        return {
            "m1":           m1,
            "m5":           m5,
            "m15":          m15,
            "consensus":    consensus,
            "strength":     round(strength, 3),
            "alignment":    round(alignment, 3),
            "align_label":  align_label,
            "align_color":  align_color,
        }


# ──────────────────────────────────────────────────────────────────────────────
def _legacy_direction(state: str) -> str:
    """Map old IV velocity state strings to direction for backward compat."""
    bullish = {"PAID_MOVE", "ORGANIC_GRIND", "HOLLOW_RISE",
               "HOLLOW_DROP", "VOL_EXPANSION", "BREAKOUT", "DRIFT_UP"}
    bearish = {"PAID_DROP", "STRESS", "DRIFT_DN"}
    if state in bullish:
        return "BULLISH"
    if state in bearish:
        return "BEARISH"
    return "NEUTRAL"
