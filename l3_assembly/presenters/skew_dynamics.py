"""l3_assembly.presenters.skew_dynamics — SkewDynamicsPresenterV2.

Pass-through adapter. The skew_dynamics presenter output remains a
dict for now (full typing deferred to Phase 2.7). This adapter ensures
a consistent interface with the other V2 presenters.
"""

from __future__ import annotations

import logging
from typing import Any


class SkewDynamicsPresenterV2:
    """Skew dynamics presenter adapter (dict pass-through)."""

    @classmethod
    def build(cls, skew_data: dict[str, Any]) -> dict[str, Any]:
        """Return skew dynamics dict (pass-through for backward compat)."""
        skew_data = skew_data if isinstance(skew_data, dict) else {}
        skew_val = cls._safe_float(skew_data.get("skew_value", 0.0))
        state = str(skew_data.get("skew_state", "NEUTRAL")).strip().upper() or "NEUTRAL"

        try:
            from l3_assembly.presenters.ui.skew_dynamics.presenter import SkewDynamicsPresenter
            rendered = SkewDynamicsPresenter.build(skew_val=skew_val, state=state)
            if isinstance(rendered, dict) and rendered:
                return rendered
            return cls._neutral_state(skew_val)
        except Exception as exc:
            logging.getLogger(__name__).warning("SkewDynamics fallback triggered: %s", exc)
            return cls._neutral_state(skew_val)

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            v = float(value)
            if v == v and abs(v) != float("inf"):
                return v
        except (TypeError, ValueError):
            pass
        return default

    @staticmethod
    def _neutral_state(skew_val: float = 0.0) -> dict[str, Any]:
        return {
            "value": f"{skew_val:.2f}",
            "state_label": "NEUTRAL",
            "color_class": "text-text-primary",
            "border_class": "border-bg-border",
            "bg_class": "bg-bg-card",
            "shadow_class": "shadow-none",
            "badge": "badge-neutral",
        }
