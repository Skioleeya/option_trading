"""DepthProfile submodule — Presenter.

Converts raw per-strike GEX into structured rows for dumb DOM rendering.
All colors reference this submodule's own palette.
"""

from typing import Any
from app.ui.depth_profile import mappings, thresholds


class DepthProfilePresenter:

    @classmethod
    def build(
        cls,
        per_strike_gex: list[dict[str, Any]],
        spot: float | None,
        flip_level: float | None,
    ) -> list[dict[str, Any]]:
        """Convert per-strike GEX snapshot to frontend-ready row list."""
        if not per_strike_gex:
            return []

        max_abs_gex = max(
            (max(abs(s.get("call_gex", 0)), abs(s.get("put_gex", 0))) for s in per_strike_gex),
            default=0.0,
        )
        if max_abs_gex == 0:
            return []

        rows = []
        for s in per_strike_gex:
            strike   = s.get("strike", 0.0)
            call_gex = s.get("call_gex", 0.0)
            put_gex  = s.get("put_gex",  0.0)

            is_spot = spot       is not None and abs(strike - spot)       < thresholds.STRIKE_PROXIMITY_THRESHOLD
            is_flip = flip_level is not None and abs(strike - flip_level) < thresholds.STRIKE_PROXIMITY_THRESHOLD

            is_dominant_put  = abs(put_gex)  > abs(call_gex) and abs(put_gex)  > max_abs_gex * thresholds.GEX_DOMINANCE_RATIO
            is_dominant_call = abs(call_gex) > abs(put_gex)  and abs(call_gex) > max_abs_gex * thresholds.GEX_DOMINANCE_RATIO

            if is_spot:
                strike_color = mappings.STRIKE_SPOT_COLOR
            elif is_flip:
                strike_color = mappings.STRIKE_FLIP_COLOR
            else:
                strike_color = mappings.STRIKE_DEFAULT_COLOR

            rows.append({
                "strike":             strike,
                "put_pct":            abs(put_gex)  / max_abs_gex,
                "call_pct":           abs(call_gex) / max_abs_gex,
                "put_color":          mappings.PUT_BAR_COLOR,
                "call_color":         mappings.CALL_BAR_COLOR,
                "put_label_color":    mappings.PUT_LABEL_COLOR,
                "call_label_color":   mappings.CALL_LABEL_COLOR,
                "spot_tag_classes":   mappings.SPOT_TAG_CLASSES,
                "flip_tag_classes":   mappings.FLIP_TAG_CLASSES,
                "is_dominant_put":    is_dominant_put,
                "is_dominant_call":   is_dominant_call,
                "is_spot":            is_spot,
                "is_flip":            is_flip,
                "strike_color":       strike_color,
            })

        return rows
