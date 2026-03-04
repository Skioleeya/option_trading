"""l3_assembly.presenters.skew_dynamics — SkewDynamicsPresenterV2.

Pass-through adapter. The skew_dynamics presenter output remains a
dict for now (full typing deferred to Phase 2.7). This adapter ensures
a consistent interface with the other V2 presenters.
"""

from __future__ import annotations

from typing import Any


class SkewDynamicsPresenterV2:
    """Skew dynamics presenter adapter (dict pass-through)."""

    @classmethod
    def build(cls, skew_data: dict[str, Any]) -> dict[str, Any]:
        """Return skew dynamics dict (pass-through for backward compat)."""
        try:
            from l3_assembly.presenters.ui.skew_dynamics.presenter import SkewDynamicsPresenter
            skew_val = float(skew_data.get("skew_value", 0.0))
            state = str(skew_data.get("skew_state", "NEUTRAL"))
            return SkewDynamicsPresenter.build(skew_val=skew_val, state=state) or {}
        except (ImportError, Exception) as e:
            import logging
            logging.getLogger(__name__).warning(f"SkewDynamics fallback triggered: {e}")
            return dict(skew_data) if skew_data else {}
