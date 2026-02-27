"""Presenter for the DepthProfile frontend component."""

from typing import Any
from app.ui import theme
from app.config import thresholds

class DepthProfilePresenter:
    """Format business data into DepthProfile UI state."""

    @classmethod
    def build(
        cls, 
        per_strike_gex: list[dict[str, Any]], 
        spot: float | None, 
        flip_level: float | None
    ) -> list[dict[str, Any]]:
        """Calculates frontend color, percentage, and styling bindings for Depth Profile.
        
        Args:
            per_strike_gex: List of gex profile dicts from Agent B1.
            spot: Current SPY spot price.
            flip_level: The gamma flip level.
            
        Returns:
            List of augmented dictionaries ready for dumb DOM rendering.
        """
        if not per_strike_gex:
            return []

        # Find maximum absolute GEX to normalize widths (0 to 1.0)
        max_abs_gex = 0.0
        for s in per_strike_gex:
            max_abs_gex = max(max_abs_gex, abs(s.get("call_gex", 0)), abs(s.get("put_gex", 0)))

        rows = []
        for s in per_strike_gex:
            strike = s.get("strike", 0.0)
            call_gex = s.get("call_gex", 0.0)
            put_gex = s.get("put_gex", 0.0)

            is_spot = spot is not None and abs(strike - spot) < thresholds.STRIKE_PROXIMITY_THRESHOLD
            is_flip = flip_level is not None and abs(strike - flip_level) < thresholds.STRIKE_PROXIMITY_THRESHOLD

            # Dominance logic
            is_dominant_put = abs(put_gex) > abs(call_gex) and abs(put_gex) > (max_abs_gex * thresholds.GEX_DOMINANCE_RATIO)
            is_dominant_call = abs(call_gex) > abs(put_gex) and abs(call_gex) > (max_abs_gex * thresholds.GEX_DOMINANCE_RATIO)

            # Center text styling
            strike_color = theme.TEXT_SECONDARY
            if is_spot:
                strike_color = f"{theme.ACCENT_AMBER} font-bold"
            elif is_flip:
                strike_color = theme.ACCENT_PURPLE

            rows.append({
                "strike": strike,
                "put_pct": abs(put_gex) / max_abs_gex if max_abs_gex > 0 else 0.0,
                "call_pct": abs(call_gex) / max_abs_gex if max_abs_gex > 0 else 0.0,
                "put_color": f"bg-{theme.MARKET_DOWN}",
                "call_color": f"bg-{theme.MARKET_UP}",
                "is_dominant_put": is_dominant_put,
                "is_dominant_call": is_dominant_call,
                "is_spot": is_spot,
                "is_flip": is_flip,
                "strike_color": strike_color
            })

        return rows
